"""
Tests for Phase 9.3.46

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Summary.
"""

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary,
    summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison,
)


def make_transition(
    transition_index=1,
    low_increase_start=10.0,
    low_increase_end=20.0,
    low_decrease_start=30.0,
    low_decrease_end=20.0,
    low_unchanged_start=60.0,
    low_unchanged_end=60.0,
    medium_increase_start=20.0,
    medium_increase_end=30.0,
    medium_decrease_start=40.0,
    medium_decrease_end=30.0,
    medium_unchanged_start=40.0,
    medium_unchanged_end=40.0,
    high_increase_start=30.0,
    high_increase_end=20.0,
    high_decrease_start=20.0,
    high_decrease_end=30.0,
    high_unchanged_start=50.0,
    high_unchanged_end=50.0,
    average_movement_start=5.0,
    average_movement_end=10.0,
    minimum_movement_start=2.0,
    minimum_movement_end=4.0,
    maximum_movement_start=10.0,
    maximum_movement_end=20.0,
    total_movement_start=20.0,
    total_movement_end=40.0,
):
    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition(
            transition_index=transition_index,

            low_increase_percentage_start=low_increase_start,
            low_increase_percentage_end=low_increase_end,
            low_increase_percentage_change=(
                low_increase_end - low_increase_start
            ),

            low_decrease_percentage_start=low_decrease_start,
            low_decrease_percentage_end=low_decrease_end,
            low_decrease_percentage_change=(
                low_decrease_end - low_decrease_start
            ),

            low_unchanged_percentage_start=low_unchanged_start,
            low_unchanged_percentage_end=low_unchanged_end,
            low_unchanged_percentage_change=(
                low_unchanged_end - low_unchanged_start
            ),

            medium_increase_percentage_start=medium_increase_start,
            medium_increase_percentage_end=medium_increase_end,
            medium_increase_percentage_change=(
                medium_increase_end - medium_increase_start
            ),

            medium_decrease_percentage_start=medium_decrease_start,
            medium_decrease_percentage_end=medium_decrease_end,
            medium_decrease_percentage_change=(
                medium_decrease_end - medium_decrease_start
            ),

            medium_unchanged_percentage_start=medium_unchanged_start,
            medium_unchanged_percentage_end=medium_unchanged_end,
            medium_unchanged_percentage_change=(
                medium_unchanged_end - medium_unchanged_start
            ),

            high_increase_percentage_start=high_increase_start,
            high_increase_percentage_end=high_increase_end,
            high_increase_percentage_change=(
                high_increase_end - high_increase_start
            ),

            high_decrease_percentage_start=high_decrease_start,
            high_decrease_percentage_end=high_decrease_end,
            high_decrease_percentage_change=(
                high_decrease_end - high_decrease_start
            ),

            high_unchanged_percentage_start=high_unchanged_start,
            high_unchanged_percentage_end=high_unchanged_end,
            high_unchanged_percentage_change=(
                high_unchanged_end - high_unchanged_start
            ),

            average_total_absolute_percentage_movement_start=average_movement_start,
            average_total_absolute_percentage_movement_end=average_movement_end,
            average_total_absolute_percentage_movement_change=(
                average_movement_end - average_movement_start
            ),

            minimum_total_absolute_percentage_movement_start=minimum_movement_start,
            minimum_total_absolute_percentage_movement_end=minimum_movement_end,
            minimum_total_absolute_percentage_movement_change=(
                minimum_movement_end - minimum_movement_start
            ),

            maximum_total_absolute_percentage_movement_start=maximum_movement_start,
            maximum_total_absolute_percentage_movement_end=maximum_movement_end,
            maximum_total_absolute_percentage_movement_change=(
                maximum_movement_end - maximum_movement_start
            ),

            total_absolute_percentage_movement_start=total_movement_start,
            total_absolute_percentage_movement_end=total_movement_end,
            total_absolute_percentage_movement_change=(
                total_movement_end - total_movement_start
            ),

            total_absolute_percentage_movement=(
                abs(low_increase_end - low_increase_start)
                + abs(low_decrease_end - low_decrease_start)
                + abs(low_unchanged_end - low_unchanged_start)
                + abs(medium_increase_end - medium_increase_start)
                + abs(medium_decrease_end - medium_decrease_start)
                + abs(medium_unchanged_end - medium_unchanged_start)
                + abs(high_increase_end - high_increase_start)
                + abs(high_decrease_end - high_decrease_start)
                + abs(high_unchanged_end - high_unchanged_start)
            ),
        )
    )


def make_detail(transitions=()):
    transitions = tuple(transitions)

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail(
            overview_count=len(transitions) + 1 if transitions else 0,
            transition_count=len(transitions),
            transitions=transitions,
        )
    )


