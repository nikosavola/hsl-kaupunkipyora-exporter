"""Fetch and cache Helsinki City Bike station coordinates."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
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

DEFAULT_CACHE_TTL_DAYS = 30

_GRAPHQL_RESOURCE = resources.files("hsl_kaupunkipyora_exporter.graphql").joinpath(
    "stations.graphql"
)
GRAPHQL_QUERY = json.dumps({"query": _GRAPHQL_RESOURCE.read_text(encoding="utf-8")})

_BUNDLED_RESOURCE = resources.files("hsl_kaupunkipyora_exporter.data").joinpath(
    "stations.json"
)


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
    """Save the station list to a local JSON cache with a timestamp envelope."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "stations": [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations],
    }
    CACHE_PATH.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.debug("Station cache written to %s", CACHE_PATH)


def _parse_cache_envelope(raw: dict | list) -> tuple[list[dict], datetime | None]:
    """Extract station dicts and fetch timestamp from a decoded cache file.

    Supports the legacy format (plain list without envelope).

    Returns:
        A tuple of ``(station_dicts, fetched_at)``. ``fetched_at`` is ``None``
        for the legacy format, which carries no timestamp.
    """
    if isinstance(raw, list):
        return raw, None
    return raw["stations"], datetime.fromisoformat(raw["fetched_at"])


def _is_expired(fetched_at: datetime | None, ttl_days: int | None) -> bool:
    """Return True if *fetched_at* is older than *ttl_days* (or unknown)."""
    if ttl_days is None:
        return False
    if fetched_at is None:
        return True
    return (datetime.now(UTC) - fetched_at).total_seconds() / 86400 >= ttl_days


def _load_cache(ttl_days: int | None = None) -> list[Station] | None:
    """Load the station list from the local JSON cache.

    Args:
        ttl_days: Maximum cache age in days. If None, any age is accepted.
            If the cache is older than *ttl_days* (or has no timestamp), returns None.

    Returns:
        The cached station list, or None if the cache is missing, corrupt, or expired.
    """
    if not CACHE_PATH.exists():
        return None
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        stations_data, fetched_at = _parse_cache_envelope(raw)
        if _is_expired(fetched_at, ttl_days):
            return None
        return [
            Station(name=s["name"], lat=s["lat"], lon=s["lon"]) for s in stations_data
        ]
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("Corrupt station cache at %s – will re-download.", CACHE_PATH)
        return None


def _load_bundled() -> list[Station] | None:
    """Load the station list bundled with the package as a last-resort fallback."""
    try:
        data = json.loads(_BUNDLED_RESOURCE.read_text(encoding="utf-8"))
        stations = [
            Station(name=s["name"], lat=s["lat"], lon=s["lon"])
            for s in data["stations"]
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Bundled station data is missing or corrupt.")
        return None
    fetched_at = data.get("fetched_at", "unknown")
    logger.warning(
        "Using bundled station data (fetched_at: %s). Station list may be outdated.",
        fetched_at,
    )
    return stations


def get_stations(
    refresh: bool = False,
    cache_ttl_days: int | None = None,
    api_key: str | None = None,
) -> list[Station]:
    """Return the station list, using a local cache when available.

    The cache is automatically refreshed when it is older than *cache_ttl_days*.
    If the refresh fetch itself fails (or returns an empty list), this falls
    back to the stale cache regardless of age, and only as a last resort to
    the dataset bundled with the package. If the fetch succeeds but writing
    the new cache to disk fails, the freshly fetched stations are still
    returned; only the write is logged as a warning.

    Args:
        refresh: Force a fresh download even when a valid cache exists.
        cache_ttl_days: Maximum cache age in days before an automatic refresh is
            triggered. Defaults to the ``HSL_KAUPUNKIPYORA_CACHE_TTL_DAYS``
            environment variable, or :data:`DEFAULT_CACHE_TTL_DAYS` (30) if not set.
        api_key: Digitransit API key. If not provided, uses DIGITRANSIT_API_KEY
            environment variable.

    Raises:
        OSError: If the live fetch fails and no cache or bundled fallback is
            available.
        json.JSONDecodeError: If the live fetch fails and no cache or bundled
            fallback is available.
        KeyError: If the live fetch fails and no cache or bundled fallback is
            available.
        TypeError: If the live fetch fails and no cache or bundled fallback is
            available.
        ValueError: If the live fetch fails and no cache or bundled fallback is
            available.
    """
    ttl = (
        cache_ttl_days
        if cache_ttl_days is not None
        else int(
            os.environ.get("HSL_KAUPUNKIPYORA_CACHE_TTL_DAYS", DEFAULT_CACHE_TTL_DAYS)
        )
    )

    if not refresh:
        cached = _load_cache(ttl_days=ttl)
        if cached is not None:
            logger.info("Loaded %d stations from cache.", len(cached))
            return cached

    logger.info("Downloading station list from Digitransit …")
    try:
        stations = list(fetch_stations(api_key=api_key))
        if not stations:
            msg = "Digitransit returned an empty station list"
            raise ValueError(msg)  # noqa: TRY301
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.warning("Live fetch failed – checking for a fallback station list.")
        stale = _load_cache(ttl_days=None)
        if stale is not None:
            logger.warning("Falling back to stale cache (%d stations).", len(stale))
            return stale
        bundled = _load_bundled()
        if bundled is not None:
            return bundled
        raise

    try:
        _save_cache(stations)
    except OSError:
        logger.warning(
            "Fetched %d stations but failed to write the cache to %s.",
            len(stations),
            CACHE_PATH,
        )

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
