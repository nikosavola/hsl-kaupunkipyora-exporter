"""Tests for the shared route-interpolation helper."""

from datetime import UTC, datetime

import pytest

from hsl_kaupunkipyora_exporter.routing import Point
from hsl_kaupunkipyora_exporter.writer._common import (
    InterpolatedPoint,
    interpolate_route,
)

DEP_TIME = datetime(2024, 6, 1, 14, 30, tzinfo=UTC)
RET_TIME = datetime(2024, 6, 1, 14, 45, tzinfo=UTC)

ROUTE_3 = [Point(60.1, 24.9), Point(60.15, 24.95), Point(60.2, 25.0)]
MIDPOINT_MINUTE = 37
EXPECTED_TWO_POINTS = 2


def test_returns_correct_count() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    assert len(result) == len(ROUTE_3)


def test_first_point_has_dep_time() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    assert result[0].time == DEP_TIME


def test_last_point_has_ret_time() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    assert result[-1].time == RET_TIME


def test_coordinates_preserved() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    for ip, pt in zip(result, ROUTE_3, strict=True):
        assert ip.lat == pytest.approx(pt.lat)
        assert ip.lon == pytest.approx(pt.lon)


def test_first_distance_is_zero() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    assert result[0].distance_m == pytest.approx(0.0)


def test_distances_are_monotonically_increasing() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    for i in range(1, len(result)):
        assert result[i].distance_m >= result[i - 1].distance_m


def test_times_are_monotonically_increasing() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    for i in range(1, len(result)):
        assert result[i].time >= result[i - 1].time


def test_midpoint_time_is_interpolated() -> None:
    """With roughly equal segments the middle point should be near the midpoint in time.

    Route has 3 nearly equidistant points, so the middle point gets ~50 %
    of the 15-minute duration → 14:30 + 7:30 ≈ 14:37.
    """
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    mid = result[1].time
    assert mid.minute == MIDPOINT_MINUTE  # ~14:37:30 for a symmetric 3-point route


def test_target_distance_scales_cumulative() -> None:
    target_km = 5.0
    result = interpolate_route(
        ROUTE_3, DEP_TIME, RET_TIME, target_distance_km=target_km
    )
    assert result[-1].distance_m == pytest.approx(target_km * 1000.0, rel=1e-6)


def test_target_distance_none_keeps_raw() -> None:
    """When target_distance_km is None the raw haversine distance is used."""
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME, target_distance_km=None)
    # The last point distance should be the cumulative haversine in metres
    assert result[-1].distance_m > 0


def test_two_identical_points_even_spacing() -> None:
    """When all points are identical (zero total distance), timestamps are evenly spaced."""
    pts = [Point(60.0, 24.0), Point(60.0, 24.0), Point(60.0, 24.0)]
    result = interpolate_route(pts, DEP_TIME, RET_TIME)
    expected_mid = DEP_TIME + (RET_TIME - DEP_TIME) / 2
    assert result[1].time == expected_mid


def test_returns_interpolated_point_instances() -> None:
    result = interpolate_route(ROUTE_3, DEP_TIME, RET_TIME)
    assert all(isinstance(ip, InterpolatedPoint) for ip in result)


def test_two_points_simple() -> None:
    pts = [Point(60.0, 24.0), Point(60.1, 24.1)]
    result = interpolate_route(pts, DEP_TIME, RET_TIME)
    assert len(result) == EXPECTED_TWO_POINTS
    assert result[0].time == DEP_TIME
    assert result[-1].time == RET_TIME
    assert result[0].distance_m == pytest.approx(0.0)
    assert result[-1].distance_m > 0


def test_single_point_no_division_by_zero() -> None:
    """A single-point route should not raise and should return dep_time."""
    pts = [Point(60.0, 24.0)]
    result = interpolate_route(pts, DEP_TIME, RET_TIME)
    assert len(result) == 1
    assert result[0].time == DEP_TIME
    assert result[0].distance_m == pytest.approx(0.0)
