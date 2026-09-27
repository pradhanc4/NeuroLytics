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
    PositionDistributionStabilityTrend,
)
from analytics.position_distribution_stability_trend_summary import (
    PositionDistributionStabilityTrendSummary,
    get_position_distribution_stability_trend_summary,
    summarize_position_distribution_stability_trends,
)


def make_trend(
    position_count=10,
    window_count=3,
    stable_percentage_start=40.0,
    stable_percentage_end=45.0,
    stable_percentage_change=5.0,
    moderate_percentage_start=30.0,
    moderate_percentage_end=30.0,
    moderate_percentage_change=0.0,
    unstable_percentage_start=30.0,
    unstable_percentage_end=25.0,
    unstable_percentage_change=-5.0,
    dominant_stability_levels=(STABLE,),
    stability_direction=STABLE_INCREASING,
    total_absolute_percentage_change=10.0,
    mean_absolute_percentage_change=5.0,
    trend_strength=HIGH,
):
    return PositionDistributionStabilityTrend(
        position_count=position_count,
        window_count=window_count,
        stable_percentage_start=stable_percentage_start,
        stable_percentage_end=stable_percentage_end,
        stable_percentage_change=stable_percentage_change,
        moderate_percentage_start=moderate_percentage_start,
        moderate_percentage_end=moderate_percentage_end,
        moderate_percentage_change=moderate_percentage_change,
        unstable_percentage_start=unstable_percentage_start,
        unstable_percentage_end=unstable_percentage_end,
        unstable_percentage_change=unstable_percentage_change,
        dominant_stability_levels=dominant_stability_levels,
        stability_direction=stability_direction,
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        mean_absolute_percentage_change=(
            mean_absolute_percentage_change
        ),
        trend_strength=trend_strength,
    )


def test_empty_input():
    result = (
        summarize_position_distribution_stability_trends(())
    )

    assert result.trend_count == 0

    assert result.stable_increasing_count == 0
    assert result.stability_decreasing_count == 0
    assert result.stable_count == 0
    assert result.mixed_count == 0

    assert result.low_strength_count == 0
    assert result.medium_strength_count == 0
    assert result.high_strength_count == 0

    assert (
        result.average_mean_absolute_percentage_change
        == 0.0
    )
    assert (
        result.minimum_mean_absolute_percentage_change
        == 0.0
    )
    assert (
        result.maximum_mean_absolute_percentage_change
        == 0.0
    )
    assert result.total_absolute_percentage_change == 0.0
    assert result.trends == ()


def test_single_trend():
    trend = make_trend()

    result = summarize_position_distribution_stability_trends(
        (trend,)
    )

    assert result.trend_count == 1
    assert result.stable_increasing_count == 1
    assert result.stability_decreasing_count == 0
    assert result.stable_count == 0
    assert result.mixed_count == 0

    assert result.low_strength_count == 0
    assert result.medium_strength_count == 0
    assert result.high_strength_count == 1

    assert (
        result.average_mean_absolute_percentage_change
        == 5.0
    )
    assert (
        result.minimum_mean_absolute_percentage_change
        == 5.0
    )
    assert (
        result.maximum_mean_absolute_percentage_change
        == 5.0
    )
    assert result.total_absolute_percentage_change == 10.0
    assert result.trends == (trend,)


