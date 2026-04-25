"""Shared export orchestration for CLI and web adapters."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.routing import Point, fetch_route
from hsl_kaupunkipyora_exporter.stations import Station, StationLookup
from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.writer.base import _RideData

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
    ride_data: list[_RideData] = field(default_factory=list)


def _resolve_ride_stations(
    ride: Ride, lookup: StationLookup, emit: EmitFn
) -> tuple[Station, Station] | None:
    """Resolve departure/return coordinates, emitting a skip event if either is missing."""
    dep = lookup.find(ride.departure_station)
    if dep is None:
        emit(
            f"[SKIP] {ride.departure_station} → {ride.return_station}"
            " — unknown departure station",
            "warning",
        )
        return None
    ret = lookup.find(ride.return_station)
    if ret is None:
        emit(
            f"[SKIP] {ride.departure_station} → {ride.return_station}"
            " — unknown return station",
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


def _ride_detail_str(ride: Ride) -> str:
    """Return a parenthesised summary of distance/duration, or empty string."""
    details: list[str] = []
    if ride.distance_km is not None:
        details.append(f"{ride.distance_km} km")
    if ride.duration_min is not None:
        details.append(f"{ride.duration_min} min")
    return f"  ({', '.join(details)})" if details else ""


def export_rides(  # noqa: PLR0913
    rides: Iterable[Ride],
    lookup: StationLookup,
    writer: BaseRideWriter,
    *,
    path_mode: Literal["summary", "linear", "routed"] = "summary",
    api_key: str | None = None,
    dry_run: bool = False,
    on_event: Callable[[ExportEvent], None] | None = None,
    collect_ride_data: bool = False,
) -> ExportResult:
    """Iterate *rides*, resolve stations, optionally route, and export.

    Args:
        rides: Parsed rides to export.
        lookup: Station-name → coordinates resolver.
        writer: The ride writer (GPX or TCX).  When its ``output_dir`` is set
            files are also written to disk.
        path_mode: ``"summary"`` (no GPS positions; TCX still includes
            Time-only trackpoints since Strava requires them), ``"linear"``
            (straight line) or ``"routed"`` (Digitransit cycling route).
        api_key: Digitransit API key, required when *path_mode* is
            ``"routed"``.
        dry_run: When ``True`` the pipeline runs in full but no files are
            written to disk, regardless of ``writer.output_dir``. Each ride
            that would be exported is reported with a ``[WOULD WRITE]``
            event instead.
        on_event: Optional callback invoked for every notable event (logging,
            progress reporting, etc.).
        collect_ride_data: When ``True``, also populate
            :attr:`ExportResult.ride_data` with the raw per-ride tuples
            needed by :meth:`BaseRideWriter.build_merged`.

    Returns:
        An :class:`ExportResult` with tallies and ``(filename, xml)`` pairs.
    """
    include_points = path_mode != "summary"
    use_route = path_mode == "routed"

    def _emit(message: str, level: str = "info") -> None:
        if on_event is not None:
            on_event(ExportEvent(message=message, level=level))

    result = ExportResult()
    seen_filenames: dict[str, int] = {}

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
        if filename in seen_filenames:
            seen_filenames[filename] += 1
            stem, _, ext = filename.rpartition(".")
            filename = f"{stem}_{seen_filenames[filename]}.{ext}"
        else:
            seen_filenames[filename] = 1

        if collect_ride_data:
            result.ride_data.append((ride, dep, ret, route_points, include_points))

        if dry_run:
            _emit(f"[WOULD WRITE] {filename}{_ride_detail_str(ride)}")
        elif writer.output_dir is not None:
            # Write to disk when the writer has an output directory.
            writer.output_dir.mkdir(parents=True, exist_ok=True)
            path = writer.output_dir / filename
            path.write_text(xml, encoding="utf-8")
            _emit(f"Wrote {path}")
        else:
            _emit(f"Generated {filename}")

        result.files.append((filename, xml))
        result.written += 1

    ext = writer.EXTENSION.upper()
    if dry_run:
        _emit(
            f"Dry run – {result.written} {ext} file(s) would be written, "
            f"{result.skipped} skipped.",
        )
    else:
        _emit(
            f"Done – {result.written} {ext} file(s) written, {result.skipped} skipped."
        )
    return result
