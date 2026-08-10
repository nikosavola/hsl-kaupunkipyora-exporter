"""Fetch and cache Helsinki City Bike station coordinates."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from hsl_kaupunkipyora_exporter import __version__

logger = logging.getLogger(__name__)

DIGITRANSIT_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"
USER_AGENT = f"hsl-kaupunkipyora-exporter/{__version__}"
HTTP_UNAUTHORIZED = 401

# Cache file lives next to the user's data (XDG_CACHE_HOME or ~/.cache).
_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
CACHE_PATH = _CACHE_DIR / "hsl-kaupunkipyora-exporter" / "stations.json"

_GRAPHQL_RESOURCE = resources.files("hsl_kaupunkipyora_exporter.graphql").joinpath(
    "stations.graphql"
)
GRAPHQL_QUERY = json.dumps({"query": _GRAPHQL_RESOURCE.read_text(encoding="utf-8")})


@dataclass(frozen=True, slots=True)
class Station:
    """A bike-share station with its location."""

    name: str
    lat: float
    lon: float


def fetch_stations(api_key: str | None = None) -> Generator[Station]:
    """Download the current station list from the Digitransit API."""
    api_key = api_key or os.environ.get("DIGITRANSIT_API_KEY")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["digitransit-subscription-key"] = api_key

    req = urllib.request.Request(
        DIGITRANSIT_URL,
        data=GRAPHQL_QUERY.encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == HTTP_UNAUTHORIZED:
            logger.exception(
                "Digitransit API access denied (401). Please set the DIGITRANSIT_API_KEY environment variable. You can get a free key at https://digitransit.fi/en/developers/api-registration/"
            )
        raise

    raw = body["data"]["vehicleRentalStations"]
    for s in raw:
        yield Station(name=s["name"], lat=s["lat"], lon=s["lon"])


def _save_cache(stations: list[Station]) -> None:
    """Save the station list to a local JSON cache."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations]
    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.debug("Station cache written to %s", CACHE_PATH)


def _load_cache() -> list[Station] | None:
    """Load the station list from the local JSON cache."""
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return [Station(name=s["name"], lat=s["lat"], lon=s["lon"]) for s in data]
    except (json.JSONDecodeError, KeyError):
        logger.warning("Corrupt station cache at %s – will re-download.", CACHE_PATH)
        return None


def get_stations(refresh: bool = False, api_key: str | None = None) -> list[Station]:
    """Return the station list, using a local cache when available.

    Args:
        refresh: Force a fresh download even when a cache exists.
        api_key: Digitransit API key. If not provided, uses DIGITRANSIT_API_KEY environment variable.
    """
    if not refresh:
        cached = _load_cache()
        if cached is not None:
            logger.info("Loaded %d stations from cache.", len(cached))
            return cached

    logger.info("Downloading station list from Digitransit …")
    stations = list(fetch_stations(api_key=api_key))
    _save_cache(stations)
    return stations


class StationLookup:
    """Map station names to coordinates."""

    def __init__(self, stations: Iterable[Station]) -> None:
        """Initialize the lookup table with a list of stations."""
        self._by_name: dict[str, Station] = {}
        for s in stations:
            key = self._normalise(s.name)
            self._by_name[key] = s

    @staticmethod
    def _normalise(name: str) -> str:
        """Normalise a station name for lookup."""
        return name.strip().lower()

    def find(self, name: str) -> Station | None:
        """Look up *name*.

        Returns:
            The station if found, or None.
        """
        key = self._normalise(name)
        return self._by_name.get(key)
