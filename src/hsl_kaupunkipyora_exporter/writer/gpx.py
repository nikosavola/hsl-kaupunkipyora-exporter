"""Generate Strava-compatible GPX files from parsed rides."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final, override

import gpxpy.gpx

from hsl_kaupunkipyora_exporter.writer._common import interpolate_route, ride_utc_window
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station

    from .base import _RideData

logger = logging.getLogger(__name__)

MIN_ROUTE_POINTS = 2


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

        dep_time, ret_time = ride_utc_window(ride)

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

    def build_merged(self, rides: list[_RideData]) -> str:
        """Build a single GPX string containing multiple tracks.

        Each ride becomes a separate ``<trk>`` element.

        Args:
            rides: Sequence of ride data tuples to merge.

        Returns:
            A GPX XML string with one ``<trk>`` per ride.
        """
        merged = gpxpy.gpx.GPX()
        merged.creator = "hsl-kaupunkipyora-exporter"

        for ride, dep, ret, route_pts, inc_pts in rides:
            single = self._build_gpx(ride, dep, ret, route_pts, inc_pts)
            for track in single.tracks:
                merged.tracks.append(track)

        return merged.to_xml()
