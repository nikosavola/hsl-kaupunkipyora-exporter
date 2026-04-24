"""Generate Strava-compatible GPX files from parsed rides."""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING, final, override
from zoneinfo import ZoneInfo

import gpxpy.gpx

from hsl_kaupunkipyora_exporter.writer._common import interpolate_route
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station

logger = logging.getLogger(__name__)

MIN_ROUTE_POINTS = 2
_HELSINKI = ZoneInfo("Europe/Helsinki")


@final
class GPXWriter(BaseRideWriter):
    """Writer for GPX format."""

    EXTENSION = "gpx"

    @override
    def build(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> str:
        """Build a GPX XML string for a single ride."""
        return self._build_gpx(
            ride, departure_coords, return_coords, route_points, include_points
        ).to_xml()

    def _build_gpx(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> gpxpy.gpx.GPX:
        """Build a GPX object for a single ride."""
        gpx = gpxpy.gpx.GPX()
        gpx.creator = "hsl-kaupunkipyora-exporter"

        track = gpxpy.gpx.GPXTrack()
        track.name = f"{ride.departure_station} → {ride.return_station}"
        track.type = "cycling"

        # Embed metadata in description
        metadata = []
        if ride.distance_km is not None:
            metadata.append(f"Reported distance: {ride.distance_km} km")
        if ride.duration_min is not None:
            metadata.append(f"Reported duration: {ride.duration_min} min")

        if metadata:
            track.description = " | ".join(metadata)

        gpx.tracks.append(track)

        if not include_points:
            return gpx

        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        dep_time = ride.departure_time.replace(tzinfo=_HELSINKI).astimezone(UTC)
        ret_time = ride.return_time.replace(tzinfo=_HELSINKI).astimezone(UTC)

        if not route_points:
            # Simple straight-line fallback
            segment.points.append(
                gpxpy.gpx.GPXTrackPoint(
                    latitude=departure_coords.lat,
                    longitude=departure_coords.lon,
                    time=dep_time,
                )
            )
            segment.points.append(
                gpxpy.gpx.GPXTrackPoint(
                    latitude=return_coords.lat,
                    longitude=return_coords.lon,
                    time=ret_time,
                )
            )
        else:
            if len(route_points) < MIN_ROUTE_POINTS:
                # Fallback to straight line
                return self._build_gpx(
                    ride, departure_coords, return_coords, None, include_points=True
                )

            for ip in interpolate_route(route_points, dep_time, ret_time):
                segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(
                        latitude=ip.lat, longitude=ip.lon, time=ip.time
                    )
                )

        return gpx
