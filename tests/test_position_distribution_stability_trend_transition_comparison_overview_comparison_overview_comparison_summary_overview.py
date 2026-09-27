"""
Tests for Phase 9.3.47

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Summary Overview.
"""

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview,
)


def make_summary(
    transition_count=10,
    low_increase_increase_count=6,
    low_increase_decrease_count=3,
    low_increase_unchanged_count=1,
    low_decrease_increase_count=3,
    low_decrease_decrease_count=5,
    low_decrease_unchanged_count=2,
    low_unchanged_increase_count=2,
    low_unchanged_decrease_count=2,
    low_unchanged_unchanged_count=6,
    medium_increase_increase_count=4,
    medium_increase_decrease_count=4,
    medium_increase_unchanged_count=2,
    medium_decrease_increase_count=2,
    medium_decrease_decrease_count=6,
    medium_decrease_unchanged_count=2,
    medium_unchanged_increase_count=1,
    medium_unchanged_decrease_count=3,
    medium_unchanged_unchanged_count=6,
    high_increase_increase_count=5,
    high_increase_decrease_count=3,
    high_increase_unchanged_count=2,
    high_decrease_increase_count=2,
    high_decrease_decrease_count=2,
    high_decrease_unchanged_count=6,
    high_unchanged_increase_count=3,
    high_unchanged_decrease_count=4,
    high_unchanged_unchanged_count=3,
    average_movement=12.0,
    minimum_movement=5.0,
    maximum_movement=25.0,
    total_movement=120.0,
):
    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary(
            transition_count=transition_count,

            low_increase_increase_count=low_increase_increase_count,
            low_increase_decrease_count=low_increase_decrease_count,
            low_increase_unchanged_count=low_increase_unchanged_count,

            low_decrease_increase_count=low_decrease_increase_count,
            low_decrease_decrease_count=low_decrease_decrease_count,
            low_decrease_unchanged_count=low_decrease_unchanged_count,

            low_unchanged_increase_count=low_unchanged_increase_count,
            low_unchanged_decrease_count=low_unchanged_decrease_count,
            low_unchanged_unchanged_count=low_unchanged_unchanged_count,

            medium_increase_increase_count=medium_increase_increase_count,
            medium_increase_decrease_count=medium_increase_decrease_count,
            medium_increase_unchanged_count=medium_increase_unchanged_count,

            medium_decrease_increase_count=medium_decrease_increase_count,
            medium_decrease_decrease_count=medium_decrease_decrease_count,
            medium_decrease_unchanged_count=medium_decrease_unchanged_count,

            medium_unchanged_increase_count=medium_unchanged_increase_count,
            medium_unchanged_decrease_count=medium_unchanged_decrease_count,
            medium_unchanged_unchanged_count=medium_unchanged_unchanged_count,

            high_increase_increase_count=high_increase_increase_count,
            high_increase_decrease_count=high_increase_decrease_count,
            high_increase_unchanged_count=high_increase_unchanged_count,

            high_decrease_increase_count=high_decrease_increase_count,
            high_decrease_decrease_count=high_decrease_decrease_count,
            high_decrease_unchanged_count=high_decrease_unchanged_count,

            high_unchanged_increase_count=high_unchanged_increase_count,
            high_unchanged_decrease_count=high_unchanged_decrease_count,
            high_unchanged_unchanged_count=high_unchanged_unchanged_count,

            average_total_absolute_percentage_movement=average_movement,
            minimum_total_absolute_percentage_movement=minimum_movement,
            maximum_total_absolute_percentage_movement=maximum_movement,
            total_absolute_percentage_movement=total_movement,

            transitions=(),
        )
    )


def make_empty_summary():
    return make_summary(
        transition_count=0,

        low_increase_increase_count=0,
        low_increase_decrease_count=0,
        low_increase_unchanged_count=0,

        low_decrease_increase_count=0,
        low_decrease_decrease_count=0,
        low_decrease_unchanged_count=0,

        low_unchanged_increase_count=0,
        low_unchanged_decrease_count=0,
        low_unchanged_unchanged_count=0,

        medium_increase_increase_count=0,
        medium_increase_decrease_count=0,
        medium_increase_unchanged_count=0,

        medium_decrease_increase_count=0,
        medium_decrease_decrease_count=0,
        medium_decrease_unchanged_count=0,

        medium_unchanged_increase_count=0,
        medium_unchanged_decrease_count=0,
        medium_unchanged_unchanged_count=0,

        high_increase_increase_count=0,
        high_increase_decrease_count=0,
        high_increase_unchanged_count=0,

        high_decrease_increase_count=0,
        high_decrease_decrease_count=0,
        high_decrease_unchanged_count=0,

        high_unchanged_increase_count=0,
        high_unchanged_decrease_count=0,
        high_unchanged_unchanged_count=0,

        average_movement=0.0,
        minimum_movement=0.0,
        maximum_movement=0.0,
        total_movement=0.0,
    )


