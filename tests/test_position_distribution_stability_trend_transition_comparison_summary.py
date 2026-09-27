import pytest

from analytics.position_distribution_stability_trend_transition_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonTransition,
)
from analytics.position_distribution_stability_trend_transition_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonSummary,
    get_position_distribution_stability_trend_transition_comparison_summary,
    summarize_position_distribution_stability_trend_transition_comparisons,
)


def make_transition(
    index=1,
    low_start=50.0,
    low_end=40.0,
    medium_start=30.0,
    medium_end=35.0,
    high_start=20.0,
    high_end=25.0,
    average_start=3.0,
    average_end=4.0,
    minimum_start=1.0,
    minimum_end=2.0,
    maximum_start=5.0,
    maximum_end=6.0,
    total_start=30.0,
    total_end=40.0,
):
    low_change = low_end - low_start
    medium_change = medium_end - medium_start
    high_change = high_end - high_start

    return PositionDistributionStabilityTrendTransitionComparisonTransition(
        transition_index=index,
        low_movement_percentage_start=low_start,
        low_movement_percentage_end=low_end,
        low_movement_percentage_change=low_change,
        medium_movement_percentage_start=medium_start,
        medium_movement_percentage_end=medium_end,
        medium_movement_percentage_change=medium_change,
        high_movement_percentage_start=high_start,
        high_movement_percentage_end=high_end,
        high_movement_percentage_change=high_change,
        average_total_absolute_percentage_change_start=average_start,
        average_total_absolute_percentage_change_end=average_end,
        average_total_absolute_percentage_change_change=(
            average_end - average_start
        ),
        minimum_total_absolute_percentage_change_start=minimum_start,
        minimum_total_absolute_percentage_change_end=minimum_end,
        minimum_total_absolute_percentage_change_change=(
            minimum_end - minimum_start
        ),
        maximum_total_absolute_percentage_change_start=maximum_start,
        maximum_total_absolute_percentage_change_end=maximum_end,
        maximum_total_absolute_percentage_change_change=(
            maximum_end - maximum_start
        ),
        total_absolute_percentage_change_start=total_start,
        total_absolute_percentage_change_end=total_end,
        total_absolute_percentage_change_change=(
            total_end - total_start
        ),
        total_absolute_percentage_movement=(
            abs(low_change)
            + abs(medium_change)
            + abs(high_change)
        ),
    )


def make_detail(transitions=()):
    transition_tuple = tuple(transitions)

    return PositionDistributionStabilityTrendTransitionComparisonDetail(
        overview_count=len(transition_tuple) + 1
        if transition_tuple
        else 0,
        transition_count=len(transition_tuple),
        transitions=transition_tuple,
    )


