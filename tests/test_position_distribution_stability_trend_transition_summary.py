import pytest

from analytics.position_distribution_stability_trend_detail import (
    PositionDistributionStabilityTrendDetail,
    PositionDistributionStabilityTrendTransition,
)
from analytics.position_distribution_stability_trend_transition_summary import (
    HIGH,
    LOW,
    MEDIUM,
    DEFAULT_HIGH_MOVEMENT_THRESHOLD,
    DEFAULT_LOW_MOVEMENT_THRESHOLD,
    PositionDistributionStabilityTrendTransitionSummary,
    classify_transition_movement,
    get_position_distribution_stability_trend_transition_summary,
    summarize_position_distribution_stability_trend_transitions,
)


def make_transition(
    transition_index=1,
    total_absolute_percentage_change=1.0,
):
    return PositionDistributionStabilityTrendTransition(
        transition_index=transition_index,
        stable_increasing_percentage_start=25.0,
        stable_increasing_percentage_end=25.0,
        stable_increasing_percentage_change=0.0,
        stability_decreasing_percentage_start=25.0,
        stability_decreasing_percentage_end=25.0,
        stability_decreasing_percentage_change=0.0,
        stable_percentage_start=25.0,
        stable_percentage_end=25.0,
        stable_percentage_change=0.0,
        mixed_percentage_start=25.0,
        mixed_percentage_end=25.0,
        mixed_percentage_change=0.0,
        low_strength_percentage_start=25.0,
        low_strength_percentage_end=25.0,
        low_strength_percentage_change=0.0,
        medium_strength_percentage_start=25.0,
        medium_strength_percentage_end=25.0,
        medium_strength_percentage_change=0.0,
        high_strength_percentage_start=50.0,
        high_strength_percentage_end=50.0,
        high_strength_percentage_change=0.0,
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
    )


def make_detail(
    transitions=(),
    summary_count=4,
):
    return PositionDistributionStabilityTrendDetail(
        summary_count=summary_count,
        transition_count=len(transitions),
        transitions=tuple(transitions),
    )


def test_summary_is_frozen_dataclass():
    summary = summarize_position_distribution_stability_trend_transitions(
        make_detail()
    )

    assert isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionSummary,
    )

    with pytest.raises(Exception):
        summary.transition_count = 10


def test_default_threshold_constants():
    assert DEFAULT_LOW_MOVEMENT_THRESHOLD == 2.0
    assert DEFAULT_HIGH_MOVEMENT_THRESHOLD == 5.0


def test_classify_low_movement():
    assert classify_transition_movement(0.0) == LOW
    assert classify_transition_movement(1.999999) == LOW


def test_classify_medium_movement():
    assert classify_transition_movement(2.0) == MEDIUM
    assert classify_transition_movement(4.999999) == MEDIUM


def test_classify_high_movement():
    assert classify_transition_movement(5.0) == HIGH
    assert classify_transition_movement(10.0) == HIGH


def test_custom_thresholds_are_supported():
    assert (
        classify_transition_movement(
            3.0,
            low_threshold=3.0,
            high_threshold=7.0,
        )
        == MEDIUM
    )

    assert (
        classify_transition_movement(
            2.9,
            low_threshold=3.0,
            high_threshold=7.0,
        )
        == LOW
    )

    assert (
        classify_transition_movement(
            7.0,
            low_threshold=3.0,
            high_threshold=7.0,
        )
        == HIGH
    )


def test_negative_movement_is_rejected():
    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        classify_transition_movement(-1.0)


def test_negative_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="low_threshold",
    ):
        classify_transition_movement(
            1.0,
            low_threshold=-1.0,
            high_threshold=5.0,
        )


def test_high_threshold_must_exceed_low_threshold():
    with pytest.raises(
        ValueError,
        match="greater than low_threshold",
    ):
        classify_transition_movement(
            1.0,
            low_threshold=5.0,
            high_threshold=5.0,
        )


def test_empty_detail_returns_zero_summary():
    result = summarize_position_distribution_stability_trend_transitions(
        make_detail()
    )

    assert result.transition_count == 0
    assert result.low_movement_count == 0
    assert result.medium_movement_count == 0
    assert result.high_movement_count == 0

    assert result.average_total_absolute_percentage_change == 0.0
    assert result.minimum_total_absolute_percentage_change == 0.0
    assert result.maximum_total_absolute_percentage_change == 0.0
    assert result.total_absolute_percentage_change == 0.0

    assert result.transitions == ()


def test_single_low_transition():
    transition = make_transition(
        total_absolute_percentage_change=1.5
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail((transition,))
    )

    assert result.transition_count == 1
    assert result.low_movement_count == 1
    assert result.medium_movement_count == 0
    assert result.high_movement_count == 0

    assert result.average_total_absolute_percentage_change == 1.5
    assert result.minimum_total_absolute_percentage_change == 1.5
    assert result.maximum_total_absolute_percentage_change == 1.5
    assert result.total_absolute_percentage_change == 1.5


