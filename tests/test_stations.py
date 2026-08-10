"""Tests for station lookup and the Digitransit station-list fetch."""

import json
from unittest.mock import MagicMock, patch

import pytest

from hsl_kaupunkipyora_exporter.stations import (
    USER_AGENT,
    Station,
    StationLookup,
    fetch_stations,
)


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
