"""Tests for the shared export_rides() orchestration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from hsl_kaupunkipyora_exporter.exporter import ExportEvent, ExportResult, export_rides
from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.routing import Point
from hsl_kaupunkipyora_exporter.stations import Station, StationLookup
from hsl_kaupunkipyora_exporter.writer import GPXWriter, TCXWriter

EXPECTED_SUMMARY_TRACKPOINT_COUNT = 2

RIDE = Ride(
    departure_station="Kaivopuisto",
    departure_time=datetime(2024, 6, 1, 14, 30),
    return_station="Hakaniemi",
    return_time=datetime(2024, 6, 1, 14, 45),
)

STATIONS = [
    Station(name="Kaivopuisto", lat=60.1575, lon=24.9502),
    Station(name="Hakaniemi", lat=60.1790, lon=24.9508),
]

LOOKUP = StationLookup(STATIONS)


def test_export_rides_returns_result_with_one_file() -> None:
    writer = TCXWriter()
    result = export_rides([RIDE], LOOKUP, writer)

    assert isinstance(result, ExportResult)
    assert result.written == 1
    assert result.skipped == 0
    assert len(result.files) == 1
    filename, xml = result.files[0]
    assert filename.endswith(".tcx")
    assert "<TrainingCenterDatabase" in xml


def test_export_rides_gpx_format() -> None:
    writer = GPXWriter()
    result = export_rides([RIDE], LOOKUP, writer)

    assert result.written == 1
    assert len(result.files) == 1
    filename, xml = result.files[0]
    assert filename.endswith(".gpx")
    assert "<gpx" in xml


def test_export_rides_skips_unknown_departure() -> None:
    ride = Ride(
        departure_station="Nowhere",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="Hakaniemi",
        return_time=datetime(2024, 6, 1, 14, 45),
    )
    result = export_rides([ride], LOOKUP, TCXWriter())

    assert result.written == 0
    assert result.skipped == 1
    assert result.files == []


def test_export_rides_skips_unknown_return() -> None:
    ride = Ride(
        departure_station="Kaivopuisto",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="Nowhere",
        return_time=datetime(2024, 6, 1, 14, 45),
    )
    result = export_rides([ride], LOOKUP, TCXWriter())

    assert result.written == 0
    assert result.skipped == 1


def test_export_rides_emits_events() -> None:
    events: list[ExportEvent] = []
    export_rides([RIDE], LOOKUP, TCXWriter(), on_event=events.append)

    assert len(events) >= 2  # noqa: PLR2004
    # Should have at least a "Generated …" and "Done …" event
    messages = [e.message for e in events]
    assert any("Generated" in m for m in messages)
    assert any("Done" in m for m in messages)


def test_export_rides_emits_warning_for_skip() -> None:
    ride = Ride(
        departure_station="Nowhere",
        departure_time=datetime(2024, 6, 1, 14, 30),
        return_station="Hakaniemi",
        return_time=datetime(2024, 6, 1, 14, 45),
    )
    events: list[ExportEvent] = []
    export_rides([ride], LOOKUP, TCXWriter(), on_event=events.append)

    warnings = [e for e in events if e.level == "warning"]
    assert len(warnings) >= 1
    assert "Nowhere" in warnings[0].message


def test_export_rides_writes_to_disk_when_output_dir_set(tmp_path: Path) -> None:
    writer = TCXWriter(tmp_path)
    result = export_rides([RIDE], LOOKUP, writer)

    assert result.written == 1
    tcx_files = list(tmp_path.glob("*.tcx"))
    assert len(tcx_files) == 1


def test_export_rides_no_disk_writes_without_output_dir() -> None:
    writer = TCXWriter()
    result = export_rides([RIDE], LOOKUP, writer)

    assert result.written == 1
    assert len(result.files) == 1


def test_export_rides_dry_run_creates_no_output_dir(tmp_path: Path) -> None:
    """dry_run=True must have zero filesystem side effects.

    Even when the writer was given a real output_dir.
    """
    missing_dir = tmp_path / "does-not-exist-yet"
    writer = TCXWriter(missing_dir)
    result = export_rides([RIDE], LOOKUP, writer, dry_run=True)

    assert result.written == 1
    assert not missing_dir.exists()


def test_export_rides_dry_run_survives_unwritable_output_dir() -> None:
    """A dry run must not touch the output_dir.

    So it can't fail just because that path isn't writable (or doesn't
    exist and can't be created).
    """
    unwritable = Path("/nonexistent-root/should-never-be-created")
    writer = TCXWriter(unwritable)
    result = export_rides([RIDE], LOOKUP, writer, dry_run=True)

    assert result.written == 1
    assert not unwritable.exists()


def test_export_rides_path_mode_summary() -> None:
    writer = TCXWriter()
    result = export_rides([RIDE], LOOKUP, writer, path_mode="summary")

    assert result.written == 1
    _, xml = result.files[0]
    # Summary mode still includes a minimal departure/return Track (with
    # Time elements) since Strava requires it, but no intermediate points.
    assert xml.count("<Trackpoint") == EXPECTED_SUMMARY_TRACKPOINT_COUNT


def test_export_rides_path_mode_linear() -> None:
    writer = GPXWriter()
    result = export_rides([RIDE], LOOKUP, writer, path_mode="linear")

    assert result.written == 1
    _, xml = result.files[0]
    # Linear mode includes track points
    assert "<trkpt" in xml


def test_export_rides_path_mode_routed_with_mock() -> None:
    route = [Point(60.1575, 24.9502), Point(60.168, 24.950), Point(60.179, 24.9508)]

    with patch("hsl_kaupunkipyora_exporter.exporter.fetch_route", return_value=route):
        writer = GPXWriter()
        result = export_rides(
            [RIDE], LOOKUP, writer, path_mode="routed", api_key="test"
        )

    assert result.written == 1
    _, xml = result.files[0]
    assert "<trkpt" in xml


def test_export_rides_routed_falls_back_on_error() -> None:
    events: list[ExportEvent] = []

    with patch(
        "hsl_kaupunkipyora_exporter.exporter.fetch_route",
        side_effect=RuntimeError("network error"),
    ):
        result = export_rides(
            [RIDE],
            LOOKUP,
            TCXWriter(),
            path_mode="routed",
            api_key="key",
            on_event=events.append,
        )

    assert result.written == 1
    warnings = [e for e in events if e.level == "warning"]
    assert any("network error" in w.message for w in warnings)
    assert any("falling back" in w.message for w in warnings)


def test_export_rides_empty_iterable() -> None:
    result = export_rides([], LOOKUP, TCXWriter())

    assert result.written == 0
    assert result.skipped == 0
    assert result.files == []


def test_export_rides_multiple_rides() -> None:
    ride2 = Ride(
        departure_station="Hakaniemi",
        departure_time=datetime(2024, 6, 2, 10, 0),
        return_station="Kaivopuisto",
        return_time=datetime(2024, 6, 2, 10, 20),
    )
    result = export_rides([RIDE, ride2], LOOKUP, TCXWriter())

    assert result.written == 2  # noqa: PLR2004
    assert result.skipped == 0
    assert len(result.files) == 2  # noqa: PLR2004
