from dataclasses import fields

import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison,
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
    transition_count=3,
    percentage_base=0.0,
    movement_base=0.0,
    dominant_directions=("INCREASE",),
):
    values = {
        field: percentage_base
        for field in PERCENTAGE_FIELDS
    }

    movement_values = {
        field: movement_base
        for field in MOVEMENT_FIELDS
    }

    dominant_values = {
        field: dominant_directions
        for field in DOMINANT_DIRECTION_FIELDS
    }

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview(
            transition_count=transition_count,
            **values,
            **movement_values,
            **dominant_values,
        )
    )


def make_zero_overview():
    return make_overview(
        transition_count=0,
        percentage_base=0.0,
        movement_base=0.0,
        dominant_directions=(),
    )


def make_custom_overview(
    *,
    transition_count=3,
    percentages=None,
    movements=None,
    dominant_directions=None,
):
    values = {
        field: 0.0
        for field in PERCENTAGE_FIELDS
    }

    if percentages:
        values.update(percentages)

    movement_values = {
        field: 0.0
        for field in MOVEMENT_FIELDS
    }

    if movements:
        movement_values.update(movements)

    dominant_values = {
        field: ()
        for field in DOMINANT_DIRECTION_FIELDS
    }

    if dominant_directions:
        dominant_values.update(dominant_directions)

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview(
            transition_count=transition_count,
            **values,
            **movement_values,
            **dominant_values,
        )
    )


def test_output_dataclass_has_expected_fields():
    result_fields = {
        field.name
        for field in fields(
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison
        )
    }

    expected_fields = {"overview_count"}

    for field in PERCENTAGE_FIELDS:
        expected_fields.add(f"{field}_start")
        expected_fields.add(f"{field}_end")
        expected_fields.add(f"{field}_change")

    for field in MOVEMENT_FIELDS:
        expected_fields.add(f"{field}_start")
        expected_fields.add(f"{field}_end")
        expected_fields.add(f"{field}_change")

    expected_fields.update(
        {
            "total_absolute_percentage_movement",
            "mean_absolute_percentage_movement",
        }
    )

    assert result_fields == expected_fields


def test_empty_input_returns_zero_result():
    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            ()
        )
    )

    assert result.overview_count == 0

    for field in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field}_start") == 0.0
        assert getattr(result, f"{field}_end") == 0.0
        assert getattr(result, f"{field}_change") == 0.0

    for field in MOVEMENT_FIELDS:
        assert getattr(result, f"{field}_start") == 0.0
        assert getattr(result, f"{field}_end") == 0.0
        assert getattr(result, f"{field}_change") == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_single_overview_preserves_values_and_has_zero_change():
    percentages = {
        PERCENTAGE_FIELDS[index]: float(index + 1)
        for index in range(len(PERCENTAGE_FIELDS))
    }

    movements = {
        MOVEMENT_FIELDS[0]: 10.0,
        MOVEMENT_FIELDS[1]: 2.0,
        MOVEMENT_FIELDS[2]: 20.0,
        MOVEMENT_FIELDS[3]: 30.0,
    }

    overview = make_custom_overview(
        transition_count=5,
        percentages=percentages,
        movements=movements,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )
    )

    assert result.overview_count == 1

    for field in PERCENTAGE_FIELDS:
        value = percentages[field]

        assert getattr(result, f"{field}_start") == value
        assert getattr(result, f"{field}_end") == value
        assert getattr(result, f"{field}_change") == 0.0

    for field in MOVEMENT_FIELDS:
        value = movements[field]

        assert getattr(result, f"{field}_start") == value
        assert getattr(result, f"{field}_end") == value
        assert getattr(result, f"{field}_change") == 0.0

    assert result.total_absolute_percentage_movement == 0.0
    assert result.mean_absolute_percentage_movement == 0.0


def test_two_overviews_calculate_all_percentage_changes():
    first_percentages = {
        field: float(index)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }

    second_percentages = {
        field: float(index + 10)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }

    first = make_custom_overview(
        transition_count=2,
        percentages=first_percentages,
    )

    second = make_custom_overview(
        transition_count=4,
        percentages=second_percentages,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second)
        )
    )

    assert result.overview_count == 2

    for field in PERCENTAGE_FIELDS:
        start = first_percentages[field]
        end = second_percentages[field]

        assert getattr(result, f"{field}_start") == start
        assert getattr(result, f"{field}_end") == end
        assert getattr(result, f"{field}_change") == end - start


def test_two_overviews_calculate_all_movement_changes():
    first_movements = {
        MOVEMENT_FIELDS[0]: 1.0,
        MOVEMENT_FIELDS[1]: 2.0,
        MOVEMENT_FIELDS[2]: 3.0,
        MOVEMENT_FIELDS[3]: 4.0,
    }

    second_movements = {
        MOVEMENT_FIELDS[0]: 5.0,
        MOVEMENT_FIELDS[1]: 7.0,
        MOVEMENT_FIELDS[2]: 9.0,
        MOVEMENT_FIELDS[3]: 11.0,
    }

    first = make_custom_overview(
        movements=first_movements,
    )

    second = make_custom_overview(
        movements=second_movements,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second)
        )
    )

    for field in MOVEMENT_FIELDS:
        start = first_movements[field]
        end = second_movements[field]

        assert getattr(result, f"{field}_start") == start
        assert getattr(result, f"{field}_end") == end
        assert getattr(result, f"{field}_change") == end - start


