"""Tests for shared Helsinki→UTC conversion helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hsl_kaupunkipyora_exporter.parser import Ride
from hsl_kaupunkipyora_exporter.writer._common import ride_utc_window, to_utc

EXPECTED_FALL_BACK_DURATION_MIN = 20


def test_to_utc_summer() -> None:
    assert to_utc(datetime(2024, 6, 1, 14, 30)) == datetime(
        2024, 6, 1, 11, 30, tzinfo=UTC
    )


def test_to_utc_winter() -> None:
    assert to_utc(datetime(2024, 1, 15, 10, 0)) == datetime(
        2024, 1, 15, 8, 0, tzinfo=UTC
    )


def test_to_utc_rejects_aware_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        to_utc(datetime(2024, 6, 1, 14, 30, tzinfo=UTC))


def test_ride_utc_window_uses_duration_min_across_fall_back_ambiguity() -> None:
    """03:50 is in the repeated (fall-back) hour on 27 Oct 2024.

    Without a reported duration, converting departure and return
    independently doubles the reported 20-minute ride to 80 minutes.
    ``duration_min`` must resolve this instead.
    """
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 10, 27, 3, 50),
        return_station="B",
        return_time=datetime(2024, 10, 27, 4, 10),
        duration_min=EXPECTED_FALL_BACK_DURATION_MIN,
    )
    dep_utc, ret_utc = ride_utc_window(ride)
    assert (ret_utc - dep_utc).total_seconds() == EXPECTED_FALL_BACK_DURATION_MIN * 60


def test_ride_utc_window_without_duration_min_logs_on_spring_forward_inversion(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """31 Mar 2024: local clocks jump 03:00 EET -> 04:00 EEST; 03:00-03:59 don't exist.

    A ride departing at 03:30 (in the gap, resolved to the pre-transition
    UTC+2 offset) and returning at 04:10 (unambiguous, UTC+3) is forward in
    local-clock terms but inverts once converted independently, since the
    departure is 30 minutes into a skipped hour. Without duration_min to
    disambiguate, this must be logged rather than silently accepted.
    """
    ride = Ride(
        departure_station="A",
        departure_time=datetime(2024, 3, 31, 3, 30),
        return_station="B",
        return_time=datetime(2024, 3, 31, 4, 10),
    )
    with caplog.at_level("WARNING"):
        dep_utc, ret_utc = ride_utc_window(ride)

    assert ret_utc <= dep_utc
    assert any("non-positive duration" in r.message for r in caplog.records)
