import pytest

from analytics.position_distribution_stability_trend_detail import (
    PositionDistributionStabilityTrendDetail,
    PositionDistributionStabilityTrendTransition,
    build_position_distribution_stability_trend_detail,
    get_position_distribution_stability_trend_detail,
)
from analytics.position_distribution_stability_trend_overview import (
    PositionDistributionStabilityTrendOverview,
)


def make_overview(
    summary_count=4,
    stable_increasing_percentage=25.0,
    stability_decreasing_percentage=25.0,
    stable_percentage=25.0,
    mixed_percentage=25.0,
    low_strength_percentage=25.0,
    medium_strength_percentage=25.0,
    high_strength_percentage=50.0,
    average_mean_absolute_percentage_change=2.0,
    minimum_mean_absolute_percentage_change=1.0,
    maximum_mean_absolute_percentage_change=4.0,
    total_absolute_percentage_change=8.0,
    dominant_trend_directions=("STABLE_INCREASING",),
    dominant_trend_strengths=("HIGH",),
):
    return PositionDistributionStabilityTrendOverview(
        summary_count=summary_count,
        stable_increasing_percentage=stable_increasing_percentage,
        stability_decreasing_percentage=stability_decreasing_percentage,
        stable_percentage=stable_percentage,
        mixed_percentage=mixed_percentage,
        low_strength_percentage=low_strength_percentage,
        medium_strength_percentage=medium_strength_percentage,
        high_strength_percentage=high_strength_percentage,
        average_mean_absolute_percentage_change=(
            average_mean_absolute_percentage_change
        ),
        minimum_mean_absolute_percentage_change=(
            minimum_mean_absolute_percentage_change
        ),
        maximum_mean_absolute_percentage_change=(
            maximum_mean_absolute_percentage_change
        ),
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        dominant_trend_directions=dominant_trend_directions,
        dominant_trend_strengths=dominant_trend_strengths,
    )


def test_transition_is_frozen_dataclass():
    transition = PositionDistributionStabilityTrendTransition(
        transition_index=1,
        stable_increasing_percentage_start=20.0,
        stable_increasing_percentage_end=30.0,
        stable_increasing_percentage_change=10.0,
        stability_decreasing_percentage_start=30.0,
        stability_decreasing_percentage_end=20.0,
        stability_decreasing_percentage_change=-10.0,
        stable_percentage_start=30.0,
        stable_percentage_end=25.0,
        stable_percentage_change=-5.0,
        mixed_percentage_start=20.0,
        mixed_percentage_end=25.0,
        mixed_percentage_change=5.0,
        low_strength_percentage_start=40.0,
        low_strength_percentage_end=30.0,
        low_strength_percentage_change=-10.0,
        medium_strength_percentage_start=30.0,
        medium_strength_percentage_end=30.0,
        medium_strength_percentage_change=0.0,
        high_strength_percentage_start=30.0,
        high_strength_percentage_end=40.0,
        high_strength_percentage_change=10.0,
        total_absolute_percentage_change=50.0,
    )

    assert transition.transition_index == 1

    with pytest.raises(Exception):
        transition.transition_index = 2


def test_detail_is_frozen_dataclass():
    detail = build_position_distribution_stability_trend_detail(
        (make_overview(),)
    )

    assert isinstance(
        detail,
        PositionDistributionStabilityTrendDetail,
    )

    with pytest.raises(Exception):
        detail.summary_count = 10


def test_empty_input_returns_empty_detail():
    result = build_position_distribution_stability_trend_detail(())

    assert result.summary_count == 0
    assert result.transition_count == 0
    assert result.transitions == ()


def test_single_overview_returns_no_transitions():
    overview = make_overview(summary_count=7)

    result = build_position_distribution_stability_trend_detail(
        (overview,)
    )

    assert result.summary_count == 7
    assert result.transition_count == 0
    assert result.transitions == ()


