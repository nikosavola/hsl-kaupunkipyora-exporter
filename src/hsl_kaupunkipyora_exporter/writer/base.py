"""Abstract base class for ride history exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station


class BaseRideWriter(ABC):
    """Abstract base class for ride writers (GPX, TCX, etc.)."""

    def __init__(self, output_dir: Path):
        """Initialize the ride writer with an output directory."""
        self.output_dir: Path = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def write(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> Path:
        """Export a single ride to a file and return the path."""
        pass

    @staticmethod
    def _safe_filename(ride: Ride, extension: str) -> str:
        """Return a filesystem-safe filename for a ride."""
        ts = ride.departure_time.strftime("%Y%m%d_%H%M")
        dep = ride.departure_station.replace("/", "-").replace(" ", "_")
        ret = ride.return_station.replace("/", "-").replace(" ", "_")
        return f"{ts}_{dep}_to_{ret}.{extension}"
