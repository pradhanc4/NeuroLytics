from __future__ import annotations

import pytest

from analytics.position_distribution_stability_comparison import (
    PositionDistributionStabilityComparison,
)
from analytics.position_distribution_stability_comparison_summary import (
    PositionDistributionStabilityComparisonSummary,
    get_position_distribution_stability_comparison_summary,
    summarize_position_distribution_stability_comparisons,
)


def build_comparison(
    position: str,
    stability_level: str,
    total_absolute_change: float,
    average_mean_absolute_change: float,
    minimum_mean_absolute_change: float,
    maximum_mean_absolute_change: float,
    digit_count: int = 10,
    stable_digit_count: int = 3,
    moderate_digit_count: int = 4,
    unstable_digit_count: int = 3,
) -> PositionDistributionStabilityComparison:
    return PositionDistributionStabilityComparison(
        position=position,
        digit_count=digit_count,
        stable_digit_count=stable_digit_count,
        moderate_digit_count=moderate_digit_count,
        unstable_digit_count=unstable_digit_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        minimum_mean_absolute_change=minimum_mean_absolute_change,
        maximum_mean_absolute_change=maximum_mean_absolute_change,
        stability_level=stability_level,
    )


def test_empty_input_returns_empty_summary() -> None:
    summary = summarize_position_distribution_stability_comparisons(
        comparisons=(),
    )

    assert summary.position_count == 0
    assert summary.stable_position_count == 0
    assert summary.moderate_position_count == 0
    assert summary.unstable_position_count == 0
    assert summary.total_absolute_change == 0.0
    assert summary.average_mean_absolute_change == 0.0
    assert summary.minimum_mean_absolute_change == 0.0
    assert summary.maximum_mean_absolute_change == 0.0
    assert summary.comparisons == ()


def test_summary_preserves_position_count() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=18.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.position_count == 2


def test_stable_position_count_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="STABLE",
            total_absolute_change=10.0,
            average_mean_absolute_change=1.8,
            minimum_mean_absolute_change=0.8,
            maximum_mean_absolute_change=3.0,
        ),
        build_comparison(
            position="col3",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.stable_position_count == 2


def test_moderate_position_count_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=22.0,
            average_mean_absolute_change=3.5,
            minimum_mean_absolute_change=1.5,
            maximum_mean_absolute_change=6.0,
        ),
        build_comparison(
            position="col3",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.moderate_position_count == 2


def test_unstable_position_count_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
        build_comparison(
            position="col2",
            stability_level="UNSTABLE",
            total_absolute_change=50.0,
            average_mean_absolute_change=7.0,
            minimum_mean_absolute_change=5.0,
            maximum_mean_absolute_change=9.0,
        ),
        build_comparison(
            position="col3",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.unstable_position_count == 2


def test_classification_counts_equal_position_count() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    classified_count = (
        summary.stable_position_count
        + summary.moderate_position_count
        + summary.unstable_position_count
    )

    assert classified_count == summary.position_count


def test_total_absolute_change_is_summed() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.total_absolute_change == 68.0


def test_average_mean_absolute_change_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.average_mean_absolute_change == pytest.approx(3.5)


def test_minimum_mean_absolute_change_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.minimum_mean_absolute_change == 1.5


def test_maximum_mean_absolute_change_is_calculated() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.maximum_mean_absolute_change == 6.0


def test_comparisons_are_preserved() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert summary.comparisons == comparisons


def test_input_order_is_preserved() -> None:
    comparisons = (
        build_comparison(
            position="col3",
            stability_level="UNSTABLE",
            total_absolute_change=40.0,
            average_mean_absolute_change=6.0,
            minimum_mean_absolute_change=4.0,
            maximum_mean_absolute_change=8.0,
        ),
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    assert tuple(
        comparison.position
        for comparison in summary.comparisons
    ) == ("col3", "col1", "col2")


def test_duplicate_positions_are_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col1",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Duplicate position comparisons",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_empty_position_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Position must not be empty",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_invalid_stability_level_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="INVALID",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Stability level must be STABLE, MODERATE, or UNSTABLE",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_negative_total_absolute_change_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=-1.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Total absolute change",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_negative_average_mean_absolute_change_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=-1.0,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Average mean absolute change",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_negative_minimum_mean_absolute_change_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=-1.0,
            maximum_mean_absolute_change=2.5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Minimum mean absolute change",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_negative_maximum_mean_absolute_change_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=-1.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Maximum mean absolute change",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_minimum_greater_than_maximum_is_rejected() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=5.0,
            maximum_mean_absolute_change=2.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Minimum mean absolute change must not exceed",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_digit_count_must_match_classification_counts() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
            digit_count=10,
            stable_digit_count=2,
            moderate_digit_count=4,
            unstable_digit_count=3,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Stability classification counts must equal digit count",
    ):
        summarize_position_distribution_stability_comparisons(
            comparisons=comparisons,
        )


def test_get_existing_position_returns_comparison() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
        build_comparison(
            position="col2",
            stability_level="MODERATE",
            total_absolute_change=20.0,
            average_mean_absolute_change=3.0,
            minimum_mean_absolute_change=1.0,
            maximum_mean_absolute_change=5.0,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    result = get_position_distribution_stability_comparison_summary(
        summary=summary,
        position="col2",
    )

    assert result == comparisons[1]


def test_get_unknown_position_returns_none() -> None:
    comparisons = (
        build_comparison(
            position="col1",
            stability_level="STABLE",
            total_absolute_change=8.0,
            average_mean_absolute_change=1.5,
            minimum_mean_absolute_change=0.5,
            maximum_mean_absolute_change=2.5,
        ),
    )

    summary = summarize_position_distribution_stability_comparisons(
        comparisons=comparisons,
    )

    result = get_position_distribution_stability_comparison_summary(
        summary=summary,
        position="col9",
    )

    assert result is None


def test_get_empty_position_is_rejected() -> None:
    summary = summarize_position_distribution_stability_comparisons(
        comparisons=(),
    )

    with pytest.raises(
        ValueError,
        match="Position must not be empty",
    ):
        get_position_distribution_stability_comparison_summary(
            summary=summary,
            position="",
        )


def test_summary_is_frozen() -> None:
    summary = PositionDistributionStabilityComparisonSummary(
        position_count=0,
        stable_position_count=0,
        moderate_position_count=0,
        unstable_position_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        minimum_mean_absolute_change=0.0,
        maximum_mean_absolute_change=0.0,
        comparisons=(),
    )

    with pytest.raises(
        AttributeError,
    ):
        summary.position_count = 1