def make_single_transition_summary():
    return make_summary(
        transition_count=1,

        low_increase_increase_count=1,
        low_increase_decrease_count=0,
        low_increase_unchanged_count=0,

        low_decrease_increase_count=0,
        low_decrease_decrease_count=1,
        low_decrease_unchanged_count=0,

        low_unchanged_increase_count=0,
        low_unchanged_decrease_count=0,
        low_unchanged_unchanged_count=1,

        medium_increase_increase_count=1,
        medium_increase_decrease_count=0,
        medium_increase_unchanged_count=0,

        medium_decrease_increase_count=0,
        medium_decrease_decrease_count=1,
        medium_decrease_unchanged_count=0,

        medium_unchanged_increase_count=0,
        medium_unchanged_decrease_count=0,
        medium_unchanged_unchanged_count=1,

        high_increase_increase_count=1,
        high_increase_decrease_count=0,
        high_increase_unchanged_count=0,

        high_decrease_increase_count=0,
        high_decrease_decrease_count=1,
        high_decrease_unchanged_count=0,

        high_unchanged_increase_count=0,
        high_unchanged_decrease_count=0,
        high_unchanged_unchanged_count=1,

        average_movement=12.0,
        minimum_movement=5.0,
        maximum_movement=25.0,
        total_movement=120.0,
    )


def test_overview_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview
    )


def test_overview_is_frozen():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            make_summary()
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.transition_count = 99


def test_empty_summary_returns_zero_overview():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            make_empty_summary()
        )
    )

    assert result.transition_count == 0

    percentage_fields = (
        "low_increase_increase_percentage",
        "low_increase_decrease_percentage",
        "low_increase_unchanged_percentage",
        "low_decrease_increase_percentage",
        "low_decrease_decrease_percentage",
        "low_decrease_unchanged_percentage",
        "low_unchanged_increase_percentage",
        "low_unchanged_decrease_percentage",
        "low_unchanged_unchanged_percentage",
        "medium_increase_increase_percentage",
        "medium_increase_decrease_percentage",
        "medium_increase_unchanged_percentage",
        "medium_decrease_increase_percentage",
        "medium_decrease_decrease_percentage",
        "medium_decrease_unchanged_percentage",
        "medium_unchanged_increase_percentage",
        "medium_unchanged_decrease_percentage",
        "medium_unchanged_unchanged_percentage",
        "high_increase_increase_percentage",
        "high_increase_decrease_percentage",
        "high_increase_unchanged_percentage",
        "high_decrease_increase_percentage",
        "high_decrease_decrease_percentage",
        "high_decrease_unchanged_percentage",
        "high_unchanged_increase_percentage",
        "high_unchanged_decrease_percentage",
        "high_unchanged_unchanged_percentage",
    )

    for field_name in percentage_fields:
        assert getattr(result, field_name) == 0.0

    assert result.average_total_absolute_percentage_movement == 0.0
    assert result.minimum_total_absolute_percentage_movement == 0.0
    assert result.maximum_total_absolute_percentage_movement == 0.0
    assert result.total_absolute_percentage_movement == 0.0

    dominant_fields = (
        "dominant_low_increase_directions",
        "dominant_low_decrease_directions",
        "dominant_low_unchanged_directions",
        "dominant_medium_increase_directions",
        "dominant_medium_decrease_directions",
        "dominant_medium_unchanged_directions",
        "dominant_high_increase_directions",
        "dominant_high_decrease_directions",
        "dominant_high_unchanged_directions",
    )

    for field_name in dominant_fields:
        assert getattr(result, field_name) == ()


