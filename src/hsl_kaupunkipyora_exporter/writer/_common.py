"""Shared route-interpolation logic for GPX and TCX writers."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from haversine import haversine  # type: ignore[import-untyped]

from hsl_kaupunkipyora_exporter.routing import Point

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride

logger = logging.getLogger(__name__)

_HELSINKI = ZoneInfo("Europe/Helsinki")


def to_utc(naive_local: datetime) -> datetime:
    """Convert a naive Helsinki-local datetime to an aware UTC datetime.

    Returns:
        The equivalent aware datetime in UTC.

    Raises:
        ValueError: If *naive_local* already carries a ``tzinfo``.
    """
    if naive_local.tzinfo is not None:
        msg = f"Expected a naive datetime, got one with tzinfo: {naive_local!r}"
        raise ValueError(msg)
    return naive_local.replace(tzinfo=_HELSINKI).astimezone(UTC)


def ride_utc_window(ride: Ride) -> tuple[datetime, datetime]:
    """Return the ride's (departure, return) instants converted to UTC.

    The departure time is converted directly. The return time is derived
    from the departure time plus ``ride.duration_min`` when that field is
    available, rather than converted independently — this avoids the
    duration silently gaining or losing an hour when the ride falls in the
    repeated (fall-back) or skipped (spring-forward) local hour, where the
    departure and return instants can each resolve to a different UTC
    offset.  When ``duration_min`` is unavailable, both instants are
    converted independently and a warning is logged if that produces a
    non-positive duration.
    """
    dep_utc = to_utc(ride.departure_time)
    if ride.duration_min is not None:
        return dep_utc, dep_utc + timedelta(minutes=ride.duration_min)

    ret_utc = to_utc(ride.return_time)
    if ret_utc <= dep_utc:
        logger.warning(
            "Ride %s → %s has a non-positive duration after UTC conversion "
            "(%s to %s); the local times likely fall across a DST transition "
            "and no reported duration was available to disambiguate.",
            ride.departure_station,
            ride.return_station,
            dep_utc,
            ret_utc,
        )
    return dep_utc, ret_utc


@dataclass(frozen=True, slots=True)
class InterpolatedPoint:
    """A route point with interpolated timestamp and cumulative distance."""

    lat: float
    lon: float
    time: datetime
    distance_m: float


def interpolate_route(
    points: Sequence[Point],
    dep_time: datetime,
    ret_time: datetime,
    target_distance_km: float | None = None,
) -> list[InterpolatedPoint]:
    """Compute cumulative distances and interpolated timestamps for route points.

    Args:
        points: Ordered geographic points along the route.
        dep_time: Departure timestamp (assigned to the first point).
        ret_time: Return timestamp (assigned to the last point).
        target_distance_km: If provided, scale cumulative distances so the
            total equals this value (in km).  ``None`` keeps the raw
            haversine distances.

    Returns:
        A list of ``InterpolatedPoint``s with interpolated times and
        cumulative distances in **metres**.
    """
    coords = [(p.lat, p.lon) for p in points]

    # Build cumulative haversine distances (km).
    cum_dists = [0.0]
    for i in range(1, len(coords)):
        cum_dists.append(cum_dists[-1] + haversine(coords[i - 1], coords[i]))

    total_dist = cum_dists[-1]
    target_km = target_distance_km if target_distance_km is not None else total_dist
    scale = (target_km / total_dist) if total_dist > 0 else 1.0

    duration = ret_time - dep_time

    result: list[InterpolatedPoint] = []
    for i, (lat, lon) in enumerate(coords):
        frac = (
            cum_dists[i] / total_dist
            if total_dist > 0
            else (i / max(len(coords) - 1, 1))
        )
        result.append(
            InterpolatedPoint(
                lat=lat,
                lon=lon,
                time=dep_time + (duration * frac),
                distance_m=cum_dists[i] * scale * 1000.0,
            )
        )

    return result
