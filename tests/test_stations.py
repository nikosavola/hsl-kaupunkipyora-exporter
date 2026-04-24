"""Tests for station lookup and the Digitransit station-list fetch."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hsl_kaupunkipyora_exporter.stations as stations_mod
from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.stations import (
    USER_AGENT,
    Station,
    StationLookup,
    _load_bundled,
    _load_cache,
    _save_cache,
    fetch_stations,
    get_stations,
)

_TEST_DATA = Path(__file__).parent / "test_data"

# Helsinki metro area, generously bounded.
_HELSINKI_LAT_RANGE = (59.9, 60.5)
_HELSINKI_LON_RANGE = (24.4, 25.3)
_MIN_BUNDLED_STATIONS = 50


def _mock_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__.return_value = resp
    return resp


@patch("hsl_kaupunkipyora_exporter.stations.urllib.request.urlopen")
def test_fetch_stations_sets_user_agent(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _mock_response({"data": {"vehicleRentalStations": []}})

    list(fetch_stations(api_key="test-key"))

    req = mock_urlopen.call_args[0][0]
    assert req.get_header("User-agent") == USER_AGENT
    assert req.get_header("Digitransit-subscription-key") == "test-key"


@pytest.fixture
def stations() -> list[Station]:
    return [
        Station(name="Kaivopuisto", lat=60.1575, lon=24.9502),
        Station(name="Hakaniemi", lat=60.1790, lon=24.9508),
        Station(name="Pasilan asema", lat=60.1985, lon=24.9331),
        Station(name="Sörnäisten metroasema", lat=60.1847, lon=24.9612),
    ]


def test_exact_match(stations: list[Station]) -> None:
    lookup = StationLookup(stations)
    s = lookup.find("Kaivopuisto")
    assert s is not None
    assert s.name == "Kaivopuisto"


def test_case_insensitive(stations: list[Station]) -> None:
    lookup = StationLookup(stations)
    s = lookup.find("kaivopuisto")
    assert s is not None
    assert s.name == "Kaivopuisto"


def test_leading_trailing_whitespace(stations: list[Station]) -> None:
    lookup = StationLookup(stations)
    s = lookup.find("  Hakaniemi  ")
    assert s is not None
    assert s.name == "Hakaniemi"


def test_no_match_returns_none(stations: list[Station]) -> None:
    lookup = StationLookup(stations)
    assert lookup.find("Nonexistent Station XYZ") is None


def test_load_bundled_returns_stations() -> None:
    result = _load_bundled()
    assert result is not None
    assert len(result) >= _MIN_BUNDLED_STATIONS
    for s in result:
        assert s.name
        assert _HELSINKI_LAT_RANGE[0] < s.lat < _HELSINKI_LAT_RANGE[1]
        assert _HELSINKI_LON_RANGE[0] < s.lon < _HELSINKI_LON_RANGE[1]


def test_load_bundled_covers_sample_ride_history() -> None:
    """Every station referenced by the sample ride histories must resolve."""
    bundled = _load_bundled()
    assert bundled is not None
    lookup = StationLookup(bundled)

    missing: set[str] = set()
    for filename in (
        "matkahistoria.txt",
        "matkahistoria_en.txt",
        "matkahistoria_se.txt",
    ):
        rides = RideHistoryParser().parse_file(str(_TEST_DATA / filename))
        for ride in rides:
            if lookup.find(ride.departure_station) is None:
                missing.add(ride.departure_station)
            if lookup.find(ride.return_station) is None:
                missing.add(ride.return_station)

    assert not missing, f"bundled stations.json is missing: {sorted(missing)}"


def test_get_stations_falls_back_to_bundled_on_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(
        stations_mod,
        "CACHE_PATH",
        tmp_path / "hsl-kaupunkipyora-exporter" / "stations.json",
    )

    def _failing_fetch(*_args, **_kwargs):
        msg = "Network error"
        raise OSError(msg)

    monkeypatch.setattr(stations_mod, "fetch_stations", _failing_fetch)

    result = get_stations(refresh=True)
    assert isinstance(result, list)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Cache TTL tests
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a temp path and patch CACHE_PATH in the stations module."""
    path = tmp_path / "stations.json"
    monkeypatch.setattr(stations_mod, "CACHE_PATH", path)
    return path


def _write_envelope(path: Path, age_days: float, station_list: list[Station]) -> None:
    """Write a cache envelope with a timestamp *age_days* days in the past."""
    fetched_at = datetime.now(UTC) - timedelta(days=age_days)
    envelope = {
        "fetched_at": fetched_at.isoformat(),
        "stations": [
            {"name": s.name, "lat": s.lat, "lon": s.lon} for s in station_list
        ],
    }
    path.write_text(json.dumps(envelope), encoding="utf-8")


