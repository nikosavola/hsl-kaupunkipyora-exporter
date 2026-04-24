"""Tests for station lookup and the Digitransit station-list fetch."""

import json
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
