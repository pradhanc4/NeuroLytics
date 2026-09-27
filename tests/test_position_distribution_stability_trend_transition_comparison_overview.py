from dataclasses import replace

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview import (
    DECREASE,
    INCREASE,
    UNCHANGED,
    PositionDistributionStabilityTrendTransitionComparisonOverview,
    build_position_distribution_stability_trend_transition_comparison_overview,
    get_position_distribution_stability_trend_transition_comparison_overview,
)
from analytics.position_distribution_stability_trend_transition_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonSummary,
)


def make_transition_objects(count):
    return tuple(object() for _ in range(count))


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
    average_total_absolute_percentage_movement=3.5,
    minimum_total_absolute_percentage_movement=1.0,
    maximum_total_absolute_percentage_movement=6.0,
    total_absolute_percentage_movement=14.0,
    transitions=None,
):
    if transitions is None:
        transitions = make_transition_objects(transition_count)

    return PositionDistributionStabilityTrendTransitionComparisonSummary(
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
        average_total_absolute_percentage_movement=(
            average_total_absolute_percentage_movement
        ),
        minimum_total_absolute_percentage_movement=(
            minimum_total_absolute_percentage_movement
        ),
        maximum_total_absolute_percentage_movement=(
            maximum_total_absolute_percentage_movement
        ),
        total_absolute_percentage_movement=(
            total_absolute_percentage_movement
        ),
        transitions=transitions,
    )


def test_output_type():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            make_summary()
        )
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendTransitionComparisonOverview,
    )


def test_transition_count_is_preserved():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            make_summary(transition_count=4)
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
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.low_increase_percentage == 50.0
    assert result.low_decrease_percentage == 25.0
    assert result.low_unchanged_percentage == 25.0


def test_medium_percentages_are_calculated():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=2,
        medium_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.medium_increase_percentage == 25.0
    assert result.medium_decrease_percentage == 50.0
    assert result.medium_unchanged_percentage == 25.0


def test_high_percentages_are_calculated():
    summary = make_summary(
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.high_increase_percentage == 25.0
    assert result.high_decrease_percentage == 25.0
    assert result.high_unchanged_percentage == 50.0


def test_percentages_sum_to_100_for_each_movement_level():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            make_summary()
        )
    )

    assert (
        result.low_increase_percentage
        + result.low_decrease_percentage
        + result.low_unchanged_percentage
    ) == 100.0

    assert (
        result.medium_increase_percentage
        + result.medium_decrease_percentage
        + result.medium_unchanged_percentage
    ) == 100.0

    assert (
        result.high_increase_percentage
        + result.high_decrease_percentage
        + result.high_unchanged_percentage
    ) == 100.0


def test_movement_metrics_are_preserved():
    summary = make_summary(
        average_total_absolute_percentage_movement=3.5,
        minimum_total_absolute_percentage_movement=1.0,
        maximum_total_absolute_percentage_movement=6.0,
        total_absolute_percentage_movement=14.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.average_total_absolute_percentage_movement == 3.5
    assert result.minimum_total_absolute_percentage_movement == 1.0
    assert result.maximum_total_absolute_percentage_movement == 6.0
    assert result.total_absolute_percentage_movement == 14.0


def test_low_dominant_direction_is_identified():
    summary = make_summary(
        low_increase_count=3,
        low_decrease_count=1,
        low_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_low_directions == (INCREASE,)


def test_medium_dominant_direction_is_identified():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=3,
        medium_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_medium_directions == (DECREASE,)


def test_high_dominant_direction_is_identified():
    summary = make_summary(
        high_increase_count=1,
        high_decrease_count=0,
        high_unchanged_count=3,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_high_directions == (UNCHANGED,)


def test_low_tie_preserves_all_dominant_directions():
    summary = make_summary(
        low_increase_count=2,
        low_decrease_count=2,
        low_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_low_directions == (
        INCREASE,
        DECREASE,
    )


def test_medium_three_way_tie_preserves_all_directions():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=1,
        medium_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_medium_directions == (UNCHANGED,)


def test_high_tie_preserves_all_dominant_directions():
    summary = make_summary(
        high_increase_count=2,
        high_decrease_count=0,
        high_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result.dominant_high_directions == (
        INCREASE,
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
        average_total_absolute_percentage_movement=0.0,
        minimum_total_absolute_percentage_movement=0.0,
        maximum_total_absolute_percentage_movement=0.0,
        total_absolute_percentage_movement=0.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert result == PositionDistributionStabilityTrendTransitionComparisonOverview(
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
        average_total_absolute_percentage_movement=0.0,
        minimum_total_absolute_percentage_movement=0.0,
        maximum_total_absolute_percentage_movement=0.0,
        total_absolute_percentage_movement=0.0,
        dominant_low_directions=(),
        dominant_medium_directions=(),
        dominant_high_directions=(),
    )


def test_single_transition_produces_100_percent_for_each_direction():
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
        build_position_distribution_stability_trend_transition_comparison_overview(
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


def test_invalid_summary_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            object()
        )


def test_negative_transition_count_is_rejected():
    summary = make_summary(transition_count=-1, transitions=())

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_boolean_transition_count_is_rejected():
    summary = replace(
        make_summary(),
        transition_count=True,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_negative_direction_count_is_rejected():
    summary = make_summary(
        low_increase_count=-1,
        low_decrease_count=3,
        low_unchanged_count=2,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_low_counts_must_match_transition_count():
    summary = make_summary(
        low_increase_count=1,
        low_decrease_count=1,
        low_unchanged_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_medium_counts_must_match_transition_count():
    summary = make_summary(
        medium_increase_count=1,
        medium_decrease_count=1,
        medium_unchanged_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_high_counts_must_match_transition_count():
    summary = make_summary(
        high_increase_count=1,
        high_decrease_count=1,
        high_unchanged_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_negative_average_movement_is_rejected():
    summary = make_summary(
        average_total_absolute_percentage_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_negative_minimum_movement_is_rejected():
    summary = make_summary(
        minimum_total_absolute_percentage_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_negative_maximum_movement_is_rejected():
    summary = make_summary(
        maximum_total_absolute_percentage_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_negative_total_movement_is_rejected():
    summary = make_summary(
        total_absolute_percentage_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_minimum_movement_cannot_exceed_maximum():
    summary = make_summary(
        minimum_total_absolute_percentage_movement=7.0,
        maximum_total_absolute_percentage_movement=6.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_transitions_must_be_tuple():
    summary = replace(
        make_summary(),
        transitions=[],
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_transition_length_must_match_count():
    summary = replace(
        make_summary(),
        transitions=(object(),),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )


def test_result_is_frozen():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            make_summary()
        )
    )

    with pytest.raises(AttributeError):
        result.transition_count = 10


def test_getter_returns_same_result_as_builder():
    summary = make_summary()

    built = (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    fetched = (
        get_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )

    assert fetched == built