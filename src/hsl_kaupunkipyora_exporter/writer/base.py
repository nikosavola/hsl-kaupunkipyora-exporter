"""Abstract base class for ride history exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.parser import Ride
    from hsl_kaupunkipyora_exporter.routing import Point
    from hsl_kaupunkipyora_exporter.stations import Station

#: Tuple of ``(ride, departure_coords, return_coords, route_points, include_points)``
#: used by :meth:`BaseRideWriter.build_merged`.
_RideData = tuple[
    "Ride",
    "Station",
    "Station",
    "list[Point] | None",
    bool,
]


class BaseRideWriter(ABC):
    """Abstract base class for ride writers (GPX, TCX, etc.)."""

    #: File extension used by the writer, without the leading dot.
    EXTENSION: str = ""

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize the ride writer.

        Args:
            output_dir: Directory to write files into. When ``None`` the writer
                can still build in-memory XML via :meth:`build`, but :meth:`write`
                will raise.
        """
        self.output_dir: Path | None = output_dir

    @abstractmethod
    def build(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> str:
        """Build an in-memory XML string for a single ride."""

    def write(
        self,
        ride: Ride,
        departure_coords: Station,
        return_coords: Station,
        route_points: list[Point] | None = None,
        include_points: bool = True,
    ) -> Path:
        """Export a single ride to a file and return the path."""
        if self.output_dir is None:
            msg = (
                f"{type(self).__name__} was initialised without an output_dir; "
                "use build() for in-memory XML or pass output_dir to write to disk."
            )
            raise ValueError(msg)
        xml = self.build(
            ride, departure_coords, return_coords, route_points, include_points
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / self._safe_filename(ride, self.EXTENSION)
        path.write_text(xml, encoding="utf-8")
        return path

    @staticmethod
    def _safe_filename(ride: Ride, extension: str) -> str:
        """Return a filesystem-safe filename for a ride."""
        ts = ride.departure_time.strftime("%Y%m%d_%H%M")
        dep = ride.departure_station.replace("/", "-").replace(" ", "_")
        ret = ride.return_station.replace("/", "-").replace(" ", "_")
        return f"{ts}_{dep}_to_{ret}.{extension}"

    def filename_for(self, ride: Ride) -> str:
        """Return the filename this writer would use for the given ride."""
        return self._safe_filename(ride, self.EXTENSION)