def make_valid_detail(
    transition_count=3,
):
    transitions = tuple(
        make_transition(
            transition_index=index,
        )
        for index in range(1, transition_count + 1)
    )

    return make_detail(transitions)


def test_summary_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    )


def test_summary_is_frozen():
    detail = make_valid_detail(1)

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.transition_count = 99


def test_empty_detail_returns_zero_summary():
    detail = make_detail()

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 0

    assert result.low_increase_increase_count == 0
    assert result.low_increase_decrease_count == 0
    assert result.low_increase_unchanged_count == 0

    assert result.low_decrease_increase_count == 0
    assert result.low_decrease_decrease_count == 0
    assert result.low_decrease_unchanged_count == 0

    assert result.low_unchanged_increase_count == 0
    assert result.low_unchanged_decrease_count == 0
    assert result.low_unchanged_unchanged_count == 0

    assert result.medium_increase_increase_count == 0
    assert result.medium_increase_decrease_count == 0
    assert result.medium_increase_unchanged_count == 0

    assert result.medium_decrease_increase_count == 0
    assert result.medium_decrease_decrease_count == 0
    assert result.medium_decrease_unchanged_count == 0

    assert result.medium_unchanged_increase_count == 0
    assert result.medium_unchanged_decrease_count == 0
    assert result.medium_unchanged_unchanged_count == 0

    assert result.high_increase_increase_count == 0
    assert result.high_increase_decrease_count == 0
    assert result.high_increase_unchanged_count == 0

    assert result.high_decrease_increase_count == 0
    assert result.high_decrease_decrease_count == 0
    assert result.high_decrease_unchanged_count == 0

    assert result.high_unchanged_increase_count == 0
    assert result.high_unchanged_decrease_count == 0
    assert result.high_unchanged_unchanged_count == 0

    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0

    assert result.transitions == ()


def test_single_transition_is_aggregated():
    transition = make_transition()

    detail = make_detail((transition,))

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 1
    assert result.transitions == (transition,)


def test_transition_is_preserved_in_summary():
    transition = make_transition()

    detail = make_detail((transition,))

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert result.transitions[0] == transition


def test_multiple_transitions_are_preserved_in_original_order():
    transitions = (
        make_transition(
            transition_index=1,
            low_increase_start=10.0,
            low_increase_end=20.0,
        ),
        make_transition(
            transition_index=2,
            low_increase_start=20.0,
            low_increase_end=40.0,
        ),
        make_transition(
            transition_index=3,
            low_increase_start=40.0,
            low_increase_end=30.0,
        ),
    )

    detail = make_detail(transitions)

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert result.transitions == transitions


