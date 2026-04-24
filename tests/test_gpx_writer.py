"""Tests for GPX generation."""

from datetime import UTC, datetime
from pathlib import Path

import gpxpy
import pytest

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.routing import Point
from hsl_kaupunkipyora_exporter.stations import Station
from hsl_kaupunkipyora_exporter.writer import GPXWriter


def _sample_ride() -> Ride:
    return Ride(
        departure_station="Kaivopuisto",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="Hakaniemi",
        return_time=datetime(2024, 6, 1, 14, 45),
    )


DEP = Station(name="Kaivopuisto", lat=60.1575, lon=24.9502)
RET = Station(name="Hakaniemi", lat=60.1790, lon=24.9508)

EXPECTED_POINT_COUNT = 2
ROUTE_POINT_COUNT = 3
MIDPOINT_MINUTE = 37
MIDPOINT_LAT = 60.15


@pytest.fixture
def gpx_writer(tmp_path: Path) -> GPXWriter:
    return GPXWriter(tmp_path)


def test_gpx_has_two_points(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET)
    points = gpx.tracks[0].segments[0].points
    assert len(points) == EXPECTED_POINT_COUNT


def test_gpx_coordinates(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET)
    pts = gpx.tracks[0].segments[0].points
    assert pts[0].latitude == pytest.approx(DEP.lat)
    assert pts[0].longitude == pytest.approx(DEP.lon)
    assert pts[1].latitude == pytest.approx(RET.lat)
    assert pts[1].longitude == pytest.approx(RET.lon)


def test_gpx_timestamps_are_utc(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET)
    pts = gpx.tracks[0].segments[0].points
    assert pts[0].time is not None
    assert pts[0].time.tzinfo == UTC


def test_gpx_track_type_is_cycling(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET)
    assert gpx.tracks[0].type == "cycling"


def test_gpx_xml_is_valid(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET)
    xml = gpx.to_xml()
    parsed = gpxpy.parse(xml)
    assert len(parsed.tracks) == 1


def test_write_gpx_creates_file(gpx_writer: GPXWriter) -> None:
    path = gpx_writer.write(_sample_ride(), DEP, RET)
    assert path.exists()
    assert path.suffix == ".gpx"
    content = path.read_text(encoding="utf-8")
    assert "<trk>" in content


def test_gpx_with_route_points(gpx_writer: GPXWriter) -> None:
    # 3 points: A, middle, B
    route = [Point(60.1, 24.9), Point(MIDPOINT_LAT, 24.95), Point(60.2, 25.0)]
    ride = _sample_ride()
    # Ride is 15 mins (14:30 to 14:45)
    gpx = gpx_writer._build_gpx(ride, DEP, RET, route_points=route)
    pts = gpx.tracks[0].segments[0].points

    assert len(pts) == ROUTE_POINT_COUNT
    # Middle point should have timestamp halfway (14:37:30)
    assert pts[1].time.minute == MIDPOINT_MINUTE
    assert pts[1].latitude == pytest.approx(MIDPOINT_LAT)


def test_gpx_summary_only(gpx_writer: GPXWriter) -> None:
    gpx = gpx_writer._build_gpx(_sample_ride(), DEP, RET, include_points=False)
    # Track exists but has no segments
    assert len(gpx.tracks[0].segments) == 0


def test_build_returns_str_without_output_dir() -> None:
    """The public build() method works without a filesystem destination."""
    writer = GPXWriter()
    xml = writer.build(_sample_ride(), DEP, RET)
    assert isinstance(xml, str)
    assert "<trk>" in xml


def test_write_without_output_dir_raises() -> None:
    writer = GPXWriter()
    ride = _sample_ride()
    with pytest.raises(ValueError, match="output_dir"):
        writer.write(ride, DEP, RET)


def test_filename_for_uses_extension() -> None:
    name = GPXWriter().filename_for(_sample_ride())
    assert name.endswith(".gpx")


def test_gpx_timestamps_converted_from_helsinki_summer(gpx_writer: GPXWriter) -> None:
    """Helsinki summer time (EEST, UTC+3) is correctly converted to UTC."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 6, 1, 14, 30),  # noqa: DTZ001
        return_station="B",
        return_time=datetime(2024, 6, 1, 14, 45),  # noqa: DTZ001
    )
    gpx = gpx_writer._build_gpx(ride, DEP, RET)
    pts = gpx.tracks[0].segments[0].points
    assert pts[0].time == datetime(2024, 6, 1, 11, 30, tzinfo=UTC)
    assert pts[1].time == datetime(2024, 6, 1, 11, 45, tzinfo=UTC)


def test_gpx_timestamps_converted_from_helsinki_winter(gpx_writer: GPXWriter) -> None:
    """Helsinki winter time (EET, UTC+2) is correctly converted to UTC."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 1, 15, 10, 0),  # noqa: DTZ001
        return_station="B",
        return_time=datetime(2024, 1, 15, 10, 20),  # noqa: DTZ001
    )
    gpx = gpx_writer._build_gpx(ride, DEP, RET)
    pts = gpx.tracks[0].segments[0].points
    assert pts[0].time == datetime(2024, 1, 15, 8, 0, tzinfo=UTC)
    assert pts[1].time == datetime(2024, 1, 15, 8, 20, tzinfo=UTC)


def test_gpx_timestamps_dst_fall_back(gpx_writer: GPXWriter) -> None:
    """Ride spanning the DST fall-back boundary (EEST→EET) on 27 Oct 2024."""
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 10, 27, 3, 30),  # noqa: DTZ001
        return_station="B",
        return_time=datetime(2024, 10, 27, 4, 30),  # noqa: DTZ001
    )
    gpx = gpx_writer._build_gpx(ride, DEP, RET)
    pts = gpx.tracks[0].segments[0].points
    # 03:30 EEST = 00:30 UTC; 04:30 is after fall-back so EET (UTC+2) = 02:30 UTC
    assert pts[0].time == datetime(2024, 10, 27, 0, 30, tzinfo=UTC)
    assert pts[1].time == datetime(2024, 10, 27, 2, 30, tzinfo=UTC)
