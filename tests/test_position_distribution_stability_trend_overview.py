from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_trend import (
    HIGH,
    LOW,
    MEDIUM,
    MIXED,
    STABLE,
    STABLE_INCREASING,
    STABILITY_DECREASING,
)
from analytics.position_distribution_stability_trend_overview import (
    PositionDistributionStabilityTrendOverview,
    build_position_distribution_stability_trend_overview,
)
from analytics.position_distribution_stability_trend_summary import (
    PositionDistributionStabilityTrendSummary,
)


def make_summary(
    trend_count=4,
    stable_increasing_count=None,
    stability_decreasing_count=None,
    stable_count=None,
    mixed_count=None,
    low_strength_count=None,
    medium_strength_count=None,
    high_strength_count=None,
    average_mean_absolute_percentage_change=5.0,
    minimum_mean_absolute_percentage_change=2.0,
    maximum_mean_absolute_percentage_change=8.0,
    total_absolute_percentage_change=20.0,
):
    if (
        stable_increasing_count is None
        and stability_decreasing_count is None
        and stable_count is None
        and mixed_count is None
    ):
        stable_increasing_count = 1
        stability_decreasing_count = 1
        stable_count = 1
        mixed_count = trend_count - 3

    else:
        stable_increasing_count = (
            0
            if stable_increasing_count is None
            else stable_increasing_count
        )
        stability_decreasing_count = (
            0
            if stability_decreasing_count is None
            else stability_decreasing_count
        )
        stable_count = (
            0
            if stable_count is None
            else stable_count
        )
        mixed_count = (
            0
            if mixed_count is None
            else mixed_count
        )

    if (
        low_strength_count is None
        and medium_strength_count is None
        and high_strength_count is None
    ):
        low_strength_count = 1
        medium_strength_count = 1
        high_strength_count = trend_count - 2

    else:
        low_strength_count = (
            0
            if low_strength_count is None
            else low_strength_count
        )
        medium_strength_count = (
            0
            if medium_strength_count is None
            else medium_strength_count
        )
        high_strength_count = (
            0
            if high_strength_count is None
            else high_strength_count
        )

    return PositionDistributionStabilityTrendSummary(
        trend_count=trend_count,
        stable_increasing_count=stable_increasing_count,
        stability_decreasing_count=stability_decreasing_count,
        stable_count=stable_count,
        mixed_count=mixed_count,
        low_strength_count=low_strength_count,
        medium_strength_count=medium_strength_count,
        high_strength_count=high_strength_count,
        average_mean_absolute_percentage_change=(
            average_mean_absolute_percentage_change
        ),
        minimum_mean_absolute_percentage_change=(
            minimum_mean_absolute_percentage_change
        ),
        maximum_mean_absolute_percentage_change=(
            maximum_mean_absolute_percentage_change
        ),
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        trends=(),
    )


def test_empty_input():
    result = (
        build_position_distribution_stability_trend_overview(())
    )

    assert result.summary_count == 0
    assert result.stable_increasing_percentage == 0.0
    assert result.stability_decreasing_percentage == 0.0
    assert result.stable_percentage == 0.0
    assert result.mixed_percentage == 0.0
    assert result.low_strength_percentage == 0.0
    assert result.medium_strength_percentage == 0.0
    assert result.high_strength_percentage == 0.0
    assert result.average_mean_absolute_percentage_change == 0.0
    assert result.minimum_mean_absolute_percentage_change == 0.0
    assert result.maximum_mean_absolute_percentage_change == 0.0
    assert result.total_absolute_percentage_change == 0.0
    assert result.dominant_trend_directions == ()
    assert result.dominant_trend_strengths == ()


def test_single_summary():
    summary = make_summary()

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.summary_count == 1

    assert result.stable_increasing_percentage == 25.0
    assert result.stability_decreasing_percentage == 25.0
    assert result.stable_percentage == 25.0
    assert result.mixed_percentage == 25.0

    assert result.low_strength_percentage == 25.0
    assert result.medium_strength_percentage == 25.0
    assert result.high_strength_percentage == 50.0

    assert result.average_mean_absolute_percentage_change == 5.0
    assert result.minimum_mean_absolute_percentage_change == 2.0
    assert result.maximum_mean_absolute_percentage_change == 8.0
    assert result.total_absolute_percentage_change == 20.0


