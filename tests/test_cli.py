"""Tests for the CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import pytest

from hsl_kaupunkipyora_exporter.cli import main
from hsl_kaupunkipyora_exporter.stations import Station

SAMPLE_TEXT = """\
Departure station: Kaivopuisto
Departure time: 01.06.2024 14:30
Return station: Hakaniemi
Return time: 01.06.2024 14:45
"""

MOCK_STATIONS = [
    Station(name="Kaivopuisto", lat=60.1575, lon=24.9502),
    Station(name="Hakaniemi", lat=60.1790, lon=24.9508),
]


def test_cli_writes_tcx_by_default(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(SAMPLE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "output_default"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir)])

    tcx_files = list(out_dir.glob("*.tcx"))
    assert len(tcx_files) == 1


def test_cli_writes_gpx(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(SAMPLE_TEXT, encoding="utf-8")
    out_dir = tmp_path / "output"

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ):
        main([str(input_file), "-o", str(out_dir), "--format", "gpx"])

    gpx_files = list(out_dir.glob("*.gpx"))
    assert len(gpx_files) == 1


def test_cli_mutual_exclusivity(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(SAMPLE_TEXT, encoding="utf-8")

    with pytest.raises(SystemExit):
        # argparse handles this and calls sys.exit(2)
        main([str(input_file), "--linear", "--use-route"])


def test_cli_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent.txt")])
    assert exc_info.value.code == 1


def test_cli_empty_file(tmp_path: Path) -> None:
    input_file = tmp_path / "empty.txt"
    input_file.write_text("nothing useful here", encoding="utf-8")

    with (
        pytest.raises(SystemExit) as exc_info,
        patch(
            "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
        ),
    ):
        main([str(input_file)])
    assert exc_info.value.code == 0


def test_cli_api_key_passed(tmp_path: Path) -> None:
    input_file = tmp_path / "rides.txt"
    input_file.write_text(SAMPLE_TEXT, encoding="utf-8")

    with patch(
        "hsl_kaupunkipyora_exporter.cli.get_stations", return_value=MOCK_STATIONS
    ) as mock_get:
        main([str(input_file), "--api-key", "test-key"])
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["api_key"] == "test-key"
