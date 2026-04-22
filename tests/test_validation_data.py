"""Validation tests using real HSL data files."""

from hsl_kaupunkipyora_exporter.parser import RideHistoryParser

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


def test_parse_matkahistoria_html() -> None:
    """Validate parsing of the HTML ride history file."""
    rides = RideHistoryParser().parse_file("tests/test_data/matkahistoria.html")
    expected_rides = 7
    assert len(rides) == expected_rides
    # Oldest ride in HTML is Asema 1 (2024-04-10 19:18)
    assert rides[0].departure_station == "Asema 1"
    # Newest ride in HTML is Lähtöasema A (2024-04-21 20:06)
    assert rides[-1].departure_station == "Lähtöasema A"