def test_low_increase_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            low_increase_start=10.0,
            low_increase_end=20.0,
        ),
        make_transition(
            transition_index=2,
            low_increase_start=20.0,
            low_increase_end=10.0,
        ),
        make_transition(
            transition_index=3,
            low_increase_start=10.0,
            low_increase_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.low_increase_increase_count == 1
    assert result.low_increase_decrease_count == 1
    assert result.low_increase_unchanged_count == 1


def test_low_decrease_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            low_decrease_start=10.0,
            low_decrease_end=20.0,
        ),
        make_transition(
            transition_index=2,
            low_decrease_start=20.0,
            low_decrease_end=10.0,
        ),
        make_transition(
            transition_index=3,
            low_decrease_start=10.0,
            low_decrease_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.low_decrease_increase_count == 1
    assert result.low_decrease_decrease_count == 1
    assert result.low_decrease_unchanged_count == 1


def test_low_unchanged_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            low_unchanged_start=10.0,
            low_unchanged_end=20.0,
        ),
        make_transition(
            transition_index=2,
            low_unchanged_start=20.0,
            low_unchanged_end=10.0,
        ),
        make_transition(
            transition_index=3,
            low_unchanged_start=10.0,
            low_unchanged_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.low_unchanged_increase_count == 1
    assert result.low_unchanged_decrease_count == 1
    assert result.low_unchanged_unchanged_count == 1


def test_medium_increase_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            medium_increase_start=10.0,
            medium_increase_end=20.0,
        ),
        make_transition(
            transition_index=2,
            medium_increase_start=20.0,
            medium_increase_end=10.0,
        ),
        make_transition(
            transition_index=3,
            medium_increase_start=10.0,
            medium_increase_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.medium_increase_increase_count == 1
    assert result.medium_increase_decrease_count == 1
    assert result.medium_increase_unchanged_count == 1


def test_medium_decrease_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            medium_decrease_start=10.0,
            medium_decrease_end=20.0,
        ),
        make_transition(
            transition_index=2,
            medium_decrease_start=20.0,
            medium_decrease_end=10.0,
        ),
        make_transition(
            transition_index=3,
            medium_decrease_start=10.0,
            medium_decrease_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.medium_decrease_increase_count == 1
    assert result.medium_decrease_decrease_count == 1
    assert result.medium_decrease_unchanged_count == 1


def test_medium_unchanged_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            medium_unchanged_start=10.0,
            medium_unchanged_end=20.0,
        ),
        make_transition(
            transition_index=2,
            medium_unchanged_start=20.0,
            medium_unchanged_end=10.0,
        ),
        make_transition(
            transition_index=3,
            medium_unchanged_start=10.0,
            medium_unchanged_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.medium_unchanged_increase_count == 1
    assert result.medium_unchanged_decrease_count == 1
    assert result.medium_unchanged_unchanged_count == 1


def test_high_increase_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            high_increase_start=10.0,
            high_increase_end=20.0,
        ),
        make_transition(
            transition_index=2,
            high_increase_start=20.0,
            high_increase_end=10.0,
        ),
        make_transition(
            transition_index=3,
            high_increase_start=10.0,
            high_increase_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.high_increase_increase_count == 1
    assert result.high_increase_decrease_count == 1
    assert result.high_increase_unchanged_count == 1


def test_high_decrease_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            high_decrease_start=10.0,
            high_decrease_end=20.0,
        ),
        make_transition(
            transition_index=2,
            high_decrease_start=20.0,
            high_decrease_end=10.0,
        ),
        make_transition(
            transition_index=3,
            high_decrease_start=10.0,
            high_decrease_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.high_decrease_increase_count == 1
    assert result.high_decrease_decrease_count == 1
    assert result.high_decrease_unchanged_count == 1


def test_high_unchanged_direction_counts():
    transitions = (
        make_transition(
            transition_index=1,
            high_unchanged_start=10.0,
            high_unchanged_end=20.0,
        ),
        make_transition(
            transition_index=2,
            high_unchanged_start=20.0,
            high_unchanged_end=10.0,
        ),
        make_transition(
            transition_index=3,
            high_unchanged_start=10.0,
            high_unchanged_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.high_unchanged_increase_count == 1
    assert result.high_unchanged_decrease_count == 1
    assert result.high_unchanged_unchanged_count == 1


def test_each_direction_count_is_independent():
    transitions = (
        make_transition(
            transition_index=1,
            low_increase_start=10.0,
            low_increase_end=20.0,
            low_decrease_start=10.0,
            low_decrease_end=20.0,
            low_unchanged_start=10.0,
            low_unchanged_end=20.0,
        ),
        make_transition(
            transition_index=2,
            low_increase_start=20.0,
            low_increase_end=10.0,
            low_decrease_start=20.0,
            low_decrease_end=10.0,
            low_unchanged_start=20.0,
            low_unchanged_end=10.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    assert result.low_increase_increase_count == 1
    assert result.low_increase_decrease_count == 1
    assert result.low_increase_unchanged_count == 0

    assert result.low_decrease_increase_count == 1
    assert result.low_decrease_decrease_count == 1
    assert result.low_decrease_unchanged_count == 0

    assert result.low_unchanged_increase_count == 1
    assert result.low_unchanged_decrease_count == 1
    assert result.low_unchanged_unchanged_count == 0


def test_movement_metrics_are_aggregated():
    transitions = (
        make_transition(
            transition_index=1,
            total_movement_start=10.0,
            total_movement_end=20.0,
        ),
        make_transition(
            transition_index=2,
            total_movement_start=20.0,
            total_movement_end=40.0,
        ),
        make_transition(
            transition_index=3,
            total_movement_start=40.0,
            total_movement_end=25.0,
        ),
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail(transitions)
        )
    )

    values = tuple(
        transition.total_absolute_percentage_movement
        for transition in transitions
    )

    assert result.average_total_absolute_percentage_movement == pytest.approx(
        sum(values) / len(values)
    )

    assert result.minimum_total_absolute_percentage_movement == min(values)
    assert result.maximum_total_absolute_percentage_movement == max(values)
    assert result.total_absolute_percentage_movement == sum(values)


def test_movement_metrics_zero_for_empty_detail():
    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_detail()
        )
    )

    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0


def test_movement_metrics_single_transition():
    transition = make_transition(
        low_increase_start=10.0,
        low_increase_end=20.0,
        low_decrease_start=30.0,
        low_decrease_end=20.0,
        low_unchanged_start=60.0,
        low_unchanged_end=60.0,
        medium_increase_start=20.0,
        medium_increase_end=30.0,
        medium_decrease_start=40.0,
        medium_decrease_end=30.0,
        medium_unchanged_start=40.0,
        medium_unchanged_end=40.0,
        high_increase_start=30.0,
        high_increase_end=20.0,
        high_decrease_start=20.0,
        high_decrease_end=30.0,
        high_unchanged_start=50.0,
        high_unchanged_end=50.0,
    )

    detail = make_detail((transition,))

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    expected = transition.total_absolute_percentage_movement

    assert result.average_total_absolute_percentage_movement == expected
    assert result.minimum_total_absolute_percentage_movement == expected
    assert result.maximum_total_absolute_percentage_movement == expected
    assert result.total_absolute_percentage_movement == expected


def test_summary_transition_count_matches_detail():
    transitions = tuple(
        make_transition(transition_index=index)
        for index in range(1, 6)
    )

    detail = make_detail(transitions)

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == detail.transition_count


def test_summary_transitions_are_tuple():
    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_valid_detail(2)
        )
    )

    assert isinstance(result.transitions, tuple)


