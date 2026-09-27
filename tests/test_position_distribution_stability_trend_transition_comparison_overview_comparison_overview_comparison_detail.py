"""
Tests for Phase 9.3.45

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Detail.
"""

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail,
)


PERCENTAGE_FIELDS = (
    "low_increase_percentage",
    "low_decrease_percentage",
    "low_unchanged_percentage",
    "medium_increase_percentage",
    "medium_decrease_percentage",
    "medium_unchanged_percentage",
    "high_increase_percentage",
    "high_decrease_percentage",
    "high_unchanged_percentage",
)

MOVEMENT_FIELDS = (
    "average_total_absolute_percentage_movement",
    "minimum_total_absolute_percentage_movement",
    "maximum_total_absolute_percentage_movement",
    "total_absolute_percentage_movement",
)


def make_overview(
    transition_count=4,
    low_increase_percentage=50.0,
    low_decrease_percentage=25.0,
    low_unchanged_percentage=25.0,
    medium_increase_percentage=25.0,
    medium_decrease_percentage=50.0,
    medium_unchanged_percentage=25.0,
    high_increase_percentage=25.0,
    high_decrease_percentage=25.0,
    high_unchanged_percentage=50.0,
    average_movement=10.0,
    minimum_movement=5.0,
    maximum_movement=20.0,
    total_movement=40.0,
    dominant_low_directions=("INCREASE",),
    dominant_medium_directions=("DECREASE",),
    dominant_high_directions=("UNCHANGED",),
):
    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview(
            transition_count=transition_count,

            low_increase_percentage=low_increase_percentage,
            low_decrease_percentage=low_decrease_percentage,
            low_unchanged_percentage=low_unchanged_percentage,

            medium_increase_percentage=medium_increase_percentage,
            medium_decrease_percentage=medium_decrease_percentage,
            medium_unchanged_percentage=medium_unchanged_percentage,

            high_increase_percentage=high_increase_percentage,
            high_decrease_percentage=high_decrease_percentage,
            high_unchanged_percentage=high_unchanged_percentage,

            average_total_absolute_percentage_movement=average_movement,
            minimum_total_absolute_percentage_movement=minimum_movement,
            maximum_total_absolute_percentage_movement=maximum_movement,
            total_absolute_percentage_movement=total_movement,

            dominant_low_directions=dominant_low_directions,
            dominant_medium_directions=dominant_medium_directions,
            dominant_high_directions=dominant_high_directions,
        )
    )


def test_transition_result_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition
    )


def test_detail_result_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail
    )


def test_transition_result_is_frozen():
    first = make_overview()

    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.transitions[0].transition_index = 99


def test_detail_result_is_frozen():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.overview_count = 99


def test_empty_input_returns_zero_detail():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            ()
        )
    )

    assert result.overview_count == 0
    assert result.transition_count == 0
    assert result.transitions == ()


def test_single_overview_returns_zero_transitions():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )
    )

    assert result.overview_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_two_overviews_create_one_transition():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    assert result.overview_count == 2
    assert result.transition_count == 1
    assert len(result.transitions) == 1


def test_three_overviews_create_two_transitions():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )
    third = make_overview(
        low_increase_percentage=70.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second, third)
        )
    )

    assert result.overview_count == 3
    assert result.transition_count == 2
    assert len(result.transitions) == 2


def test_transition_indexes_start_at_one():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )
    third = make_overview(
        low_increase_percentage=70.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second, third)
        )
    )

    assert result.transitions[0].transition_index == 1
    assert result.transitions[1].transition_index == 2


def test_transition_indexes_are_sequential():
    overviews = tuple(
        make_overview(
            low_increase_percentage=float(20 + index * 5),
        )
        for index in range(5)
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            overviews
        )
    )

    assert tuple(
        transition.transition_index
        for transition in result.transitions
    ) == (1, 2, 3, 4)


def test_first_transition_uses_first_and_second_overview():
    first = make_overview(
        low_increase_percentage=10.0,
    )
    second = make_overview(
        low_increase_percentage=30.0,
    )
    third = make_overview(
        low_increase_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second, third)
        )
    )

    transition = result.transitions[0]

    assert transition.low_increase_percentage_start == 10.0
    assert transition.low_increase_percentage_end == 30.0
    assert transition.low_increase_percentage_change == 20.0


def test_second_transition_uses_second_and_third_overview():
    first = make_overview(
        low_increase_percentage=10.0,
    )
    second = make_overview(
        low_increase_percentage=30.0,
    )
    third = make_overview(
        low_increase_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second, third)
        )
    )

    transition = result.transitions[1]

    assert transition.low_increase_percentage_start == 30.0
    assert transition.low_increase_percentage_end == 50.0
    assert transition.low_increase_percentage_change == 20.0


