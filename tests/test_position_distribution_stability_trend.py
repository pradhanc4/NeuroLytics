from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_overview import (
    PositionDistributionStabilityOverview,
)
from analytics.position_distribution_stability_trend import (
    DEFAULT_HIGH_TREND_THRESHOLD,
    DEFAULT_LOW_TREND_THRESHOLD,
    HIGH,
    LOW,
    MEDIUM,
    MIXED,
    MODERATE,
    STABLE,
    STABLE_INCREASING,
    STABILITY_DECREASING,
    UNSTABLE,
    PositionDistributionStabilityTrend,
    build_position_distribution_stability_trend,
    classify_stability_direction,
    classify_trend_strength,
)


def make_overview(
    position_count=10,
    stable_position_count=4,
    moderate_position_count=3,
    unstable_position_count=3,
    stable_percentage=40.0,
    moderate_percentage=30.0,
    unstable_percentage=30.0,
    total_absolute_change=0.0,
    average_mean_absolute_change=0.0,
    minimum_mean_absolute_change=0.0,
    maximum_mean_absolute_change=0.0,
    overall_stability_level=STABLE,
):
    return PositionDistributionStabilityOverview(
        position_count=position_count,
        stable_position_count=stable_position_count,
        moderate_position_count=moderate_position_count,
        unstable_position_count=unstable_position_count,
        stable_percentage=stable_percentage,
        moderate_percentage=moderate_percentage,
        unstable_percentage=unstable_percentage,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        minimum_mean_absolute_change=minimum_mean_absolute_change,
        maximum_mean_absolute_change=maximum_mean_absolute_change,
        overall_stability_level=overall_stability_level,
    )


def test_empty_input():
    result = build_position_distribution_stability_trend(())

    assert result.position_count == 0
    assert result.window_count == 0

    assert result.stable_percentage_start == 0.0
    assert result.stable_percentage_end == 0.0
    assert result.stable_percentage_change == 0.0

    assert result.moderate_percentage_start == 0.0
    assert result.moderate_percentage_end == 0.0
    assert result.moderate_percentage_change == 0.0

    assert result.unstable_percentage_start == 0.0
    assert result.unstable_percentage_end == 0.0
    assert result.unstable_percentage_change == 0.0

    assert result.dominant_stability_levels == ()
    assert result.stability_direction == STABLE
    assert result.total_absolute_percentage_change == 0.0
    assert result.mean_absolute_percentage_change == 0.0
    assert result.trend_strength == LOW


def test_single_overview():
    overview = make_overview()

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.position_count == 10
    assert result.window_count == 1

    assert result.stable_percentage_start == 40.0
    assert result.stable_percentage_end == 40.0
    assert result.stable_percentage_change == 0.0

    assert result.moderate_percentage_start == 30.0
    assert result.moderate_percentage_end == 30.0
    assert result.moderate_percentage_change == 0.0

    assert result.unstable_percentage_start == 30.0
    assert result.unstable_percentage_end == 30.0
    assert result.unstable_percentage_change == 0.0

    assert result.stability_direction == STABLE
    assert result.total_absolute_percentage_change == 0.0
    assert result.mean_absolute_percentage_change == 0.0
    assert result.trend_strength == LOW


def test_multiple_overviews():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    second = make_overview(
        stable_percentage=45.0,
        moderate_percentage=30.0,
        unstable_percentage=25.0,
    )

    third = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    result = build_position_distribution_stability_trend(
        (first, second, third)
    )

    assert result.position_count == 10
    assert result.window_count == 3


def test_invalid_input_type():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend(
            ("invalid",)
        )


def test_input_collection_must_be_tuple():
    overview = make_overview()

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend(
            [overview]
        )


