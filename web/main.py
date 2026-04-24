"""Entry point for the browser build, invoked from JavaScript via Pyodide.

The real parsing and export logic lives in the ``hsl_kaupunkipyora_exporter``
package, which is installed into the Pyodide runtime from a locally-built
wheel. This module is a thin adapter between the JS host (upload callbacks,
station data, options) and the CLI package (parser + writers).
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import TYPE_CHECKING

from hsl_kaupunkipyora_exporter.exporter import ExportEvent, export_rides
from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.stations import Station, StationLookup
from hsl_kaupunkipyora_exporter.writer import GPXWriter, TCXWriter

try:
    import js  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - only importable under Pyodide
    js = None

try:
    import pyodide_http

    pyodide_http.patch_all()
except ImportError:
    pass


if TYPE_CHECKING:
    from hsl_kaupunkipyora_exporter.writer.base import BaseRideWriter

_JS_LEVELS = {"warning": "warn"}


def _log(msg: str, level: str = "info") -> None:
    """Forward a log message to the JS-side logger."""
    if js is not None:
        js.globalThis._pyLog(msg, level)


def _log_event(event: ExportEvent) -> None:
    """Forward an :class:`ExportEvent` to the JS logger."""
    _log(event.message, _JS_LEVELS.get(event.level, event.level))


def _writer_for(fmt: str) -> BaseRideWriter:
    """Return a writer instance for the requested output format."""
    if fmt == "tcx":
        return TCXWriter()
    if fmt == "gpx":
        return GPXWriter()
    msg = f"Unsupported format: {fmt!r}"
    raise ValueError(msg)


def process_rides(  # noqa: PLR0913, PLR0917
    content: str,
    stations_json: str,
    fmt: str,
    include_points: bool,
    use_route: bool = False,
    api_key: str | None = None,
) -> list[tuple[str, str]]:
    """Parse ride content and return a list of ``(filename, xml)`` tuples.

    Args:
        content: Raw ride-history content (HTML or plain text).
        stations_json: JSON-encoded list of ``{name, lat, lon}`` objects as
            returned by the Digitransit API.
        fmt: Export format — ``"tcx"`` or ``"gpx"``.
        include_points: Whether to include a straight-line path between the
            departure and return stations.
        use_route: Whether to fetch a suggested cycling route from Digitransit.
        api_key: Optional Digitransit API key for route fetching.

    Returns:
        A list of ``(filename, xml_content)`` tuples, one per exported ride.
    """
    rides = RideHistoryParser().parse_content(content)
    if not rides:
        _log("No rides found in input.", "warn")
        return []
    _log(f"Found {len(rides)} ride(s).")

    raw = json.loads(stations_json) if stations_json else []
    stations = [Station(name=s["name"], lat=s["lat"], lon=s["lon"]) for s in raw]
    lookup = StationLookup(stations)
    _log(f"Station lookup initialized with {len(stations)} station(s).")

    writer = _writer_for(fmt)

    # Derive path_mode from the boolean flags passed by the JS host.
    if use_route:
        path_mode = "routed"
    elif include_points:
        path_mode = "linear"
    else:
        path_mode = "summary"

    result = export_rides(
        rides,
        lookup,
        writer,
        path_mode=path_mode,
        api_key=api_key,
        on_event=_log_event,
    )
    return result.files


def create_zip(files_json: str) -> bytes:
    """Create an in-memory ZIP archive from exported files.

    Args:
        files_json: JSON-encoded list of ``[filename, xml_content]`` pairs.

    Returns:
        Raw bytes of a ZIP archive containing the given files.
    """
    pairs = json.loads(files_json)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in pairs:
            zf.writestr(fname, content)
    return buf.getvalue()
