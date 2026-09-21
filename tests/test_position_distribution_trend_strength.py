from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_trend_strength import (
    PositionDistributionTrendStrength,
    calculate_all_position_distribution_trend_strength,
    calculate_position_distribution_trend_strength,
)


def make_distribution(
    position: str,
    percentages: tuple[float, ...],
    total_observations: int = 100,
) -> PositionDistribution:
    return PositionDistribution(
        position=position,
        total_observations=total_observations,
        percentages=percentages,
    )


def make_windows(
    position: str,
    values: tuple[float, ...],
) -> tuple[tuple[str, PositionDistribution], ...]:
    windows = []

    for index, value in enumerate(values, start=1):
        percentages = [0.0] * 10
        percentages[0] = value

        windows.append(
            (
                f"W{index}",
                make_distribution(
                    position=position,
                    percentages=tuple(percentages),
                ),
            )
        )

    return tuple(windows)


def test_all_increasing_trend() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 13.0, 17.0, 22.0),
        ),
    )

    assert result.position == "col1"
    assert result.digit == 0
    assert result.window_count == 4
    assert result.change_count == 3
    assert result.total_change == 12.0
    assert result.mean_change == 4.0
    assert result.absolute_total_change == 12.0
    assert result.mean_absolute_change == 4.0
    assert result.trend_direction == "INCREASING"
    assert result.strength == "MEDIUM"


def test_all_decreasing_trend() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (30.0, 25.0, 20.0, 15.0),
        ),
    )

    assert result.total_change == -15.0
    assert result.mean_change == -5.0
    assert result.absolute_total_change == 15.0
    assert result.mean_absolute_change == 5.0
    assert result.trend_direction == "DECREASING"
    assert result.strength == "HIGH"


def test_all_unchanged_trend() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (20.0, 20.0, 20.0),
        ),
    )

    assert result.change_count == 2
    assert result.total_change == 0.0
    assert result.mean_change == 0.0
    assert result.absolute_total_change == 0.0
    assert result.mean_absolute_change == 0.0
    assert result.trend_direction == "UNCHANGED"
    assert result.strength == "LOW"


def test_mixed_trend_uses_absolute_change_for_strength() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 16.0, 11.0, 17.0),
        ),
    )

    assert result.trend_direction == "MIXED"
    assert result.total_change == 7.0
    assert result.mean_change == pytest.approx(7.0 / 3.0)
    assert result.absolute_total_change == 17.0
    assert result.mean_absolute_change == pytest.approx(17.0 / 3.0)
    assert result.strength == "HIGH"


def test_low_strength_boundary() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 11.0, 12.0),
        ),
    )

    assert result.mean_absolute_change == 1.0
    assert result.strength == "LOW"


def test_medium_strength_boundary() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 12.0, 14.0),
        ),
    )

    assert result.mean_absolute_change == 2.0
    assert result.strength == "MEDIUM"


def test_high_strength_boundary() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 15.0, 20.0),
        ),
    )

    assert result.mean_absolute_change == 5.0
    assert result.strength == "HIGH"


def test_custom_thresholds() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 13.0, 16.0),
        ),
        low_threshold=4.0,
        high_threshold=8.0,
    )

    assert result.mean_absolute_change == 3.0
    assert result.strength == "LOW"


def test_zero_digit_is_valid() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (0.0, 5.0, 10.0),
        ),
    )

    assert result.digit == 0
    assert result.total_change == 10.0
    assert result.trend_direction == "INCREASING"


def test_digit_nine_is_valid() -> None:
    percentages_a = (0.0,) * 9 + (10.0,)
    percentages_b = (0.0,) * 9 + (15.0,)

    windows = (
        (
            "W1",
            make_distribution(
                "col1",
                percentages_a,
            ),
        ),
        (
            "W2",
            make_distribution(
                "col1",
                percentages_b,
            ),
        ),
    )

    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=9,
        windows=windows,
    )

    assert result.digit == 9
    assert result.total_change == 5.0
    assert result.trend_direction == "INCREASING"
    assert result.strength == "HIGH"


def test_single_window_returns_unchanged_low() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0,),
        ),
    )

    assert result.window_count == 1
    assert result.change_count == 0
    assert result.trend_direction == "UNCHANGED"
    assert result.strength == "LOW"


def test_empty_windows_returns_unchanged_low() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=(),
    )

    assert result.window_count == 0
    assert result.change_count == 0
    assert result.trend_direction == "UNCHANGED"
    assert result.strength == "LOW"


def test_two_windows_create_one_change() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 16.0),
        ),
    )

    assert result.window_count == 2
    assert result.change_count == 1
    assert result.total_change == 6.0
    assert result.mean_change == 6.0
    assert result.absolute_total_change == 6.0
    assert result.mean_absolute_change == 6.0
    assert result.trend_direction == "INCREASING"
    assert result.strength == "HIGH"


def test_position_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Distribution position does not match",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=0,
            windows=make_windows(
                "col2",
                (10.0, 15.0),
            ),
        )


def test_invalid_distribution_length_is_rejected() -> None:
    invalid_distribution = make_distribution(
        position="col1",
        percentages=(10.0,) * 9,
    )

    windows = (
        ("W1", invalid_distribution),
    )

    with pytest.raises(
        ValueError,
        match="exactly 10 digit percentages",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=0,
            windows=windows,
        )


def test_negative_digit_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=-1,
            windows=(),
        )


def test_digit_above_nine_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=10,
            windows=(),
        )


def test_negative_low_threshold_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Low threshold must be greater than or equal to zero",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=0,
            windows=(),
            low_threshold=-1.0,
        )


def test_high_threshold_below_low_threshold_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="High threshold must be greater than or equal",
    ):
        calculate_position_distribution_trend_strength(
            position="col1",
            digit=0,
            windows=(),
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_all_digits_are_supported() -> None:
    windows = make_windows(
        "col1",
        (10.0, 15.0),
    )

    results = calculate_all_position_distribution_trend_strength(
        position="col1",
        windows=windows,
    )

    assert len(results) == 10
    assert tuple(
        result.digit
        for result in results
    ) == tuple(range(10))


def test_all_results_have_correct_type() -> None:
    results = calculate_all_position_distribution_trend_strength(
        position="col1",
        windows=make_windows(
            "col1",
            (10.0, 15.0),
        ),
    )

    assert all(
        isinstance(
            result,
            PositionDistributionTrendStrength,
        )
        for result in results
    )


def test_result_dataclass_is_frozen() -> None:
    result = calculate_position_distribution_trend_strength(
        position="col1",
        digit=0,
        windows=make_windows(
            "col1",
            (10.0, 15.0),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"