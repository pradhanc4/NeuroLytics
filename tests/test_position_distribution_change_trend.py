from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_change_trend import (
    PositionDistributionChangeTrend,
    calculate_all_position_distribution_change_trends,
    calculate_position_distribution_change_trend,
)


def make_distribution(
    position: str,
    percentages: tuple[float, ...],
) -> PositionDistribution:
    return PositionDistribution(
        position=position,
        total_observations=100,
        percentages=percentages,
    )


def make_windows(
    position: str,
    digit_values: tuple[float, ...],
) -> tuple[tuple[str, PositionDistribution], ...]:
    windows = []

    for index, value in enumerate(digit_values):
        percentages = [0.0] * 10
        percentages[5] = value

        windows.append(
            (
                f"W{index + 1}",
                make_distribution(
                    position=position,
                    percentages=tuple(percentages),
                ),
            )
        )

    return tuple(windows)


def test_increasing_trend():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0, 10.0, 12.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.trend_direction == "INCREASING"
    assert result.window_count == 4
    assert result.change_count == 3
    assert result.increases == 3
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.total_change == 7.0
    assert result.mean_change == pytest.approx(7.0 / 3)


def test_decreasing_trend():
    windows = make_windows(
        position="col1",
        digit_values=(12.0, 10.0, 7.0, 5.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.trend_direction == "DECREASING"
    assert result.change_count == 3
    assert result.increases == 0
    assert result.decreases == 3
    assert result.unchanged == 0
    assert result.total_change == -7.0
    assert result.mean_change == pytest.approx(-7.0 / 3)


def test_unchanged_trend():
    windows = make_windows(
        position="col1",
        digit_values=(8.0, 8.0, 8.0, 8.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.trend_direction == "UNCHANGED"
    assert result.change_count == 3
    assert result.increases == 0
    assert result.decreases == 0
    assert result.unchanged == 3
    assert result.total_change == 0.0
    assert result.mean_change == 0.0


def test_mixed_trend():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 6.0, 9.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.trend_direction == "MIXED"
    assert result.change_count == 3
    assert result.increases == 2
    assert result.decreases == 1
    assert result.unchanged == 0
    assert result.total_change == 4.0
    assert result.mean_change == pytest.approx(4.0 / 3)


def test_mixed_trend_with_unchanged_change():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 8.0, 6.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.trend_direction == "MIXED"
    assert result.change_count == 3
    assert result.increases == 1
    assert result.decreases == 1
    assert result.unchanged == 1


def test_zero_digit_is_valid():
    windows = []

    for index, value in enumerate((0.0, 2.0, 4.0)):
        percentages = [0.0] * 10
        percentages[0] = value

        windows.append(
            (
                f"W{index + 1}",
                make_distribution(
                    position="col1",
                    percentages=tuple(percentages),
                ),
            )
        )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=0,
        windows=tuple(windows),
    )

    assert result.digit == 0
    assert result.trend_direction == "INCREASING"
    assert result.total_change == 4.0


def test_all_digits_can_be_analyzed():
    windows = make_windows(
        position="col2",
        digit_values=(5.0, 7.0, 9.0),
    )

    results = calculate_all_position_distribution_change_trends(
        position="col2",
        windows=windows,
    )

    assert len(results) == 10
    assert tuple(result.digit for result in results) == tuple(range(10))

    for result in results:
        assert result.position == "col2"
        assert result.window_count == 3


def test_single_window_returns_unchanged():
    windows = make_windows(
        position="col1",
        digit_values=(7.0,),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.window_count == 1
    assert result.change_count == 0
    assert result.increases == 0
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.total_change == 0.0
    assert result.mean_change == 0.0
    assert result.trend_direction == "UNCHANGED"


def test_empty_windows_are_supported():
    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=(),
    )

    assert result.window_count == 0
    assert result.change_count == 0
    assert result.increases == 0
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.total_change == 0.0
    assert result.mean_change == 0.0
    assert result.trend_direction == "UNCHANGED"


def test_invalid_digit_is_rejected():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(ValueError, match="Digit must be between 0 and 9"):
        calculate_position_distribution_change_trend(
            position="col1",
            digit=10,
            windows=windows,
        )


def test_negative_digit_is_rejected():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(ValueError, match="Digit must be between 0 and 9"):
        calculate_position_distribution_change_trend(
            position="col1",
            digit=-1,
            windows=windows,
        )


def test_position_mismatch_is_rejected():
    windows = make_windows(
        position="col2",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(
        ValueError,
        match="Distribution position does not match",
    ):
        calculate_position_distribution_change_trend(
            position="col1",
            digit=5,
            windows=windows,
        )


def test_invalid_distribution_length_is_rejected():
    invalid_distribution = PositionDistribution(
        position="col1",
        total_observations=100,
        percentages=(1.0, 2.0, 3.0),
    )

    windows = (
        ("W1", invalid_distribution),
    )

    with pytest.raises(
        ValueError,
        match="exactly 10 digit percentages",
    ):
        calculate_position_distribution_change_trend(
            position="col1",
            digit=5,
            windows=windows,
        )


def test_window_order_is_preserved():
    windows = make_windows(
        position="col1",
        digit_values=(10.0, 5.0, 8.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.total_change == -2.0
    assert result.mean_change == pytest.approx(-1.0)
    assert result.increases == 1
    assert result.decreases == 1
    assert result.trend_direction == "MIXED"


def test_change_count_equals_window_count_minus_one():
    windows = make_windows(
        position="col1",
        digit_values=(1.0, 2.0, 3.0, 4.0, 5.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.change_count == result.window_count - 1


def test_digit_specific_analysis():
    windows = []

    values = (
        (2.0, 8.0),
        (4.0, 6.0),
        (6.0, 4.0),
    )

    for index, (digit_2_value, digit_5_value) in enumerate(values):
        percentages = [0.0] * 10
        percentages[2] = digit_2_value
        percentages[5] = digit_5_value

        windows.append(
            (
                f"W{index + 1}",
                make_distribution(
                    position="col1",
                    percentages=tuple(percentages),
                ),
            )
        )

    digit_2_result = calculate_position_distribution_change_trend(
        position="col1",
        digit=2,
        windows=tuple(windows),
    )

    digit_5_result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=tuple(windows),
    )

    assert digit_2_result.trend_direction == "INCREASING"
    assert digit_2_result.total_change == 4.0

    assert digit_5_result.trend_direction == "DECREASING"
    assert digit_5_result.total_change == -4.0


def test_result_is_correct_dataclass_type():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert isinstance(
        result,
        PositionDistributionChangeTrend,
    )


def test_result_dataclass_is_frozen():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    result = calculate_position_distribution_change_trend(
        position="col1",
        digit=5,
        windows=windows,
    )

    with pytest.raises(FrozenInstanceError):
        result.trend_direction = "DECREASING"