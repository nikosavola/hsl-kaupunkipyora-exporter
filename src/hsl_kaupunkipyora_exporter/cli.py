"""Command-line interface for the HSL City Bike ride history exporter."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from hsl_kaupunkipyora_exporter.exporter import ExportEvent, export_rides
from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.stations import StationLookup, get_stations
from hsl_kaupunkipyora_exporter.writer import GPXWriter, TCXWriter


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="hsl-kaupunkipyora-exporter",
        description=(
            "Parse an HSL City Bike ride history file (HTML or plain text) "
            "and export each ride as a Strava-compatible GPX or TCX file."
        ),
    )
    parser.add_argument(
        "file",
        help="Path to the saved ride-history file (HTML or .txt).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="tcx_output",
        help="Directory to write files into (default: ./tcx_output).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["gpx", "tcx"],
        default="tcx",
        help="Export format (default: tcx). TCX is recommended for accurate distance.",
    )

    path_group = parser.add_mutually_exclusive_group()
    path_group.add_argument(
        "--linear",
        action="store_true",
        help="Include a straight-line path between stations (default: summary only).",
    )
    path_group.add_argument(
        "--use-route",
        action="store_true",
        help="Use suggested HSL cycling route (requires API key).",
    )

    parser.add_argument(
        "--api-key",
        help="Digitransit API key (alternative to DIGITRANSIT_API_KEY env var).",
    )
    parser.add_argument(
        "--refresh-stations",
        action="store_true",
        help="Force re-download of the bike station list from Digitransit.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    return parser


_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def _log_event(event: ExportEvent) -> None:
    """Forward an :class:`ExportEvent` to the :mod:`logging` system."""
    logging.log(_LOG_LEVELS.get(event.level, logging.INFO), "%s", event.message)


def main(argv: list[str] | None = None) -> None:
    """Entry point invoked by the console script."""
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Parse rides
    input_path = args.file
    if not Path(input_path).is_file():
        logging.error("File not found: %s", input_path)
        sys.exit(1)

    rides = RideHistoryParser().parse_file(input_path)
    if not rides:
        logging.warning("No rides found in %s", input_path)
        sys.exit(0)
    logging.info("Found %d ride(s).", len(rides))

    # Fetch station coordinates
    if args.use_route and not (args.api_key or os.environ.get("DIGITRANSIT_API_KEY")):
        logging.error(
            "Digitransit API key is required when using --use-route. Provide it via --api-key or DIGITRANSIT_API_KEY environment variable."
        )
        sys.exit(1)

    try:
        stations = get_stations(refresh=args.refresh_stations, api_key=args.api_key)
    except Exception:
        logging.exception("Failed to fetch station data")
        sys.exit(1)

    lookup = StationLookup(stations)

    # Determine path mode from CLI flags
    if args.use_route:
        path_mode = "routed"
    elif args.linear:
        path_mode = "linear"
    else:
        path_mode = "summary"

    # Initialize writer based on format
    output_dir = Path(args.output_dir)
    writer = TCXWriter(output_dir) if args.format == "tcx" else GPXWriter(output_dir)

    export_rides(
        rides,
        lookup,
        writer,
        path_mode=path_mode,
        api_key=args.api_key,
        on_event=_log_event,
    )
