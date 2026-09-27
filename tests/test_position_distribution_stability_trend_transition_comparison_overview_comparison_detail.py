import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_detail,
)


def make_overview(
    *,
    transition_count=10,
    low_increase=20.0,
    low_decrease=30.0,
    low_unchanged=50.0,
    medium_increase=30.0,
    medium_decrease=20.0,
    medium_unchanged=50.0,
    high_increase=40.0,
    high_decrease=10.0,
    high_unchanged=50.0,
    average_movement=2.0,
    minimum_movement=1.0,
    maximum_movement=4.0,
    total_movement=20.0,
    dominant_low=("UNCHANGED",),
    dominant_medium=("UNCHANGED",),
    dominant_high=("INCREASE",),
):
    return PositionDistributionStabilityTrendTransitionComparisonOverview(
        transition_count=transition_count,
        low_increase_percentage=low_increase,
        low_decrease_percentage=low_decrease,
        low_unchanged_percentage=low_unchanged,
        medium_increase_percentage=medium_increase,
        medium_decrease_percentage=medium_decrease,
        medium_unchanged_percentage=medium_unchanged,
        high_increase_percentage=high_increase,
        high_decrease_percentage=high_decrease,
        high_unchanged_percentage=high_unchanged,
        average_total_absolute_percentage_movement=average_movement,
        minimum_total_absolute_percentage_movement=minimum_movement,
        maximum_total_absolute_percentage_movement=maximum_movement,
        total_absolute_percentage_movement=total_movement,
        dominant_low_directions=dominant_low,
        dominant_medium_directions=dominant_medium,
        dominant_high_directions=dominant_high,
    )


def make_zero_transition_overview():
    return make_overview(
        transition_count=0,
        low_increase=0.0,
        low_decrease=0.0,
        low_unchanged=0.0,
        medium_increase=0.0,
        medium_decrease=0.0,
        medium_unchanged=0.0,
        high_increase=0.0,
        high_decrease=0.0,
        high_unchanged=0.0,
        average_movement=0.0,
        minimum_movement=0.0,
        maximum_movement=0.0,
        total_movement=0.0,
        dominant_low=(),
        dominant_medium=(),
        dominant_high=(),
    )


def validate_overview(overview):
    return build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (overview,)
    )


def test_empty_input_returns_empty_detail():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(())
    assert result == PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail(
        overview_count=0,
        transition_count=0,
        transitions=(),
    )


def test_single_overview_has_no_transitions():
    result = validate_overview(make_overview())
    assert result.overview_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_two_overviews_create_one_transition():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    assert result.overview_count == 2
    assert result.transition_count == 1
    assert len(result.transitions) == 1


def test_three_overviews_create_two_transitions():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        tuple(make_overview() for _ in range(3))
    )
    assert result.overview_count == 3
    assert result.transition_count == 2
    assert [item.transition_index for item in result.transitions] == [1, 2]


def test_transition_indexes_are_sequential():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        tuple(make_overview() for _ in range(5))
    )
    assert [item.transition_index for item in result.transitions] == [1, 2, 3, 4]


def test_start_and_end_percentages_are_preserved():
    first = make_overview(low_increase=10.0, low_decrease=20.0, low_unchanged=70.0)
    second = make_overview(low_increase=30.0, low_decrease=25.0, low_unchanged=45.0)

    transition = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    ).transitions[0]

    assert transition.low_increase_percentage_start == 10.0
    assert transition.low_increase_percentage_end == 30.0
    assert transition.low_decrease_percentage_start == 20.0
    assert transition.low_decrease_percentage_end == 25.0
    assert transition.low_unchanged_percentage_start == 70.0
    assert transition.low_unchanged_percentage_end == 45.0


