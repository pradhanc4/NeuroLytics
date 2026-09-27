"""
Tests for Phase 9.3.43

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview.
"""

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview import (
    DECREASE,
    INCREASE,
    UNCHANGED,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
)


def make_summary(
    transition_count=4,
    low_increase_count=2,
    low_decrease_count=1,
    low_unchanged_count=1,
    medium_increase_count=1,
    medium_decrease_count=2,
    medium_unchanged_count=1,
    high_increase_count=1,
    high_decrease_count=1,
    high_unchanged_count=2,
    average_movement=10.0,
    minimum_movement=5.0,
    maximum_movement=20.0,
    total_movement=40.0,
):
    transitions = tuple(
        object() for _ in range(transition_count)
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
            transition_count=transition_count,

            low_increase_count=low_increase_count,
            low_decrease_count=low_decrease_count,
            low_unchanged_count=low_unchanged_count,

            medium_increase_count=medium_increase_count,
            medium_decrease_count=medium_decrease_count,
            medium_unchanged_count=medium_unchanged_count,

            high_increase_count=high_increase_count,
            high_decrease_count=high_decrease_count,
            high_unchanged_count=high_unchanged_count,

            average_total_absolute_percentage_movement=average_movement,
            minimum_total_absolute_percentage_movement=minimum_movement,
            maximum_total_absolute_percentage_movement=maximum_movement,
            total_absolute_percentage_movement=total_movement,

            transitions=transitions,
        )
    )


def test_result_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview
    )


def test_result_is_frozen():
    summary = make_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.transition_count = 99


def test_basic_overview_is_created():
    summary = make_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.transition_count == 4


