"""Tests for --zip, --merge CLI flags and web create_zip helper."""

import io
import json
import sys
import xml.etree.ElementTree as ET  # noqa: S405
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import gpxpy

from hsl_kaupunkipyora_exporter.cli import main
from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.stations import Station
from hsl_kaupunkipyora_exporter.writer import GPXWriter, TCXWriter

# Two rides so we can test multi-ride merge / zip
MULTI_RIDE_TEXT = """\
Departure station: Kaivopuisto
Departure time: 01.06.2024 14:30
Return station: Hakaniemi
Return time: 01.06.2024 14:45

Departure station: Hakaniemi
Departure time: 02.06.2024 10:00
Return station: Kaivopuisto
Return time: 02.06.2024 10:20
"""

MOCK_STATIONS = [
    Station(name="Kaivopuisto", lat=60.1575, lon=24.9502),
    Station(name="Hakaniemi", lat=60.1790, lon=24.9508),
]

DEP = Station(name="Kaivopuisto", lat=60.1575, lon=24.9502)
RET = Station(name="Hakaniemi", lat=60.1790, lon=24.9508)

EXPECTED_MULTI_RIDE_COUNT = 2


def _sample_rides() -> list[Ride]:
    return [
        Ride(
            departure_station="Kaivopuisto",
            departure_time=datetime(2024, 6, 1, 14, 30),
            return_station="Hakaniemi",
            return_time=datetime(2024, 6, 1, 14, 45),
            distance_km=2.9,
        ),
        Ride(
            departure_station="Hakaniemi",
            departure_time=datetime(2024, 6, 2, 10, 0),
            return_station="Kaivopuisto",
            return_time=datetime(2024, 6, 2, 10, 20),
            distance_km=3.1,
        ),
    ]


# ── CLI --zip ──────────────────────────────────────────────────────────


def test_cli_zip_creates_archive(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(MULTI_RIDE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out_zip"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--zip"])

    zip_path = out_dir / "rides.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None  # no corrupt entries
        assert len(zf.namelist()) == EXPECTED_MULTI_RIDE_COUNT
        for name in zf.namelist():
            assert name.endswith(".tcx")


def test_cli_zip_with_gpx(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(MULTI_RIDE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out_zip_gpx"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--format", "gpx", "--zip"])

    zip_path = out_dir / "rides.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None
        for name in zf.namelist():
            assert name.endswith(".gpx")


# ── CLI --merge ────────────────────────────────────────────────────────


def test_cli_merge_gpx(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(MULTI_RIDE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out_merge_gpx"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--format", "gpx", "--merge"])

    merged = out_dir / "merged_rides.gpx"
    assert merged.exists()
    parsed = gpxpy.parse(merged.read_text(encoding="utf-8"))
    assert len(parsed.tracks) == EXPECTED_MULTI_RIDE_COUNT


def test_cli_merge_tcx(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(MULTI_RIDE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out_merge_tcx"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--merge"])

    merged = out_dir / "merged_rides.tcx"
    assert merged.exists()
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    root = ET.fromstring(merged.read_text(encoding="utf-8"))  # noqa: S314
    activities = root.findall(".//tcx:Activity", ns)
    assert len(activities) == EXPECTED_MULTI_RIDE_COUNT


def test_cli_merge_and_zip(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(MULTI_RIDE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out_merge_zip"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--merge", "--zip"])

    zip_path = out_dir / "rides.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None
        assert len(zf.namelist()) == 1
        assert zf.namelist()[0] == "merged_rides.tcx"


# ── Writer build_merged ───────────────────────────────────────────────


def test_gpx_build_merged_multiple_tracks() -> None:
    writer = GPXWriter()
    rides = _sample_rides()
    data = [
        (rides[0], DEP, RET, None, False),
        (rides[1], RET, DEP, None, False),
    ]
    xml = writer.build_merged(data)
    parsed = gpxpy.parse(xml)
    assert len(parsed.tracks) == EXPECTED_MULTI_RIDE_COUNT
    assert "Kaivopuisto" in parsed.tracks[0].name
    assert "Hakaniemi" in parsed.tracks[1].name


def test_tcx_build_merged_multiple_activities() -> None:
    writer = TCXWriter()
    rides = _sample_rides()
    data = [
        (rides[0], DEP, RET, None, True),
        (rides[1], RET, DEP, None, True),
    ]
    xml = writer.build_merged(data)
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    root = ET.fromstring(xml)  # noqa: S314
    activities = root.findall(".//tcx:Activity", ns)
    assert len(activities) == EXPECTED_MULTI_RIDE_COUNT


# ── web/main.py create_zip ────────────────────────────────────────────


def test_create_zip_produces_valid_archive() -> None:
    web_dir = str(Path(__file__).resolve().parent.parent / "web")
    sys.path.insert(0, web_dir)
    try:
        from main import create_zip  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    files = [
        ["ride1.tcx", "<xml>ride1</xml>"],
        ["ride2.tcx", "<xml>ride2</xml>"],
    ]
    data = create_zip(json.dumps(files))
    assert isinstance(data, bytes)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.testzip() is None
        assert sorted(zf.namelist()) == ["ride1.tcx", "ride2.tcx"]
        assert zf.read("ride1.tcx") == b"<xml>ride1</xml>"
