"""
Tests for Phase 9.3.44

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison.
"""

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison,
    compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overviews,
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


def test_result_is_dataclass():
    assert is_dataclass(
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison
    )


def test_result_is_frozen():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.overview_count = 99


def test_empty_input_returns_zero_comparison():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            ()
        )
    )

    assert result.overview_count == 0

    for field_name in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field_name}_start") == 0.0
        assert getattr(result, f"{field_name}_end") == 0.0
        assert getattr(result, f"{field_name}_change") == 0.0

    assert result.average_total_absolute_percentage_movement_start == 0.0
    assert result.average_total_absolute_percentage_movement_end == 0.0
    assert result.average_total_absolute_percentage_movement_change == 0.0

    assert result.minimum_total_absolute_percentage_movement_start == 0.0
    assert result.minimum_total_absolute_percentage_movement_end == 0.0
    assert result.minimum_total_absolute_percentage_movement_change == 0.0

    assert result.maximum_total_absolute_percentage_movement_start == 0.0
    assert result.maximum_total_absolute_percentage_movement_end == 0.0
    assert result.maximum_total_absolute_percentage_movement_change == 0.0

    assert result.total_absolute_percentage_movement_start == 0.0
    assert result.total_absolute_percentage_movement_end == 0.0
    assert result.total_absolute_percentage_movement_change == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_single_overview_has_zero_percentage_movement():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )
    )

    assert result.overview_count == 1
    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_single_overview_start_and_end_are_equal():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )
    )

    for field_name in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field_name}_start") == getattr(
            result,
            f"{field_name}_end",
        )
        assert getattr(result, f"{field_name}_change") == 0.0


def test_percentage_changes_are_end_minus_start():
    first = make_overview(
        low_increase_percentage=20.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=50.0,
        medium_increase_percentage=30.0,
        medium_decrease_percentage=20.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=40.0,
        high_decrease_percentage=30.0,
        high_unchanged_percentage=30.0,
    )

    second = make_overview(
        low_increase_percentage=30.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=50.0,
        medium_increase_percentage=20.0,
        medium_decrease_percentage=30.0,
        medium_unchanged_percentage=50.0,
        high_increase_percentage=30.0,
        high_decrease_percentage=20.0,
        high_unchanged_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == 10.0
    assert result.low_decrease_percentage_change == -10.0
    assert result.low_unchanged_percentage_change == 0.0

    assert result.medium_increase_percentage_change == -10.0
    assert result.medium_decrease_percentage_change == 10.0
    assert result.medium_unchanged_percentage_change == 0.0

    assert result.high_increase_percentage_change == -10.0
    assert result.high_decrease_percentage_change == -10.0
    assert result.high_unchanged_percentage_change == 20.0


def test_first_observation_supplies_start_values():
    first = make_overview(
        low_increase_percentage=10.0,
        medium_increase_percentage=20.0,
        high_increase_percentage=30.0,
    )

    second = make_overview(
        low_increase_percentage=40.0,
        medium_increase_percentage=50.0,
        high_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_start == 10.0
    assert result.medium_increase_percentage_start == 20.0
    assert result.high_increase_percentage_start == 30.0


def test_last_observation_supplies_end_values():
    first = make_overview(
        low_increase_percentage=10.0,
        medium_increase_percentage=20.0,
        high_increase_percentage=30.0,
    )

    second = make_overview(
        low_increase_percentage=40.0,
        medium_increase_percentage=50.0,
        high_increase_percentage=60.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_end == 40.0
    assert result.medium_increase_percentage_end == 50.0
    assert result.high_increase_percentage_end == 60.0


def test_intermediate_observations_are_used_for_total_movement():
    first = make_overview(
        low_increase_percentage=20.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=50.0,
    )

    middle = make_overview(
        low_increase_percentage=40.0,
        low_decrease_percentage=10.0,
        low_unchanged_percentage=50.0,
    )

    last = make_overview(
        low_increase_percentage=30.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, middle, last)
        )
    )

    expected_movement = (
        abs(40.0 - 20.0)
        + abs(10.0 - 30.0)
        + abs(50.0 - 50.0)
        + abs(30.0 - 40.0)
        + abs(20.0 - 10.0)
        + abs(50.0 - 50.0)
    )

    assert result.total_absolute_percentage_movement == pytest.approx(
        expected_movement
    )


def test_total_movement_uses_all_nine_percentage_fields():
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
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

    assert result.total_absolute_percentage_movement == pytest.approx(
        expected
    )


def test_mean_movement_is_total_divided_by_transition_count():
    first = make_overview(
        low_increase_percentage=20.0,
        low_decrease_percentage=30.0,
        low_unchanged_percentage=50.0,
    )

    second = make_overview(
        low_increase_percentage=30.0,
        low_decrease_percentage=20.0,
        low_unchanged_percentage=50.0,
    )

    third = make_overview(
        low_increase_percentage=40.0,
        low_decrease_percentage=10.0,
        low_unchanged_percentage=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second, third)
        )
    )

    assert result.mean_absolute_percentage_movement == pytest.approx(
        result.total_absolute_percentage_movement / 2
    )