def test_all_nine_percentage_fields_are_preserved():
    first = make_overview(
        low_increase_percentage=10.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=70.0,
        medium_increase_percentage=20.0,
        medium_decrease_percentage=30.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=30.0,
        high_decrease_percentage=20.0,
        high_unchanged_percentage=50.0,
    )

    second = make_overview(
        low_increase_percentage=20.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=50.0,
        medium_increase_percentage=30.0,
        medium_decrease_percentage=20.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=20.0,
        high_decrease_percentage=30.0,
        high_unchanged_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    transition = result.transitions[0]

    assert transition.low_increase_percentage_start == 10.0
    assert transition.low_increase_percentage_end == 20.0
    assert transition.low_increase_percentage_change == 10.0

    assert transition.low_decrease_percentage_start == 20.0
    assert transition.low_decrease_percentage_end == 30.0
    assert transition.low_decrease_percentage_change == 10.0

    assert transition.low_unchanged_percentage_start == 70.0
    assert transition.low_unchanged_percentage_end == 50.0
    assert transition.low_unchanged_percentage_change == -20.0

    assert transition.medium_increase_percentage_start == 20.0
    assert transition.medium_increase_percentage_end == 30.0
    assert transition.medium_increase_percentage_change == 10.0

    assert transition.medium_decrease_percentage_start == 30.0
    assert transition.medium_decrease_percentage_end == 20.0
    assert transition.medium_decrease_percentage_change == -10.0

    assert transition.medium_unchanged_percentage_start == 50.0
    assert transition.medium_unchanged_percentage_end == 50.0
    assert transition.medium_unchanged_percentage_change == 0.0

    assert transition.high_increase_percentage_start == 30.0
    assert transition.high_increase_percentage_end == 20.0
    assert transition.high_increase_percentage_change == -10.0

    assert transition.high_decrease_percentage_start == 20.0
    assert transition.high_decrease_percentage_end == 30.0
    assert transition.high_decrease_percentage_change == 10.0

    assert transition.high_unchanged_percentage_start == 50.0
    assert transition.high_unchanged_percentage_end == 50.0
    assert transition.high_unchanged_percentage_change == 0.0


def test_movement_fields_are_preserved():
    first = make_overview(
        average_movement=5.0,
        minimum_movement=2.0,
        maximum_movement=10.0,
        total_movement=20.0,
    )

    second = make_overview(
        average_movement=12.0,
        minimum_movement=6.0,
        maximum_movement=25.0,
        total_movement=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    transition = result.transitions[0]

    assert transition.average_total_absolute_percentage_movement_start == 5.0
    assert transition.average_total_absolute_percentage_movement_end == 12.0
    assert transition.average_total_absolute_percentage_movement_change == 7.0

    assert transition.minimum_total_absolute_percentage_movement_start == 2.0
    assert transition.minimum_total_absolute_percentage_movement_end == 6.0
    assert transition.minimum_total_absolute_percentage_movement_change == 4.0

    assert transition.maximum_total_absolute_percentage_movement_start == 10.0
    assert transition.maximum_total_absolute_percentage_movement_end == 25.0
    assert transition.maximum_total_absolute_percentage_movement_change == 15.0

    assert transition.total_absolute_percentage_movement_start == 20.0
    assert transition.total_absolute_percentage_movement_end == 50.0
    assert transition.total_absolute_percentage_movement_change == 30.0


def test_change_equals_end_minus_start_for_all_percentage_fields():
    first = make_overview(
        low_increase_percentage=10.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=60.0,
        medium_increase_percentage=20.0,
        medium_decrease_percentage=40.0,
        medium_unchanged_percentage=40.0,
        high_increase_percentage=30.0,
        high_decrease_percentage=30.0,
        high_unchanged_percentage=40.0,
    )

    second = make_overview(
        low_increase_percentage=25.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=55.0,
        medium_increase_percentage=30.0,
        medium_decrease_percentage=30.0,
        medium_unchanged_percentage=40.0,
        high_increase_percentage=20.0,
        high_decrease_percentage=35.0,
        high_unchanged_percentage=45.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    transition = result.transitions[0]

    for field_name in PERCENTAGE_FIELDS:
        assert getattr(
            transition,
            f"{field_name}_change",
        ) == pytest.approx(
            getattr(transition, f"{field_name}_end")
            - getattr(transition, f"{field_name}_start")
        )


def test_change_equals_end_minus_start_for_movement_fields():
    first = make_overview(
        average_movement=5.0,
        minimum_movement=2.0,
        maximum_movement=10.0,
        total_movement=20.0,
    )

    second = make_overview(
        average_movement=12.0,
        minimum_movement=6.0,
        maximum_movement=25.0,
        total_movement=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    transition = result.transitions[0]

    for field_name in MOVEMENT_FIELDS:
        assert getattr(
            transition,
            f"{field_name}_change",
        ) == pytest.approx(
            getattr(transition, f"{field_name}_end")
            - getattr(transition, f"{field_name}_start")
        )


def test_transition_total_absolute_percentage_movement_uses_all_nine_fields():
    first = make_overview(
        low_increase_percentage=10.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=70.0,
        medium_increase_percentage=20.0,
        medium_decrease_percentage=30.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=30.0,
        high_decrease_percentage=20.0,
        high_unchanged_percentage=50.0,
    )

    second = make_overview(
        low_increase_percentage=20.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=50.0,
        medium_increase_percentage=30.0,
        medium_decrease_percentage=20.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=20.0,
        high_decrease_percentage=30.0,
        high_unchanged_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    expected = (
        abs(20.0 - 10.0)
        + abs(30.0 - 20.0)
        + abs(50.0 - 70.0)
        + abs(30.0 - 20.0)
        + abs(20.0 - 30.0)
        + abs(50.0 - 50.0)
        + abs(20.0 - 30.0)
        + abs(30.0 - 20.0)
        + abs(50.0 - 50.0)
    )

    assert result.transitions[0].total_absolute_percentage_movement == pytest.approx(
        expected
    )


def test_transition_movement_is_zero_when_all_percentage_values_are_unchanged():
    first = make_overview()

    second = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    assert result.transitions[0].total_absolute_percentage_movement == 0.0


def test_transition_movement_is_nonnegative():
    first = make_overview(
        low_increase_percentage=10.0,
    )

    second = make_overview(
        low_increase_percentage=90.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    assert result.transitions[0].total_absolute_percentage_movement >= 0.0


def test_source_order_is_respected():
    first = make_overview(
        low_increase_percentage=10.0,
    )

    second = make_overview(
        low_increase_percentage=30.0,
    )

    third = make_overview(
        low_increase_percentage=70.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second, third)
        )
    )

    assert result.transitions[0].low_increase_percentage_start == 10.0
    assert result.transitions[0].low_increase_percentage_end == 30.0

    assert result.transitions[1].low_increase_percentage_start == 30.0
    assert result.transitions[1].low_increase_percentage_end == 70.0


def test_transition_count_is_overview_count_minus_one():
    overviews = tuple(
        make_overview(
            low_increase_percentage=float(20 + index),
        )
        for index in range(6)
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            overviews
        )
    )

    assert result.transition_count == 5
    assert result.overview_count == 6


def test_invalid_input_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            []
        )


def test_invalid_overview_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (object(),)
        )


def test_negative_transition_count_raises():
    overview = make_overview(
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_boolean_transition_count_raises():
    overview = make_overview()

    invalid = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview(
            transition_count=True,

            low_increase_percentage=overview.low_increase_percentage,
            low_decrease_percentage=overview.low_decrease_percentage,
            low_unchanged_percentage=overview.low_unchanged_percentage,

            medium_increase_percentage=overview.medium_increase_percentage,
            medium_decrease_percentage=overview.medium_decrease_percentage,
            medium_unchanged_percentage=overview.medium_unchanged_percentage,

            high_increase_percentage=overview.high_increase_percentage,
            high_decrease_percentage=overview.high_decrease_percentage,
            high_unchanged_percentage=overview.high_unchanged_percentage,

            average_total_absolute_percentage_movement=overview.average_total_absolute_percentage_movement,
            minimum_total_absolute_percentage_movement=overview.minimum_total_absolute_percentage_movement,
            maximum_total_absolute_percentage_movement=overview.maximum_total_absolute_percentage_movement,
            total_absolute_percentage_movement=overview.total_absolute_percentage_movement,

            dominant_low_directions=overview.dominant_low_directions,
            dominant_medium_directions=overview.dominant_medium_directions,
            dominant_high_directions=overview.dominant_high_directions,
        )
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (invalid,)
        )


def test_percentage_below_zero_raises():
    overview = make_overview(
        low_increase_percentage=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_percentage_above_100_raises():
    overview = make_overview(
        low_increase_percentage=101.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_negative_average_movement_raises():
    overview = make_overview(
        average_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_negative_minimum_movement_raises():
    overview = make_overview(
        minimum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_negative_maximum_movement_raises():
    overview = make_overview(
        maximum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_negative_total_movement_raises():
    overview = make_overview(
        total_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_minimum_movement_cannot_exceed_maximum():
    overview = make_overview(
        minimum_movement=30.0,
        maximum_movement=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_dominant_low_directions_must_be_tuple():
    overview = make_overview()

    invalid = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview(
            transition_count=overview.transition_count,

            low_increase_percentage=overview.low_increase_percentage,
            low_decrease_percentage=overview.low_decrease_percentage,
            low_unchanged_percentage=overview.low_unchanged_percentage,

            medium_increase_percentage=overview.medium_increase_percentage,
            medium_decrease_percentage=overview.medium_decrease_percentage,
            medium_unchanged_percentage=overview.medium_unchanged_percentage,

            high_increase_percentage=overview.high_increase_percentage,
            high_decrease_percentage=overview.high_decrease_percentage,
            high_unchanged_percentage=overview.high_unchanged_percentage,

            average_total_absolute_percentage_movement=overview.average_total_absolute_percentage_movement,
            minimum_total_absolute_percentage_movement=overview.minimum_total_absolute_percentage_movement,
            maximum_total_absolute_percentage_movement=overview.maximum_total_absolute_percentage_movement,
            total_absolute_percentage_movement=overview.total_absolute_percentage_movement,

            dominant_low_directions=["INCREASE"],
            dominant_medium_directions=overview.dominant_medium_directions,
            dominant_high_directions=overview.dominant_high_directions,
        )
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (invalid,)
        )


def test_duplicate_dominant_direction_raises():
    overview = make_overview(
        dominant_low_directions=("INCREASE", "INCREASE"),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_invalid_dominant_direction_raises():
    overview = make_overview(
        dominant_low_directions=("INVALID",),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_empty_dominant_directions_are_allowed_when_transition_count_is_zero():
    overview = make_overview(
        transition_count=0,
        low_increase_percentage=0.0,
        low_decrease_percentage=0.0,
        low_unchanged_percentage=0.0,
        medium_increase_percentage=0.0,
        medium_decrease_percentage=0.0,
        medium_unchanged_percentage=0.0,
        high_increase_percentage=0.0,
        high_decrease_percentage=0.0,
        high_unchanged_percentage=0.0,
        average_movement=0.0,
        minimum_movement=0.0,
        maximum_movement=0.0,
        total_movement=0.0,
        dominant_low_directions=(),
        dominant_medium_directions=(),
        dominant_high_directions=(),
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )
    )

    assert result.overview_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_empty_dominant_directions_are_rejected_when_transition_count_is_positive():
    overview = make_overview(
        dominant_low_directions=(),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (overview,)
        )


def test_getter_matches_builder():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    expected = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    actual = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    assert actual == expected


def test_expected_transition_fields_exist():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    expected_fields = {
        "transition_index",

        "low_increase_percentage_start",
        "low_increase_percentage_end",
        "low_increase_percentage_change",

        "low_decrease_percentage_start",
        "low_decrease_percentage_end",
        "low_decrease_percentage_change",

        "low_unchanged_percentage_start",
        "low_unchanged_percentage_end",
        "low_unchanged_percentage_change",

        "medium_increase_percentage_start",
        "medium_increase_percentage_end",
        "medium_increase_percentage_change",

        "medium_decrease_percentage_start",
        "medium_decrease_percentage_end",
        "medium_decrease_percentage_change",

        "medium_unchanged_percentage_start",
        "medium_unchanged_percentage_end",
        "medium_unchanged_percentage_change",

        "high_increase_percentage_start",
        "high_increase_percentage_end",
        "high_increase_percentage_change",

        "high_decrease_percentage_start",
        "high_decrease_percentage_end",
        "high_decrease_percentage_change",

        "high_unchanged_percentage_start",
        "high_unchanged_percentage_end",
        "high_unchanged_percentage_change",

        "average_total_absolute_percentage_movement_start",
        "average_total_absolute_percentage_movement_end",
        "average_total_absolute_percentage_movement_change",

        "minimum_total_absolute_percentage_movement_start",
        "minimum_total_absolute_percentage_movement_end",
        "minimum_total_absolute_percentage_movement_change",

        "maximum_total_absolute_percentage_movement_start",
        "maximum_total_absolute_percentage_movement_end",
        "maximum_total_absolute_percentage_movement_change",

        "total_absolute_percentage_movement_start",
        "total_absolute_percentage_movement_end",
        "total_absolute_percentage_movement_change",

        "total_absolute_percentage_movement",
    }

    assert set(result.transitions[0].__dataclass_fields__) == expected_fields


def test_expected_detail_fields_exist():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    expected_fields = {
        "overview_count",
        "transition_count",
        "transitions",
    }

    assert set(result.__dataclass_fields__) == expected_fields


def test_no_prediction_or_ranking_fields_exist():
    first = make_overview()
    second = make_overview(
        low_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            (first, second)
        )
    )

    forbidden_fields = {
        "prediction",
        "predicted_value",
        "probability",
        "score",
        "rank",
        "ranking",
    }

    transition_fields = set(
        result.transitions[0].__dataclass_fields__
    )

    detail_fields = set(
        result.__dataclass_fields__
    )

    assert transition_fields.isdisjoint(
        forbidden_fields
    )

    assert detail_fields.isdisjoint(
        forbidden_fields
    )