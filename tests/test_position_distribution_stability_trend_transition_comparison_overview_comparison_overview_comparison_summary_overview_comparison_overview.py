from dataclasses import fields

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview,
    compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overviews,
)


PERCENTAGE_FIELDS = (
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

MOVEMENT_FIELDS = (
    "average_total_absolute_percentage_movement",
    "minimum_total_absolute_percentage_movement",
    "maximum_total_absolute_percentage_movement",
    "total_absolute_percentage_movement",
)

DOMINANT_DIRECTION_FIELDS = (
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


def make_overview(
    *,
    transition_count=1,
    percentage_values=None,
    movement_values=None,
    dominant_directions=None,
):
    percentage_values = percentage_values or {}
    movement_values = movement_values or {}
    dominant_directions = dominant_directions or {}

    values = {"transition_count": transition_count}

    for field in PERCENTAGE_FIELDS:
        values[field] = percentage_values.get(field, 0.0)

    for field in MOVEMENT_FIELDS:
        values[field] = movement_values.get(field, 0.0)

    for field in DOMINANT_DIRECTION_FIELDS:
        values[field] = dominant_directions.get(field, ())

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview(
            **values
        )
    )


def test_output_dataclass_has_expected_fields():
    actual = {
        field.name
        for field in fields(
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview
        )
    }

    expected = {"overview_count"}

    for field in PERCENTAGE_FIELDS:
        expected.add(f"{field}_start")
        expected.add(f"{field}_end")
        expected.add(f"{field}_change")

    for field in MOVEMENT_FIELDS:
        expected.add(f"{field}_start")
        expected.add(f"{field}_end")
        expected.add(f"{field}_change")

    expected.update(
        {
            "total_absolute_percentage_movement",
            "mean_absolute_percentage_movement",
        }
    )

    assert actual == expected


def test_empty_input_returns_zero_result():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            ()
        )
    )

    assert result.overview_count == 0

    for field in PERCENTAGE_FIELDS + MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_start") == 0.0
        assert getattr(result, f"{field}_end") == 0.0
        assert getattr(result, f"{field}_change") == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_single_overview_preserves_values_and_has_zero_aggregate_movement():
    percentages = {
        field: float(index + 1)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }
    movements = {
        MOVEMENT_FIELDS[0]: 10.0,
        MOVEMENT_FIELDS[1]: 2.0,
        MOVEMENT_FIELDS[2]: 20.0,
        MOVEMENT_FIELDS[3]: 30.0,
    }
    directions = {
        field: ("INCREASE",)
        for field in DOMINANT_DIRECTION_FIELDS
    }

    overview = make_overview(
        transition_count=5,
        percentage_values=percentages,
        movement_values=movements,
        dominant_directions=directions,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )
    )

    assert result.overview_count == 1

    for field in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field}_start") == percentages[field]
        assert getattr(result, f"{field}_end") == percentages[field]
        assert getattr(result, f"{field}_change") == 0.0

    for field in MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_start") == movements[field]
        assert getattr(result, f"{field}_end") == movements[field]
        assert getattr(result, f"{field}_change") == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_two_overviews_calculate_all_percentage_changes():
    first_values = {
        field: float(index)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }
    second_values = {
        field: float(index + 10)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }

    first = make_overview(percentage_values=first_values)
    second = make_overview(percentage_values=second_values)

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    assert result.overview_count == 2

    for field in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field}_start") == first_values[field]
        assert getattr(result, f"{field}_end") == second_values[field]
        assert getattr(result, f"{field}_change") == (
            second_values[field] - first_values[field]
        )


def test_two_overviews_calculate_all_movement_changes():
    first_values = {
        MOVEMENT_FIELDS[0]: 1.0,
        MOVEMENT_FIELDS[1]: 2.0,
        MOVEMENT_FIELDS[2]: 3.0,
        MOVEMENT_FIELDS[3]: 4.0,
    }
    second_values = {
        MOVEMENT_FIELDS[0]: 5.0,
        MOVEMENT_FIELDS[1]: 7.0,
        MOVEMENT_FIELDS[2]: 9.0,
        MOVEMENT_FIELDS[3]: 11.0,
    }

    first = make_overview(movement_values=first_values)
    second = make_overview(movement_values=second_values)

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    for field in MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_start") == first_values[field]
        assert getattr(result, f"{field}_end") == second_values[field]
        assert getattr(result, f"{field}_change") == (
            second_values[field] - first_values[field]
        )


def test_total_absolute_percentage_movement_uses_all_27_percentage_fields():
    first = make_overview(
        percentage_values={field: 0.0 for field in PERCENTAGE_FIELDS}
    )
    second = make_overview(
        percentage_values={
            field: float(index + 1)
            for index, field in enumerate(PERCENTAGE_FIELDS)
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    expected_total = sum(range(1, 28))

    assert result.total_absolute_percentage_movement == expected_total
    assert result.mean_absolute_percentage_movement == expected_total


def test_mean_absolute_percentage_movement_uses_number_of_transitions():
    first = make_overview(
        percentage_values={field: 0.0 for field in PERCENTAGE_FIELDS}
    )
    second = make_overview(
        percentage_values={field: 1.0 for field in PERCENTAGE_FIELDS}
    )
    third = make_overview(
        percentage_values={field: 3.0 for field in PERCENTAGE_FIELDS}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second, third)
        )
    )

    assert result.total_absolute_percentage_movement == 81.0
    assert result.mean_absolute_percentage_movement == 40.5


