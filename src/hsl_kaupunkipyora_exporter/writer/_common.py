"""Shared route-interpolation logic for GPX and TCX writers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from haversine import haversine  # type: ignore[import-untyped]

from hsl_kaupunkipyora_exporter.routing import Point


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
        frac = cum_dists[i] / total_dist if total_dist > 0 else (i / max(len(coords) - 1, 1))
        result.append(
            InterpolatedPoint(
                lat=lat,
                lon=lon,
                time=dep_time + (duration * frac),
                distance_m=cum_dists[i] * scale * 1000.0,
            )
        )

    return result