def test_percentage_changes_are_end_minus_start():
    first = make_overview(
        low_increase=10.0, low_decrease=20.0, low_unchanged=70.0,
        medium_increase=40.0, medium_decrease=30.0, medium_unchanged=30.0,
        high_increase=20.0, high_decrease=50.0, high_unchanged=30.0,
    )
    second = make_overview(
        low_increase=30.0, low_decrease=15.0, low_unchanged=55.0,
        medium_increase=25.0, medium_decrease=35.0, medium_unchanged=40.0,
        high_increase=35.0, high_decrease=40.0, high_unchanged=25.0,
    )

    transition = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    ).transitions[0]

    assert transition.low_increase_percentage_change == 20.0
    assert transition.low_decrease_percentage_change == -5.0
    assert transition.low_unchanged_percentage_change == -15.0
    assert transition.medium_increase_percentage_change == -15.0
    assert transition.medium_decrease_percentage_change == 5.0
    assert transition.medium_unchanged_percentage_change == 10.0
    assert transition.high_increase_percentage_change == 15.0
    assert transition.high_decrease_percentage_change == -10.0
    assert transition.high_unchanged_percentage_change == -5.0


def test_movement_metrics_start_end_and_change_are_preserved():
    first = make_overview(
        average_movement=2.0, minimum_movement=1.0,
        maximum_movement=5.0, total_movement=20.0,
    )
    second = make_overview(
        average_movement=4.0, minimum_movement=2.0,
        maximum_movement=8.0, total_movement=35.0,
    )

    transition = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    ).transitions[0]

    assert transition.average_total_absolute_percentage_movement_start == 2.0
    assert transition.average_total_absolute_percentage_movement_end == 4.0
    assert transition.average_total_absolute_percentage_movement_change == 2.0
    assert transition.minimum_total_absolute_percentage_movement_start == 1.0
    assert transition.minimum_total_absolute_percentage_movement_end == 2.0
    assert transition.minimum_total_absolute_percentage_movement_change == 1.0
    assert transition.maximum_total_absolute_percentage_movement_start == 5.0
    assert transition.maximum_total_absolute_percentage_movement_end == 8.0
    assert transition.maximum_total_absolute_percentage_movement_change == 3.0
    assert transition.total_absolute_percentage_movement_start == 20.0
    assert transition.total_absolute_percentage_movement_end == 35.0
    assert transition.total_absolute_percentage_movement_change == 15.0


def test_total_absolute_percentage_movement_sums_nine_direction_changes():
    first = make_overview(
        low_increase=10.0, low_decrease=20.0, low_unchanged=70.0,
        medium_increase=20.0, medium_decrease=30.0, medium_unchanged=50.0,
        high_increase=30.0, high_decrease=40.0, high_unchanged=30.0,
    )
    second = make_overview(
        low_increase=20.0, low_decrease=15.0, low_unchanged=65.0,
        medium_increase=25.0, medium_decrease=25.0, medium_unchanged=50.0,
        high_increase=40.0, high_decrease=30.0, high_unchanged=30.0,
    )

    transition = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    ).transitions[0]

    expected = 10.0 + 5.0 + 5.0 + 5.0 + 5.0 + 0.0 + 10.0 + 10.0 + 0.0
    assert transition.total_absolute_percentage_movement == expected


def test_zero_change_produces_zero_movement():
    overview = make_overview()
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (overview, overview)
    )
    assert result.transitions[0].total_absolute_percentage_movement == 0.0


def test_three_overviews_preserve_each_consecutive_transition():
    first = make_overview(low_increase=10.0, low_decrease=20.0, low_unchanged=70.0)
    second = make_overview(low_increase=30.0, low_decrease=20.0, low_unchanged=50.0)
    third = make_overview(low_increase=20.0, low_decrease=30.0, low_unchanged=50.0)

    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second, third)
    )

    assert result.transitions[0].low_increase_percentage_change == 20.0
    assert result.transitions[1].low_increase_percentage_change == -10.0
    assert result.transitions[0].low_decrease_percentage_change == 0.0
    assert result.transitions[1].low_decrease_percentage_change == 10.0


