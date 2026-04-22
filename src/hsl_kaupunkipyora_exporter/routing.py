"""Fetch cycling routes from the Digitransit Routing API."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from importlib import resources
from itertools import starmap
from typing import NamedTuple

import polyline

logger = logging.getLogger(__name__)

DIGITRANSIT_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"

_GRAPHQL_RESOURCE = resources.files("hsl_kaupunkipyora_exporter.graphql").joinpath(
    "route.graphql"
)
ROUTING_QUERY = _GRAPHQL_RESOURCE.read_text(encoding="utf-8")


class Point(NamedTuple):
    """A geographic point with latitude and longitude."""

    lat: float
    lon: float


def fetch_route(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    api_key: str | None = None,
) -> list[Point] | None:
    """Fetch a cycling route between two points."""
    api_key = api_key or os.environ.get("DIGITRANSIT_API_KEY")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["digitransit-subscription-key"] = api_key

    variables = {
        "fromLat": from_lat,
        "fromLon": from_lon,
        "toLat": to_lat,
        "toLon": to_lon,
    }

    body = json.dumps({"query": ROUTING_QUERY, "variables": variables})

    if not DIGITRANSIT_URL.startswith(("http://", "https://")):
        msg = f"Invalid URL scheme: {DIGITRANSIT_URL}"
        raise ValueError(msg)

    req = urllib.request.Request(
        DIGITRANSIT_URL,
        data=body.encode(),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())

        itineraries = data.get("data", {}).get("plan", {}).get("itineraries", [])
        if not itineraries:
            logger.warning("No route found between coordinates.")
            return None

        legs = itineraries[0].get("legs", [])
        all_points = []
        for leg in legs:
            points_str = leg.get("legGeometry", {}).get("points", "")
            if points_str:
                decoded = polyline.decode(points_str)
                all_points.extend(starmap(Point, decoded))
    except Exception:
        logger.exception("Failed to fetch route")
        return None
    else:
        return all_points