def test_low_percentages_are_calculated():
    summary = make_summary(
        low_increase_count=2,
        low_decrease_count=1,
        low_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.low_increase_percentage == pytest.approx(50.0)
    assert result.low_decrease_percentage == pytest.approx(25.0)
    assert result.low_unchanged_percentage == pytest.approx(25.0)


def test_medium_percentages_are_calculated():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=2,
        medium_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.medium_increase_percentage == pytest.approx(25.0)
    assert result.medium_decrease_percentage == pytest.approx(50.0)
    assert result.medium_unchanged_percentage == pytest.approx(25.0)


def test_high_percentages_are_calculated():
    summary = make_summary(
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.high_increase_percentage == pytest.approx(25.0)
    assert result.high_decrease_percentage == pytest.approx(25.0)
    assert result.high_unchanged_percentage == pytest.approx(50.0)


def test_movement_metrics_are_preserved():
    summary = make_summary(
        average_movement=12.5,
        minimum_movement=4.5,
        maximum_movement=25.0,
        total_movement=55.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.average_total_absolute_percentage_movement == 12.5
    assert result.minimum_total_absolute_percentage_movement == 4.5
    assert result.maximum_total_absolute_percentage_movement == 25.0
    assert result.total_absolute_percentage_movement == 55.0


def test_low_dominant_direction_is_calculated():
    summary = make_summary(
        low_increase_count=3,
        low_decrease_count=1,
        low_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_low_directions == (INCREASE,)


def test_medium_dominant_direction_is_calculated():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=3,
        medium_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_medium_directions == (DECREASE,)


def test_high_dominant_direction_is_calculated():
    summary = make_summary(
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=3,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_high_directions == (UNCHANGED,)


def test_low_dominant_direction_preserves_ties():
    summary = make_summary(
        low_increase_count=2,
        low_decrease_count=2,
        low_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_low_directions == (
        INCREASE,
        DECREASE,
    )


def test_medium_dominant_direction_preserves_three_way_tie():
    summary = make_summary(
        medium_increase_count=2,
        medium_decrease_count=2,
        medium_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_medium_directions == (
        INCREASE,
        DECREASE,
        UNCHANGED,
    )


def test_high_dominant_direction_preserves_tie_order():
    summary = make_summary(
        high_increase_count=0,
        high_decrease_count=2,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.dominant_high_directions == (
        DECREASE,
        UNCHANGED,
    )


def test_empty_summary_returns_zero_overview():
    summary = make_summary(
        transition_count=0,
        low_increase_count=0,
        low_decrease_count=0,
        low_unchanged_count=0,
        medium_increase_count=0,
        medium_decrease_count=0,
        medium_unchanged_count=0,
        high_increase_count=0,
        high_decrease_count=0,
        high_unchanged_count=0,
        average_movement=0.0,
        minimum_movement=0.0,
        maximum_movement=0.0,
        total_movement=0.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.transition_count == 0

    assert result.low_increase_percentage == 0.0
    assert result.low_decrease_percentage == 0.0
    assert result.low_unchanged_percentage == 0.0

    assert result.medium_increase_percentage == 0.0
    assert result.medium_decrease_percentage == 0.0
    assert result.medium_unchanged_percentage == 0.0

    assert result.high_increase_percentage == 0.0
    assert result.high_decrease_percentage == 0.0
    assert result.high_unchanged_percentage == 0.0

    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0

    assert result.dominant_low_directions == ()
    assert result.dominant_medium_directions == ()
    assert result.dominant_high_directions == ()


def test_zero_count_direction_produces_zero_percentage():
    summary = make_summary(
        low_increase_count=0,
        low_decrease_count=4,
        low_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.low_increase_percentage == 0.0
    assert result.low_decrease_percentage == 100.0
    assert result.low_unchanged_percentage == 0.0


def test_percentages_are_between_zero_and_one_hundred():
    summary = make_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    percentage_fields = (
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

    for field_name in percentage_fields:
        value = getattr(result, field_name)
        assert 0.0 <= value <= 100.0


def test_each_direction_group_percentage_total_is_based_on_independent_counts():
    summary = make_summary(
        low_increase_count=2,
        low_decrease_count=1,
        low_unchanged_count=1,
        medium_increase_count=1,
        medium_decrease_count=2,
        medium_unchanged_count=1,
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert (
        result.low_increase_percentage
        + result.low_decrease_percentage
        + result.low_unchanged_percentage
        == pytest.approx(100.0)
    )

    assert (
        result.medium_increase_percentage
        + result.medium_decrease_percentage
        + result.medium_unchanged_percentage
        == pytest.approx(100.0)
    )

    assert (
        result.high_increase_percentage
        + result.high_decrease_percentage
        + result.high_unchanged_percentage
        == pytest.approx(100.0)
    )


def test_invalid_summary_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            object()
        )


def test_negative_transition_count_raises():
    summary = make_summary(
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_boolean_transition_count_raises():
    summary = make_summary()
    summary = PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
        transition_count=True,
        low_increase_count=2,
        low_decrease_count=1,
        low_unchanged_count=1,
        medium_increase_count=1,
        medium_decrease_count=2,
        medium_unchanged_count=1,
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=2,
        average_total_absolute_percentage_movement=10.0,
        minimum_total_absolute_percentage_movement=5.0,
        maximum_total_absolute_percentage_movement=20.0,
        total_absolute_percentage_movement=40.0,
        transitions=(),
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_negative_direction_count_raises():
    summary = make_summary(
        low_increase_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_direction_count_above_transition_count_raises():
    summary = make_summary(
        low_increase_count=5,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_negative_average_movement_raises():
    summary = make_summary(
        average_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_negative_minimum_movement_raises():
    summary = make_summary(
        minimum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_negative_maximum_movement_raises():
    summary = make_summary(
        maximum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_negative_total_movement_raises():
    summary = make_summary(
        total_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_minimum_movement_cannot_exceed_maximum_movement():
    summary = make_summary(
        minimum_movement=30.0,
        maximum_movement=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )


def test_transitions_must_be_tuple():
    summary = make_summary()

    invalid_summary = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
            transition_count=summary.transition_count,
            low_increase_count=summary.low_increase_count,
            low_decrease_count=summary.low_decrease_count,
            low_unchanged_count=summary.low_unchanged_count,
            medium_increase_count=summary.medium_increase_count,
            medium_decrease_count=summary.medium_decrease_count,
            medium_unchanged_count=summary.medium_unchanged_count,
            high_increase_count=summary.high_increase_count,
            high_decrease_count=summary.high_decrease_count,
            high_unchanged_count=summary.high_unchanged_count,
            average_total_absolute_percentage_movement=summary.average_total_absolute_percentage_movement,
            minimum_total_absolute_percentage_movement=summary.minimum_total_absolute_percentage_movement,
            maximum_total_absolute_percentage_movement=summary.maximum_total_absolute_percentage_movement,
            total_absolute_percentage_movement=summary.total_absolute_percentage_movement,
            transitions=list(summary.transitions),
        )
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            invalid_summary
        )


def test_transitions_length_must_match_transition_count():
    summary = make_summary()

    invalid_summary = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
            transition_count=summary.transition_count,
            low_increase_count=summary.low_increase_count,
            low_decrease_count=summary.low_decrease_count,
            low_unchanged_count=summary.low_unchanged_count,
            medium_increase_count=summary.medium_increase_count,
            medium_decrease_count=summary.medium_decrease_count,
            medium_unchanged_count=summary.medium_unchanged_count,
            high_increase_count=summary.high_increase_count,
            high_decrease_count=summary.high_decrease_count,
            high_unchanged_count=summary.high_unchanged_count,
            average_total_absolute_percentage_movement=summary.average_total_absolute_percentage_movement,
            minimum_total_absolute_percentage_movement=summary.minimum_total_absolute_percentage_movement,
            maximum_total_absolute_percentage_movement=summary.maximum_total_absolute_percentage_movement,
            total_absolute_percentage_movement=summary.total_absolute_percentage_movement,
            transitions=(),
        )
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            invalid_summary
        )


def test_getter_matches_builder():
    summary = make_summary()

    expected = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    actual = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert actual == expected


def test_getter_handles_empty_summary():
    summary = make_summary(
        transition_count=0,
        low_increase_count=0,
        low_decrease_count=0,
        low_unchanged_count=0,
        medium_increase_count=0,
        medium_decrease_count=0,
        medium_unchanged_count=0,
        high_increase_count=0,
        high_decrease_count=0,
        high_unchanged_count=0,
        average_movement=0.0,
        minimum_movement=0.0,
        maximum_movement=0.0,
        total_movement=0.0,
    )

    result = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.transition_count == 0
    assert result.dominant_low_directions == ()
    assert result.dominant_medium_directions == ()
    assert result.dominant_high_directions == ()


def test_expected_fields_exist():
    summary = make_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    expected_fields = {
        "transition_count",
        "low_increase_percentage",
        "low_decrease_percentage",
        "low_unchanged_percentage",
        "medium_increase_percentage",
        "medium_decrease_percentage",
        "medium_unchanged_percentage",
        "high_increase_percentage",
        "high_decrease_percentage",
        "high_unchanged_percentage",
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
        "dominant_low_directions",
        "dominant_medium_directions",
        "dominant_high_directions",
    }

    assert set(result.__dataclass_fields__) == expected_fields


def test_single_transition_produces_hundred_percent_for_each_counted_direction():
    summary = make_summary(
        transition_count=1,
        low_increase_count=1,
        low_decrease_count=0,
        low_unchanged_count=0,
        medium_increase_count=0,
        medium_decrease_count=1,
        medium_unchanged_count=0,
        high_increase_count=0,
        high_decrease_count=0,
        high_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    assert result.low_increase_percentage == 100.0
    assert result.low_decrease_percentage == 0.0
    assert result.low_unchanged_percentage == 0.0

    assert result.medium_increase_percentage == 0.0
    assert result.medium_decrease_percentage == 100.0
    assert result.medium_unchanged_percentage == 0.0

    assert result.high_increase_percentage == 0.0
    assert result.high_decrease_percentage == 0.0
    assert result.high_unchanged_percentage == 100.0


def test_dominant_direction_order_is_increase_decrease_unchanged():
    summary = make_summary(
        low_increase_count=2,
        low_decrease_count=2,
        low_unchanged_count=2,
        medium_increase_count=2,
        medium_decrease_count=2,
        medium_unchanged_count=2,
        high_increase_count=2,
        high_decrease_count=2,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    expected = (
        INCREASE,
        DECREASE,
        UNCHANGED,
    )

    assert result.dominant_low_directions == expected
    assert result.dominant_medium_directions == expected
    assert result.dominant_high_directions == expected


def test_output_contains_no_prediction_fields():
    summary = make_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )

    field_names = set(result.__dataclass_fields__)

    forbidden_fields = {
        "prediction",
        "predicted_value",
        "probability",
        "score",
        "rank",
        "ranking",
    }

    assert field_names.isdisjoint(forbidden_fields)