class TestPositionDistributionStabilityTrendTransitionComparisonSummary:
    def test_empty_detail(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=0,
            transition_count=0,
            transitions=(),
        )

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert isinstance(
            result,
            PositionDistributionStabilityTrendTransitionComparisonSummary,
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

        assert (
            result.average_total_absolute_percentage_movement
            == 0.0
        )
        assert (
            result.minimum_total_absolute_percentage_movement
            == 0.0
        )
        assert (
            result.maximum_total_absolute_percentage_movement
            == 0.0
        )
        assert result.total_absolute_percentage_movement == 0.0
        assert result.transitions == ()

    def test_single_transition_direction_counts(self):
        transition = make_transition()

        detail = make_detail((transition,))

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert result.transition_count == 1

        assert result.low_increase_count == 0
        assert result.low_decrease_count == 1
        assert result.low_unchanged_count == 0

        assert result.medium_increase_count == 1
        assert result.medium_decrease_count == 0
        assert result.medium_unchanged_count == 0

        assert result.high_increase_count == 1
        assert result.high_decrease_count == 0
        assert result.high_unchanged_count == 0

    def test_unchanged_direction_counts(self):
        transition = make_transition(
            low_start=50.0,
            low_end=50.0,
            medium_start=30.0,
            medium_end=30.0,
            high_start=20.0,
            high_end=20.0,
        )

        detail = make_detail((transition,))

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert result.low_unchanged_count == 1
        assert result.medium_unchanged_count == 1
        assert result.high_unchanged_count == 1

        assert result.low_increase_count == 0
        assert result.low_decrease_count == 0
        assert result.medium_increase_count == 0
        assert result.medium_decrease_count == 0
        assert result.high_increase_count == 0
        assert result.high_decrease_count == 0

    def test_multiple_transition_direction_counts(self):
        transition_one = make_transition(
            index=1,
            low_start=50.0,
            low_end=40.0,
            medium_start=30.0,
            medium_end=35.0,
            high_start=20.0,
            high_end=25.0,
        )

        transition_two = make_transition(
            index=2,
            low_start=40.0,
            low_end=45.0,
            medium_start=35.0,
            medium_end=25.0,
            high_start=25.0,
            high_end=30.0,
        )

        transition_three = make_transition(
            index=3,
            low_start=45.0,
            low_end=45.0,
            medium_start=25.0,
            medium_end=30.0,
            high_start=30.0,
            high_end=25.0,
        )

        detail = make_detail(
            (
                transition_one,
                transition_two,
                transition_three,
            )
        )

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert result.transition_count == 3

        # LOW:
        # 50 -> 40 = decrease
        # 40 -> 45 = increase
        # 45 -> 45 = unchanged
        assert result.low_increase_count == 1
        assert result.low_decrease_count == 1
        assert result.low_unchanged_count == 1

        # MEDIUM:
        # 30 -> 35 = increase
        # 35 -> 25 = decrease
        # 25 -> 30 = increase
        assert result.medium_increase_count == 2
        assert result.medium_decrease_count == 1
        assert result.medium_unchanged_count == 0

        # HIGH:
        # 20 -> 25 = increase
        # 25 -> 30 = increase
        # 30 -> 25 = decrease
        assert result.high_increase_count == 2
        assert result.high_decrease_count == 1
        assert result.high_unchanged_count == 0

    def test_movement_metrics(self):
        transition_one = make_transition(
            index=1,
            low_start=50.0,
            low_end=40.0,
            medium_start=30.0,
            medium_end=35.0,
            high_start=20.0,
            high_end=25.0,
        )

        transition_two = make_transition(
            index=2,
            low_start=40.0,
            low_end=45.0,
            medium_start=35.0,
            medium_end=25.0,
            high_start=25.0,
            high_end=30.0,
        )

        detail = make_detail(
            (
                transition_one,
                transition_two,
            )
        )

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert transition_one.total_absolute_percentage_movement == 20.0
        assert transition_two.total_absolute_percentage_movement == 20.0

        assert (
            result.average_total_absolute_percentage_movement
            == 20.0
        )
        assert (
            result.minimum_total_absolute_percentage_movement
            == 20.0
        )
        assert (
            result.maximum_total_absolute_percentage_movement
            == 20.0
        )
        assert (
            result.total_absolute_percentage_movement
            == 40.0
        )

    def test_different_movement_metrics(self):
        transition_one = make_transition(
            index=1,
            low_start=50.0,
            low_end=49.0,
            medium_start=30.0,
            medium_end=31.0,
            high_start=20.0,
            high_end=20.0,
        )

        transition_two = make_transition(
            index=2,
            low_start=49.0,
            low_end=39.0,
            medium_start=31.0,
            medium_end=36.0,
            high_start=20.0,
            high_end=25.0,
        )

        detail = make_detail(
            (
                transition_one,
                transition_two,
            )
        )

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert transition_one.total_absolute_percentage_movement == 2.0
        assert transition_two.total_absolute_percentage_movement == 20.0

        assert (
            result.average_total_absolute_percentage_movement
            == 11.0
        )
        assert (
            result.minimum_total_absolute_percentage_movement
            == 2.0
        )
        assert (
            result.maximum_total_absolute_percentage_movement
            == 20.0
        )
        assert (
            result.total_absolute_percentage_movement
            == 22.0
        )

    def test_transitions_are_preserved(self):
        transition = make_transition()

        detail = make_detail((transition,))

        result = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        assert result.transitions == (transition,)

    def test_wrapper_matches_builder(self):
        transition = make_transition()
        detail = make_detail((transition,))

        direct = (
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )
        )

        wrapped = (
            get_position_distribution_stability_trend_transition_comparison_summary(
                detail
            )
        )

        assert wrapped == direct

    def test_invalid_detail_type(self):
        with pytest.raises(TypeError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                object()
            )

    def test_negative_overview_count_is_rejected(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=-1,
            transition_count=0,
            transitions=(),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_negative_transition_count_is_rejected(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=0,
            transition_count=-1,
            transitions=(),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_transition_count_must_match_overview_count(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=5,
            transition_count=2,
            transitions=(
                make_transition(index=1),
                make_transition(index=2),
            ),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_transition_tuple_length_must_match_count(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=2,
            transition_count=2,
            transitions=(make_transition(index=1),),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_transition_indexes_must_start_at_one(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=2,
            transition_count=1,
            transitions=(make_transition(index=2),),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_transition_indexes_must_be_sequential(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=3,
            transition_count=2,
            transitions=(
                make_transition(index=1),
                make_transition(index=3),
            ),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_invalid_transition_type(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=2,
            transition_count=1,
            transitions=(object(),),
        )

        with pytest.raises(TypeError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_invalid_transition_index_type(self):
        transition = make_transition()
        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "transition_index": "1",
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_zero_index_is_rejected(self):
        transition = make_transition(index=0)

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_negative_index_is_rejected(self):
        transition = make_transition(index=-1)

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_invalid_percentage_above_100(self):
        transition = make_transition(
            low_start=101.0,
            low_end=100.0,
            medium_start=0.0,
            medium_end=0.0,
            high_start=0.0,
            high_end=0.0,
        )

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_invalid_percentage_below_zero(self):
        transition = make_transition(
            low_start=-1.0,
            low_end=0.0,
            medium_start=51.0,
            medium_end=50.0,
            high_start=50.0,
            high_end=50.0,
        )

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_inconsistent_low_change_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "low_movement_percentage_change": 999.0,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_inconsistent_medium_change_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "medium_movement_percentage_change": 999.0,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_inconsistent_high_change_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "high_movement_percentage_change": 999.0,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_inconsistent_total_movement_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "total_absolute_percentage_movement": 999.0,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_negative_movement_metric_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "total_absolute_percentage_movement": -1.0,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_starting_minimum_cannot_exceed_maximum(self):
        transition = make_transition(
            minimum_start=10.0,
            maximum_start=5.0,
        )

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_ending_minimum_cannot_exceed_maximum(self):
        transition = make_transition(
            minimum_end=10.0,
            maximum_end=5.0,
        )

        detail = make_detail((transition,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_bool_overview_count_is_rejected(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=True,
            transition_count=0,
            transitions=(),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_bool_transition_count_is_rejected(self):
        detail = PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=1,
            transition_count=True,
            transitions=(),
        )

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_bool_transition_index_is_rejected(self):
        transition = make_transition(index=1)

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "transition_index": True,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_bool_percentage_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "low_movement_percentage_start": True,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )

    def test_bool_movement_metric_is_rejected(self):
        transition = make_transition()

        invalid = PositionDistributionStabilityTrendTransitionComparisonTransition(
            **{
                **transition.__dict__,
                "total_absolute_percentage_movement": True,
            }
        )

        detail = make_detail((invalid,))

        with pytest.raises(ValueError):
            summarize_position_distribution_stability_trend_transition_comparisons(
                detail
            )