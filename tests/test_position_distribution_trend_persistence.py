from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_trend_persistence import (
    PositionDistributionTrendPersistence,
    calculate_all_position_distribution_trend_persistence,
    calculate_position_distribution_trend_persistence,
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


def test_all_increasing_changes():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0, 10.0, 12.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.position == "col1"
    assert result.digit == 5
    assert result.window_count == 4
    assert result.change_count == 3
    assert result.increases == 3
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.dominant_direction == "INCREASING"
    assert result.persistence_percentage == 100.0
    assert result.longest_streak == 3


def test_all_decreasing_changes():
    windows = make_windows(
        position="col1",
        digit_values=(12.0, 10.0, 7.0, 5.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.dominant_direction == "DECREASING"
    assert result.change_count == 3
    assert result.increases == 0
    assert result.decreases == 3
    assert result.unchanged == 0
    assert result.persistence_percentage == 100.0
    assert result.longest_streak == 3


def test_all_unchanged_changes():
    windows = make_windows(
        position="col1",
        digit_values=(8.0, 8.0, 8.0, 8.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.dominant_direction == "UNCHANGED"
    assert result.change_count == 3
    assert result.increases == 0
    assert result.decreases == 0
    assert result.unchanged == 3
    assert result.persistence_percentage == 100.0
    assert result.longest_streak == 3


def test_mixed_changes_with_increasing_dominance():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 6.0, 9.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.dominant_direction == "INCREASING"
    assert result.change_count == 3
    assert result.increases == 2
    assert result.decreases == 1
    assert result.unchanged == 0
    assert result.persistence_percentage == pytest.approx(
        2 / 3 * 100
    )
    assert result.longest_streak == 1


def test_mixed_changes_with_decreasing_dominance():
    windows = make_windows(
        position="col1",
        digit_values=(9.0, 6.0, 8.0, 5.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.dominant_direction == "DECREASING"
    assert result.change_count == 3
    assert result.increases == 1
    assert result.decreases == 2
    assert result.unchanged == 0
    assert result.persistence_percentage == pytest.approx(
        2 / 3 * 100
    )
    assert result.longest_streak == 1


def test_equal_increases_and_decreases_are_mixed():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 6.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.dominant_direction == "MIXED"
    assert result.increases == 1
    assert result.decreases == 1
    assert result.unchanged == 0
    assert result.persistence_percentage == 50.0
    assert result.longest_streak == 1


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

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=0,
        windows=tuple(windows),
    )

    assert result.digit == 0
    assert result.dominant_direction == "INCREASING"
    assert result.persistence_percentage == 100.0
    assert result.longest_streak == 2


def test_digit_nine_is_valid():
    windows = make_windows(
        position="col1",
        digit_values=(10.0, 8.0, 6.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=9,
        windows=windows,
    )

    assert result.digit == 9
    assert result.dominant_direction == "UNCHANGED"
    assert result.change_count == 2


def test_single_window_returns_zero_persistence():
    windows = make_windows(
        position="col1",
        digit_values=(7.0,),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.window_count == 1
    assert result.change_count == 0
    assert result.increases == 0
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.dominant_direction == "UNCHANGED"
    assert result.persistence_percentage == 0.0
    assert result.longest_streak == 0


def test_empty_windows_are_supported():
    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=(),
    )

    assert result.window_count == 0
    assert result.change_count == 0
    assert result.dominant_direction == "UNCHANGED"
    assert result.persistence_percentage == 0.0
    assert result.longest_streak == 0


def test_two_windows_create_one_change():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 9.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.window_count == 2
    assert result.change_count == 1
    assert result.increases == 1
    assert result.decreases == 0
    assert result.unchanged == 0
    assert result.persistence_percentage == 100.0
    assert result.longest_streak == 1


def test_position_mismatch_is_rejected():
    windows = make_windows(
        position="col2",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(
        ValueError,
        match="Distribution position does not match",
    ):
        calculate_position_distribution_trend_persistence(
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
        calculate_position_distribution_trend_persistence(
            position="col1",
            digit=5,
            windows=windows,
        )


def test_invalid_digit_is_rejected():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_persistence(
            position="col1",
            digit=10,
            windows=windows,
        )


def test_negative_digit_is_rejected():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_persistence(
            position="col1",
            digit=-1,
            windows=windows,
        )


def test_longest_increasing_streak_is_calculated():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 11.0, 14.0, 10.0, 12.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.increases == 4
    assert result.decreases == 1
    assert result.longest_streak == 3


def test_longest_decreasing_streak_is_calculated():
    windows = make_windows(
        position="col1",
        digit_values=(14.0, 11.0, 8.0, 5.0, 9.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.decreases == 3
    assert result.increases == 1
    assert result.longest_streak == 3


def test_unchanged_values_break_direction_streak():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 8.0, 8.0, 11.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert result.increases == 2
    assert result.unchanged == 1
    assert result.longest_streak == 1


def test_all_digits_are_returned():
    windows = make_windows(
        position="col2",
        digit_values=(5.0, 7.0, 9.0),
    )

    results = calculate_all_position_distribution_trend_persistence(
        position="col2",
        windows=windows,
    )

    assert len(results) == 10
    assert tuple(
        result.digit
        for result in results
    ) == tuple(range(10))

    for result in results:
        assert result.position == "col2"
        assert result.window_count == 3


def test_result_is_frozen():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    with pytest.raises(FrozenInstanceError):
        result.dominant_direction = "DECREASING"


def test_result_is_correct_dataclass_type():
    windows = make_windows(
        position="col1",
        digit_values=(5.0, 7.0),
    )

    result = calculate_position_distribution_trend_persistence(
        position="col1",
        digit=5,
        windows=windows,
    )

    assert isinstance(
        result,
        PositionDistributionTrendPersistence,
    )