def test_multiple_summaries():
    first = make_summary()

    second = make_summary(
        trend_count=2,
        stable_increasing_count=1,
        stability_decreasing_count=0,
        stable_count=1,
        mixed_count=0,
        low_strength_count=1,
        medium_strength_count=0,
        high_strength_count=1,
        average_mean_absolute_percentage_change=3.0,
        minimum_mean_absolute_percentage_change=1.0,
        maximum_mean_absolute_percentage_change=5.0,
        total_absolute_percentage_change=6.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    assert result.summary_count == 2


def test_direction_percentages_are_aggregated():
    first = make_summary(
        trend_count=10,
        stable_increasing_count=4,
        stability_decreasing_count=3,
        stable_count=2,
        mixed_count=1,
        low_strength_count=3,
        medium_strength_count=3,
        high_strength_count=4,
    )

    second = make_summary(
        trend_count=10,
        stable_increasing_count=2,
        stability_decreasing_count=4,
        stable_count=3,
        mixed_count=1,
        low_strength_count=2,
        medium_strength_count=4,
        high_strength_count=4,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    assert result.stable_increasing_percentage == 30.0
    assert result.stability_decreasing_percentage == 35.0
    assert result.stable_percentage == 25.0
    assert result.mixed_percentage == 10.0


def test_strength_percentages_are_aggregated():
    first = make_summary(
        trend_count=10,
        stable_increasing_count=3,
        stability_decreasing_count=3,
        stable_count=2,
        mixed_count=2,
        low_strength_count=2,
        medium_strength_count=3,
        high_strength_count=5,
    )

    second = make_summary(
        trend_count=10,
        stable_increasing_count=3,
        stability_decreasing_count=3,
        stable_count=2,
        mixed_count=2,
        low_strength_count=4,
        medium_strength_count=2,
        high_strength_count=4,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    assert result.low_strength_percentage == 30.0
    assert result.medium_strength_percentage == 25.0
    assert result.high_strength_percentage == 45.0


def test_direction_percentages_sum_to_100():
    first = make_summary()

    second = make_summary(
        trend_count=4,
        stable_increasing_count=2,
        stability_decreasing_count=1,
        stable_count=1,
        mixed_count=0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    total = (
        result.stable_increasing_percentage
        + result.stability_decreasing_percentage
        + result.stable_percentage
        + result.mixed_percentage
    )

    assert total == 100.0


def test_strength_percentages_sum_to_100():
    first = make_summary()

    second = make_summary(
        trend_count=4,
        stable_increasing_count=2,
        stability_decreasing_count=1,
        stable_count=1,
        mixed_count=0,
        low_strength_count=2,
        medium_strength_count=1,
        high_strength_count=1,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    total = (
        result.low_strength_percentage
        + result.medium_strength_percentage
        + result.high_strength_percentage
    )

    assert total == 100.0


def test_average_mean_absolute_percentage_change():
    first = make_summary(
        average_mean_absolute_percentage_change=4.0,
    )

    second = make_summary(
        average_mean_absolute_percentage_change=8.0,
    )

    third = make_summary(
        average_mean_absolute_percentage_change=6.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second, third)
    )

    assert result.average_mean_absolute_percentage_change == 6.0


def test_minimum_mean_absolute_percentage_change():
    first = make_summary(
        minimum_mean_absolute_percentage_change=4.0,
    )

    second = make_summary(
        minimum_mean_absolute_percentage_change=1.0,
    )

    third = make_summary(
        minimum_mean_absolute_percentage_change=3.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second, third)
    )

    assert result.minimum_mean_absolute_percentage_change == 1.0


def test_maximum_mean_absolute_percentage_change():
    first = make_summary(
        maximum_mean_absolute_percentage_change=4.0,
    )

    second = make_summary(
        maximum_mean_absolute_percentage_change=10.0,
    )

    third = make_summary(
        maximum_mean_absolute_percentage_change=7.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second, third)
    )

    assert result.maximum_mean_absolute_percentage_change == 10.0


def test_total_absolute_percentage_change():
    first = make_summary(
        total_absolute_percentage_change=10.0,
    )

    second = make_summary(
        total_absolute_percentage_change=20.0,
    )

    third = make_summary(
        total_absolute_percentage_change=5.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second, third)
    )

    assert result.total_absolute_percentage_change == 35.0


def test_dominant_direction_stable_increasing():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=6,
        stability_decreasing_count=2,
        stable_count=1,
        mixed_count=1,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (
        STABLE_INCREASING,
    )


def test_dominant_direction_stability_decreasing():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=1,
        stability_decreasing_count=6,
        stable_count=2,
        mixed_count=1,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (
        STABILITY_DECREASING,
    )


def test_dominant_direction_stable():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=1,
        stability_decreasing_count=2,
        stable_count=6,
        mixed_count=1,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (STABLE,)


def test_dominant_direction_mixed():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=1,
        stability_decreasing_count=2,
        stable_count=1,
        mixed_count=6,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (MIXED,)


def test_dominant_direction_tie():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=4,
        stability_decreasing_count=4,
        stable_count=1,
        mixed_count=1,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (
        STABLE_INCREASING,
        STABILITY_DECREASING,
    )


def test_three_way_direction_tie():
    summary = make_summary(
        trend_count=9,
        stable_increasing_count=3,
        stability_decreasing_count=3,
        stable_count=3,
        mixed_count=0,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (
        STABLE_INCREASING,
        STABILITY_DECREASING,
        STABLE,
    )


def test_dominant_strength_low():
    summary = make_summary(
        trend_count=10,
        low_strength_count=6,
        medium_strength_count=2,
        high_strength_count=2,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (LOW,)


def test_dominant_strength_medium():
    summary = make_summary(
        trend_count=10,
        low_strength_count=2,
        medium_strength_count=6,
        high_strength_count=2,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (MEDIUM,)


def test_dominant_strength_high():
    summary = make_summary(
        trend_count=10,
        low_strength_count=2,
        medium_strength_count=2,
        high_strength_count=6,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (HIGH,)


def test_dominant_strength_tie():
    summary = make_summary(
        trend_count=10,
        low_strength_count=4,
        medium_strength_count=4,
        high_strength_count=2,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (
        LOW,
        MEDIUM,
    )


def test_three_way_strength_tie():
    summary = make_summary(
        trend_count=9,
        low_strength_count=3,
        medium_strength_count=3,
        high_strength_count=3,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (
        LOW,
        MEDIUM,
        HIGH,
    )


def test_invalid_input_type():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_overview(
            ("invalid",)
        )


def test_input_collection_must_be_tuple():
    summary = make_summary()

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_overview(
            [summary]
        )


def test_negative_trend_count():
    summary = make_summary(
        trend_count=-1,
        stable_increasing_count=0,
        stability_decreasing_count=0,
        stable_count=0,
        mixed_count=0,
        low_strength_count=0,
        medium_strength_count=0,
        high_strength_count=0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_direction_count():
    summary = make_summary(
        trend_count=4,
        stable_increasing_count=-1,
        stability_decreasing_count=2,
        stable_count=2,
        mixed_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_strength_count():
    summary = make_summary(
        trend_count=4,
        stable_increasing_count=1,
        stability_decreasing_count=1,
        stable_count=1,
        mixed_count=1,
        low_strength_count=-1,
        medium_strength_count=2,
        high_strength_count=3,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_direction_counts_must_equal_trend_count():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=2,
        stability_decreasing_count=2,
        stable_count=2,
        mixed_count=2,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_strength_counts_must_equal_trend_count():
    summary = make_summary(
        trend_count=10,
        stable_increasing_count=3,
        stability_decreasing_count=3,
        stable_count=2,
        mixed_count=2,
        low_strength_count=2,
        medium_strength_count=2,
        high_strength_count=2,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_average_mean_absolute_percentage_change():
    summary = make_summary(
        average_mean_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_minimum_mean_absolute_percentage_change():
    summary = make_summary(
        minimum_mean_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_maximum_mean_absolute_percentage_change():
    summary = make_summary(
        maximum_mean_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_negative_total_absolute_percentage_change():
    summary = make_summary(
        total_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_overview(
            (summary,)
        )


def test_result_type():
    result = build_position_distribution_stability_trend_overview(
        ()
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendOverview,
    )


def test_result_is_frozen():
    result = build_position_distribution_stability_trend_overview(
        ()
    )

    with pytest.raises(FrozenInstanceError):
        result.summary_count = 10


def test_multiple_summary_aggregation():
    first = make_summary(
        trend_count=4,
        stable_increasing_count=2,
        stability_decreasing_count=1,
        stable_count=1,
        mixed_count=0,
        low_strength_count=1,
        medium_strength_count=1,
        high_strength_count=2,
        average_mean_absolute_percentage_change=4.0,
        minimum_mean_absolute_percentage_change=2.0,
        maximum_mean_absolute_percentage_change=6.0,
        total_absolute_percentage_change=12.0,
    )

    second = make_summary(
        trend_count=6,
        stable_increasing_count=1,
        stability_decreasing_count=2,
        stable_count=1,
        mixed_count=2,
        low_strength_count=2,
        medium_strength_count=2,
        high_strength_count=2,
        average_mean_absolute_percentage_change=8.0,
        minimum_mean_absolute_percentage_change=4.0,
        maximum_mean_absolute_percentage_change=10.0,
        total_absolute_percentage_change=24.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (first, second)
    )

    assert result.summary_count == 2

    assert result.stable_increasing_percentage == 30.0
    assert result.stability_decreasing_percentage == 30.0
    assert result.stable_percentage == 20.0
    assert result.mixed_percentage == 20.0

    assert result.low_strength_percentage == 30.0
    assert result.medium_strength_percentage == 30.0
    assert result.high_strength_percentage == 40.0

    assert result.average_mean_absolute_percentage_change == 6.0
    assert result.minimum_mean_absolute_percentage_change == 2.0
    assert result.maximum_mean_absolute_percentage_change == 10.0
    assert result.total_absolute_percentage_change == 36.0


def test_zero_count_summaries_are_valid():
    summary = make_summary(
        trend_count=0,
        stable_increasing_count=0,
        stability_decreasing_count=0,
        stable_count=0,
        mixed_count=0,
        low_strength_count=0,
        medium_strength_count=0,
        high_strength_count=0,
        average_mean_absolute_percentage_change=0.0,
        minimum_mean_absolute_percentage_change=0.0,
        maximum_mean_absolute_percentage_change=0.0,
        total_absolute_percentage_change=0.0,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.summary_count == 1
    assert result.stable_increasing_percentage == 0.0
    assert result.stability_decreasing_percentage == 0.0
    assert result.stable_percentage == 0.0
    assert result.mixed_percentage == 0.0
    assert result.low_strength_percentage == 0.0
    assert result.medium_strength_percentage == 0.0
    assert result.high_strength_percentage == 0.0
    assert result.dominant_trend_directions == ()
    assert result.dominant_trend_strengths == ()


def test_direction_order_is_preserved_for_ties():
    summary = make_summary(
        trend_count=8,
        stable_increasing_count=2,
        stability_decreasing_count=2,
        stable_count=2,
        mixed_count=2,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_directions == (
        STABLE_INCREASING,
        STABILITY_DECREASING,
        STABLE,
        MIXED,
    )


def test_strength_order_is_preserved_for_ties():
    summary = make_summary(
        trend_count=9,
        low_strength_count=3,
        medium_strength_count=3,
        high_strength_count=3,
    )

    result = build_position_distribution_stability_trend_overview(
        (summary,)
    )

    assert result.dominant_trend_strengths == (
        LOW,
        MEDIUM,
        HIGH,
    )


def test_source_summary_values_are_not_mutated():
    summary = make_summary()

    original_values = (
        summary.trend_count,
        summary.stable_increasing_count,
        summary.stability_decreasing_count,
        summary.stable_count,
        summary.mixed_count,
        summary.low_strength_count,
        summary.medium_strength_count,
        summary.high_strength_count,
        summary.average_mean_absolute_percentage_change,
        summary.minimum_mean_absolute_percentage_change,
        summary.maximum_mean_absolute_percentage_change,
        summary.total_absolute_percentage_change,
    )

    build_position_distribution_stability_trend_overview(
        (summary,)
    )

    current_values = (
        summary.trend_count,
        summary.stable_increasing_count,
        summary.stability_decreasing_count,
        summary.stable_count,
        summary.mixed_count,
        summary.low_strength_count,
        summary.medium_strength_count,
        summary.high_strength_count,
        summary.average_mean_absolute_percentage_change,
        summary.minimum_mean_absolute_percentage_change,
        summary.maximum_mean_absolute_percentage_change,
        summary.total_absolute_percentage_change,
    )

    assert current_values == original_values