def test_multiple_trends():
    first = make_trend()

    second = make_trend(
        stability_direction=STABILITY_DECREASING,
        total_absolute_percentage_change=6.0,
        mean_absolute_percentage_change=3.0,
        trend_strength=MEDIUM,
    )

    third = make_trend(
        stability_direction=STABLE,
        total_absolute_percentage_change=2.0,
        mean_absolute_percentage_change=1.0,
        trend_strength=LOW,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.trend_count == 3
    assert result.trends == (first, second, third)


def test_stable_increasing_count():
    first = make_trend(
        stability_direction=STABLE_INCREASING,
    )

    second = make_trend(
        stability_direction=STABLE_INCREASING,
    )

    third = make_trend(
        stability_direction=STABLE,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.stable_increasing_count == 2


def test_stability_decreasing_count():
    first = make_trend(
        stability_direction=STABILITY_DECREASING,
    )

    second = make_trend(
        stability_direction=STABLE,
    )

    third = make_trend(
        stability_direction=STABILITY_DECREASING,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.stability_decreasing_count == 2


def test_stable_count():
    first = make_trend(
        stability_direction=STABLE,
    )

    second = make_trend(
        stability_direction=STABLE,
    )

    third = make_trend(
        stability_direction=MIXED,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.stable_count == 2


def test_mixed_count():
    first = make_trend(
        stability_direction=MIXED,
    )

    second = make_trend(
        stability_direction=MIXED,
    )

    third = make_trend(
        stability_direction=STABLE,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.mixed_count == 2


def test_direction_counts_cover_all_trends():
    trends = (
        make_trend(
            stability_direction=STABLE_INCREASING,
        ),
        make_trend(
            stability_direction=STABILITY_DECREASING,
        ),
        make_trend(
            stability_direction=STABLE,
        ),
        make_trend(
            stability_direction=MIXED,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    total_direction_count = (
        result.stable_increasing_count
        + result.stability_decreasing_count
        + result.stable_count
        + result.mixed_count
    )

    assert total_direction_count == result.trend_count


def test_low_strength_count():
    trends = (
        make_trend(
            trend_strength=LOW,
        ),
        make_trend(
            trend_strength=LOW,
        ),
        make_trend(
            trend_strength=MEDIUM,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert result.low_strength_count == 2


def test_medium_strength_count():
    trends = (
        make_trend(
            trend_strength=MEDIUM,
        ),
        make_trend(
            trend_strength=MEDIUM,
        ),
        make_trend(
            trend_strength=HIGH,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert result.medium_strength_count == 2


def test_high_strength_count():
    trends = (
        make_trend(
            trend_strength=HIGH,
        ),
        make_trend(
            trend_strength=HIGH,
        ),
        make_trend(
            trend_strength=LOW,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert result.high_strength_count == 2


def test_strength_counts_cover_all_trends():
    trends = (
        make_trend(
            trend_strength=LOW,
        ),
        make_trend(
            trend_strength=MEDIUM,
        ),
        make_trend(
            trend_strength=HIGH,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    total_strength_count = (
        result.low_strength_count
        + result.medium_strength_count
        + result.high_strength_count
    )

    assert total_strength_count == result.trend_count


def test_average_mean_absolute_percentage_change():
    trends = (
        make_trend(
            mean_absolute_percentage_change=2.0,
        ),
        make_trend(
            mean_absolute_percentage_change=4.0,
        ),
        make_trend(
            mean_absolute_percentage_change=6.0,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert (
        result.average_mean_absolute_percentage_change
        == 4.0
    )


def test_minimum_mean_absolute_percentage_change():
    trends = (
        make_trend(
            mean_absolute_percentage_change=8.0,
        ),
        make_trend(
            mean_absolute_percentage_change=2.0,
        ),
        make_trend(
            mean_absolute_percentage_change=5.0,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert (
        result.minimum_mean_absolute_percentage_change
        == 2.0
    )


def test_maximum_mean_absolute_percentage_change():
    trends = (
        make_trend(
            mean_absolute_percentage_change=8.0,
        ),
        make_trend(
            mean_absolute_percentage_change=2.0,
        ),
        make_trend(
            mean_absolute_percentage_change=5.0,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert (
        result.maximum_mean_absolute_percentage_change
        == 8.0
    )


def test_total_absolute_percentage_change():
    trends = (
        make_trend(
            total_absolute_percentage_change=10.0,
        ),
        make_trend(
            total_absolute_percentage_change=20.0,
        ),
        make_trend(
            total_absolute_percentage_change=5.0,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert result.total_absolute_percentage_change == 35.0


def test_input_order_is_preserved():
    first = make_trend(
        mean_absolute_percentage_change=1.0,
    )

    second = make_trend(
        mean_absolute_percentage_change=5.0,
    )

    third = make_trend(
        mean_absolute_percentage_change=10.0,
    )

    result = summarize_position_distribution_stability_trends(
        (first, second, third)
    )

    assert result.trends[0] is first
    assert result.trends[1] is second
    assert result.trends[2] is third


def test_invalid_input_type():
    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trends(
            ("invalid",)
        )


def test_input_collection_must_be_tuple():
    trend = make_trend()

    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trends(
            [trend]
        )


def test_negative_position_count():
    trend = make_trend(
        position_count=-1,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_window_count():
    trend = make_trend(
        window_count=-1,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_stable_percentage_start():
    trend = make_trend(
        stable_percentage_start=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_stable_percentage_end():
    trend = make_trend(
        stable_percentage_end=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_moderate_percentage_start():
    trend = make_trend(
        moderate_percentage_start=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_moderate_percentage_end():
    trend = make_trend(
        moderate_percentage_end=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_unstable_percentage_start():
    trend = make_trend(
        unstable_percentage_start=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_unstable_percentage_end():
    trend = make_trend(
        unstable_percentage_end=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_percentage_above_100():
    trend = make_trend(
        stable_percentage_end=101.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_total_absolute_percentage_change():
    trend = make_trend(
        total_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_negative_mean_absolute_percentage_change():
    trend = make_trend(
        mean_absolute_percentage_change=-1.0,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_invalid_stability_direction():
    trend = make_trend(
        stability_direction="INVALID",
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_invalid_trend_strength():
    trend = make_trend(
        trend_strength="INVALID",
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trends(
            (trend,)
        )


def test_result_type():
    result = summarize_position_distribution_stability_trends(
        ()
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendSummary,
    )


def test_result_is_frozen():
    result = summarize_position_distribution_stability_trends(
        ()
    )

    with pytest.raises(FrozenInstanceError):
        result.trend_count = 10


def test_lookup_returns_same_summary():
    summary = summarize_position_distribution_stability_trends(
        (make_trend(),)
    )

    result = (
        get_position_distribution_stability_trend_summary(
            summary
        )
    )

    assert result is summary


def test_lookup_rejects_invalid_type():
    with pytest.raises(TypeError):
        get_position_distribution_stability_trend_summary(
            "invalid"
        )


def test_single_trend_preserves_all_source_data():
    trend = make_trend(
        position_count=12,
        window_count=5,
        stable_percentage_start=25.0,
        stable_percentage_end=55.0,
        stable_percentage_change=30.0,
        moderate_percentage_start=35.0,
        moderate_percentage_end=25.0,
        moderate_percentage_change=-10.0,
        unstable_percentage_start=40.0,
        unstable_percentage_end=20.0,
        unstable_percentage_change=-20.0,
        dominant_stability_levels=(STABLE,),
        stability_direction=STABLE_INCREASING,
        total_absolute_percentage_change=60.0,
        mean_absolute_percentage_change=15.0,
        trend_strength=HIGH,
    )

    result = summarize_position_distribution_stability_trends(
        (trend,)
    )

    assert result.trends == (trend,)
    assert result.trend_count == 1
    assert result.total_absolute_percentage_change == 60.0
    assert (
        result.average_mean_absolute_percentage_change
        == 15.0
    )
    assert (
        result.minimum_mean_absolute_percentage_change
        == 15.0
    )
    assert (
        result.maximum_mean_absolute_percentage_change
        == 15.0
    )


def test_all_direction_and_strength_categories_together():
    trends = (
        make_trend(
            stability_direction=STABLE_INCREASING,
            trend_strength=LOW,
        ),
        make_trend(
            stability_direction=STABILITY_DECREASING,
            trend_strength=MEDIUM,
        ),
        make_trend(
            stability_direction=STABLE,
            trend_strength=HIGH,
        ),
        make_trend(
            stability_direction=MIXED,
            trend_strength=HIGH,
        ),
    )

    result = summarize_position_distribution_stability_trends(
        trends
    )

    assert result.trend_count == 4

    assert result.stable_increasing_count == 1
    assert result.stability_decreasing_count == 1
    assert result.stable_count == 1
    assert result.mixed_count == 1

    assert result.low_strength_count == 1
    assert result.medium_strength_count == 1
    assert result.high_strength_count == 2