def test_save_cache_writes_envelope(cache_path: Path, stations: list[Station]) -> None:
    _save_cache(stations)
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "fetched_at" in raw
    assert "stations" in raw
    assert len(raw["stations"]) == len(stations)
    # fetched_at must be a valid ISO-8601 timestamp
    datetime.fromisoformat(raw["fetched_at"])


def test_load_cache_fresh(cache_path: Path, stations: list[Station]) -> None:
    _write_envelope(cache_path, age_days=1, station_list=stations)
    result = _load_cache(ttl_days=30)
    assert result is not None
    assert [s.name for s in result] == [s.name for s in stations]


def test_load_cache_expired_returns_none(
    cache_path: Path, stations: list[Station]
) -> None:
    _write_envelope(cache_path, age_days=31, station_list=stations)
    assert _load_cache(ttl_days=30) is None


def test_load_cache_no_ttl_check(cache_path: Path, stations: list[Station]) -> None:
    _write_envelope(cache_path, age_days=365, station_list=stations)
    result = _load_cache(ttl_days=None)
    assert result is not None
    assert len(result) == len(stations)


def test_load_cache_legacy_format_with_ttl_returns_none(
    cache_path: Path, stations: list[Station]
) -> None:
    """Old plain-list cache has no timestamp so it is treated as expired."""
    data = [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations]
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    assert _load_cache(ttl_days=30) is None


def test_load_cache_legacy_format_without_ttl_loaded(
    cache_path: Path, stations: list[Station]
) -> None:
    """Old plain-list cache is still usable when TTL is not checked."""
    data = [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations]
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    result = _load_cache(ttl_days=None)
    assert result is not None
    assert len(result) == len(stations)


def test_get_stations_uses_fresh_cache(
    cache_path: Path, stations: list[Station]
) -> None:
    _write_envelope(cache_path, age_days=1, station_list=stations)
    with patch.object(stations_mod, "fetch_stations") as mock_fetch:
        result = get_stations(cache_ttl_days=30)
    mock_fetch.assert_not_called()
    assert len(result) == len(stations)


def test_get_stations_refreshes_expired_cache(
    cache_path: Path, stations: list[Station]
) -> None:
    _write_envelope(cache_path, age_days=31, station_list=stations)
    new_stations = [Station(name="Uusi asema", lat=60.2, lon=25.0)]
    with patch.object(stations_mod, "fetch_stations", return_value=iter(new_stations)):
        result = get_stations(cache_ttl_days=30)
    assert result == new_stations


def test_get_stations_fallback_to_stale_on_refresh_failure(
    cache_path: Path, stations: list[Station]
) -> None:
    _write_envelope(cache_path, age_days=31, station_list=stations)
    with patch.object(
        stations_mod, "fetch_stations", side_effect=OSError("network down")
    ):
        result = get_stations(cache_ttl_days=30)
    # Should fall back to the stale cache instead of raising
    assert len(result) == len(stations)


def test_get_stations_forced_refresh_uses_network(
    cache_path: Path, stations: list[Station]
) -> None:
    _write_envelope(cache_path, age_days=1, station_list=stations)
    new_stations = [Station(name="Uusi asema", lat=60.2, lon=25.0)]
    with patch.object(stations_mod, "fetch_stations", return_value=iter(new_stations)):
        result = get_stations(refresh=True, cache_ttl_days=30)
    assert result == new_stations


def test_get_stations_returns_fresh_data_even_if_cache_write_fails(
    cache_path: Path,
) -> None:
    """A successful fetch must not be discarded just because saving it fails."""
    new_stations = [Station(name="Uusi asema", lat=60.2, lon=25.0)]
    with (
        patch.object(stations_mod, "fetch_stations", return_value=iter(new_stations)),
        patch.object(stations_mod, "_save_cache", side_effect=OSError("disk full")),
    ):
        result = get_stations(refresh=True, cache_ttl_days=30)
    assert result == new_stations
    assert not cache_path.exists()


def test_get_stations_empty_fetch_falls_back_to_stale_cache(
    cache_path: Path, stations: list[Station]
) -> None:
    """An empty API response must not silently poison the cache for 30 days."""
    _write_envelope(cache_path, age_days=31, station_list=stations)
    with patch.object(stations_mod, "fetch_stations", return_value=iter([])):
        result = get_stations(cache_ttl_days=30)
    assert len(result) == len(stations)
    # The stale envelope on disk must not have been overwritten with "[]".
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    assert len(raw["stations"]) == len(stations)


def test_get_stations_env_var_ttl(
    cache_path: Path, stations: list[Station], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSL_KAUPUNKIPYORA_CACHE_TTL_DAYS", "7")
    _write_envelope(cache_path, age_days=8, station_list=stations)
    new_stations = [Station(name="Uusi asema", lat=60.2, lon=25.0)]
    with patch.object(stations_mod, "fetch_stations", return_value=iter(new_stations)):
        result = get_stations()  # no explicit ttl — reads env var
    assert result == new_stations
