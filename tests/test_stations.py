"""Tests for station lookup."""

import pytest

from hsl_kaupunkipyora_exporter.stations import Station, StationLookup


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
