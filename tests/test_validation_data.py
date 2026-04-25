"""Validation tests using real HSL data files."""

import json
from pathlib import Path

from hsl_kaupunkipyora_exporter.parser import RideHistoryParser
from hsl_kaupunkipyora_exporter.stations import Station, StationLookup

EXPECTED_MATKAHISTORIA_RIDES = 7


def test_parse_matkahistoria_txt() -> None:
    """Validate parsing of Finnish ride history text file."""
    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria.txt")
    # All 7 rides are now captured.
    # Chronological sorting puts the oldest ride first.
    assert len(rides) == EXPECTED_MATKAHISTORIA_RIDES
    assert rides[0].departure_station == "Apollonkatu"
    assert rides[-1].departure_station == "Venttiilikuja"


def test_parse_matkahistoria_en_txt() -> None:
    """Validate parsing of English ride history text file."""
    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria_en.txt")
    assert len(rides) == EXPECTED_MATKAHISTORIA_RIDES
    assert rides[0].departure_station == "Apollonkatu"
    assert rides[-1].departure_station == "Venttiilikuja"


def test_parse_matkahistoria_se_txt() -> None:
    """Validate parsing of Swedish ride history text file."""
    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria_se.txt")
    assert len(rides) == EXPECTED_MATKAHISTORIA_RIDES
    assert rides[0].departure_station == "Apollonkatu"
    assert rides[-1].departure_station == "Venttiilikuja"


def test_stations_fixture_covers_matkahistoria() -> None:
    """The web-smoke fixture must resolve every sample-history station.

    Otherwise the smoke test would silently skip rides without failing —
    the exact drift scenario this test exists to catch.
    """
    fixture_path = Path("tests/test_data/stations_fixture.json")
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    lookup = StationLookup(Station(**s) for s in raw)

    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria.txt")
    missing = {
        name
        for ride in rides
        for name in (ride.departure_station, ride.return_station)
        if lookup.find(name) is None
    }
    assert not missing, f"stations_fixture.json is missing: {sorted(missing)}"


def test_parse_matkahistoria_html() -> None:
    """Validate parsing of the HTML ride history file."""
    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria.html")
    expected_rides = 7
    assert len(rides) == expected_rides
    # Oldest ride in HTML is Asema 1 (2024-04-10 19:18)
    assert rides[0].departure_station == "Asema 1"
    # Newest ride in HTML is Lähtöasema A (2024-04-21 20:06)
    assert rides[-1].departure_station == "Lähtöasema A"
