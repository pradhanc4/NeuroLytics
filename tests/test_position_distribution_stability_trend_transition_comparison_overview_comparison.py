from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparison,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison,
    compare_position_distribution_stability_trend_transition_comparison_overviews,
)


def make_overview(
    *,
    transition_count=10,
    low_increase=20.0,
    low_decrease=30.0,
    low_unchanged=50.0,
    medium_increase=30.0,
    medium_decrease=20.0,
    medium_unchanged=50.0,
    high_increase=40.0,
    high_decrease=20.0,
    high_unchanged=40.0,
    average_movement=4.0,
    minimum_movement=1.0,
    maximum_movement=8.0,
    total_movement=40.0,
    dominant_low=("UNCHANGED",),
    dominant_medium=("UNCHANGED",),
    dominant_high=("INCREASE",),
):
    return PositionDistributionStabilityTrendTransitionComparisonOverview(
        transition_count=transition_count,
        low_increase_percentage=low_increase,
        low_decrease_percentage=low_decrease,
        low_unchanged_percentage=low_unchanged,
        medium_increase_percentage=medium_increase,
        medium_decrease_percentage=medium_decrease,
        medium_unchanged_percentage=medium_unchanged,
        high_increase_percentage=high_increase,
        high_decrease_percentage=high_decrease,
        high_unchanged_percentage=high_unchanged,
        average_total_absolute_percentage_movement=average_movement,
        minimum_total_absolute_percentage_movement=minimum_movement,
        maximum_total_absolute_percentage_movement=maximum_movement,
        total_absolute_percentage_movement=total_movement,
        dominant_low_directions=dominant_low,
        dominant_medium_directions=dominant_medium,
        dominant_high_directions=dominant_high,
    )


def test_empty_input_returns_zero_comparison():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            ()
        )
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparison,
    )
    assert result.overview_count == 0

    assert result.low_increase_percentage_start == 0.0
    assert result.low_increase_percentage_end == 0.0
    assert result.low_increase_percentage_change == 0.0

    assert result.medium_increase_percentage_start == 0.0
    assert result.medium_increase_percentage_end == 0.0
    assert result.medium_increase_percentage_change == 0.0

    assert result.high_increase_percentage_start == 0.0
    assert result.high_increase_percentage_end == 0.0
    assert result.high_increase_percentage_change == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_single_overview_preserves_start_and_end_values():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )
    )

    assert result.overview_count == 1

    assert result.low_increase_percentage_start == 20.0
    assert result.low_increase_percentage_end == 20.0
    assert result.low_increase_percentage_change == 0.0

    assert result.low_decrease_percentage_start == 30.0
    assert result.low_decrease_percentage_end == 30.0
    assert result.low_decrease_percentage_change == 0.0

    assert result.low_unchanged_percentage_start == 50.0
    assert result.low_unchanged_percentage_end == 50.0
    assert result.low_unchanged_percentage_change == 0.0


