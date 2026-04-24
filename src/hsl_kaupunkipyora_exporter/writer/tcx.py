"""Generate Strava-compatible TCX files with explicit distance data."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET  # noqa: S405
from datetime import datetime
from typing import TYPE_CHECKING, final, override

from hsl_kaupunkipyora_exporter.writer._common import interpolate_route, ride_utc_window
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station

logger = logging.getLogger(__name__)

MIN_ROUTE_POINTS = 2


@final
class TCXWriter(BaseRideWriter):
    """Writer for TCX format."""

    EXTENSION = "tcx"

    @override
    def build(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> str:
        """Build a TCX XML string for a single ride."""
        return self._build_tcx(
            ride, departure_coords, return_coords, route_points, include_points
        )

    @staticmethod
    def _add_trackpoint(
        track: ET.Element,
        time: datetime,
        lat: float,
        lon: float,
        dist_meters: float,
    ) -> None:
        """Add a trackpoint to the TCX track."""
        tp = ET.SubElement(track, "Trackpoint")
        ET.SubElement(tp, "Time").text = time.isoformat()
        pos = ET.SubElement(tp, "Position")
        ET.SubElement(pos, "LatitudeDegrees").text = str(lat)
        ET.SubElement(pos, "LongitudeDegrees").text = str(lon)
        ET.SubElement(tp, "DistanceMeters").text = f"{dist_meters:.1f}"

    def _build_tcx(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> str:
        """Build a TCX string for a single ride."""
        root = ET.Element(
            "TrainingCenterDatabase",
            {
                "xmlns": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd",
            },
        )

        activities = ET.SubElement(root, "Activities")
        activity = ET.SubElement(activities, "Activity", {"Sport": "Cycling"})

        dep_time, ret_time = ride_utc_window(ride)
        id_val = dep_time.isoformat()
        ET.SubElement(activity, "Id").text = id_val

        total_seconds = (ret_time - dep_time).total_seconds()
        dist_meters = (
            (ride.distance_km * 1000.0) if ride.distance_km is not None else 0.0
        )

        lap = ET.SubElement(activity, "Lap", {"StartTime": id_val})
        ET.SubElement(lap, "TotalTimeSeconds").text = f"{total_seconds:.1f}"
        ET.SubElement(lap, "DistanceMeters").text = f"{dist_meters:.1f}"
        ET.SubElement(lap, "Intensity").text = "Active"
        ET.SubElement(lap, "TriggerMethod").text = "Manual"

        if include_points:
            track = ET.SubElement(lap, "Track")

            if not route_points or len(route_points) < MIN_ROUTE_POINTS:
                self._add_trackpoint(
                    track, dep_time, departure_coords.lat, departure_coords.lon, 0.0
                )
                self._add_trackpoint(
                    track, ret_time, return_coords.lat, return_coords.lon, dist_meters
                )
            else:
                self._add_route_points(
                    track, dep_time, ret_time, ride.distance_km, route_points
                )

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _add_route_points(
        self,
        track: ET.Element,
        dep_time: datetime,
        ret_time: datetime,
        ride_dist_km: float | None,
        route_points: list[Point],
    ) -> None:
        """Add route points to the TCX track, scaling distance and time."""
        for ip in interpolate_route(route_points, dep_time, ret_time, ride_dist_km):
            self._add_trackpoint(track, ip.time, ip.lat, ip.lon, ip.distance_m)
