from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
    calculate_all_position_distribution_volatility,
    calculate_position_distribution_volatility,
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
    values: tuple[float, ...],
    position: str = "col1",
) -> tuple[tuple[str, PositionDistribution], ...]:
    return tuple(
        (
            f"W{index + 1}",
            make_distribution(
                position=position,
                percentages=tuple(
                    value if digit == 0 else 0.0
                    for digit in range(10)
                ),
            ),
        )
        for index, value in enumerate(values)
    )


def test_zero_change_has_zero_volatility():
    windows = make_windows((10.0, 10.0, 10.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.total_absolute_change == 0.0
    assert result.mean_absolute_change == 0.0
    assert result.maximum_absolute_change == 0.0
    assert result.minimum_absolute_change == 0.0
    assert result.volatility_level == "LOW"


def test_low_volatility():
    windows = make_windows((10.0, 11.0, 12.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 2
    assert result.total_absolute_change == 2.0
    assert result.mean_absolute_change == 1.0
    assert result.maximum_absolute_change == 1.0
    assert result.minimum_absolute_change == 1.0
    assert result.volatility_level == "LOW"


def test_medium_volatility():
    windows = make_windows((10.0, 13.0, 17.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 2
    assert result.total_absolute_change == 7.0
    assert result.mean_absolute_change == 3.5
    assert result.maximum_absolute_change == 4.0
    assert result.minimum_absolute_change == 3.0
    assert result.volatility_level == "MEDIUM"


def test_high_volatility():
    windows = make_windows((10.0, 16.0, 22.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.change_count == 2
    assert result.total_absolute_change == 12.0
    assert result.mean_absolute_change == 6.0
    assert result.maximum_absolute_change == 6.0
    assert result.minimum_absolute_change == 6.0
    assert result.volatility_level == "HIGH"


def test_direction_is_ignored():
    windows = make_windows((10.0, 15.0, 9.0, 16.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.total_absolute_change == 18.0
    assert result.mean_absolute_change == 6.0
    assert result.maximum_absolute_change == 7.0
    assert result.minimum_absolute_change == 5.0
    assert result.volatility_level == "HIGH"


def test_two_windows_create_one_change():
    windows = make_windows((10.0, 14.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.window_count == 2
    assert result.change_count == 1
    assert result.total_absolute_change == 4.0
    assert result.mean_absolute_change == 4.0
    assert result.maximum_absolute_change == 4.0
    assert result.minimum_absolute_change == 4.0
    assert result.volatility_level == "MEDIUM"


def test_one_window_returns_zero_metrics():
    windows = make_windows((10.0,))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.window_count == 1
    assert result.change_count == 0
    assert result.total_absolute_change == 0.0
    assert result.mean_absolute_change == 0.0
    assert result.maximum_absolute_change == 0.0
    assert result.minimum_absolute_change == 0.0
    assert result.volatility_level == "LOW"


def test_empty_windows_return_zero_metrics():
    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=(),
    )

    assert result.window_count == 0
    assert result.change_count == 0
    assert result.total_absolute_change == 0.0
    assert result.mean_absolute_change == 0.0
    assert result.maximum_absolute_change == 0.0
    assert result.minimum_absolute_change == 0.0
    assert result.volatility_level == "LOW"


def test_low_threshold_boundary_is_medium():
    windows = make_windows((10.0, 12.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.mean_absolute_change == 2.0
    assert result.volatility_level == "MEDIUM"


def test_high_threshold_boundary_is_high():
    windows = make_windows((10.0, 15.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.mean_absolute_change == 5.0
    assert result.volatility_level == "HIGH"


def test_custom_thresholds():
    windows = make_windows((10.0, 14.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
        low_threshold=3.0,
        high_threshold=6.0,
    )

    assert result.mean_absolute_change == 4.0
    assert result.volatility_level == "MEDIUM"


def test_digit_zero_is_supported():
    windows = make_windows((5.0, 11.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    assert result.digit == 0
    assert result.mean_absolute_change == 6.0


def test_digit_nine_is_supported():
    percentages_a = tuple(
        5.0 if digit == 9 else 0.0
        for digit in range(10)
    )
    percentages_b = tuple(
        12.0 if digit == 9 else 0.0
        for digit in range(10)
    )

    windows = (
        (
            "W1",
            make_distribution("col1", percentages_a),
        ),
        (
            "W2",
            make_distribution("col1", percentages_b),
        ),
    )

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=9,
        windows=windows,
    )

    assert result.digit == 9
    assert result.mean_absolute_change == 7.0
    assert result.volatility_level == "HIGH"


def test_invalid_digit_is_rejected():
    windows = make_windows((10.0, 12.0))

    with pytest.raises(ValueError, match="between 0 and 9"):
        calculate_position_distribution_volatility(
            position="col1",
            digit=10,
            windows=windows,
        )


def test_negative_digit_is_rejected():
    windows = make_windows((10.0, 12.0))

    with pytest.raises(ValueError, match="between 0 and 9"):
        calculate_position_distribution_volatility(
            position="col1",
            digit=-1,
            windows=windows,
        )


def test_position_mismatch_is_rejected():
    windows = make_windows(
        (10.0, 12.0),
        position="col2",
    )

    with pytest.raises(ValueError, match="does not match"):
        calculate_position_distribution_volatility(
            position="col1",
            digit=0,
            windows=windows,
        )


def test_invalid_distribution_length_is_rejected():
    invalid_distribution = PositionDistribution(
        position="col1",
        total_observations=100,
        percentages=(10.0, 20.0),
    )

    windows = (
        ("W1", invalid_distribution),
    )

    with pytest.raises(ValueError, match="exactly 10"):
        calculate_position_distribution_volatility(
            position="col1",
            digit=0,
            windows=windows,
        )


def test_negative_low_threshold_is_rejected():
    windows = make_windows((10.0, 12.0))

    with pytest.raises(
        ValueError,
        match="Low threshold",
    ):
        calculate_position_distribution_volatility(
            position="col1",
            digit=0,
            windows=windows,
            low_threshold=-1.0,
        )


def test_high_threshold_below_low_threshold_is_rejected():
    windows = make_windows((10.0, 12.0))

    with pytest.raises(
        ValueError,
        match="High threshold",
    ):
        calculate_position_distribution_volatility(
            position="col1",
            digit=0,
            windows=windows,
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_all_digits_are_returned():
    windows = make_windows((10.0, 15.0))

    results = calculate_all_position_distribution_volatility(
        position="col1",
        windows=windows,
    )

    assert len(results) == 10
    assert tuple(result.digit for result in results) == tuple(range(10))
    assert all(
        result.position == "col1"
        for result in results
    )


def test_all_digit_results_preserve_window_count():
    windows = make_windows((10.0, 15.0, 12.0))

    results = calculate_all_position_distribution_volatility(
        position="col1",
        windows=windows,
    )

    assert all(
        result.window_count == 3
        for result in results
    )
    assert all(
        result.change_count == 2
        for result in results
    )


def test_result_is_frozen():
    windows = make_windows((10.0, 12.0))

    result = calculate_position_distribution_volatility(
        position="col1",
        digit=0,
        windows=windows,
    )

    with pytest.raises(FrozenInstanceError):
        result.volatility_level = "HIGH"