def test_single_overview_has_zero_movement():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )
    )

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_start_values_are_taken_from_first_overview():
    first = make_overview(
        low_increase=10.0,
        low_decrease=20.0,
        low_unchanged=70.0,
    )
    second = make_overview(
        low_increase=30.0,
        low_decrease=30.0,
        low_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_start == 10.0
    assert result.low_decrease_percentage_start == 20.0
    assert result.low_unchanged_percentage_start == 70.0


def test_end_values_are_taken_from_last_overview():
    first = make_overview()
    second = make_overview(
        low_increase=35.0,
        low_decrease=25.0,
        low_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_end == 35.0
    assert result.low_decrease_percentage_end == 25.0
    assert result.low_unchanged_percentage_end == 40.0


def test_low_increase_percentage_change_is_end_minus_start():
    first = make_overview(
        low_increase=20.0,
        low_decrease=30.0,
        low_unchanged=50.0,
    )
    second = make_overview(
        low_increase=35.0,
        low_decrease=25.0,
        low_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == 15.0
    assert result.low_decrease_percentage_change == -5.0
    assert result.low_unchanged_percentage_change == -10.0


def test_medium_percentage_changes_are_calculated():
    first = make_overview(
        medium_increase=20.0,
        medium_decrease=30.0,
        medium_unchanged=50.0,
    )
    second = make_overview(
        medium_increase=40.0,
        medium_decrease=25.0,
        medium_unchanged=35.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.medium_increase_percentage_change == 20.0
    assert result.medium_decrease_percentage_change == -5.0
    assert result.medium_unchanged_percentage_change == -15.0


def test_high_percentage_changes_are_calculated():
    first = make_overview(
        high_increase=40.0,
        high_decrease=20.0,
        high_unchanged=40.0,
    )
    second = make_overview(
        high_increase=25.0,
        high_decrease=35.0,
        high_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.high_increase_percentage_change == -15.0
    assert result.high_decrease_percentage_change == 15.0
    assert result.high_unchanged_percentage_change == 0.0


def test_movement_metrics_use_first_and_last_overviews():
    first = make_overview(
        average_movement=2.0,
        minimum_movement=0.5,
        maximum_movement=4.0,
        total_movement=20.0,
    )
    second = make_overview(
        average_movement=6.0,
        minimum_movement=1.5,
        maximum_movement=10.0,
        total_movement=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.average_total_absolute_percentage_movement_start == 2.0
    assert result.average_total_absolute_percentage_movement_end == 6.0
    assert result.average_total_absolute_percentage_movement_change == 4.0

    assert result.minimum_total_absolute_percentage_movement_start == 0.5
    assert result.minimum_total_absolute_percentage_movement_end == 1.5
    assert result.minimum_total_absolute_percentage_movement_change == 1.0

    assert result.maximum_total_absolute_percentage_movement_start == 4.0
    assert result.maximum_total_absolute_percentage_movement_end == 10.0
    assert result.maximum_total_absolute_percentage_movement_change == 6.0

    assert result.total_absolute_percentage_movement_start == 20.0
    assert result.total_absolute_percentage_movement_end == 60.0
    assert result.total_absolute_percentage_movement_change == 40.0


def test_two_overviews_calculate_total_absolute_percentage_movement():
    first = make_overview(
        low_increase=20.0,
        low_decrease=30.0,
        low_unchanged=50.0,
        medium_increase=30.0,
        medium_decrease=20.0,
        medium_unchanged=50.0,
        high_increase=40.0,
        high_decrease=20.0,
        high_unchanged=40.0,
    )

    second = make_overview(
        low_increase=30.0,
        low_decrease=20.0,
        low_unchanged=50.0,
        medium_increase=40.0,
        medium_decrease=10.0,
        medium_unchanged=50.0,
        high_increase=30.0,
        high_decrease=30.0,
        high_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    expected = (
        abs(30.0 - 20.0)
        + abs(20.0 - 30.0)
        + abs(50.0 - 50.0)
        + abs(40.0 - 30.0)
        + abs(10.0 - 20.0)
        + abs(50.0 - 50.0)
        + abs(30.0 - 40.0)
        + abs(30.0 - 20.0)
        + abs(40.0 - 40.0)
    )

    assert result.total_absolute_percentage_movement == expected
    assert result.mean_absolute_percentage_movement == expected


def test_three_overviews_use_all_consecutive_transitions_for_movement():
    first = make_overview(
        low_increase=10.0,
        low_decrease=20.0,
        low_unchanged=70.0,
        medium_increase=20.0,
        medium_decrease=30.0,
        medium_unchanged=50.0,
        high_increase=30.0,
        high_decrease=20.0,
        high_unchanged=50.0,
    )

    second = make_overview(
        low_increase=20.0,
        low_decrease=30.0,
        low_unchanged=50.0,
        medium_increase=30.0,
        medium_decrease=20.0,
        medium_unchanged=50.0,
        high_increase=40.0,
        high_decrease=30.0,
        high_unchanged=30.0,
    )

    third = make_overview(
        low_increase=30.0,
        low_decrease=20.0,
        low_unchanged=50.0,
        medium_increase=40.0,
        medium_decrease=20.0,
        medium_unchanged=40.0,
        high_increase=30.0,
        high_decrease=20.0,
        high_unchanged=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second, third)
        )
    )

    first_movement = (
        10.0
        + 10.0
        + 20.0
        + 10.0
        + 10.0
        + 0.0
        + 10.0
        + 10.0
        + 20.0
    )

    second_movement = (
        10.0
        + 10.0
        + 0.0
        + 10.0
        + 0.0
        + 10.0
        + 10.0
        + 10.0
        + 20.0
    )

    expected_total = first_movement + second_movement

    assert result.total_absolute_percentage_movement == expected_total
    assert (
        result.mean_absolute_percentage_movement
        == expected_total / 2
    )


def test_first_and_last_changes_ignore_intermediate_overviews():
    first = make_overview(
        low_increase=10.0,
        low_decrease=20.0,
        low_unchanged=70.0,
    )
    middle = make_overview(
        low_increase=60.0,
        low_decrease=20.0,
        low_unchanged=20.0,
    )
    last = make_overview(
        low_increase=30.0,
        low_decrease=30.0,
        low_unchanged=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, middle, last)
        )
    )

    assert result.low_increase_percentage_start == 10.0
    assert result.low_increase_percentage_end == 30.0
    assert result.low_increase_percentage_change == 20.0


def test_overview_count_is_preserved():
    overviews = (
        make_overview(),
        make_overview(),
        make_overview(),
        make_overview(),
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            overviews
        )
    )

    assert result.overview_count == 4


def test_input_must_be_tuple():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            []
        )


def test_invalid_overview_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (object(),)
        )


