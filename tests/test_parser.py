"""Tests for the ride history parser."""

from datetime import datetime

import pytest

from hsl_kaupunkipyora_exporter.parser import Ride, RideHistoryParser

SAMPLE_TEXT = """\
Ride 1
Duration: 00:15
Details
Departure station: Kaivopuisto
Departure time: 01.06.2024 14:30
Return station: Hakaniemi
Return time: 01.06.2024 14:45
Vikailmoitus

Ride 2
Duration: 00:22
Details
Departure station: Pasilan asema
Departure time: 02.06.2024 09:00
Return station: Sörnäisten metroasema
Return time: 02.06.2024 09:22
Vikailmoitus
"""

SAMPLE_TEXT_FI = """\
Matka 1
Kesto: 00:15
Tiedot
Lähtöasema: Kaivopuisto
Lähtöaika: 01.06.2024 14:30
Palautusasema: Hakaniemi
Palautusaika: 01.06.2024 14:45
Vikailmoitus
"""

SAMPLE_TEXT_WEB = """\
Departure station: Venttiilikuja
Departure time: 21.4.2026 20:06
Return station: Kansallismuseo
city-bikes/return-date: 21.4.2026 20:15
"""


EXPECTED_RIDE_COUNT = 2
SINGLE_RIDE_COUNT = 1
JOURNEY_DISTANCE_KM = 2.4
JOURNEY_DURATION_MIN = 12


@pytest.fixture
def parser() -> RideHistoryParser:
    return RideHistoryParser()


def test_parse_text_extracts_two_rides(parser: RideHistoryParser) -> None:
    rides = parser.parse_text(SAMPLE_TEXT)
    assert len(rides) == EXPECTED_RIDE_COUNT


def test_parse_text_fields_correct(parser: RideHistoryParser) -> None:
    rides = parser.parse_text(SAMPLE_TEXT)
    r = rides[0]
    assert r.departure_station == "Kaivopuisto"
    assert r.departure_time == datetime(2024, 6, 1, 14, 30)
    assert r.return_station == "Hakaniemi"
    assert r.return_time == datetime(2024, 6, 1, 14, 45)


def test_parse_text_second_ride(parser: RideHistoryParser) -> None:
    rides = parser.parse_text(SAMPLE_TEXT)
    r = rides[1]
    assert r.departure_station == "Pasilan asema"
    assert r.return_station == "Sörnäisten metroasema"
    assert r.return_time == datetime(2024, 6, 2, 9, 22)


def test_parse_text_finnish(parser: RideHistoryParser) -> None:
    rides = parser.parse_text(SAMPLE_TEXT_FI)
    assert len(rides) == SINGLE_RIDE_COUNT
    r = rides[0]
    assert r.departure_station == "Kaivopuisto"
    assert r.return_station == "Hakaniemi"


def test_parse_text_web_variant(parser: RideHistoryParser) -> None:
    rides = parser.parse_text(SAMPLE_TEXT_WEB)
    assert len(rides) == SINGLE_RIDE_COUNT
    r = rides[0]
    assert r.departure_station == "Venttiilikuja"
    assert r.return_time == datetime(2026, 4, 21, 20, 15)


def test_parse_text_european_decimal(parser: RideHistoryParser) -> None:
    text = """\
Departure station: A
Departure time: 01.01.2026 10:00
Return station: B
Return time: 01.01.2026 10:15
Journey length and duration: 2,4 km, 12 min
"""
    rides = parser.parse_text(text)
    assert len(rides) == SINGLE_RIDE_COUNT
    assert rides[0].distance_km == JOURNEY_DISTANCE_KM
    assert rides[0].duration_min == JOURNEY_DURATION_MIN


def test_parse_text_empty(parser: RideHistoryParser) -> None:
    assert parser.parse_text("") == []
    assert parser.parse_text("no rides here\njust random text\n") == []


def test_parse_html_wraps_text(parser: RideHistoryParser) -> None:
    """Ensure HTML parsing works by extracting text and reusing the text parser."""
    html = (
        f"<html><body><div>{SAMPLE_TEXT.replace(chr(10), '<br/>')}</div></body></html>"
    )
    rides = parser.parse_html(html)
    assert len(rides) == EXPECTED_RIDE_COUNT
    assert rides[0].departure_station == "Kaivopuisto"


def test_parse_content_detects_text(parser: RideHistoryParser) -> None:
    rides = parser.parse_content(SAMPLE_TEXT)
    assert len(rides) == EXPECTED_RIDE_COUNT


def test_parse_content_detects_html(parser: RideHistoryParser) -> None:
    html = (
        f"<html><body><div>{SAMPLE_TEXT.replace(chr(10), '<br/>')}</div></body></html>"
    )
    rides = parser.parse_content(html)
    assert len(rides) == EXPECTED_RIDE_COUNT
    assert rides[0].departure_station == "Kaivopuisto"


def test_ride_str() -> None:
    r = Ride(
        departure_station="A",
        departure_time=datetime(2024, 6, 1, 10, 0),
        return_station="B",
        return_time=datetime(2024, 6, 1, 10, 15),
    )
    s = str(r)
    assert "A" in s
    assert "B" in s