def test_movement_metrics_use_first_and_last_values():
    first = make_overview(
        average_movement=5.0,
        minimum_movement=2.0,
        maximum_movement=10.0,
        total_movement=20.0,
    )

    second = make_overview(
        average_movement=8.0,
        minimum_movement=4.0,
        maximum_movement=15.0,
        total_movement=30.0,
    )

    third = make_overview(
        average_movement=12.0,
        minimum_movement=6.0,
        maximum_movement=25.0,
        total_movement=50.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second, third)
        )
    )

    assert result.average_total_absolute_percentage_movement_start == 5.0
    assert result.average_total_absolute_percentage_movement_end == 12.0
    assert result.average_total_absolute_percentage_movement_change == 7.0

    assert result.minimum_total_absolute_percentage_movement_start == 2.0
    assert result.minimum_total_absolute_percentage_movement_end == 6.0
    assert result.minimum_total_absolute_percentage_movement_change == 4.0

    assert result.maximum_total_absolute_percentage_movement_start == 10.0
    assert result.maximum_total_absolute_percentage_movement_end == 25.0
    assert result.maximum_total_absolute_percentage_movement_change == 15.0

    assert result.total_absolute_percentage_movement_start == 20.0
    assert result.total_absolute_percentage_movement_end == 50.0
    assert result.total_absolute_percentage_movement_change == 30.0


def test_zero_change_is_preserved():
    first = make_overview(
        low_increase_percentage=25.0,
    )

    second = make_overview(
        low_increase_percentage=25.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == 0.0


def test_negative_change_is_preserved():
    first = make_overview(
        low_increase_percentage=60.0,
    )

    second = make_overview(
        low_increase_percentage=40.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == -20.0


def test_positive_change_is_preserved():
    first = make_overview(
        low_increase_percentage=20.0,
    )

    second = make_overview(
        low_increase_percentage=45.0,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_percentage_change == 25.0


def test_overview_count_matches_input_length():
    overviews = (
        make_overview(),
        make_overview(),
        make_overview(),
        make_overview(),
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            overviews
        )
    )

    assert result.overview_count == 4


def test_input_order_is_preserved():
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (first, second, third)
        )
    )

    assert result.low_increase_percentage_start == 10.0
    assert result.low_increase_percentage_end == 70.0
    assert result.low_increase_percentage_change == 60.0


def test_invalid_input_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            []
        )


def test_invalid_item_type_raises():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (object(),)
        )


def test_negative_transition_count_in_overview_raises():
    overview = make_overview(
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_boolean_transition_count_in_overview_raises():
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (invalid,)
        )


def test_percentage_below_zero_raises():
    overview = make_overview(
        low_increase_percentage=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_percentage_above_100_raises():
    overview = make_overview(
        low_increase_percentage=101.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_average_movement_below_zero_raises():
    overview = make_overview(
        average_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_minimum_movement_below_zero_raises():
    overview = make_overview(
        minimum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_maximum_movement_below_zero_raises():
    overview = make_overview(
        maximum_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_total_movement_below_zero_raises():
    overview = make_overview(
        total_movement=-1.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_minimum_movement_cannot_exceed_maximum():
    overview = make_overview(
        minimum_movement=30.0,
        maximum_movement=20.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_dominant_directions_must_be_tuple():
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (invalid,)
        )


def test_duplicate_dominant_directions_raise():
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

            dominant_low_directions=("INCREASE", "INCREASE"),
            dominant_medium_directions=overview.dominant_medium_directions,
            dominant_high_directions=overview.dominant_high_directions,
        )
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (invalid,)
        )


def test_invalid_dominant_direction_raises():
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

            dominant_low_directions=("INVALID",),
            dominant_medium_directions=overview.dominant_medium_directions,
            dominant_high_directions=overview.dominant_high_directions,
        )
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (invalid,)
        )


def test_empty_dominant_directions_are_allowed_for_zero_transition_count():
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )
    )

    assert result.overview_count == 1
    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_empty_dominant_directions_are_rejected_for_positive_transition_count():
    overview = make_overview(
        dominant_low_directions=(),
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )


def test_wrapper_matches_builder():
    first = make_overview(
        low_increase_percentage=20.0,
    )

    second = make_overview(
        low_increase_percentage=40.0,
    )

    overviews = (
        first,
        second,
    )

    expected = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            overviews
        )
    )

    actual = (
        compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overviews(
            overviews
        )
    )

    assert actual == expected


def test_expected_fields_exist():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
        )
    )

    expected_fields = {
        "overview_count",

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
        "mean_absolute_percentage_movement",
    }

    assert set(result.__dataclass_fields__) == expected_fields


def test_no_prediction_or_ranking_fields_exist():
    overview = make_overview()

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            (overview,)
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