def test_percentage_calculation():
    summary = make_summary(
        transition_count=10,
        low_increase_increase_count=6,
        low_increase_decrease_count=3,
        low_increase_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.low_increase_increase_percentage == 60.0
    assert result.low_increase_decrease_percentage == 30.0
    assert result.low_increase_unchanged_percentage == 10.0


def test_percentage_calculation_with_single_transition():
    summary = make_single_transition_summary()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.low_increase_increase_percentage == 100.0
    assert result.low_increase_decrease_percentage == 0.0
    assert result.low_increase_unchanged_percentage == 0.0


def test_all_low_series_percentages_are_calculated():
    summary = make_summary(
        transition_count=10,

        low_increase_increase_count=6,
        low_increase_decrease_count=3,
        low_increase_unchanged_count=1,

        low_decrease_increase_count=3,
        low_decrease_decrease_count=5,
        low_decrease_unchanged_count=2,

        low_unchanged_increase_count=2,
        low_unchanged_decrease_count=2,
        low_unchanged_unchanged_count=6,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.low_increase_increase_percentage == 60.0
    assert result.low_increase_decrease_percentage == 30.0
    assert result.low_increase_unchanged_percentage == 10.0

    assert result.low_decrease_increase_percentage == 30.0
    assert result.low_decrease_decrease_percentage == 50.0
    assert result.low_decrease_unchanged_percentage == 20.0

    assert result.low_unchanged_increase_percentage == 20.0
    assert result.low_unchanged_decrease_percentage == 20.0
    assert result.low_unchanged_unchanged_percentage == 60.0


def test_all_medium_series_percentages_are_calculated():
    summary = make_summary(
        transition_count=10,

        medium_increase_increase_count=4,
        medium_increase_decrease_count=4,
        medium_increase_unchanged_count=2,

        medium_decrease_increase_count=2,
        medium_decrease_decrease_count=6,
        medium_decrease_unchanged_count=2,

        medium_unchanged_increase_count=1,
        medium_unchanged_decrease_count=3,
        medium_unchanged_unchanged_count=6,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.medium_increase_increase_percentage == 40.0
    assert result.medium_increase_decrease_percentage == 40.0
    assert result.medium_increase_unchanged_percentage == 20.0

    assert result.medium_decrease_increase_percentage == 20.0
    assert result.medium_decrease_decrease_percentage == 60.0
    assert result.medium_decrease_unchanged_percentage == 20.0

    assert result.medium_unchanged_increase_percentage == 10.0
    assert result.medium_unchanged_decrease_percentage == 30.0
    assert result.medium_unchanged_unchanged_percentage == 60.0


def test_all_high_series_percentages_are_calculated():
    summary = make_summary(
        transition_count=10,

        high_increase_increase_count=5,
        high_increase_decrease_count=3,
        high_increase_unchanged_count=2,

        high_decrease_increase_count=2,
        high_decrease_decrease_count=2,
        high_decrease_unchanged_count=6,

        high_unchanged_increase_count=3,
        high_unchanged_decrease_count=4,
        high_unchanged_unchanged_count=3,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.high_increase_increase_percentage == 50.0
    assert result.high_increase_decrease_percentage == 30.0
    assert result.high_increase_unchanged_percentage == 20.0

    assert result.high_decrease_increase_percentage == 20.0
    assert result.high_decrease_decrease_percentage == 20.0
    assert result.high_decrease_unchanged_percentage == 60.0

    assert result.high_unchanged_increase_percentage == 30.0
    assert result.high_unchanged_decrease_percentage == 40.0
    assert result.high_unchanged_unchanged_percentage == 30.0


def test_dominant_low_increase_direction():
    summary = make_summary(
        low_increase_increase_count=7,
        low_increase_decrease_count=2,
        low_increase_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_increase_directions == ("INCREASE",)


def test_dominant_low_decrease_direction():
    summary = make_summary(
        low_decrease_increase_count=2,
        low_decrease_decrease_count=7,
        low_decrease_unchanged_count=1,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_decrease_directions == ("DECREASE",)


def test_dominant_low_unchanged_direction():
    summary = make_summary(
        low_unchanged_increase_count=1,
        low_unchanged_decrease_count=2,
        low_unchanged_unchanged_count=7,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_unchanged_directions == ("UNCHANGED",)


def test_dominant_direction_tie_is_preserved():
    summary = make_summary(
        low_increase_increase_count=4,
        low_increase_decrease_count=4,
        low_increase_unchanged_count=2,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_increase_directions == (
        "INCREASE",
        "DECREASE",
    )


def test_three_way_dominant_direction_tie_is_preserved():
    summary = make_summary(
        low_increase_increase_count=4,
        low_increase_decrease_count=4,
        low_increase_unchanged_count=4,
        transition_count=12,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_increase_directions == (
        "INCREASE",
        "DECREASE",
        "UNCHANGED",
    )


def test_dominant_direction_is_empty_when_all_counts_are_zero():
    summary = make_summary(
        transition_count=10,
        low_increase_increase_count=0,
        low_increase_decrease_count=0,
        low_increase_unchanged_count=0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_increase_directions == ()


def test_movement_metrics_are_preserved():
    summary = make_summary(
        average_movement=12.5,
        minimum_movement=4.0,
        maximum_movement=30.0,
        total_movement=125.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.average_total_absolute_percentage_movement == 12.5
    assert result.minimum_total_absolute_percentage_movement == 4.0
    assert result.maximum_total_absolute_percentage_movement == 30.0
    assert result.total_absolute_percentage_movement == 125.0


def test_summary_transition_count_is_preserved():
    summary = make_summary(
        transition_count=25,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.transition_count == 25


def test_direction_percentages_are_independent():
    summary = make_summary(
        transition_count=10,

        low_increase_increase_count=10,
        low_increase_decrease_count=10,
        low_increase_unchanged_count=10,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.low_increase_increase_percentage == 100.0
    assert result.low_increase_decrease_percentage == 100.0
    assert result.low_increase_unchanged_percentage == 100.0


def test_invalid_summary_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            object()
        )


def test_negative_transition_count_raises():
    summary = make_summary(
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_boolean_transition_count_raises():
    summary = make_summary(
        transition_count=True,
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_negative_direction_count_raises():
    summary = make_summary(
        low_increase_increase_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_boolean_direction_count_raises():
    summary = make_summary(
        low_increase_increase_count=True,
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_direction_count_cannot_exceed_transition_count():
    summary = make_summary(
        transition_count=5,
        low_increase_increase_count=6,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_negative_average_movement_raises():
    summary = make_summary(
        average_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_negative_minimum_movement_raises():
    summary = make_summary(
        minimum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_negative_maximum_movement_raises():
    summary = make_summary(
        maximum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_negative_total_movement_raises():
    summary = make_summary(
        total_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_minimum_movement_cannot_exceed_maximum_movement():
    summary = make_summary(
        minimum_movement=30.0,
        maximum_movement=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_zero_transition_summary_requires_zero_counts():
    summary = make_summary(
        transition_count=0,
        low_increase_increase_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_zero_transition_summary_requires_zero_movement_metrics():
    summary = make_summary(
        transition_count=0,
        average_movement=1.0,
        minimum_movement=0.0,
        maximum_movement=1.0,
        total_movement=1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )


def test_getter_matches_builder():
    summary = make_summary()

    expected = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    actual = (
        get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert actual == expected


def test_expected_overview_fields_exist():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            make_summary()
        )
    )

    expected_fields = {
        "transition_count",

        "low_increase_increase_percentage",
        "low_increase_decrease_percentage",
        "low_increase_unchanged_percentage",

        "low_decrease_increase_percentage",
        "low_decrease_decrease_percentage",
        "low_decrease_unchanged_percentage",

        "low_unchanged_increase_percentage",
        "low_unchanged_decrease_percentage",
        "low_unchanged_unchanged_percentage",

        "medium_increase_increase_percentage",
        "medium_increase_decrease_percentage",
        "medium_increase_unchanged_percentage",

        "medium_decrease_increase_percentage",
        "medium_decrease_decrease_percentage",
        "medium_decrease_unchanged_percentage",

        "medium_unchanged_increase_percentage",
        "medium_unchanged_decrease_percentage",
        "medium_unchanged_unchanged_percentage",

        "high_increase_increase_percentage",
        "high_increase_decrease_percentage",
        "high_increase_unchanged_percentage",

        "high_decrease_increase_percentage",
        "high_decrease_decrease_percentage",
        "high_decrease_unchanged_percentage",

        "high_unchanged_increase_percentage",
        "high_unchanged_decrease_percentage",
        "high_unchanged_unchanged_percentage",

        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",

        "dominant_low_increase_directions",
        "dominant_low_decrease_directions",
        "dominant_low_unchanged_directions",

        "dominant_medium_increase_directions",
        "dominant_medium_decrease_directions",
        "dominant_medium_unchanged_directions",

        "dominant_high_increase_directions",
        "dominant_high_decrease_directions",
        "dominant_high_unchanged_directions",
    }

    assert set(result.__dataclass_fields__) == expected_fields


def test_dominant_direction_order_is_deterministic():
    summary = make_summary(
        low_increase_increase_count=4,
        low_increase_decrease_count=4,
        low_increase_unchanged_count=4,
        transition_count=12,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )

    assert result.dominant_low_increase_directions == (
        "INCREASE",
        "DECREASE",
        "UNCHANGED",
    )


def test_result_does_not_contain_prediction_or_ranking_fields():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            make_summary()
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


def test_source_summary_is_not_modified():
    summary = make_summary()

    original_values = {
        field_name: getattr(summary, field_name)
        for field_name in summary.__dataclass_fields__
    }

    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
        summary
    )

    for field_name, original_value in original_values.items():
        assert getattr(summary, field_name) == original_value