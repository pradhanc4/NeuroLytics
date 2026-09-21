from __future__ import annotations

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_stability import (
    PositionDistributionStabilityComparison,
    PositionDistributionStabilitySummary,
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


def test_empty_windows_return_empty_comparisons() -> None:
    result = compare_position_distribution_windows(
        position="col1",
        windows=(),
    )

    assert result == ()


def test_single_window_returns_empty_comparisons() -> None:
    distribution = make_distribution(
        position="col1",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    result = compare_position_distribution_windows(
        position="col1",
        windows=(
            ("window_1", distribution),
        ),
    )

    assert result == ()


def test_two_windows_create_one_comparison() -> None:
    distribution_a = make_distribution(
        position="col1",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col1",
        percentages=(20.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0),
    )

    result = compare_position_distribution_windows(
        position="col1",
        windows=(
            ("window_1", distribution_a),
            ("window_2", distribution_b),
        ),
    )

    assert len(result) == 1
    assert isinstance(
        result[0],
        PositionDistributionStabilityComparison,
    )
    assert result[0].position == "col1"
    assert result[0].window_a == "window_1"
    assert result[0].window_b == "window_2"
    assert result[0].mean_absolute_difference == pytest.approx(2.0)


def test_window_pair_preserves_window_names() -> None:
    distribution_a = make_distribution(
        position="col2",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col2",
        percentages=(20.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0),
    )

    result = compare_position_distribution_window_pair(
        position="col2",
        window_a="previous",
        distribution_a=distribution_a,
        window_b="current",
        distribution_b=distribution_b,
    )

    assert result.window_a == "previous"
    assert result.window_b == "current"


def test_identical_windows_have_zero_difference() -> None:
    distribution_a = make_distribution(
        position="col3",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col3",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    result = compare_position_distribution_window_pair(
        position="col3",
        window_a="window_a",
        distribution_a=distribution_a,
        window_b="window_b",
        distribution_b=distribution_b,
    )

    assert result.mean_absolute_difference == pytest.approx(0.0)


def test_multiple_windows_create_adjacent_comparisons() -> None:
    distribution_1 = make_distribution(
        position="col4",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_2 = make_distribution(
        position="col4",
        percentages=(20.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0),
    )

    distribution_3 = make_distribution(
        position="col4",
        percentages=(30.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0, 0.0),
    )

    result = compare_position_distribution_windows(
        position="col4",
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


def test_position_mismatch_in_first_distribution_is_rejected() -> None:
    distribution = make_distribution(
        position="col2",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    with pytest.raises(ValueError, match="First distribution position"):
        compare_position_distribution_window_pair(
            position="col1",
            window_a="window_1",
            distribution_a=distribution,
            window_b="window_2",
            distribution_b=distribution,
        )


def test_position_mismatch_in_second_distribution_is_rejected() -> None:
    distribution_a = make_distribution(
        position="col1",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col2",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    with pytest.raises(ValueError, match="Second distribution position"):
        compare_position_distribution_window_pair(
            position="col1",
            window_a="window_1",
            distribution_a=distribution_a,
            window_b="window_2",
            distribution_b=distribution_b,
        )


def test_multiple_window_position_mismatch_is_rejected() -> None:
    distribution_a = make_distribution(
        position="col1",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col2",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    with pytest.raises(ValueError, match="All distributions"):
        compare_position_distribution_windows(
            position="col1",
            windows=(
                ("window_1", distribution_a),
                ("window_2", distribution_b),
            ),
        )


def test_summary_for_empty_windows() -> None:
    result = summarize_position_distribution_stability(
        position="col1",
        windows=(),
    )

    assert isinstance(
        result,
        PositionDistributionStabilitySummary,
    )
    assert result.position == "col1"
    assert result.window_count == 0
    assert result.comparison_count == 0
    assert result.total_mean_absolute_difference == 0.0
    assert result.mean_mean_absolute_difference == 0.0
    assert result.minimum_mean_absolute_difference == 0.0
    assert result.maximum_mean_absolute_difference == 0.0


def test_summary_calculates_stability_metrics() -> None:
    distribution_1 = make_distribution(
        position="col5",
        percentages=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
    )

    distribution_2 = make_distribution(
        position="col5",
        percentages=(20.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0),
    )

    distribution_3 = make_distribution(
        position="col5",
        percentages=(30.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 0.0, 0.0),
    )

    result = summarize_position_distribution_stability(
        position="col5",
        windows=(
            ("window_1", distribution_1),
            ("window_2", distribution_2),
            ("window_3", distribution_3),
        ),
    )

    assert result.position == "col5"
    assert result.window_count == 3
    assert result.comparison_count == 2
    assert result.total_mean_absolute_difference == pytest.approx(4.0)
    assert result.mean_mean_absolute_difference == pytest.approx(2.0)
    assert result.minimum_mean_absolute_difference == pytest.approx(2.0)
    assert result.maximum_mean_absolute_difference == pytest.approx(2.0)