def test_two_overviews_create_one_transition():
    first = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=40.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=30.0,
    )

    second = make_overview(
        stable_increasing_percentage=30.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=25.0,
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=40.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    assert result.summary_count == 4
    assert result.transition_count == 1
    assert len(result.transitions) == 1

    transition = result.transitions[0]

    assert transition.transition_index == 1
    assert transition.stable_increasing_percentage_start == 20.0
    assert transition.stable_increasing_percentage_end == 30.0
    assert transition.stable_increasing_percentage_change == 10.0

    assert transition.stability_decreasing_percentage_start == 30.0
    assert transition.stability_decreasing_percentage_end == 20.0
    assert transition.stability_decreasing_percentage_change == -10.0

    assert transition.stable_percentage_start == 30.0
    assert transition.stable_percentage_end == 25.0
    assert transition.stable_percentage_change == -5.0

    assert transition.mixed_percentage_start == 20.0
    assert transition.mixed_percentage_end == 25.0
    assert transition.mixed_percentage_change == 5.0


def test_all_strength_changes_are_calculated():
    first = make_overview(
        low_strength_percentage=50.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=20.0,
    )

    second = make_overview(
        low_strength_percentage=30.0,
        medium_strength_percentage=40.0,
        high_strength_percentage=30.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    transition = result.transitions[0]

    assert transition.low_strength_percentage_start == 50.0
    assert transition.low_strength_percentage_end == 30.0
    assert transition.low_strength_percentage_change == -20.0

    assert transition.medium_strength_percentage_start == 30.0
    assert transition.medium_strength_percentage_end == 40.0
    assert transition.medium_strength_percentage_change == 10.0

    assert transition.high_strength_percentage_start == 20.0
    assert transition.high_strength_percentage_end == 30.0
    assert transition.high_strength_percentage_change == 10.0


def test_zero_changes_are_preserved():
    first = make_overview()
    second = make_overview()

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    transition = result.transitions[0]

    assert transition.stable_increasing_percentage_change == 0.0
    assert transition.stability_decreasing_percentage_change == 0.0
    assert transition.stable_percentage_change == 0.0
    assert transition.mixed_percentage_change == 0.0
    assert transition.low_strength_percentage_change == 0.0
    assert transition.medium_strength_percentage_change == 0.0
    assert transition.high_strength_percentage_change == 0.0
    assert transition.total_absolute_percentage_change == 0.0


def test_negative_changes_are_preserved():
    first = make_overview(
        stable_increasing_percentage=40.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=15.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    second = make_overview(
        stable_increasing_percentage=25.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=15.0,
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=40.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    transition = result.transitions[0]

    assert transition.stable_increasing_percentage_change == -15.0
    assert transition.stability_decreasing_percentage_change == 10.0
    assert transition.stable_percentage_change == 5.0
    assert transition.mixed_percentage_change == 0.0
    assert transition.low_strength_percentage_change == 10.0
    assert transition.medium_strength_percentage_change == 0.0
    assert transition.high_strength_percentage_change == -10.0


def test_total_absolute_change_is_sum_of_all_absolute_changes():
    first = make_overview(
        stable_increasing_percentage=10.0,
        stability_decreasing_percentage=40.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=50.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=20.0,
    )

    second = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=20.0,
        mixed_percentage=30.0,
        low_strength_percentage=40.0,
        medium_strength_percentage=20.0,
        high_strength_percentage=40.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    expected = (
        abs(20.0 - 10.0)
        + abs(30.0 - 40.0)
        + abs(20.0 - 30.0)
        + abs(30.0 - 20.0)
        + abs(40.0 - 50.0)
        + abs(20.0 - 30.0)
        + abs(40.0 - 20.0)
    )

    assert result.transitions[0].total_absolute_percentage_change == expected


def test_three_overviews_create_two_transitions():
    first = make_overview()
    second = make_overview(
        stable_increasing_percentage=35.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=20.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )
    third = make_overview(
        stable_increasing_percentage=45.0,
        stability_decreasing_percentage=15.0,
        stable_percentage=20.0,
        mixed_percentage=20.0,
        low_strength_percentage=10.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=60.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second, third)
    )

    assert result.transition_count == 2
    assert len(result.transitions) == 2

    assert result.transitions[0].transition_index == 1
    assert result.transitions[1].transition_index == 2


def test_transition_indices_are_sequential():
    overviews = (
        make_overview(),
        make_overview(
            stable_increasing_percentage=30.0,
            stability_decreasing_percentage=20.0,
            stable_percentage=25.0,
            mixed_percentage=25.0,
            low_strength_percentage=30.0,
            medium_strength_percentage=30.0,
            high_strength_percentage=40.0,
        ),
        make_overview(
            stable_increasing_percentage=40.0,
            stability_decreasing_percentage=15.0,
            stable_percentage=25.0,
            mixed_percentage=20.0,
            low_strength_percentage=20.0,
            medium_strength_percentage=30.0,
            high_strength_percentage=50.0,
        ),
        make_overview(
            stable_increasing_percentage=50.0,
            stability_decreasing_percentage=10.0,
            stable_percentage=20.0,
            mixed_percentage=20.0,
            low_strength_percentage=10.0,
            medium_strength_percentage=30.0,
            high_strength_percentage=60.0,
        ),
    )

    result = build_position_distribution_stability_trend_detail(
        overviews
    )

    assert [t.transition_index for t in result.transitions] == [1, 2, 3]


def test_each_transition_uses_consecutive_overviews():
    first = make_overview(
        stable_increasing_percentage=10.0,
        stability_decreasing_percentage=40.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=50.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=20.0,
    )

    second = make_overview(
        stable_increasing_percentage=30.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=20.0,
        mixed_percentage=20.0,
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=40.0,
    )

    third = make_overview(
        stable_increasing_percentage=40.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=15.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    result = build_position_distribution_stability_trend_detail(
        (first, second, third)
    )

    first_transition = result.transitions[0]
    second_transition = result.transitions[1]

    assert first_transition.stable_increasing_percentage_start == 10.0
    assert first_transition.stable_increasing_percentage_end == 30.0

    assert second_transition.stable_increasing_percentage_start == 30.0
    assert second_transition.stable_increasing_percentage_end == 40.0


def test_summary_count_is_preserved():
    first = make_overview(summary_count=9)
    second = make_overview(summary_count=9)

    result = build_position_distribution_stability_trend_detail(
        (first, second)
    )

    assert result.summary_count == 9


def test_summary_count_must_match():
    first = make_overview(summary_count=4)
    second = make_overview(summary_count=5)

    with pytest.raises(ValueError, match="same summary_count"):
        build_position_distribution_stability_trend_detail(
            (first, second)
        )


def test_input_must_be_tuple():
    with pytest.raises(TypeError, match="overviews must be a tuple"):
        build_position_distribution_stability_trend_detail(
            [make_overview()]
        )


def test_invalid_overview_type_is_rejected():
    with pytest.raises(TypeError, match="Each item must be"):
        build_position_distribution_stability_trend_detail(
            ("invalid",)
        )


def test_negative_summary_count_is_rejected():
    overview = make_overview(summary_count=-1)

    with pytest.raises(ValueError, match="summary_count"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "stable_increasing_percentage",
        "stability_decreasing_percentage",
        "stable_percentage",
        "mixed_percentage",
        "low_strength_percentage",
        "medium_strength_percentage",
        "high_strength_percentage",
    ],
)
def test_percentage_below_zero_is_rejected(field_name):
    values = {
        "stable_increasing_percentage": 25.0,
        "stability_decreasing_percentage": 25.0,
        "stable_percentage": 25.0,
        "mixed_percentage": 25.0,
        "low_strength_percentage": 25.0,
        "medium_strength_percentage": 25.0,
        "high_strength_percentage": 50.0,
    }

    values[field_name] = -1.0

    with pytest.raises(ValueError, match="between 0 and 100"):
        build_position_distribution_stability_trend_detail(
            (make_overview(**values),)
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "stable_increasing_percentage",
        "stability_decreasing_percentage",
        "stable_percentage",
        "mixed_percentage",
        "low_strength_percentage",
        "medium_strength_percentage",
        "high_strength_percentage",
    ],
)
def test_percentage_above_100_is_rejected(field_name):
    values = {
        "stable_increasing_percentage": 25.0,
        "stability_decreasing_percentage": 25.0,
        "stable_percentage": 25.0,
        "mixed_percentage": 25.0,
        "low_strength_percentage": 25.0,
        "medium_strength_percentage": 25.0,
        "high_strength_percentage": 50.0,
    }

    values[field_name] = 101.0

    with pytest.raises(ValueError, match="between 0 and 100"):
        build_position_distribution_stability_trend_detail(
            (make_overview(**values),)
        )


def test_direction_percentages_must_sum_to_100():
    overview = make_overview(
        stable_increasing_percentage=30.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=5.0,
    )

    with pytest.raises(ValueError, match="direction percentages"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


def test_strength_percentages_must_sum_to_100():
    overview = make_overview(
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=30.0,
    )

    with pytest.raises(ValueError, match="strength percentages"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "average_mean_absolute_percentage_change",
        "minimum_mean_absolute_percentage_change",
        "maximum_mean_absolute_percentage_change",
        "total_absolute_percentage_change",
    ],
)
def test_negative_metrics_are_rejected(field_name):
    values = {
        "average_mean_absolute_percentage_change": 2.0,
        "minimum_mean_absolute_percentage_change": 1.0,
        "maximum_mean_absolute_percentage_change": 4.0,
        "total_absolute_percentage_change": 8.0,
    }

    values[field_name] = -1.0

    with pytest.raises(ValueError, match="non-negative"):
        build_position_distribution_stability_trend_detail(
            (make_overview(**values),)
        )


def test_minimum_metric_cannot_exceed_maximum_metric():
    overview = make_overview(
        minimum_mean_absolute_percentage_change=5.0,
        maximum_mean_absolute_percentage_change=4.0,
    )

    with pytest.raises(ValueError, match="minimum_mean"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


@pytest.mark.parametrize(
    "directions",
    [
        ("INVALID",),
        ("STABLE_INCREASING", "INVALID"),
    ],
)
def test_invalid_dominant_trend_direction_is_rejected(directions):
    overview = make_overview(
        dominant_trend_directions=directions
    )

    with pytest.raises(ValueError, match="Invalid trend direction"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


@pytest.mark.parametrize(
    "strengths",
    [
        ("INVALID",),
        ("HIGH", "INVALID"),
    ],
)
def test_invalid_dominant_trend_strength_is_rejected(strengths):
    overview = make_overview(
        dominant_trend_strengths=strengths
    )

    with pytest.raises(ValueError, match="Invalid trend strength"):
        build_position_distribution_stability_trend_detail(
            (overview,)
        )


def test_get_detail_returns_same_detail():
    detail = build_position_distribution_stability_trend_detail(
        (
            make_overview(),
            make_overview(
                stable_increasing_percentage=30.0,
                stability_decreasing_percentage=20.0,
                stable_percentage=25.0,
                mixed_percentage=25.0,
                low_strength_percentage=30.0,
                medium_strength_percentage=30.0,
                high_strength_percentage=40.0,
            ),
        )
    )

    result = get_position_distribution_stability_trend_detail(detail)

    assert result == detail


def test_get_detail_rejects_invalid_type():
    with pytest.raises(
        TypeError,
        match="PositionDistributionStabilityTrendDetail",
    ):
        get_position_distribution_stability_trend_detail("invalid")