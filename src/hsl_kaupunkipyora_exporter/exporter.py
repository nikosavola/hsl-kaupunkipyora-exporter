"""Shared export orchestration for CLI and web adapters."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Literal

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.routing import Point, fetch_route
from hsl_kaupunkipyora_exporter.stations import Station, StationLookup
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

EmitFn = Callable[[str, str], None]


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


def _resolve_ride_stations(
    ride: Ride, lookup: StationLookup, emit: EmitFn
) -> tuple[Station, Station] | None:
    """Resolve departure/return coordinates, emitting a skip event if either is missing."""
    dep = lookup.find(ride.departure_station)
    if dep is None:
        emit(
            f"Could not find coordinates for '{ride.departure_station}' "
            "– skipping ride.",
            "warning",
        )
        return None
    ret = lookup.find(ride.return_station)
    if ret is None:
        emit(
            f"Could not find coordinates for '{ride.return_station}' – skipping ride.",
            "warning",
        )
        return None
    return dep, ret


def _fetch_ride_route(
    ride: Ride,
    dep: Station,
    ret: Station,
    api_key: str | None,
    emit: EmitFn,
) -> list[Point] | None:
    """Fetch a cycling route between two stations, emitting a fallback warning on failure."""
    emit(
        f"Fetching route for {ride.departure_station} → {ride.return_station} …",
        "debug",
    )
    try:
        route_points = fetch_route(dep.lat, dep.lon, ret.lat, ret.lon, api_key=api_key)
    except Exception as exc:
        emit(f"Routing request failed: {exc}", "warning")
        route_points = None

    if not route_points:
        emit(
            f"Could not fetch route for '{ride}' – falling back to straight line.",
            "warning",
        )
    return route_points


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
        resolved = _resolve_ride_stations(ride, lookup, _emit)
        if resolved is None:
            result.skipped += 1
            continue
        dep, ret = resolved

        route_points = None
        if use_route:
            route_points = _fetch_ride_route(ride, dep, ret, api_key, _emit)

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
