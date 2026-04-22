"""Tests for TCX generation."""

import xml.etree.ElementTree as ET  # noqa: S405
from datetime import datetime
from pathlib import Path

import pytest

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.stations import Station
from hsl_kaupunkipyora_exporter.writer import TCXWriter

EXPECTED_DISTANCE_M = "2900.0"
EXPECTED_DURATION_S = "900.0"


def _sample_ride() -> Ride:
    return Ride(
        departure_station="Kaivopuisto",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="Hakaniemi",
        return_time=datetime(2024, 6, 1, 14, 45),
        distance_km=2.9,
    )


DEP = Station(name="Kaivopuisto", lat=60.1575, lon=24.9502)
RET = Station(name="Hakaniemi", lat=60.1790, lon=24.9508)


@pytest.fixture
def tcx_writer(tmp_path: Path) -> TCXWriter:
    return TCXWriter(tmp_path)


def test_tcx_has_correct_distance(tcx_writer: TCXWriter) -> None:
    tcx_str = tcx_writer._build_tcx(_sample_ride(), DEP, RET)
    root = ET.fromstring(tcx_str)  # noqa: S314
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}

    dist = root.find(".//tcx:DistanceMeters", ns)
    assert dist is not None
    assert dist.text == EXPECTED_DISTANCE_M

    total_time = root.find(".//tcx:TotalTimeSeconds", ns)
    assert total_time is not None
    assert total_time.text == EXPECTED_DURATION_S  # 15 mins


def test_write_tcx_creates_file(tcx_writer: TCXWriter) -> None:
    path = tcx_writer.write(_sample_ride(), DEP, RET)
    assert path.exists()
    assert path.suffix == ".tcx"
    assert "TrainingCenterDatabase" in path.read_text()


def test_tcx_summary_only(tcx_writer: TCXWriter) -> None:
    tcx_str = tcx_writer._build_tcx(_sample_ride(), DEP, RET, include_points=False)
    root = ET.fromstring(tcx_str)  # noqa: S314
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}

    # Track should not be present
    track = root.find(".//tcx:Track", ns)
    assert track is None

    # Summary data still present
    dist = root.find(".//tcx:DistanceMeters", ns)
    assert dist is not None
    assert dist.text == EXPECTED_DISTANCE_M
