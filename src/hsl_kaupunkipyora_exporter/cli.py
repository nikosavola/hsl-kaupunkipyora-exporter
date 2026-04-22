"""Command-line interface for the HSL City Bike ride history exporter."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.routing import fetch_route
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
            "Digitransit API key is required when using --use-route. "
            "Provide it via --api-key or DIGITRANSIT_API_KEY environment variable."
        )
        sys.exit(1)

    try:
        stations = get_stations(refresh=args.refresh_stations, api_key=args.api_key)
    except Exception:
        logging.exception("Failed to fetch station data")
        sys.exit(1)

    lookup = StationLookup(stations)

    # Generate files 
    output_dir = Path(args.output_dir)
    written = 0
    skipped = 0

    # Initialize writer based on format
    writer = TCXWriter(output_dir) if args.format == "tcx" else GPXWriter(output_dir)

    for ride in rides:
        dep = lookup.find(ride.departure_station)
        ret = lookup.find(ride.return_station)

        if dep is None:
            logging.warning(
                "Could not find coordinates for '%s' – skipping ride.",
                ride.departure_station,
            )
            skipped += 1
            continue
        if ret is None:
            logging.warning(
                "Could not find coordinates for '%s' – skipping ride.",
                ride.return_station,
            )
            skipped += 1
            continue

        route_points = None
        if args.use_route:
            logging.debug(
                "Fetching route for %s → %s",
                ride.departure_station,
                ride.return_station,
            )
            route_points = fetch_route(
                dep.lat, dep.lon, ret.lat, ret.lon, api_key=args.api_key
            )
            if not route_points:
                logging.warning(
                    "Could not fetch route for '%s' – falling back to straight line.",
                    ride,
                )

        path = writer.write(
            ride,
            dep,
            ret,
            route_points=route_points,
            include_points=(args.linear or args.use_route),
        )
        logging.info("Wrote %s", path)
        written += 1

    logging.info(
        "Done – %d %s file(s) written, %d skipped.",
        written,
        args.format.upper(),
        skipped,
    )
