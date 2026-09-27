import pytest

from analytics.position_distribution_stability_trend_transition_comparison import (
    PositionDistributionStabilityTrendTransitionComparison,
    build_position_distribution_stability_trend_transition_comparison,
    compare_position_distribution_stability_trend_transitions,
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


class TestPositionDistributionStabilityTrendTransitionComparison:
    def test_empty_input(self):
        result = build_position_distribution_stability_trend_transition_comparison(
            ()
        )

        assert isinstance(
            result,
            PositionDistributionStabilityTrendTransitionComparison,
        )
        assert result.overview_count == 0
        assert result.low_movement_percentage_start == 0.0
        assert result.low_movement_percentage_end == 0.0
        assert result.low_movement_percentage_change == 0.0
        assert result.medium_movement_percentage_start == 0.0
        assert result.medium_movement_percentage_end == 0.0
        assert result.medium_movement_percentage_change == 0.0
        assert result.high_movement_percentage_start == 0.0
        assert result.high_movement_percentage_end == 0.0
        assert result.high_movement_percentage_change == 0.0
        assert result.total_absolute_percentage_movement == 0.0
        assert result.mean_absolute_percentage_movement == 0.0

    def test_single_overview_has_zero_change(self):
        overview = make_overview()

        result = build_position_distribution_stability_trend_transition_comparison(
            (overview,)
        )

        assert result.overview_count == 1
        assert result.low_movement_percentage_start == 50.0
        assert result.low_movement_percentage_end == 50.0
        assert result.low_movement_percentage_change == 0.0
        assert result.medium_movement_percentage_change == 0.0
        assert result.high_movement_percentage_change == 0.0
        assert result.average_total_absolute_percentage_change_change == 0.0
        assert result.minimum_total_absolute_percentage_change_change == 0.0
        assert result.maximum_total_absolute_percentage_change_change == 0.0
        assert result.total_absolute_percentage_change_change == 0.0
        assert result.total_absolute_percentage_movement == 0.0
        assert result.mean_absolute_percentage_movement == 0.0

    def test_two_overviews_calculate_changes(self):
        first = make_overview(
            low=50.0,
            medium=30.0,
            high=20.0,
            average=3.0,
            minimum=1.0,
            maximum=5.0,
            total=30.0,
        )
        second = make_overview(
            low=40.0,
            medium=35.0,
            high=25.0,
            average=4.0,
            minimum=2.0,
            maximum=6.0,
            total=40.0,
        )

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second)
        )

        assert result.overview_count == 2

        assert result.low_movement_percentage_start == 50.0
        assert result.low_movement_percentage_end == 40.0
        assert result.low_movement_percentage_change == -10.0

        assert result.medium_movement_percentage_start == 30.0
        assert result.medium_movement_percentage_end == 35.0
        assert result.medium_movement_percentage_change == 5.0

        assert result.high_movement_percentage_start == 20.0
        assert result.high_movement_percentage_end == 25.0
        assert result.high_movement_percentage_change == 5.0

        assert (
            result.average_total_absolute_percentage_change_start == 3.0
        )
        assert result.average_total_absolute_percentage_change_end == 4.0
        assert (
            result.average_total_absolute_percentage_change_change == 1.0
        )

        assert (
            result.minimum_total_absolute_percentage_change_change == 1.0
        )
        assert (
            result.maximum_total_absolute_percentage_change_change == 1.0
        )
        assert result.total_absolute_percentage_change_change == 10.0

    def test_total_absolute_movement_for_two_overviews(self):
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

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second)
        )

        assert result.total_absolute_percentage_movement == 20.0
        assert result.mean_absolute_percentage_movement == 20.0

    def test_total_and_mean_movement_for_three_overviews(self):
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

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second, third)
        )

        first_movement = (
            abs(40.0 - 50.0)
            + abs(35.0 - 30.0)
            + abs(25.0 - 20.0)
        )

        second_movement = (
            abs(45.0 - 40.0)
            + abs(25.0 - 35.0)
            + abs(30.0 - 25.0)
        )

        assert first_movement == 20.0
        assert second_movement == 20.0
        assert result.total_absolute_percentage_movement == 40.0
        assert result.mean_absolute_percentage_movement == 20.0

    def test_order_is_preserved_for_start_and_end(self):
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

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second)
        )

        assert result.low_movement_percentage_start == 60.0
        assert result.low_movement_percentage_end == 30.0
        assert result.medium_movement_percentage_start == 25.0
        assert result.medium_movement_percentage_end == 40.0
        assert result.high_movement_percentage_start == 15.0
        assert result.high_movement_percentage_end == 30.0

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

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second)
        )

        assert result.low_movement_percentage_change == -20.0
        assert result.medium_movement_percentage_change == 10.0
        assert result.high_movement_percentage_change == 10.0

    def test_zero_movement_between_identical_overviews(self):
        overview = make_overview()

        result = build_position_distribution_stability_trend_transition_comparison(
            (overview, overview)
        )

        assert result.total_absolute_percentage_movement == 0.0
        assert result.mean_absolute_percentage_movement == 0.0

    def test_wrapper_matches_builder(self):
        first = make_overview()
        second = make_overview(
            low=45.0,
            medium=35.0,
            high=20.0,
        )

        direct = build_position_distribution_stability_trend_transition_comparison(
            (first, second)
        )
        wrapped = compare_position_distribution_stability_trend_transitions(
            (first, second)
        )

        assert wrapped == direct

    def test_invalid_input_type(self):
        with pytest.raises(TypeError):
            build_position_distribution_stability_trend_transition_comparison(
                "invalid"
            )

    def test_invalid_overview_type(self):
        with pytest.raises(TypeError):
            build_position_distribution_stability_trend_transition_comparison(
                (object(),)
            )

    def test_negative_transition_count(self):
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
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_invalid_percentage_above_100(self):
        overview = make_overview(
            low=101.0,
            medium=-1.0,
            high=0.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_invalid_percentage_below_zero(self):
        overview = make_overview(
            low=-1.0,
            medium=51.0,
            high=50.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_percentages_must_sum_to_100(self):
        overview = make_overview(
            low=50.0,
            medium=20.0,
            high=20.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_negative_average_metric(self):
        overview = make_overview(
            average=-1.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_negative_minimum_metric(self):
        overview = make_overview(
            minimum=-1.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_negative_maximum_metric(self):
        overview = make_overview(
            maximum=-1.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_negative_total_metric(self):
        overview = make_overview(
            total=-1.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_minimum_cannot_exceed_maximum(self):
        overview = make_overview(
            minimum=10.0,
            maximum=5.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_integer_percentages_are_accepted(self):
        overview = make_overview(
            low=50,
            medium=30,
            high=20,
        )

        result = build_position_distribution_stability_trend_transition_comparison(
            (overview,)
        )

        assert result.low_movement_percentage_start == 50
        assert result.medium_movement_percentage_start == 30
        assert result.high_movement_percentage_start == 20

    def test_bool_percentage_is_rejected(self):
        overview = make_overview(
            low=True,
            medium=30.0,
            high=69.0,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_bool_metric_is_rejected(self):
        overview = make_overview(
            average=True,
        )

        with pytest.raises(ValueError):
            build_position_distribution_stability_trend_transition_comparison(
                (overview,)
            )

    def test_large_multi_window_movement(self):
        first = make_overview(
            low=80.0,
            medium=15.0,
            high=5.0,
        )
        second = make_overview(
            low=20.0,
            medium=30.0,
            high=50.0,
        )
        third = make_overview(
            low=50.0,
            medium=20.0,
            high=30.0,
        )

        result = build_position_distribution_stability_trend_transition_comparison(
            (first, second, third)
        )

        movement_one = (
            abs(20.0 - 80.0)
            + abs(30.0 - 15.0)
            + abs(50.0 - 5.0)
        )

        movement_two = (
            abs(50.0 - 20.0)
            + abs(20.0 - 30.0)
            + abs(30.0 - 50.0)
        )

        assert result.total_absolute_percentage_movement == (
            movement_one + movement_two
        )

        assert result.mean_absolute_percentage_movement == (
            movement_one + movement_two
        ) / 2