def test_intermediate_overview_is_not_skipped():
    first = make_overview(low_increase=10.0, low_decrease=20.0, low_unchanged=70.0)
    second = make_overview(low_increase=50.0, low_decrease=10.0, low_unchanged=40.0)
    third = make_overview(low_increase=20.0, low_decrease=30.0, low_unchanged=50.0)

    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second, third)
    )

    assert result.transitions[0].low_increase_percentage_change == 40.0
    assert result.transitions[1].low_increase_percentage_change == -30.0


def test_non_tuple_input_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
            [make_overview()]
        )


def test_invalid_overview_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
            (object(),)
        )


def test_negative_transition_count_is_rejected():
    overview = make_overview(transition_count=-1)
    with pytest.raises(ValueError):
        validate_overview(overview)


@pytest.mark.parametrize(
    "field_name",
    [
        "low_increase",
        "low_decrease",
        "low_unchanged",
        "medium_increase",
        "medium_decrease",
        "medium_unchanged",
        "high_increase",
        "high_decrease",
        "high_unchanged",
    ],
)
def test_percentage_below_zero_is_rejected(field_name):
    values = {
        "low_increase": 20.0, "low_decrease": 30.0, "low_unchanged": 50.0,
        "medium_increase": 30.0, "medium_decrease": 20.0, "medium_unchanged": 50.0,
        "high_increase": 40.0, "high_decrease": 10.0, "high_unchanged": 50.0,
    }
    values[field_name] = -1.0

    with pytest.raises(ValueError):
        validate_overview(make_overview(**values))


@pytest.mark.parametrize(
    "field_name",
    [
        "low_increase",
        "low_decrease",
        "low_unchanged",
        "medium_increase",
        "medium_decrease",
        "medium_unchanged",
        "high_increase",
        "high_decrease",
        "high_unchanged",
    ],
)
def test_percentage_above_100_is_rejected(field_name):
    values = {
        "low_increase": 20.0, "low_decrease": 30.0, "low_unchanged": 50.0,
        "medium_increase": 30.0, "medium_decrease": 20.0, "medium_unchanged": 50.0,
        "high_increase": 40.0, "high_decrease": 10.0, "high_unchanged": 50.0,
    }
    values[field_name] = 101.0

    with pytest.raises(ValueError):
        validate_overview(make_overview(**values))


def test_direction_group_must_sum_to_100():
    overview = make_overview(
        low_increase=20.0,
        low_decrease=20.0,
        low_unchanged=20.0,
    )
    with pytest.raises(ValueError):
        validate_overview(overview)


def test_zero_transition_count_requires_zero_percentages():
    overview = make_overview(
        transition_count=0,
        low_increase=20.0,
        low_decrease=0.0,
        low_unchanged=0.0,
        medium_increase=0.0,
        medium_decrease=0.0,
        medium_unchanged=0.0,
        high_increase=0.0,
        high_decrease=0.0,
        high_unchanged=0.0,
        dominant_low=(),
        dominant_medium=(),
        dominant_high=(),
    )
    with pytest.raises(ValueError):
        validate_overview(overview)


def test_zero_transition_count_requires_empty_dominant_directions():
    overview = make_overview(
        transition_count=0,
        low_increase=0.0,
        low_decrease=0.0,
        low_unchanged=0.0,
        medium_increase=0.0,
        medium_decrease=0.0,
        medium_unchanged=0.0,
        high_increase=0.0,
        high_decrease=0.0,
        high_unchanged=0.0,
        dominant_low=("INCREASE",),
        dominant_medium=(),
        dominant_high=(),
    )
    with pytest.raises(ValueError):
        validate_overview(overview)


def test_negative_movement_metric_is_rejected():
    with pytest.raises(ValueError):
        validate_overview(make_overview(average_movement=-1.0))


def test_minimum_movement_cannot_exceed_maximum_movement():
    with pytest.raises(ValueError):
        validate_overview(make_overview(minimum_movement=10.0, maximum_movement=5.0))