def test_negative_transition_count_is_rejected():
    overview = make_overview(transition_count=-1)

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_percentage_above_100_is_rejected():
    overview = make_overview(
        low_increase=101.0,
        low_decrease=0.0,
        low_unchanged=0.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_percentage_below_zero_is_rejected():
    overview = make_overview(
        low_increase=-1.0,
        low_decrease=1.0,
        low_unchanged=99.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_direction_percentage_group_must_sum_to_100():
    overview = make_overview(
        low_increase=20.0,
        low_decrease=20.0,
        low_unchanged=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_zero_transition_count_requires_zero_percentages():
    overview = make_overview(
        transition_count=0,
        low_increase=0.0,
        low_decrease=0.0,
        low_unchanged=0.0,
        medium_increase=0.0,
        medium_decrease=0.0,
        medium_unchanged=0.0,
        high_increase=0.0,
        high_decrease=0.0,
        high_unchanged=0.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )
    )

    assert result.overview_count == 1
    assert result.low_increase_percentage_start == 0.0


def test_negative_movement_metric_is_rejected():
    overview = make_overview(
        average_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_minimum_movement_cannot_exceed_maximum():
    overview = make_overview(
        minimum_movement=10.0,
        maximum_movement=5.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_invalid_dominant_direction_is_rejected():
    overview = make_overview(
        dominant_low=("INVALID",),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_dominant_direction_fields_must_be_tuples():
    overview = make_overview()

    object.__setattr__(
        overview,
        "dominant_low_directions",
        ["INCREASE"],
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_negative_numeric_movement_is_rejected():
    overview = make_overview(
        minimum_movement=-0.1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_wrapper_returns_same_result_as_builder():
    first = make_overview(
        low_increase=10.0,
        low_decrease=20.0,
        low_unchanged=70.0,
    )
    second = make_overview(
        low_increase=30.0,
        low_decrease=30.0,
        low_unchanged=40.0,
    )

    built = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    wrapped = (
        compare_position_distribution_stability_trend_transition_comparison_overviews(
            (first, second)
        )
    )

    assert wrapped == built


def test_result_is_frozen():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            ()
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.overview_count = 5


def test_result_preserves_all_direction_changes():
    first = make_overview(
        low_increase=10.0,
        low_decrease=30.0,
        low_unchanged=60.0,
        medium_increase=30.0,
        medium_decrease=40.0,
        medium_unchanged=30.0,
        high_increase=50.0,
        high_decrease=20.0,
        high_unchanged=30.0,
    )

    second = make_overview(
        low_increase=25.0,
        low_decrease=25.0,
        low_unchanged=50.0,
        medium_increase=20.0,
        medium_decrease=30.0,
        medium_unchanged=50.0,
        high_increase=30.0,
        high_decrease=40.0,
        high_unchanged=30.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == 15.0
    assert result.low_decrease_percentage_change == -5.0
    assert result.low_unchanged_percentage_change == -10.0

    assert result.medium_increase_percentage_change == -10.0
    assert result.medium_decrease_percentage_change == -10.0
    assert result.medium_unchanged_percentage_change == 20.0

    assert result.high_increase_percentage_change == -20.0
    assert result.high_decrease_percentage_change == 20.0
    assert result.high_unchanged_percentage_change == 0.0


def test_equal_overviews_have_zero_changes():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview, overview, overview)
        )
    )

    assert result.low_increase_percentage_change == 0.0
    assert result.low_decrease_percentage_change == 0.0
    assert result.low_unchanged_percentage_change == 0.0

    assert result.medium_increase_percentage_change == 0.0
    assert result.medium_decrease_percentage_change == 0.0
    assert result.medium_unchanged_percentage_change == 0.0

    assert result.high_increase_percentage_change == 0.0
    assert result.high_decrease_percentage_change == 0.0
    assert result.high_unchanged_percentage_change == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_zero_transition_overview_with_nonzero_percentage_is_rejected():
    overview = make_overview(
        transition_count=0,
        low_increase=20.0,
        low_decrease=30.0,
        low_unchanged=50.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_non_numeric_percentage_is_rejected():
    overview = make_overview()

    object.__setattr__(
        overview,
        "low_increase_percentage",
        "20",
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_boolean_transition_count_is_rejected():
    overview = make_overview()

    object.__setattr__(
        overview,
        "transition_count",
        True,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_boolean_percentage_is_rejected():
    overview = make_overview()

    object.__setattr__(
        overview,
        "low_increase_percentage",
        True,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_boolean_movement_metric_is_rejected():
    overview = make_overview()

    object.__setattr__(
        overview,
        "average_total_absolute_percentage_movement",
        True,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (overview,)
        )


def test_three_overviews_use_first_and_last_for_percentage_changes():
    first = make_overview(
        low_increase=10.0,
        low_decrease=20.0,
        low_unchanged=70.0,
    )

    middle = make_overview(
        low_increase=80.0,
        low_decrease=10.0,
        low_unchanged=10.0,
    )

    last = make_overview(
        low_increase=40.0,
        low_decrease=30.0,
        low_unchanged=30.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, middle, last)
        )
    )

    assert result.low_increase_percentage_start == 10.0
    assert result.low_increase_percentage_end == 40.0
    assert result.low_increase_percentage_change == 30.0

    assert result.low_decrease_percentage_start == 20.0
    assert result.low_decrease_percentage_end == 30.0
    assert result.low_decrease_percentage_change == 10.0

    assert result.low_unchanged_percentage_start == 70.0
    assert result.low_unchanged_percentage_end == 30.0
    assert result.low_unchanged_percentage_change == -40.0


def test_result_type_is_correct():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            ()
        )
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparison,
    )


def test_empty_input_preserves_empty_semantics():
    result = (
        compare_position_distribution_stability_trend_transition_comparison_overviews(
            ()
        )
    )

    assert result.overview_count == 0
    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_movement_is_nonnegative():
    first = make_overview()
    second = make_overview(
        low_increase=30.0,
        low_decrease=20.0,
        low_unchanged=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.total_absolute_percentage_movement >= 0.0
    assert result.mean_absolute_percentage_movement >= 0.0