from __future__ import annotations

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_stability import (
    PositionDistributionStabilityComparison,
    compare_position_distribution_window_pair,
    compare_position_distribution_windows,
    summarize_position_distribution_stability,
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


def test_empty_windows_return_no_comparisons() -> None:
    result = compare_position_distribution_windows(
        position="col1",
        windows=(),
    )

    assert result == ()


def test_single_window_returns_no_comparison() -> None:
    distribution = make_distribution(
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
            10.0,
        ),
    )

    result = compare_position_distribution_windows(
        position="col1",
        windows=(
            ("window_1", distribution),
        ),
    )

    assert result == ()


def test_identical_window_distributions_have_zero_difference() -> None:
    distribution_a = make_distribution(
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
            10.0,
        ),
    )

    distribution_b = make_distribution(
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
            10.0,
        ),
    )

    result = compare_position_distribution_window_pair(
        position="col1",
        window_a="window_1",
        distribution_a=distribution_a,
        window_b="window_2",
        distribution_b=distribution_b,
    )

    assert isinstance(
        result,
        PositionDistributionStabilityComparison,
    )

    assert result.position == "col1"
    assert result.window_a == "window_1"
    assert result.window_b == "window_2"
    assert result.mean_absolute_difference == 0.0


def test_comparison_preserves_window_names() -> None:
    distribution_a = make_distribution(
        position="col2",
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
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col2",
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
            10.0,
        ),
    )

    result = compare_position_distribution_window_pair(
        position="col2",
        window_a="last_30_days",
        distribution_a=distribution_a,
        window_b="last_60_days",
        distribution_b=distribution_b,
    )

    assert result.window_a == "last_30_days"
    assert result.window_b == "last_60_days"


def test_position_mismatch_in_first_distribution_is_rejected() -> None:
    distribution_a = make_distribution(
        position="col2",
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
            10.0,
        ),
    )

    distribution_b = make_distribution(
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
            10.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="First distribution position does not match",
    ):
        compare_position_distribution_window_pair(
            position="col1",
            window_a="window_1",
            distribution_a=distribution_a,
            window_b="window_2",
            distribution_b=distribution_b,
        )


def test_position_mismatch_in_second_distribution_is_rejected() -> None:
    distribution_a = make_distribution(
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
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col2",
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
            10.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Second distribution position does not match",
    ):
        compare_position_distribution_window_pair(
            position="col1",
            window_a="window_1",
            distribution_a=distribution_a,
            window_b="window_2",
            distribution_b=distribution_b,
        )


def test_multiple_windows_compare_adjacent_windows() -> None:
    distribution_1 = make_distribution(
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
            10.0,
        ),
    )

    distribution_2 = make_distribution(
        position="col1",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    distribution_3 = make_distribution(
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
            10.0,
        ),
    )

    result = compare_position_distribution_windows(
        position="col1",
        windows=(
            ("window_1", distribution_1),
            ("window_2", distribution_2),
            ("window_3", distribution_3),
        ),
    )

    assert len(result) == 2

    assert result[0].window_a == "window_1"
    assert result[0].window_b == "window_2"

    assert result[1].window_a == "window_2"
    assert result[1].window_b == "window_3"

    assert result[0].mean_absolute_difference == 2.0
    assert result[1].mean_absolute_difference == 2.0


def test_all_windows_must_belong_to_requested_position() -> None:
    distribution_a = make_distribution(
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
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col2",
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
            10.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="All distributions must belong to the requested position",
    ):
        compare_position_distribution_windows(
            position="col1",
            windows=(
                ("window_1", distribution_a),
                ("window_2", distribution_b),
            ),
        )


def test_empty_stability_summary() -> None:
    result = summarize_position_distribution_stability(
        position="col1",
        windows=(),
    )

    assert result.position == "col1"
    assert result.window_count == 0
    assert result.comparison_count == 0
    assert result.total_mean_absolute_difference == 0.0
    assert result.mean_mean_absolute_difference == 0.0
    assert result.minimum_mean_absolute_difference == 0.0
    assert result.maximum_mean_absolute_difference == 0.0


def test_stability_summary_for_single_window() -> None:
    distribution = make_distribution(
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
            10.0,
        ),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        windows=(
            ("window_1", distribution),
        ),
    )

    assert result.position == "col1"
    assert result.window_count == 1
    assert result.comparison_count == 0
    assert result.total_mean_absolute_difference == 0.0
    assert result.mean_mean_absolute_difference == 0.0
    assert result.minimum_mean_absolute_difference == 0.0
    assert result.maximum_mean_absolute_difference == 0.0


def test_stability_summary_calculates_statistics() -> None:
    distribution_1 = make_distribution(
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
            10.0,
        ),
    )

    distribution_2 = make_distribution(
        position="col1",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    distribution_3 = make_distribution(
        position="col1",
        percentages=(
            30.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            -10.0,
        ),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        windows=(
            ("window_1", distribution_1),
            ("window_2", distribution_2),
            ("window_3", distribution_3),
        ),
    )

    assert result.position == "col1"
    assert result.window_count == 3
    assert result.comparison_count == 2
    assert result.total_mean_absolute_difference == 4.0
    assert result.mean_mean_absolute_difference == 2.0
    assert result.minimum_mean_absolute_difference == 2.0
    assert result.maximum_mean_absolute_difference == 2.0