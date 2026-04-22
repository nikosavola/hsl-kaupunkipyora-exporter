"""Generate Strava-compatible GPX files from parsed rides."""

from __future__ import annotations

import logging
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING, override

import gpxpy.gpx
from haversine import haversine

from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station

logger = logging.getLogger(__name__)

MIN_ROUTE_POINTS = 2


class GPXWriter(BaseRideWriter):
    """Writer for GPX format."""

    @override
    def write(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> Path:
        """Export a single ride as a GPX file."""
        gpx = self._build_gpx(
            ride, departure_coords, return_coords, route_points, include_points
        )
        path = self.output_dir / self._safe_filename(ride, "gpx")
        path.write_text(gpx.to_xml(), encoding="utf-8")
        return path

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

        dep_time = ride.departure_time.replace(tzinfo=UTC)
        ret_time = ride.return_time.replace(tzinfo=UTC)

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
            points = [(p.lat, p.lon) for p in route_points]
            if len(points) < MIN_ROUTE_POINTS:
                # Fallback to straight line
                return self._build_gpx(
                    ride, departure_coords, return_coords, None, include_points=True
                )

            distances = [0.0]
            total_dist = 0.0
            for i in range(1, len(points)):
                d = haversine(points[i - 1], points[i])
                total_dist += d
                distances.append(total_dist)

            duration_delta = ret_time - dep_time
            for i, (lat, lon) in enumerate(points):
                frac = (
                    distances[i] / total_dist
                    if total_dist > 0
                    else (i / (len(points) - 1))
                )
                pt_time = dep_time + (duration_delta * frac)
                segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon, time=pt_time)
                )

        return gpx