def test_dominant_direction_must_be_valid():
    with pytest.raises(ValueError):
        validate_overview(make_overview(dominant_low=("INVALID",)))


def test_dominant_direction_must_be_tuple():
    with pytest.raises(TypeError):
        validate_overview(make_overview(dominant_low=["INCREASE"]))


def test_duplicate_dominant_direction_is_rejected():
    with pytest.raises(ValueError):
        validate_overview(make_overview(dominant_low=("INCREASE", "INCREASE")))


def test_result_is_frozen():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    with pytest.raises(AttributeError):
        result.overview_count = 99


def test_transition_result_is_frozen():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    with pytest.raises(AttributeError):
        result.transitions[0].transition_index = 99


def test_result_type_is_correct():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    assert isinstance(
        result,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail,
    )


def test_transition_type_is_correct():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    assert isinstance(
        result.transitions[0],
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
    )


def test_wrapper_matches_builder():
    overviews = (
        make_overview(),
        make_overview(
            low_increase=30.0,
            low_decrease=20.0,
            low_unchanged=50.0,
        ),
    )

    built = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        overviews
    )
    wrapped = get_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        overviews
    )

    assert wrapped == built


def test_all_nine_direction_changes_are_recorded():
    first = make_overview(
        low_increase=10.0, low_decrease=20.0, low_unchanged=70.0,
        medium_increase=20.0, medium_decrease=30.0, medium_unchanged=50.0,
        high_increase=30.0, high_decrease=40.0, high_unchanged=30.0,
    )
    second = make_overview(
        low_increase=20.0, low_decrease=30.0, low_unchanged=50.0,
        medium_increase=30.0, medium_decrease=20.0, medium_unchanged=50.0,
        high_increase=40.0, high_decrease=30.0, high_unchanged=30.0,
    )

    transition = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    ).transitions[0]

    assert transition.low_increase_percentage_change == 10.0
    assert transition.low_decrease_percentage_change == 10.0
    assert transition.low_unchanged_percentage_change == -20.0
    assert transition.medium_increase_percentage_change == 10.0
    assert transition.medium_decrease_percentage_change == -10.0
    assert transition.medium_unchanged_percentage_change == 0.0
    assert transition.high_increase_percentage_change == 10.0
    assert transition.high_decrease_percentage_change == -10.0
    assert transition.high_unchanged_percentage_change == 0.0


def test_zero_transition_overview_is_valid():
    result = validate_overview(make_zero_transition_overview())
    assert result.overview_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_movement_is_nonnegative():
    first = make_overview()
    second = make_overview(
        low_increase=25.0,
        low_decrease=25.0,
        low_unchanged=50.0,
    )
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second)
    )
    assert result.transitions[0].total_absolute_percentage_movement >= 0.0


def test_transition_count_matches_overview_count_minus_one():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        tuple(make_overview() for _ in range(7))
    )
    assert result.transition_count == result.overview_count - 1


def test_input_order_is_preserved():
    first = make_overview(low_increase=10.0, low_decrease=20.0, low_unchanged=70.0)
    second = make_overview(low_increase=30.0, low_decrease=20.0, low_unchanged=50.0)
    third = make_overview(low_increase=50.0, low_decrease=10.0, low_unchanged=40.0)

    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (first, second, third)
    )

    assert result.transitions[0].low_increase_percentage_start == 10.0
    assert result.transitions[0].low_increase_percentage_end == 30.0
    assert result.transitions[1].low_increase_percentage_start == 30.0
    assert result.transitions[1].low_increase_percentage_end == 50.0


def test_no_prediction_or_ranking_fields_are_present():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
        (make_overview(), make_overview())
    )
    transition = result.transitions[0]

    assert not hasattr(transition, "prediction")
    assert not hasattr(transition, "ranking")
    assert not hasattr(transition, "probability")