def test_invalid_detail_type_raises():
    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            object()
        )


def test_invalid_detail_transitions_type_is_rejected():
    transition = make_transition()

    invalid_detail = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail(
            overview_count=2,
            transition_count=1,
            transitions=[transition],
        )
    )

    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            invalid_detail
        )


def test_invalid_transition_type_is_rejected():
    invalid_detail = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail(
            overview_count=2,
            transition_count=1,
            transitions=(object(),),
        )
    )

    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            invalid_detail
        )


def test_invalid_transition_index_is_rejected():
    transition = make_transition(
        transition_index=0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_nonsequential_transition_index_is_rejected():
    transitions = (
        make_transition(transition_index=1),
        make_transition(transition_index=3),
    )

    detail = make_detail(transitions)

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_percentage_change_inconsistency_is_rejected():
    transition = make_transition()

    invalid_transition = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition(
            **{
                **transition.__dict__,
                "low_increase_percentage_change": 999.0,
            }
        )
    )

    detail = make_detail((invalid_transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_movement_change_inconsistency_is_rejected():
    transition = make_transition()

    invalid_transition = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition(
            **{
                **transition.__dict__,
                "average_total_absolute_percentage_movement_change": 999.0,
            }
        )
    )

    detail = make_detail((invalid_transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_minimum_start_movement_cannot_exceed_maximum_start_movement():
    transition = make_transition(
        minimum_movement_start=30.0,
        maximum_movement_start=20.0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_minimum_end_movement_cannot_exceed_maximum_end_movement():
    transition = make_transition(
        minimum_movement_end=30.0,
        maximum_movement_end=20.0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_negative_percentage_is_rejected():
    transition = make_transition(
        low_increase_start=-1.0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_percentage_above_100_is_rejected():
    transition = make_transition(
        low_increase_end=101.0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_negative_movement_is_rejected():
    transition = make_transition(
        average_movement_start=-1.0,
    )

    detail = make_detail((transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_total_absolute_percentage_movement_must_be_consistent():
    transition = make_transition()

    invalid_transition = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition(
            **{
                **transition.__dict__,
                "total_absolute_percentage_movement": 999.0,
            }
        )
    )

    detail = make_detail((invalid_transition,))

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )


def test_getter_matches_summary_function():
    detail = make_valid_detail(3)

    expected = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    actual = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary(
            detail
        )
    )

    assert actual == expected


def test_expected_summary_fields_exist():
    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_valid_detail(1)
        )
    )

    expected_fields = {
        "transition_count",

        "low_increase_increase_count",
        "low_increase_decrease_count",
        "low_increase_unchanged_count",

        "low_decrease_increase_count",
        "low_decrease_decrease_count",
        "low_decrease_unchanged_count",

        "low_unchanged_increase_count",
        "low_unchanged_decrease_count",
        "low_unchanged_unchanged_count",

        "medium_increase_increase_count",
        "medium_increase_decrease_count",
        "medium_increase_unchanged_count",

        "medium_decrease_increase_count",
        "medium_decrease_decrease_count",
        "medium_decrease_unchanged_count",

        "medium_unchanged_increase_count",
        "medium_unchanged_decrease_count",
        "medium_unchanged_unchanged_count",

        "high_increase_increase_count",
        "high_increase_decrease_count",
        "high_increase_unchanged_count",

        "high_decrease_increase_count",
        "high_decrease_decrease_count",
        "high_decrease_unchanged_count",

        "high_unchanged_increase_count",
        "high_unchanged_decrease_count",
        "high_unchanged_unchanged_count",

        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",

        "transitions",
    }

    assert set(result.__dataclass_fields__) == expected_fields


def test_no_prediction_or_ranking_fields_exist():
    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            make_valid_detail(1)
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

    assert set(result.__dataclass_fields__).isdisjoint(
        forbidden_fields
    )


def test_summary_does_not_modify_source_detail():
    transitions = (
        make_transition(transition_index=1),
        make_transition(transition_index=2),
    )

    detail = make_detail(transitions)

    original_transitions = detail.transitions

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )

    assert detail.transitions == original_transitions
    assert result.transitions == original_transitions