"""Entry point for the browser build, invoked from JavaScript via Pyodide.

The real parsing and export logic lives in the ``hsl_kaupunkipyora_exporter``
package, which is installed into the Pyodide runtime from a locally-built
wheel. This module is a thin adapter between the JS host (upload callbacks,
station data, options) and the CLI package (parser + writers).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.routing import fetch_route
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


def _log(msg: str, level: str = "info") -> None:
    """Forward a log message to the JS-side logger."""
    if js is not None:
        js.globalThis._pyLog(msg, level)


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

    results: list[tuple[str, str]] = []
    skipped = 0

    for ride in rides:
        dep = lookup.find(ride.departure_station)
        ret = lookup.find(ride.return_station)

        if dep is None:
            _log(
                f"Could not find coordinates for '{ride.departure_station}' – skipping.",
                "warn",
            )
            skipped += 1
            continue
        if ret is None:
            _log(
                f"Could not find coordinates for '{ride.return_station}' – skipping.",
                "warn",
            )
            skipped += 1
            continue

        route_points = None
        if use_route:
            _log(
                f"Fetching route for {ride.departure_station} → {ride.return_station} …"
            )
            try:
                route_points = fetch_route(
                    dep.lat, dep.lon, ret.lat, ret.lon, api_key=api_key
                )
            except Exception as e:
                _log(f"Routing logic failed with error: {e}", "error")

            if not route_points:
                _log(
                    f"Could not fetch route for '{ride}' – falling back to straight line.",
                    "warn",
                )

        xml = writer.build(
            ride,
            dep,
            ret,
            route_points=route_points,
            include_points=include_points,
        )
        fname = writer.filename_for(ride)
        results.append((fname, xml))
        _log(f"Generated {fname}")

    _log(
        f"Done – {len(results)} {fmt.upper()} file(s) written, {skipped} skipped.",
    )
    return results