def test_negative_position_count():
    overview = make_overview(
        position_count=-1,
        stable_position_count=0,
        moderate_position_count=0,
        unstable_position_count=0,
        stable_percentage=0.0,
        moderate_percentage=0.0,
        unstable_percentage=0.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_position_count_mismatch():
    first = make_overview(position_count=10)

    second = make_overview(
        position_count=12,
        stable_position_count=5,
        moderate_position_count=4,
        unstable_position_count=3,
        stable_percentage=41.6666666667,
        moderate_percentage=33.3333333333,
        unstable_percentage=25.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (first, second)
        )


def test_invalid_percentage_above_100():
    overview = make_overview(
        stable_percentage=101.0,
        moderate_percentage=0.0,
        unstable_percentage=0.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_invalid_negative_percentage():
    overview = make_overview(
        stable_percentage=-1.0,
        moderate_percentage=51.0,
        unstable_percentage=50.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_percentage_sum_inconsistency():
    overview = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_stable_percentage_start_end():
    first = make_overview(
        stable_percentage=35.0,
        moderate_percentage=35.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stable_percentage_start == 35.0
    assert result.stable_percentage_end == 50.0


def test_stable_percentage_change():
    first = make_overview(
        stable_percentage=35.0,
        moderate_percentage=35.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stable_percentage_change == 15.0


def test_moderate_percentage_start_end():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=35.0,
        unstable_percentage=25.0,
    )

    last = make_overview(
        stable_percentage=45.0,
        moderate_percentage=20.0,
        unstable_percentage=35.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.moderate_percentage_start == 35.0
    assert result.moderate_percentage_end == 20.0


def test_moderate_percentage_change():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=35.0,
        unstable_percentage=25.0,
    )

    last = make_overview(
        stable_percentage=45.0,
        moderate_percentage=20.0,
        unstable_percentage=35.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.moderate_percentage_change == -15.0


def test_unstable_percentage_start_end():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=50.0,
        moderate_percentage=20.0,
        unstable_percentage=30.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.unstable_percentage_start == 30.0
    assert result.unstable_percentage_end == 30.0


def test_unstable_percentage_change():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=35.0,
        moderate_percentage=25.0,
        unstable_percentage=40.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.unstable_percentage_change == 10.0


def test_one_window_has_zero_change():
    overview = make_overview(
        stable_percentage=45.0,
        moderate_percentage=35.0,
        unstable_percentage=20.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.stable_percentage_change == 0.0
    assert result.moderate_percentage_change == 0.0
    assert result.unstable_percentage_change == 0.0
    assert result.total_absolute_percentage_change == 0.0
    assert result.mean_absolute_percentage_change == 0.0
    assert result.stability_direction == STABLE
    assert result.trend_strength == LOW


def test_stability_increasing():
    first = make_overview(
        stable_percentage=30.0,
        moderate_percentage=30.0,
        unstable_percentage=40.0,
    )

    last = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stability_direction == STABLE_INCREASING


def test_stability_decreasing():
    first = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    last = make_overview(
        stable_percentage=30.0,
        moderate_percentage=30.0,
        unstable_percentage=40.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stability_direction == STABILITY_DECREASING


def test_stable_direction():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stability_direction == STABLE


def test_mixed_direction():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    last = make_overview(
        stable_percentage=35.0,
        moderate_percentage=40.0,
        unstable_percentage=25.0,
    )

    result = build_position_distribution_stability_trend(
        (first, last)
    )

    assert result.stability_direction == MIXED


def test_stable_dominant_level():
    overview = make_overview(
        stable_percentage=60.0,
        moderate_percentage=25.0,
        unstable_percentage=15.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.dominant_stability_levels == (STABLE,)


def test_moderate_dominant_level():
    overview = make_overview(
        stable_percentage=20.0,
        moderate_percentage=60.0,
        unstable_percentage=20.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.dominant_stability_levels == (MODERATE,)


def test_unstable_dominant_level():
    overview = make_overview(
        stable_percentage=20.0,
        moderate_percentage=25.0,
        unstable_percentage=55.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.dominant_stability_levels == (UNSTABLE,)


def test_stable_moderate_tie():
    overview = make_overview(
        stable_percentage=40.0,
        moderate_percentage=40.0,
        unstable_percentage=20.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert result.dominant_stability_levels == (
        STABLE,
        MODERATE,
    )


def test_three_way_dominant_tie():
    overview = make_overview(
        stable_percentage=40.0,
        moderate_percentage=40.0,
        unstable_percentage=20.0,
    )

    result = build_position_distribution_stability_trend(
        (overview,)
    )

    assert len(result.dominant_stability_levels) == 2


def test_total_absolute_percentage_change():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    second = make_overview(
        stable_percentage=45.0,
        moderate_percentage=25.0,
        unstable_percentage=30.0,
    )

    third = make_overview(
        stable_percentage=50.0,
        moderate_percentage=20.0,
        unstable_percentage=30.0,
    )

    result = build_position_distribution_stability_trend(
        (first, second, third)
    )

    assert result.total_absolute_percentage_change == 20.0


def test_mean_absolute_percentage_change():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    second = make_overview(
        stable_percentage=45.0,
        moderate_percentage=25.0,
        unstable_percentage=30.0,
    )

    third = make_overview(
        stable_percentage=50.0,
        moderate_percentage=20.0,
        unstable_percentage=30.0,
    )

    result = build_position_distribution_stability_trend(
        (first, second, third)
    )

    assert result.mean_absolute_percentage_change == 10.0


def test_multiple_transition_calculation():
    first = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    second = make_overview(
        stable_percentage=50.0,
        moderate_percentage=25.0,
        unstable_percentage=25.0,
    )

    third = make_overview(
        stable_percentage=45.0,
        moderate_percentage=35.0,
        unstable_percentage=20.0,
    )

    result = build_position_distribution_stability_trend(
        (first, second, third)
    )

    assert result.total_absolute_percentage_change == 40.0
    assert result.mean_absolute_percentage_change == 20.0


def test_low_trend_strength():
    result = classify_trend_strength(
        DEFAULT_LOW_TREND_THRESHOLD - 0.1
    )

    assert result == LOW


def test_medium_trend_strength():
    result = classify_trend_strength(
        DEFAULT_LOW_TREND_THRESHOLD
    )

    assert result == MEDIUM


def test_high_trend_strength():
    result = classify_trend_strength(
        DEFAULT_HIGH_TREND_THRESHOLD
    )

    assert result == HIGH


def test_custom_thresholds():
    assert (
        classify_trend_strength(
            3.0,
            low_threshold=3.0,
            high_threshold=7.0,
        )
        == MEDIUM
    )

    assert (
        classify_trend_strength(
            7.0,
            low_threshold=3.0,
            high_threshold=7.0,
        )
        == HIGH
    )


def test_invalid_threshold_order():
    with pytest.raises(ValueError):
        classify_trend_strength(
            2.0,
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_negative_trend_strength_value():
    with pytest.raises(ValueError):
        classify_trend_strength(-1.0)


def test_classify_stability_direction_increasing():
    assert (
        classify_stability_direction(
            10.0,
            -5.0,
            -5.0,
        )
        == STABLE_INCREASING
    )


def test_classify_stability_direction_decreasing():
    assert (
        classify_stability_direction(
            -10.0,
            5.0,
            5.0,
        )
        == STABILITY_DECREASING
    )


def test_classify_stability_direction_stable():
    assert (
        classify_stability_direction(
            0.0,
            0.0,
            0.0,
        )
        == STABLE
    )


def test_classify_stability_direction_mixed():
    assert (
        classify_stability_direction(
            5.0,
            5.0,
            0.0,
        )
        == MIXED
    )


def test_floating_point_percentage_tolerance():
    first = make_overview(
        stable_percentage=33.3333333333,
        moderate_percentage=33.3333333333,
        unstable_percentage=33.3333333334,
    )

    result = build_position_distribution_stability_trend(
        (first,)
    )

    assert result.position_count == 10
    assert result.window_count == 1


def test_input_order_is_preserved():
    first = make_overview(
        stable_percentage=20.0,
        moderate_percentage=30.0,
        unstable_percentage=50.0,
    )

    second = make_overview(
        stable_percentage=40.0,
        moderate_percentage=30.0,
        unstable_percentage=30.0,
    )

    result = build_position_distribution_stability_trend(
        (first, second)
    )

    assert result.stable_percentage_start == 20.0
    assert result.stable_percentage_end == 40.0
    assert result.unstable_percentage_start == 50.0
    assert result.unstable_percentage_end == 30.0


def test_result_type():
    result = build_position_distribution_stability_trend(())

    assert isinstance(
        result,
        PositionDistributionStabilityTrend,
    )


def test_result_is_frozen():
    result = build_position_distribution_stability_trend(())

    with pytest.raises(FrozenInstanceError):
        result.window_count = 10


def test_invalid_overall_stability_level():
    overview = make_overview(
        overall_stability_level="INVALID",
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_empty_position_count_requires_zero_percentages():
    overview = make_overview(
        position_count=0,
        stable_position_count=0,
        moderate_position_count=0,
        unstable_position_count=0,
        stable_percentage=100.0,
        moderate_percentage=0.0,
        unstable_percentage=0.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_count_consistency_is_validated():
    overview = make_overview(
        position_count=10,
        stable_position_count=5,
        moderate_position_count=5,
        unstable_position_count=1,
        stable_percentage=50.0,
        moderate_percentage=40.0,
        unstable_percentage=10.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_minimum_mean_change_cannot_exceed_maximum():
    overview = make_overview(
        minimum_mean_absolute_change=5.0,
        maximum_mean_absolute_change=2.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_negative_total_absolute_change():
    overview = make_overview(
        total_absolute_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_negative_average_mean_absolute_change():
    overview = make_overview(
        average_mean_absolute_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_negative_minimum_mean_absolute_change():
    overview = make_overview(
        minimum_mean_absolute_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )


def test_negative_maximum_mean_absolute_change():
    overview = make_overview(
        maximum_mean_absolute_change=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend(
            (overview,)
        )