def test_single_medium_transition():
    transition = make_transition(
        total_absolute_percentage_change=3.5
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail((transition,))
    )

    assert result.transition_count == 1
    assert result.low_movement_count == 0
    assert result.medium_movement_count == 1
    assert result.high_movement_count == 0

    assert result.average_total_absolute_percentage_change == 3.5
    assert result.minimum_total_absolute_percentage_change == 3.5
    assert result.maximum_total_absolute_percentage_change == 3.5
    assert result.total_absolute_percentage_change == 3.5


def test_single_high_transition():
    transition = make_transition(
        total_absolute_percentage_change=7.0
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail((transition,))
    )

    assert result.transition_count == 1
    assert result.low_movement_count == 0
    assert result.medium_movement_count == 0
    assert result.high_movement_count == 1

    assert result.average_total_absolute_percentage_change == 7.0
    assert result.minimum_total_absolute_percentage_change == 7.0
    assert result.maximum_total_absolute_percentage_change == 7.0
    assert result.total_absolute_percentage_change == 7.0


def test_multiple_transitions_are_classified():
    transitions = (
        make_transition(1, 1.0),
        make_transition(2, 2.0),
        make_transition(3, 4.0),
        make_transition(4, 5.0),
        make_transition(5, 8.0),
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail(transitions)
    )

    assert result.transition_count == 5
    assert result.low_movement_count == 1
    assert result.medium_movement_count == 2
    assert result.high_movement_count == 2


def test_boundary_values_are_classified_correctly():
    transitions = (
        make_transition(1, 0.0),
        make_transition(2, 1.999999),
        make_transition(3, 2.0),
        make_transition(4, 4.999999),
        make_transition(5, 5.0),
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail(transitions)
    )

    assert result.low_movement_count == 2
    assert result.medium_movement_count == 2
    assert result.high_movement_count == 1


def test_average_minimum_maximum_and_total_are_calculated():
    transitions = (
        make_transition(1, 1.0),
        make_transition(2, 3.0),
        make_transition(3, 7.0),
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail(transitions)
    )

    assert result.total_absolute_percentage_change == 11.0
    assert result.average_total_absolute_percentage_change == pytest.approx(
        11.0 / 3.0
    )
    assert result.minimum_total_absolute_percentage_change == 1.0
    assert result.maximum_total_absolute_percentage_change == 7.0


def test_original_transition_objects_are_preserved():
    first = make_transition(1, 1.0)
    second = make_transition(2, 6.0)

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail((first, second))
    )

    assert result.transitions[0] is first
    assert result.transitions[1] is second


def test_transition_order_is_preserved():
    transitions = (
        make_transition(1, 7.0),
        make_transition(2, 1.0),
        make_transition(3, 3.0),
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail(transitions)
    )

    assert result.transitions == transitions


def test_custom_summary_thresholds_are_applied():
    transitions = (
        make_transition(1, 2.0),
        make_transition(2, 4.0),
        make_transition(3, 8.0),
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail(transitions),
        low_threshold=3.0,
        high_threshold=7.0,
    )

    assert result.low_movement_count == 1
    assert result.medium_movement_count == 1
    assert result.high_movement_count == 1


def test_summary_low_threshold_must_be_non_negative():
    with pytest.raises(
        ValueError,
        match="low_threshold",
    ):
        summarize_position_distribution_stability_trend_transitions(
            make_detail(),
            low_threshold=-1.0,
            high_threshold=5.0,
        )


def test_summary_high_threshold_must_exceed_low_threshold():
    with pytest.raises(
        ValueError,
        match="greater than low_threshold",
    ):
        summarize_position_distribution_stability_trend_transitions(
            make_detail(),
            low_threshold=5.0,
            high_threshold=5.0,
        )


def test_invalid_detail_type_is_rejected():
    with pytest.raises(
        TypeError,
        match="PositionDistributionStabilityTrendDetail",
    ):
        summarize_position_distribution_stability_trend_transitions(
            "invalid"
        )


def test_detail_summary_count_is_not_used_as_transition_count():
    transitions = (
        make_transition(1, 2.0),
        make_transition(2, 4.0),
    )

    detail = make_detail(
        transitions=transitions,
        summary_count=100,
    )

    result = summarize_position_distribution_stability_trend_transitions(
        detail
    )

    assert result.transition_count == 2


def test_negative_transition_movement_is_rejected():
    transition = make_transition(
        total_absolute_percentage_change=-1.0
    )

    detail = make_detail((transition,))

    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        summarize_position_distribution_stability_trend_transitions(
            detail
        )


def test_zero_movement_is_low():
    transition = make_transition(
        total_absolute_percentage_change=0.0
    )

    result = summarize_position_distribution_stability_trend_transitions(
        make_detail((transition,))
    )

    assert result.low_movement_count == 1
    assert result.medium_movement_count == 0
    assert result.high_movement_count == 0


def test_get_summary_returns_same_summary():
    summary = summarize_position_distribution_stability_trend_transitions(
        make_detail(
            (
                make_transition(1, 1.0),
                make_transition(2, 3.0),
                make_transition(3, 7.0),
            )
        )
    )

    result = (
        get_position_distribution_stability_trend_transition_summary(
            summary
        )
    )

    assert result == summary


def test_get_summary_rejects_invalid_type():
    with pytest.raises(
        TypeError,
        match="PositionDistributionStabilityTrendTransitionSummary",
    ):
        get_position_distribution_stability_trend_transition_summary(
            "invalid"
        )