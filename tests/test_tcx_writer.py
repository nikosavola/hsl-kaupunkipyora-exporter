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


def test_build_returns_str_without_output_dir() -> None:
    """The public build() method works without a filesystem destination."""
    writer = TCXWriter()
    xml = writer.build(_sample_ride(), DEP, RET)
    assert isinstance(xml, str)
    assert "TrainingCenterDatabase" in xml


def test_write_without_output_dir_raises() -> None:
    writer = TCXWriter()
    ride = _sample_ride()
    with pytest.raises(ValueError, match="output_dir"):
        writer.write(ride, DEP, RET)


def test_filename_for_uses_extension() -> None:
    name = TCXWriter().filename_for(_sample_ride())
    assert name.endswith(".tcx")


def test_tcx_timestamps_converted_from_helsinki_summer(tcx_writer: TCXWriter) -> None:
    """Helsinki summer time (EEST, UTC+3) is correctly converted to UTC."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="B",
        return_time=datetime(2024, 6, 1, 14, 45),
        distance_km=2.0,
    )
    tcx_str = tcx_writer._build_tcx(ride, DEP, RET)
    root = ET.fromstring(tcx_str)  # noqa: S314
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    id_el = root.find(".//tcx:Id", ns)
    assert id_el is not None
    assert id_el.text is not None
    assert id_el.text.startswith("2024-06-01T11:30:00")
    time_els = root.findall(".//tcx:Time", ns)
    assert time_els[0].text is not None
    assert time_els[0].text.startswith("2024-06-01T11:30:00")
    assert time_els[1].text is not None
    assert time_els[1].text.startswith("2024-06-01T11:45:00")


def test_tcx_timestamps_converted_from_helsinki_winter(tcx_writer: TCXWriter) -> None:
    """Helsinki winter time (EET, UTC+2) is correctly converted to UTC."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 1, 15, 10, 0),
        return_station="B",
        return_time=datetime(2024, 1, 15, 10, 20),
        distance_km=1.5,
    )
    tcx_str = tcx_writer._build_tcx(ride, DEP, RET)
    root = ET.fromstring(tcx_str)  # noqa: S314
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    id_el = root.find(".//tcx:Id", ns)
    assert id_el is not None
    assert id_el.text is not None
    assert id_el.text.startswith("2024-01-15T08:00:00")


def test_tcx_timestamps_dst_fall_back(tcx_writer: TCXWriter) -> None:
    """Ride spanning the DST fall-back boundary (EEST→EET) on 27 Oct 2024."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 10, 27, 3, 30),
        return_station="B",
        return_time=datetime(2024, 10, 27, 4, 30),
        distance_km=3.0,
    )
    tcx_str = tcx_writer._build_tcx(ride, DEP, RET)
    root = ET.fromstring(tcx_str)  # noqa: S314
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    # 03:30 EEST = 00:30 UTC
    id_el = root.find(".//tcx:Id", ns)
    assert id_el is not None
    assert id_el.text is not None
    assert id_el.text.startswith("2024-10-27T00:30:00")
    time_els = root.findall(".//tcx:Time", ns)
    # 04:30 is after fall-back so EET (UTC+2) = 02:30 UTC
    assert time_els[1].text is not None
    assert time_els[1].text.startswith("2024-10-27T02:30:00")
