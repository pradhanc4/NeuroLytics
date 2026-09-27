import pytest

from analytics.position_distribution_stability_trend_transition_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonTransition,
    build_position_distribution_stability_trend_transition_comparison_detail,
    get_position_distribution_stability_trend_transition_comparison_detail,
)
from analytics.position_distribution_stability_trend_transition_overview import (
    PositionDistributionStabilityTrendTransitionOverview,
)


def make_overview(
    transition_count=10,
    low=50.0,
    medium=30.0,
    high=20.0,
    average=3.0,
    minimum=1.0,
    maximum=5.0,
    total=30.0,
):
    return PositionDistributionStabilityTrendTransitionOverview(
        transition_count=transition_count,
        low_movement_percentage=low,
        medium_movement_percentage=medium,
        high_movement_percentage=high,
        average_total_absolute_percentage_change=average,
        minimum_total_absolute_percentage_change=minimum,
        maximum_total_absolute_percentage_change=maximum,
        total_absolute_percentage_change=total,
        dominant_movement_levels=("LOW",),
    )


class TestPositionDistributionStabilityTrendTransitionComparisonDetail:
    def test_empty_input(self):
        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                ()
            )
        )

        assert isinstance(
            result,
            PositionDistributionStabilityTrendTransitionComparisonDetail,
        )
        assert result.overview_count == 0
        assert result.transition_count == 0
        assert result.transitions == ()

    def test_single_overview_has_no_transitions(self):
        overview = make_overview()

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )
        )

        assert result.overview_count == 1
        assert result.transition_count == 0
        assert result.transitions == ()

    def test_two_overviews_create_one_transition(self):
        first = make_overview()
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
            average=4.0,
            minimum=2.0,
            maximum=6.0,
            total=40.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        assert result.overview_count == 2
        assert result.transition_count == 1
        assert len(result.transitions) == 1

        transition = result.transitions[0]

        assert isinstance(
            transition,
            PositionDistributionStabilityTrendTransitionComparisonTransition,
        )

        assert transition.transition_index == 1

    def test_transition_preserves_start_and_end_percentages(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        transition = result.transitions[0]

        assert transition.low_movement_percentage_start == 50.0
        assert transition.low_movement_percentage_end == 40.0

        assert transition.medium_movement_percentage_start == 30.0
        assert transition.medium_movement_percentage_end == 35.0

        assert transition.high_movement_percentage_start == 20.0
        assert transition.high_movement_percentage_end == 25.0

    def test_transition_calculates_percentage_changes(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        transition = result.transitions[0]

        assert transition.low_movement_percentage_change == -10.0
        assert transition.medium_movement_percentage_change == 5.0
        assert transition.high_movement_percentage_change == 5.0

    def test_transition_calculates_metric_changes(self):
        first = make_overview(
            average=3.0,
            minimum=1.0,
            maximum=5.0,
            total=30.0,
        )
        second = make_overview(
            average=4.0,
            minimum=2.0,
            maximum=6.0,
            total=40.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        transition = result.transitions[0]

        assert (
            transition.average_total_absolute_percentage_change_start == 3.0
        )
        assert (
            transition.average_total_absolute_percentage_change_end == 4.0
        )
        assert (
            transition.average_total_absolute_percentage_change_change == 1.0
        )

        assert (
            transition.minimum_total_absolute_percentage_change_start == 1.0
        )
        assert (
            transition.minimum_total_absolute_percentage_change_end == 2.0
        )
        assert (
            transition.minimum_total_absolute_percentage_change_change == 1.0
        )

        assert (
            transition.maximum_total_absolute_percentage_change_start == 5.0
        )
        assert (
            transition.maximum_total_absolute_percentage_change_end == 6.0
        )
        assert (
            transition.maximum_total_absolute_percentage_change_change == 1.0
        )

        assert transition.total_absolute_percentage_change_start == 30.0
        assert transition.total_absolute_percentage_change_end == 40.0
        assert transition.total_absolute_percentage_change_change == 10.0

    def test_total_absolute_percentage_movement(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        transition = result.transitions[0]

        assert transition.total_absolute_percentage_movement == 20.0

    def test_three_overviews_create_two_transitions(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )
        third = make_overview(
            low=45.0,
            medium=25.0,
            high=30.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        assert result.overview_count == 3
        assert result.transition_count == 2
        assert len(result.transitions) == 2

    def test_transition_indexes_are_sequential(self):
        first = make_overview()
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )
        third = make_overview(
            low=45.0,
            medium=25.0,
            high=30.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        assert result.transitions[0].transition_index == 1
        assert result.transitions[1].transition_index == 2

    def test_second_transition_uses_second_and_third_overviews(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )
        third = make_overview(
            low=45.0,
            medium=25.0,
            high=30.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        transition = result.transitions[1]

        assert transition.low_movement_percentage_start == 40.0
        assert transition.low_movement_percentage_end == 45.0
        assert transition.low_movement_percentage_change == 5.0

        assert transition.medium_movement_percentage_start == 35.0
        assert transition.medium_movement_percentage_end == 25.0
        assert transition.medium_movement_percentage_change == -10.0

        assert transition.high_movement_percentage_start == 25.0
        assert transition.high_movement_percentage_end == 30.0
        assert transition.high_movement_percentage_change == 5.0

    def test_each_transition_has_independent_movement(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )
        third = make_overview(
            low=45.0,
            medium=25.0,
            high=30.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        assert result.transitions[0].total_absolute_percentage_movement == 20.0
        assert result.transitions[1].total_absolute_percentage_movement == 20.0

    def test_identical_overviews_have_zero_movement(self):
        overview = make_overview()

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview, overview)
            )
        )

        transition = result.transitions[0]

        assert transition.low_movement_percentage_change == 0.0
        assert transition.medium_movement_percentage_change == 0.0
        assert transition.high_movement_percentage_change == 0.0
        assert transition.total_absolute_percentage_movement == 0.0

    def test_negative_change_is_preserved(self):
        first = make_overview(
            low=70.0,
            medium=20.0,
            high=10.0,
        )
        second = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second)
            )
        )

        transition = result.transitions[0]

        assert transition.low_movement_percentage_change == -20.0
        assert transition.medium_movement_percentage_change == 10.0
        assert transition.high_movement_percentage_change == 10.0
        assert transition.total_absolute_percentage_movement == 40.0

    def test_invalid_input_type(self):
        with pytest.raises(TypeError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                "invalid"
            )

    def test_invalid_overview_type(self):
        with pytest.raises(TypeError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (object(),)
            )

    def test_negative_transition_count_is_rejected(self):
        overview = PositionDistributionStabilityTrendTransitionOverview(
            transition_count=-1,
            low_movement_percentage=50.0,
            medium_movement_percentage=30.0,
            high_movement_percentage=20.0,
            average_total_absolute_percentage_change=3.0,
            minimum_total_absolute_percentage_change=1.0,
            maximum_total_absolute_percentage_change=5.0,
            total_absolute_percentage_change=30.0,
            dominant_movement_levels=("LOW",),
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_percentage_above_100_is_rejected(self):
        overview = make_overview(
            low=101.0,
            medium=0.0,
            high=0.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_percentage_below_zero_is_rejected(self):
        overview = make_overview(
            low=-1.0,
            medium=51.0,
            high=50.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_percentages_must_sum_to_100(self):
        overview = make_overview(
            low=50.0,
            medium=20.0,
            high=20.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_negative_average_metric_is_rejected(self):
        overview = make_overview(average=-1.0)

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_negative_minimum_metric_is_rejected(self):
        overview = make_overview(minimum=-1.0)

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_negative_maximum_metric_is_rejected(self):
        overview = make_overview(maximum=-1.0)

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_negative_total_metric_is_rejected(self):
        overview = make_overview(total=-1.0)

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_minimum_cannot_exceed_maximum(self):
        overview = make_overview(
            minimum=10.0,
            maximum=5.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_zero_transition_count_requires_zero_percentages(self):
        overview = PositionDistributionStabilityTrendTransitionOverview(
            transition_count=0,
            low_movement_percentage=50.0,
            medium_movement_percentage=30.0,
            high_movement_percentage=20.0,
            average_total_absolute_percentage_change=0.0,
            minimum_total_absolute_percentage_change=0.0,
            maximum_total_absolute_percentage_change=0.0,
            total_absolute_percentage_change=0.0,
            dominant_movement_levels=(),
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_zero_transition_count_with_zero_percentages_is_valid(self):
        overview = PositionDistributionStabilityTrendTransitionOverview(
            transition_count=0,
            low_movement_percentage=0.0,
            medium_movement_percentage=0.0,
            high_movement_percentage=0.0,
            average_total_absolute_percentage_change=0.0,
            minimum_total_absolute_percentage_change=0.0,
            maximum_total_absolute_percentage_change=0.0,
            total_absolute_percentage_change=0.0,
            dominant_movement_levels=(),
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )
        )

        assert result.overview_count == 1
        assert result.transition_count == 0
        assert result.transitions == ()

    def test_bool_percentage_is_rejected(self):
        overview = make_overview(
            low=True,
            medium=30.0,
            high=69.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_bool_transition_count_is_rejected(self):
        overview = PositionDistributionStabilityTrendTransitionOverview(
            transition_count=True,
            low_movement_percentage=50.0,
            medium_movement_percentage=30.0,
            high_movement_percentage=20.0,
            average_total_absolute_percentage_change=3.0,
            minimum_total_absolute_percentage_change=1.0,
            maximum_total_absolute_percentage_change=5.0,
            total_absolute_percentage_change=30.0,
            dominant_movement_levels=("LOW",),
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison_detail(
                (overview,)
            )

    def test_wrapper_matches_builder(self):
        first = make_overview()
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
        )
        third = make_overview(
            low=45.0,
            medium=25.0,
            high=30.0,
        )

        direct = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        wrapped = (
            get_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        assert wrapped == direct

    def test_input_order_is_preserved(self):
        first = make_overview(
            low=60.0,
            medium=25.0,
            high=15.0,
        )
        second = make_overview(
            low=30.0,
            medium=40.0,
            high=30.0,
        )
        third = make_overview(
            low=20.0,
            medium=30.0,
            high=50.0,
        )

        result = (
            build_position_distribution_stability_trend_transition_comparison_detail(
                (first, second, third)
            )
        )

        assert result.transitions[0].low_movement_percentage_start == 60.0
        assert result.transitions[0].low_movement_percentage_end == 30.0

        assert result.transitions[1].low_movement_percentage_start == 30.0
        assert result.transitions[1].low_movement_percentage_end == 20.0