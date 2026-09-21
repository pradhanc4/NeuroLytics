from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_trend_consistency import (
    PositionDistributionTrendConsistency,
    calculate_all_position_distribution_trend_consistency,
    calculate_position_distribution_trend_consistency,
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
    values: tuple[float, ...],
) -> tuple[tuple[str, PositionDistribution], ...]:
    return tuple(
        (
            f"window_{index + 1}",
            make_distribution(
                position=position,
                percentages=(
                    value,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
        )
        for index, value in enumerate(values)
    )


def test_empty_windows_return_zero_result() -> None:
    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=(),
    )

    assert result.position == "col1"
    assert result.digit == 0
    assert result.window_count == 0
    assert result.change_count == 0
    assert result.positive_changes == 0
    assert result.negative_changes == 0
    assert result.unchanged_changes == 0
    assert result.consistency_percentage == 0.0
    assert result.direction_switches == 0
    assert result.maximum_direction_streak == 0
    assert result.consistency_level == "LOW"


def test_single_window_returns_zero_result() -> None:
    windows = make_windows(
        "col1",
        (10.0,),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.window_count == 1
    assert result.change_count == 0
    assert result.consistency_percentage == 0.0
    assert result.direction_switches == 0
    assert result.maximum_direction_streak == 0
    assert result.consistency_level == "LOW"


def test_all_increasing_is_highly_consistent() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 15.0, 20.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 3
    assert result.positive_changes == 3
    assert result.negative_changes == 0
    assert result.unchanged_changes == 0
    assert result.consistency_percentage == 100.0
    assert result.direction_switches == 0
    assert result.maximum_direction_streak == 3
    assert result.consistency_level == "HIGH"


def test_all_decreasing_is_highly_consistent() -> None:
    windows = make_windows(
        "col1",
        (20.0, 15.0, 12.0, 10.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 3
    assert result.positive_changes == 0
    assert result.negative_changes == 3
    assert result.unchanged_changes == 0
    assert result.consistency_percentage == 100.0
    assert result.direction_switches == 0
    assert result.maximum_direction_streak == 3
    assert result.consistency_level == "HIGH"


def test_all_unchanged_is_highly_consistent() -> None:
    windows = make_windows(
        "col1",
        (10.0, 10.0, 10.0, 10.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 3
    assert result.positive_changes == 0
    assert result.negative_changes == 0
    assert result.unchanged_changes == 3
    assert result.consistency_percentage == 100.0
    assert result.direction_switches == 0
    assert result.maximum_direction_streak == 3
    assert result.consistency_level == "HIGH"


def test_mixed_direction_has_lower_consistency() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 11.0, 13.0, 12.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 4
    assert result.positive_changes == 2
    assert result.negative_changes == 2
    assert result.unchanged_changes == 0
    assert result.consistency_percentage == 50.0
    assert result.direction_switches == 3
    assert result.maximum_direction_streak == 1
    assert result.consistency_level == "MEDIUM"


def test_direction_switches_are_calculated() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 11.0, 14.0, 13.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.direction_switches == 3


def test_unchanged_change_does_not_count_as_direction_switch() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 12.0, 11.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.positive_changes == 1
    assert result.negative_changes == 1
    assert result.unchanged_changes == 1
    assert result.direction_switches == 0


def test_unchanged_changes_can_form_a_streak() -> None:
    windows = make_windows(
        "col1",
        (10.0, 10.0, 10.0, 10.0, 12.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.unchanged_changes == 3
    assert result.positive_changes == 1
    assert result.maximum_direction_streak == 3


def test_high_consistency_threshold_is_80_percent() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 14.0, 16.0, 18.0, 17.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 5
    assert result.positive_changes == 4
    assert result.negative_changes == 1
    assert result.consistency_percentage == 80.0
    assert result.consistency_level == "HIGH"


def test_medium_consistency_threshold_is_50_percent() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 11.0, 13.0, 12.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.consistency_percentage == 50.0
    assert result.consistency_level == "MEDIUM"


def test_low_consistency_is_below_50_percent() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 6
    assert result.positive_changes == 3
    assert result.negative_changes == 3
    assert result.consistency_percentage == 50.0
    assert result.consistency_level == "MEDIUM"


def test_zero_digit_is_valid() -> None:
    windows = make_windows(
        "col1",
        (0.0, 2.0, 4.0),
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.digit == 0
    assert result.positive_changes == 2
    assert result.consistency_percentage == 100.0


def test_digit_nine_is_valid() -> None:
    windows = tuple(
        (
            f"window_{index + 1}",
            make_distribution(
                position="col1",
                percentages=(
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    value,
                ),
            ),
        )
        for index, value in enumerate(
            (10.0, 12.0, 15.0)
        )
    )

    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=9,
        windows=windows,
    )

    assert result.digit == 9
    assert result.positive_changes == 2
    assert result.consistency_percentage == 100.0


def test_invalid_digit_above_nine_is_rejected() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_consistency(
            position="col1",
            digit=10,
            windows=windows,
        )


def test_negative_digit_is_rejected() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_consistency(
            position="col1",
            digit=-1,
            windows=windows,
        )


def test_position_mismatch_is_rejected() -> None:
    windows = make_windows(
        "col2",
        (10.0, 12.0),
    )

    with pytest.raises(
        ValueError,
        match="Distribution position does not match",
    ):
        calculate_position_distribution_trend_consistency(
            position="col1",
            digit=0,
            windows=windows,
        )


def test_invalid_distribution_length_is_rejected() -> None:
    invalid_distribution = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    windows = (
        ("window_1", invalid_distribution),
        (
            "window_2",
            make_distribution(
                position="col1",
                percentages=(
                    12.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="exactly 10 digit percentages",
    ):
        calculate_position_distribution_trend_consistency(
            position="col1",
            digit=0,
            windows=windows,
        )


def test_all_digits_are_supported() -> None:
    windows = make_windows(
        "col1",
        (10.0, 12.0, 14.0),
    )

    results = calculate_all_position_distribution_trend_consistency(
        position="col1",
        windows=windows,
    )

    assert len(results) == 10
    assert tuple(
        result.digit
        for result in results
    ) == tuple(range(10))


def test_all_digit_results_have_correct_position() -> None:
    windows = make_windows(
        "col8",
        (10.0, 12.0, 14.0),
    )

    results = calculate_all_position_distribution_trend_consistency(
        position="col8",
        windows=windows,
    )

    assert all(
        result.position == "col8"
        for result in results
    )


def test_result_has_correct_dataclass_type() -> None:
    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=(),
    )

    assert isinstance(
        result,
        PositionDistributionTrendConsistency,
    )


def test_result_dataclass_is_frozen() -> None:
    result = calculate_position_distribution_trend_consistency(
        position="col1",
        digit=0,
        windows=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"