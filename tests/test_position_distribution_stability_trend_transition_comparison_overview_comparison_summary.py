"""
Tests for Phase 9.3.42
Position Distribution Stability Trend Transition Comparison Overview Comparison Summary
"""

from dataclasses import FrozenInstanceError, is_dataclass, replace

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary import (
    DECREASE,
    INCREASE,
    UNCHANGED,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_summary,
    summarize_position_distribution_stability_trend_transition_comparison_overview_comparison,
)


def make_transition(
    index=1,
    low_increase_start=20.0,
    low_increase_end=30.0,
    low_decrease_start=30.0,
    low_decrease_end=20.0,
    low_unchanged_start=50.0,
    low_unchanged_end=50.0,
    medium_increase_start=30.0,
    medium_increase_end=20.0,
    medium_decrease_start=20.0,
    medium_decrease_end=30.0,
    medium_unchanged_start=50.0,
    medium_unchanged_end=50.0,
    high_increase_start=40.0,
    high_increase_end=40.0,
    high_decrease_start=30.0,
    high_decrease_end=20.0,
    high_unchanged_start=30.0,
    high_unchanged_end=40.0,
    average_movement_start=10.0,
    average_movement_end=20.0,
    minimum_movement_start=5.0,
    minimum_movement_end=10.0,
    maximum_movement_start=15.0,
    maximum_movement_end=30.0,
):
    percentage_fields = {
        "low_increase": (
            low_increase_start,
            low_increase_end,
        ),
        "low_decrease": (
            low_decrease_start,
            low_decrease_end,
        ),
        "low_unchanged": (
            low_unchanged_start,
            low_unchanged_end,
        ),
        "medium_increase": (
            medium_increase_start,
            medium_increase_end,
        ),
        "medium_decrease": (
            medium_decrease_start,
            medium_decrease_end,
        ),
        "medium_unchanged": (
            medium_unchanged_start,
            medium_unchanged_end,
        ),
        "high_increase": (
            high_increase_start,
            high_increase_end,
        ),
        "high_decrease": (
            high_decrease_start,
            high_decrease_end,
        ),
        "high_unchanged": (
            high_unchanged_start,
            high_unchanged_end,
        ),
    }

    values = {}

    for name, (start, end) in percentage_fields.items():
        values[f"{name}_percentage_start"] = start
        values[f"{name}_percentage_end"] = end
        values[f"{name}_percentage_change"] = end - start

    values["average_total_absolute_percentage_movement_start"] = (
        average_movement_start
    )
    values["average_total_absolute_percentage_movement_end"] = (
        average_movement_end
    )
    values["average_total_absolute_percentage_movement_change"] = (
        average_movement_end - average_movement_start
    )

    values["minimum_total_absolute_percentage_movement_start"] = (
        minimum_movement_start
    )
    values["minimum_total_absolute_percentage_movement_end"] = (
        minimum_movement_end
    )
    values["minimum_total_absolute_percentage_movement_change"] = (
        minimum_movement_end - minimum_movement_start
    )

    values["maximum_total_absolute_percentage_movement_start"] = (
        maximum_movement_start
    )
    values["maximum_total_absolute_percentage_movement_end"] = (
        maximum_movement_end
    )
    values["maximum_total_absolute_percentage_movement_change"] = (
        maximum_movement_end - maximum_movement_start
    )

    percentage_starts = tuple(
        start
        for start, end in percentage_fields.values()
    )

    percentage_ends = tuple(
        end
        for start, end in percentage_fields.values()
    )

    percentage_changes = tuple(
        end - start
        for start, end in percentage_fields.values()
    )

    values["total_absolute_percentage_movement_start"] = sum(
        abs(value) for value in percentage_starts
    )

    values["total_absolute_percentage_movement_end"] = sum(
        abs(value) for value in percentage_ends
    )

    values["total_absolute_percentage_movement_change"] = (
        values["total_absolute_percentage_movement_end"]
        - values["total_absolute_percentage_movement_start"]
    )

    values["total_absolute_percentage_movement"] = sum(
        abs(change) for change in percentage_changes
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition(
            transition_index=index,
            **values,
        )
    )