def test_multiple_overviews_use_caller_order():
    first = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 10.0}
    )
    middle = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 50.0}
    )
    last = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 20.0}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, middle, last)
        )
    )

    assert result.overview_count == 3
    assert result.low_increase_increase_percentage_start == 10.0
    assert result.low_increase_increase_percentage_end == 20.0
    assert result.low_increase_increase_percentage_change == 10.0
    assert result.total_absolute_percentage_movement == 70.0
    assert result.mean_absolute_percentage_movement == 35.0


def test_negative_percentage_is_rejected():
    overview = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: -0.01}
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )


def test_percentage_above_100_is_rejected():
    overview = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 100.01}
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )


def test_negative_movement_is_rejected():
    overview = make_overview(
        movement_values={MOVEMENT_FIELDS[0]: -1.0}
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )


def test_minimum_greater_than_maximum_is_rejected():
    overview = make_overview(
        movement_values={
            "minimum_total_absolute_percentage_movement": 20.0,
            "maximum_total_absolute_percentage_movement": 10.0,
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (object(),)
        )


def test_invalid_input_container_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            [make_overview()]
        )


def test_wrapper_matches_builder():
    first = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 10.0}
    )
    second = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 25.0}
    )

    built = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    wrapped = (
        compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overviews(
            (first, second)
        )
    )

    assert wrapped == built


def test_result_is_frozen_dataclass():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (make_overview(),)
        )
    )

    with pytest.raises(AttributeError):
        result.overview_count = 10


def test_all_percentage_changes_can_be_negative():
    first = make_overview(
        percentage_values={field: 90.0 for field in PERCENTAGE_FIELDS}
    )
    second = make_overview(
        percentage_values={field: 10.0 for field in PERCENTAGE_FIELDS}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    for field in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field}_change") == -80.0

    assert result.total_absolute_percentage_movement == 2160.0
    assert result.mean_absolute_percentage_movement == 2160.0


def test_movement_metric_changes_do_not_contribute_to_percentage_movement_total():
    first = make_overview(
        movement_values={
            MOVEMENT_FIELDS[0]: 10.0,
            MOVEMENT_FIELDS[1]: 20.0,
            MOVEMENT_FIELDS[2]: 30.0,
            MOVEMENT_FIELDS[3]: 40.0,
        }
    )
    second = make_overview(
        movement_values={
            MOVEMENT_FIELDS[0]: 50.0,
            MOVEMENT_FIELDS[1]: 60.0,
            MOVEMENT_FIELDS[2]: 70.0,
            MOVEMENT_FIELDS[3]: 80.0,
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    assert result.average_total_absolute_percentage_movement_change == 40.0
    assert result.minimum_total_absolute_percentage_movement_change == 40.0
    assert result.maximum_total_absolute_percentage_movement_change == 40.0
    assert result.total_absolute_percentage_movement_change == 40.0
    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_zero_input_and_one_input_are_distinct_cases():
    empty = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            ()
        )
    )
    one = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (make_overview(),)
        )
    )

    assert empty.overview_count == 0
    assert one.overview_count == 1


def test_transition_count_does_not_control_output_count():
    first = make_overview(transition_count=1)
    second = make_overview(transition_count=100)

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    assert result.overview_count == 2


def test_boundary_percentages_are_accepted():
    overview = make_overview(
        percentage_values={
            PERCENTAGE_FIELDS[0]: 0.0,
            PERCENTAGE_FIELDS[1]: 100.0,
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )
    )

    assert result.low_increase_increase_percentage_start == 0.0
    assert result.low_increase_decrease_percentage_start == 100.0


def test_boundary_movement_zero_is_accepted():
    overview = make_overview(
        movement_values={field: 0.0 for field in MOVEMENT_FIELDS}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (overview,)
        )
    )

    for field in MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_change") == 0.0


def test_total_absolute_movement_uses_consecutive_pairs():
    first = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 0.0}
    )
    second = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 2.0}
    )
    third = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 10.0}
    )
    fourth = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 5.0}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second, third, fourth)
        )
    )

    assert result.total_absolute_percentage_movement == 15.0
    assert result.mean_absolute_percentage_movement == 5.0


def test_intermediate_overviews_are_not_skipped():
    first = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 10.0}
    )
    second = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 50.0}
    )
    third = make_overview(
        percentage_values={PERCENTAGE_FIELDS[0]: 20.0}
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second, third)
        )
    )

    assert result.total_absolute_percentage_movement == 70.0
    assert result.mean_absolute_percentage_movement == 35.0


def test_summary_fields_are_taken_from_first_and_last():
    first = make_overview(
        percentage_values={field: 10.0 for field in PERCENTAGE_FIELDS},
        movement_values={field: 10.0 for field in MOVEMENT_FIELDS},
    )
    middle = make_overview(
        percentage_values={field: 90.0 for field in PERCENTAGE_FIELDS},
        movement_values={field: 90.0 for field in MOVEMENT_FIELDS},
    )
    last = make_overview(
        percentage_values={field: 30.0 for field in PERCENTAGE_FIELDS},
        movement_values={field: 30.0 for field in MOVEMENT_FIELDS},
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, middle, last)
        )
    )

    for field in PERCENTAGE_FIELDS + MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_start") == 10.0
        assert getattr(result, f"{field}_end") == 30.0
        assert getattr(result, f"{field}_change") == 20.0


def test_total_absolute_percentage_movement_ignores_movement_summary_fields():
    first = make_overview(
        percentage_values={field: 10.0 for field in PERCENTAGE_FIELDS},
        movement_values={field: 0.0 for field in MOVEMENT_FIELDS},
    )
    second = make_overview(
        percentage_values={field: 10.0 for field in PERCENTAGE_FIELDS},
        movement_values={field: 100.0 for field in MOVEMENT_FIELDS},
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (first, second)
        )
    )

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_result_type_is_correct():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview(
            (make_overview(),)
        )
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview,
    )