def test_total_absolute_percentage_movement_uses_all_27_percentage_fields():
    first_percentages = {
        field: 0.0
        for field in PERCENTAGE_FIELDS
    }

    second_percentages = {
        field: float(index + 1)
        for index, field in enumerate(PERCENTAGE_FIELDS)
    }

    first = make_custom_overview(
        percentages=first_percentages,
    )

    second = make_custom_overview(
        percentages=second_percentages,
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second)
        )
    )

    expected_total = sum(second_percentages.values())

    assert result.total_absolute_percentage_movement == expected_total
    assert result.mean_absolute_percentage_movement == expected_total


def test_mean_absolute_percentage_movement_uses_number_of_transitions():
    first = make_custom_overview(
        percentages={
            field: 0.0
            for field in PERCENTAGE_FIELDS
        }
    )

    second = make_custom_overview(
        percentages={
            field: 1.0
            for field in PERCENTAGE_FIELDS
        }
    )

    third = make_custom_overview(
        percentages={
            field: 3.0
            for field in PERCENTAGE_FIELDS
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second, third)
        )
    )

    first_movement = 27.0
    second_movement = 54.0

    assert result.total_absolute_percentage_movement == 81.0
    assert result.mean_absolute_percentage_movement == (
        (first_movement + second_movement) / 2
    )


def test_multiple_overviews_use_caller_order():
    first = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 10.0,
        }
    )

    middle = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 50.0,
        }
    )

    last = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 20.0,
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
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
    overview = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: -0.01,
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_percentage_above_100_is_rejected():
    overview = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 100.01,
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_negative_movement_is_rejected():
    overview = make_custom_overview(
        movements={
            MOVEMENT_FIELDS[0]: -1.0,
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_minimum_greater_than_maximum_is_rejected():
    overview = make_custom_overview(
        movements={
            "minimum_total_absolute_percentage_movement": 20.0,
            "maximum_total_absolute_percentage_movement": 10.0,
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_negative_transition_count_is_rejected():
    overview = make_custom_overview(
        transition_count=-1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_non_integer_transition_count_is_rejected():
    overview = make_custom_overview(
        transition_count=1.5,
    )

    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_zero_transition_overview_must_have_zero_metrics():
    overview = make_custom_overview(
        transition_count=0,
        percentages={
            PERCENTAGE_FIELDS[0]: 1.0,
        },
        movements={
            MOVEMENT_FIELDS[0]: 1.0,
        },
        dominant_directions={
            DOMINANT_DIRECTION_FIELDS[0]: ("INCREASE",),
        },
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_zero_transition_overview_must_have_empty_dominant_directions():
    overview = make_zero_overview()

    invalid = make_custom_overview(
        transition_count=0,
        dominant_directions={
            DOMINANT_DIRECTION_FIELDS[0]: ("INCREASE",),
        },
    )

    assert (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        ).overview_count
        == 1
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (invalid,)
        )


def test_duplicate_dominant_direction_is_rejected():
    overview = make_custom_overview(
        dominant_directions={
            DOMINANT_DIRECTION_FIELDS[0]: (
                "INCREASE",
                "INCREASE",
            ),
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_invalid_dominant_direction_is_rejected():
    overview = make_custom_overview(
        dominant_directions={
            DOMINANT_DIRECTION_FIELDS[0]: (
                "INVALID",
            ),
        }
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (overview,)
        )


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (object(),)
        )


def test_invalid_input_container_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            [make_overview()]
        )


def test_wrapper_matches_builder():
    first = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 10.0,
        }
    )

    second = make_custom_overview(
        percentages={
            PERCENTAGE_FIELDS[0]: 25.0,
        }
    )

    built = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (make_overview(),)
        )
    )

    with pytest.raises(Exception):
        result.overview_count = 10


def test_all_percentage_changes_can_be_negative():
    first = make_custom_overview(
        percentages={
            field: 90.0
            for field in PERCENTAGE_FIELDS
        }
    )

    second = make_custom_overview(
        percentages={
            field: 10.0
            for field in PERCENTAGE_FIELDS
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second)
        )
    )

    for field in PERCENTAGE_FIELDS:
        assert getattr(result, f"{field}_change") == -80.0

    assert result.total_absolute_percentage_movement == 27 * 80.0
    assert result.mean_absolute_percentage_movement == 27 * 80.0


def test_movement_metric_changes_do_not_contribute_to_percentage_movement_total():
    first = make_custom_overview(
        movements={
            "average_total_absolute_percentage_movement": 10.0,
            "minimum_total_absolute_percentage_movement": 20.0,
            "maximum_total_absolute_percentage_movement": 30.0,
            "total_absolute_percentage_movement": 40.0,
        }
    )

    second = make_custom_overview(
        movements={
            "average_total_absolute_percentage_movement": 50.0,
            "minimum_total_absolute_percentage_movement": 60.0,
            "maximum_total_absolute_percentage_movement": 70.0,
            "total_absolute_percentage_movement": 80.0,
        }
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
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
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            ()
        )
    )

    one = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (make_overview(),)
        )
    )

    assert empty.overview_count == 0
    assert one.overview_count == 1


def test_transition_count_does_not_control_percentage_calculation():
    first = make_custom_overview(
        transition_count=1,
        percentages={
            PERCENTAGE_FIELDS[0]: 20.0,
        },
    )

    second = make_custom_overview(
        transition_count=100,
        percentages={
            PERCENTAGE_FIELDS[0]: 70.0,
        },
    )

    result = (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            (first, second)
        )
    )

    assert result.low_increase_increase_percentage_start == 20.0
    assert result.low_increase_increase_percentage_end == 70.0
    assert result.low_increase_increase_percentage_change == 50.0