def make_detail(transitions):
    transitions = tuple(transitions)

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail(
            overview_count=len(transitions) + 1
            if transitions
            else 0,
            transition_count=len(transitions),
            transitions=transitions,
        )
    )


def test_result_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary
    )


def test_result_is_frozen():
    transition = make_transition()
    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.transition_count = 99


def test_empty_detail_returns_zero_summary():
    detail = make_detail([])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 0

    assert result.low_increase_count == 0
    assert result.low_decrease_count == 0
    assert result.low_unchanged_count == 0

    assert result.medium_increase_count == 0
    assert result.medium_decrease_count == 0
    assert result.medium_unchanged_count == 0

    assert result.high_increase_count == 0
    assert result.high_decrease_count == 0
    assert result.high_unchanged_count == 0

    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0

    assert result.transitions == ()


def test_single_transition_is_aggregated():
    transition = make_transition()
    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 1
    assert result.transitions == (transition,)


def test_single_transition_direction_counts_are_correct():
    transition = make_transition()
    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.low_increase_count == 1
    assert result.low_decrease_count == 1
    assert result.low_unchanged_count == 1

    assert result.medium_increase_count == 1
    assert result.medium_decrease_count == 1
    assert result.medium_unchanged_count == 1

    assert result.high_increase_count == 1
    assert result.high_decrease_count == 1
    assert result.high_unchanged_count == 1


