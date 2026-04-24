"""Shared export orchestration for CLI and web adapters."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Literal

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.routing import fetch_route
from hsl_kaupunkipyora_exporter.stations import StationLookup
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter


@dataclass(frozen=True, slots=True)
class ExportEvent:
    """An event emitted during the export pipeline."""

    message: str
    level: str = "info"


@dataclass(slots=True)
class ExportResult:
    """Tallies and output files produced by :func:`export_rides`."""

    written: int = 0
    skipped: int = 0
    files: list[tuple[str, str]] = field(default_factory=list)


def export_rides(  # noqa: PLR0913
    rides: Iterable[Ride],
    lookup: StationLookup,
    writer: BaseRideWriter,
    *,
    path_mode: Literal["summary", "linear", "routed"] = "summary",
    api_key: str | None = None,
    on_event: Callable[[ExportEvent], None] | None = None,
) -> ExportResult:
    """Iterate *rides*, resolve stations, optionally route, and export.

    Args:
        rides: Parsed rides to export.
        lookup: Station-name → coordinates resolver.
        writer: The ride writer (GPX or TCX).  When its ``output_dir`` is set
            files are also written to disk.
        path_mode: ``"summary"`` (no track points), ``"linear"`` (straight
            line) or ``"routed"`` (Digitransit cycling route).
        api_key: Digitransit API key, required when *path_mode* is
            ``"routed"``.
        on_event: Optional callback invoked for every notable event (logging,
            progress reporting, etc.).

    Returns:
        An :class:`ExportResult` with tallies and ``(filename, xml)`` pairs.
    """
    include_points = path_mode != "summary"
    use_route = path_mode == "routed"

    def _emit(message: str, level: str = "info") -> None:
        if on_event is not None:
            on_event(ExportEvent(message=message, level=level))

    result = ExportResult()

    for ride in rides:
        dep = lookup.find(ride.departure_station)
        ret = lookup.find(ride.return_station)

        if dep is None:
            _emit(
                f"Could not find coordinates for '{ride.departure_station}' "
                "– skipping ride.",
                "warning",
            )
            result.skipped += 1
            continue
        if ret is None:
            _emit(
                f"Could not find coordinates for '{ride.return_station}' "
                "– skipping ride.",
                "warning",
            )
            result.skipped += 1
            continue

        route_points = None
        if use_route:
            _emit(
                f"Fetching route for {ride.departure_station} → "
                f"{ride.return_station} …",
                "debug",
            )
            try:
                route_points = fetch_route(
                    dep.lat, dep.lon, ret.lat, ret.lon, api_key=api_key
                )
            except Exception as exc:
                _emit(f"Routing request failed: {exc}", "warning")

            if not route_points:
                _emit(
                    f"Could not fetch route for '{ride}' "
                    "– falling back to straight line.",
                    "warning",
                )

        xml = writer.build(
            ride, dep, ret, route_points=route_points, include_points=include_points
        )
        filename = writer.filename_for(ride)

        # Write to disk when the writer has an output directory.
        if writer.output_dir is not None:
            path = writer.output_dir / filename
            path.write_text(xml, encoding="utf-8")
            _emit(f"Wrote {path}")
        else:
            _emit(f"Generated {filename}")

        result.files.append((filename, xml))
        result.written += 1

    _emit(
        f"Done – {result.written} {writer.EXTENSION.upper()} file(s) written, "
        f"{result.skipped} skipped.",
    )
    return result