def test_direction_counts_are_aggregated_across_multiple_transitions():
    transition_1 = make_transition(index=1)

    transition_2 = make_transition(
        index=2,
        low_increase_start=30.0,
        low_increase_end=20.0,
        low_decrease_start=20.0,
        low_decrease_end=20.0,
        low_unchanged_start=50.0,
        low_unchanged_end=60.0,
    )

    detail = make_detail(
        [
            transition_1,
            transition_2,
        ]
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 2

    assert result.low_increase_count == 2
    assert result.low_decrease_count == 2
    assert result.low_unchanged_count == 2


def test_medium_direction_counts_are_aggregated():
    transition_1 = make_transition(index=1)

    transition_2 = make_transition(
        index=2,
        medium_increase_start=20.0,
        medium_increase_end=20.0,
        medium_decrease_start=30.0,
        medium_decrease_end=20.0,
        medium_unchanged_start=50.0,
        medium_unchanged_end=60.0,
    )

    detail = make_detail(
        [
            transition_1,
            transition_2,
        ]
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.medium_increase_count == 2
    assert result.medium_decrease_count == 2
    assert result.medium_unchanged_count == 2


def test_high_direction_counts_are_aggregated():
    transition_1 = make_transition(index=1)

    transition_2 = make_transition(
        index=2,
        high_increase_start=40.0,
        high_increase_end=30.0,
        high_decrease_start=20.0,
        high_decrease_end=20.0,
        high_unchanged_start=40.0,
        high_unchanged_end=50.0,
    )

    detail = make_detail(
        [
            transition_1,
            transition_2,
        ]
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.high_increase_count == 2
    assert result.high_decrease_count == 2
    assert result.high_unchanged_count == 2


def test_movement_metrics_are_calculated():
    transition_1 = make_transition(
        index=1,
        low_increase_start=20.0,
        low_increase_end=30.0,
        low_decrease_start=30.0,
        low_decrease_end=20.0,
        low_unchanged_start=50.0,
        low_unchanged_end=50.0,
        average_movement_start=10.0,
        average_movement_end=20.0,
        minimum_movement_start=5.0,
        minimum_movement_end=10.0,
        maximum_movement_start=15.0,
        maximum_movement_end=30.0,
    )

    transition_2 = make_transition(
        index=2,
        low_increase_start=30.0,
        low_increase_end=40.0,
        low_decrease_start=20.0,
        low_decrease_end=10.0,
        low_unchanged_start=50.0,
        low_unchanged_end=50.0,
        average_movement_start=20.0,
        average_movement_end=30.0,
        minimum_movement_start=10.0,
        minimum_movement_end=15.0,
        maximum_movement_start=30.0,
        maximum_movement_end=40.0,
    )

    detail = make_detail(
        [
            transition_1,
            transition_2,
        ]
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    movements = (
        transition_1.total_absolute_percentage_movement,
        transition_2.total_absolute_percentage_movement,
    )

    assert result.average_total_absolute_percentage_movement == pytest.approx(
        sum(movements) / 2
    )

    assert result.minimum_total_absolute_percentage_movement == pytest.approx(
        min(movements)
    )

    assert result.maximum_total_absolute_percentage_movement == pytest.approx(
        max(movements)
    )

    assert result.total_absolute_percentage_movement == pytest.approx(
        sum(movements)
    )


def test_source_transitions_are_preserved_in_order():
    transition_1 = make_transition(index=1)
    transition_2 = make_transition(index=2)
    transition_3 = make_transition(index=3)

    detail = make_detail(
        [
            transition_1,
            transition_2,
            transition_3,
        ]
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transitions == (
        transition_1,
        transition_2,
        transition_3,
    )


def test_getter_returns_same_summary_as_builder():
    transition = make_transition()
    detail = make_detail([transition])

    expected = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    actual = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_summary(
            detail
        )
    )

    assert actual == expected


def test_invalid_detail_type_raises():
    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            object()
        )


def test_negative_overview_count_raises():
    transition = make_transition()
    detail = make_detail([transition])

    invalid_detail = replace(
        detail,
        overview_count=-1,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            invalid_detail
        )


def test_negative_transition_count_raises():
    transition = make_transition()
    detail = make_detail([transition])

    invalid_detail = replace(
        detail,
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            invalid_detail
        )


def test_transition_count_must_match_overview_count():
    transition = make_transition()
    detail = make_detail([transition])

    invalid_detail = replace(
        detail,
        overview_count=10,
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            invalid_detail
        )


def test_transition_tuple_length_must_match_count():
    transition = make_transition()
    detail = make_detail([transition])

    invalid_detail = replace(
        detail,
        transitions=(),
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            invalid_detail
        )


def test_transition_indexes_must_be_sequential():
    transition_1 = make_transition(index=1)
    transition_2 = make_transition(index=3)

    detail = make_detail(
        [
            transition_1,
            transition_2,
        ]
    )

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_invalid_transition_type_raises():
    detail = make_detail([make_transition()])

    invalid_detail = replace(
        detail,
        transitions=(object(),),
    )

    with pytest.raises(TypeError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            invalid_detail
        )


def test_percentage_below_zero_raises():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        low_increase_percentage_start=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_percentage_above_100_raises():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        low_increase_percentage_end=101.0,
        low_increase_percentage_change=81.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_percentage_change_must_match_start_and_end():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        low_increase_percentage_change=999.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_negative_average_movement_raises():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        average_total_absolute_percentage_movement_start=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_negative_minimum_movement_raises():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        minimum_total_absolute_percentage_movement_start=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_negative_maximum_movement_raises():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        maximum_total_absolute_percentage_movement_end=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_movement_minimum_cannot_exceed_maximum_at_start():
    transition = make_transition(
        minimum_movement_start=20.0,
        maximum_movement_start=10.0,
    )

    detail = make_detail([transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_movement_minimum_cannot_exceed_maximum_at_end():
    transition = make_transition(
        minimum_movement_end=40.0,
        maximum_movement_end=30.0,
    )

    detail = make_detail([transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_movement_change_must_match_start_and_end():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        average_total_absolute_percentage_movement_change=999.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_total_movement_start_end_change_are_consistent():
    transition = make_transition()

    assert (
        transition.total_absolute_percentage_movement_change
        == pytest.approx(
            transition.total_absolute_percentage_movement_end
            - transition.total_absolute_percentage_movement_start
        )
    )


def test_total_movement_must_match_direction_changes():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        total_absolute_percentage_movement=999.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_total_movement_start_must_be_nonnegative():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        total_absolute_percentage_movement_start=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_total_movement_end_must_be_nonnegative():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        total_absolute_percentage_movement_end=-1.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_total_movement_change_must_match_start_and_end():
    transition = make_transition()

    invalid_transition = replace(
        transition,
        total_absolute_percentage_movement_change=999.0,
    )

    detail = make_detail([invalid_transition])

    with pytest.raises(ValueError):
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )


def test_zero_change_is_classified_as_unchanged():
    transition = make_transition(
        low_increase_start=20.0,
        low_increase_end=20.0,
        low_decrease_start=30.0,
        low_decrease_end=30.0,
        low_unchanged_start=50.0,
        low_unchanged_end=50.0,
    )

    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.low_increase_count == 0
    assert result.low_decrease_count == 0
    assert result.low_unchanged_count == 3


def test_positive_change_is_classified_as_increase():
    transition = make_transition(
        low_increase_start=10.0,
        low_increase_end=20.0,
        low_decrease_start=20.0,
        low_decrease_end=30.0,
        low_unchanged_start=70.0,
        low_unchanged_end=50.0,
    )

    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.low_increase_count == 2
    assert result.low_decrease_count == 1
    assert result.low_unchanged_count == 0


def test_negative_change_is_classified_as_decrease():
    transition = make_transition(
        low_increase_start=30.0,
        low_increase_end=20.0,
        low_decrease_start=30.0,
        low_decrease_end=20.0,
        low_unchanged_start=40.0,
        low_unchanged_end=60.0,
    )

    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.low_increase_count == 1
    assert result.low_decrease_count == 2
    assert result.low_unchanged_count == 0


def test_direction_constants_are_stable():
    assert INCREASE == "INCREASE"
    assert DECREASE == "DECREASE"
    assert UNCHANGED == "UNCHANGED"


def test_summary_transition_count_matches_source():
    transitions = (
        make_transition(index=1),
        make_transition(index=2),
        make_transition(index=3),
    )

    detail = make_detail(transitions)

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 3


def test_direction_counts_are_bounded_by_transition_count():
    transitions = (
        make_transition(index=1),
        make_transition(index=2),
    )

    detail = make_detail(transitions)

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert 0 <= result.low_increase_count <= result.transition_count
    assert 0 <= result.low_decrease_count <= result.transition_count
    assert 0 <= result.low_unchanged_count <= result.transition_count

    assert 0 <= result.medium_increase_count <= result.transition_count
    assert 0 <= result.medium_decrease_count <= result.transition_count
    assert 0 <= result.medium_unchanged_count <= result.transition_count

    assert 0 <= result.high_increase_count <= result.transition_count
    assert 0 <= result.high_decrease_count <= result.transition_count
    assert 0 <= result.high_unchanged_count <= result.transition_count


def test_summary_preserves_exact_movement_values():
    transition = make_transition(
        low_increase_start=20.0,
        low_increase_end=25.0,
        low_decrease_start=30.0,
        low_decrease_end=25.0,
        low_unchanged_start=50.0,
        low_unchanged_end=50.0,
    )

    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.total_absolute_percentage_movement == pytest.approx(
        transition.total_absolute_percentage_movement
    )


def test_summary_preserves_source_transition_identity():
    transition = make_transition()
    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transitions[0] is transition


def test_zero_transition_detail_does_not_create_fake_metrics():
    detail = (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail(
            overview_count=1,
            transition_count=0,
            transitions=(),
        )
    )

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    assert result.transition_count == 0
    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0


def test_summary_has_expected_field_values():
    transition = make_transition()
    detail = make_detail([transition])

    result = (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )

    expected_fields = {
        "transition_count",
        "low_increase_count",
        "low_decrease_count",
        "low_unchanged_count",
        "medium_increase_count",
        "medium_decrease_count",
        "medium_unchanged_count",
        "high_increase_count",
        "high_decrease_count",
        "high_unchanged_count",
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
        "transitions",
    }

    assert set(result.__dataclass_fields__) == expected_fields