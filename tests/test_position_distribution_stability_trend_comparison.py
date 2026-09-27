import pytest

from analytics.position_distribution_stability_trend_overview import (
    PositionDistributionStabilityTrendOverview,
)
from analytics.position_distribution_stability_trend_comparison import (
    PositionDistributionStabilityTrendComparison,
    build_position_distribution_stability_trend_comparison,
    compare_position_distribution_stability_trends,
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


def test_result_is_frozen_dataclass():
    result = build_position_distribution_stability_trend_comparison(
        (make_overview(),)
    )

    assert isinstance(
        result,
        PositionDistributionStabilityTrendComparison,
    )

    with pytest.raises(Exception):
        result.summary_count = 10


def test_empty_input_returns_zero_result():
    result = build_position_distribution_stability_trend_comparison(())

    assert result.summary_count == 0

    assert result.stable_increasing_percentage_start == 0.0
    assert result.stable_increasing_percentage_end == 0.0
    assert result.stable_increasing_percentage_change == 0.0

    assert result.stability_decreasing_percentage_start == 0.0
    assert result.stability_decreasing_percentage_end == 0.0
    assert result.stability_decreasing_percentage_change == 0.0

    assert result.stable_percentage_start == 0.0
    assert result.stable_percentage_end == 0.0
    assert result.stable_percentage_change == 0.0

    assert result.mixed_percentage_start == 0.0
    assert result.mixed_percentage_end == 0.0
    assert result.mixed_percentage_change == 0.0

    assert result.low_strength_percentage_start == 0.0
    assert result.low_strength_percentage_end == 0.0
    assert result.low_strength_percentage_change == 0.0

    assert result.medium_strength_percentage_start == 0.0
    assert result.medium_strength_percentage_end == 0.0
    assert result.medium_strength_percentage_change == 0.0

    assert result.high_strength_percentage_start == 0.0
    assert result.high_strength_percentage_end == 0.0
    assert result.high_strength_percentage_change == 0.0

    assert result.total_absolute_percentage_change == 0.0
    assert result.mean_absolute_percentage_change == 0.0


def test_single_overview_uses_same_start_and_end_values():
    overview = make_overview(
        stable_increasing_percentage=40.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=30.0,
        mixed_percentage=10.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    result = build_position_distribution_stability_trend_comparison(
        (overview,)
    )

    assert result.summary_count == 4

    assert result.stable_increasing_percentage_start == 40.0
    assert result.stable_increasing_percentage_end == 40.0
    assert result.stable_increasing_percentage_change == 0.0

    assert result.stability_decreasing_percentage_start == 20.0
    assert result.stability_decreasing_percentage_end == 20.0
    assert result.stability_decreasing_percentage_change == 0.0

    assert result.stable_percentage_start == 30.0
    assert result.stable_percentage_end == 30.0
    assert result.stable_percentage_change == 0.0

    assert result.mixed_percentage_start == 10.0
    assert result.mixed_percentage_end == 10.0
    assert result.mixed_percentage_change == 0.0

    assert result.low_strength_percentage_start == 20.0
    assert result.low_strength_percentage_end == 20.0
    assert result.low_strength_percentage_change == 0.0

    assert result.medium_strength_percentage_start == 30.0
    assert result.medium_strength_percentage_end == 30.0
    assert result.medium_strength_percentage_change == 0.0

    assert result.high_strength_percentage_start == 50.0
    assert result.high_strength_percentage_end == 50.0
    assert result.high_strength_percentage_change == 0.0

    assert result.total_absolute_percentage_change == 0.0
    assert result.mean_absolute_percentage_change == 0.0


def test_multiple_overviews_use_first_and_last_for_start_end():
    first = make_overview(
        stable_increasing_percentage=10.0,
        stability_decreasing_percentage=40.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=50.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=20.0,
    )

    middle = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=40.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=30.0,
    )

    last = make_overview(
        stable_increasing_percentage=40.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=15.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    result = build_position_distribution_stability_trend_comparison(
        (first, middle, last)
    )

    assert result.stable_increasing_percentage_start == 10.0
    assert result.stable_increasing_percentage_end == 40.0
    assert result.stable_increasing_percentage_change == 30.0

    assert result.stability_decreasing_percentage_start == 40.0
    assert result.stability_decreasing_percentage_end == 20.0
    assert result.stability_decreasing_percentage_change == -20.0

    assert result.stable_percentage_start == 30.0
    assert result.stable_percentage_end == 25.0
    assert result.stable_percentage_change == -5.0

    assert result.mixed_percentage_start == 20.0
    assert result.mixed_percentage_end == 15.0
    assert result.mixed_percentage_change == -5.0

    assert result.low_strength_percentage_start == 50.0
    assert result.low_strength_percentage_end == 20.0
    assert result.low_strength_percentage_change == -30.0

    assert result.medium_strength_percentage_start == 30.0
    assert result.medium_strength_percentage_end == 30.0
    assert result.medium_strength_percentage_change == 0.0

    assert result.high_strength_percentage_start == 20.0
    assert result.high_strength_percentage_end == 50.0
    assert result.high_strength_percentage_change == 30.0


def test_positive_percentage_changes_are_calculated():
    first = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=40.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=30.0,
    )

    last = make_overview(
        stable_increasing_percentage=35.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=30.0,
        mixed_percentage=15.0,
        low_strength_percentage=25.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=45.0,
    )

    result = build_position_distribution_stability_trend_comparison(
        (first, last)
    )

    assert result.stable_increasing_percentage_change == 15.0
    assert result.high_strength_percentage_change == 15.0


def test_negative_percentage_changes_are_calculated():
    first = make_overview(
        stable_increasing_percentage=40.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=25.0,
        mixed_percentage=15.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    last = make_overview(
        stable_increasing_percentage=25.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=30.0,
        mixed_percentage=15.0,
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=40.0,
    )

    result = build_position_distribution_stability_trend_comparison(
        (first, last)
    )

    assert result.stable_increasing_percentage_change == -15.0
    assert result.stability_decreasing_percentage_change == 10.0
    assert result.high_strength_percentage_change == -10.0


def test_zero_percentage_changes_are_calculated():
    first = make_overview()
    last = make_overview()

    result = build_position_distribution_stability_trend_comparison(
        (first, last)
    )

    assert result.stable_increasing_percentage_change == 0.0
    assert result.stability_decreasing_percentage_change == 0.0
    assert result.stable_percentage_change == 0.0
    assert result.mixed_percentage_change == 0.0
    assert result.low_strength_percentage_change == 0.0
    assert result.medium_strength_percentage_change == 0.0
    assert result.high_strength_percentage_change == 0.0


def test_total_absolute_percentage_change_for_one_transition():
    first = make_overview(
        stable_increasing_percentage=10.0,
        stability_decreasing_percentage=40.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=50.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=20.0,
    )

    last = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=20.0,
        mixed_percentage=30.0,
        low_strength_percentage=40.0,
        medium_strength_percentage=20.0,
        high_strength_percentage=40.0,
    )

    result = build_position_distribution_stability_trend_comparison(
        (first, last)
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

    assert result.total_absolute_percentage_change == expected
    assert result.mean_absolute_percentage_change == expected


def test_total_and_mean_absolute_change_for_multiple_transitions():
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

    result = build_position_distribution_stability_trend_comparison(
        (first, second, third)
    )

    transition_one = (
        abs(35.0 - 25.0)
        + abs(20.0 - 25.0)
        + abs(25.0 - 25.0)
        + abs(20.0 - 25.0)
        + abs(20.0 - 25.0)
        + abs(30.0 - 25.0)
        + abs(50.0 - 50.0)
    )

    transition_two = (
        abs(45.0 - 35.0)
        + abs(15.0 - 20.0)
        + abs(20.0 - 25.0)
        + abs(20.0 - 20.0)
        + abs(10.0 - 20.0)
        + abs(30.0 - 30.0)
        + abs(60.0 - 50.0)
    )

    expected_total = transition_one + transition_two

    assert result.total_absolute_percentage_change == expected_total
    assert result.mean_absolute_percentage_change == expected_total / 2


def test_summary_count_is_preserved():
    first = make_overview(summary_count=7)
    last = make_overview(summary_count=7)

    result = build_position_distribution_stability_trend_comparison(
        (first, last)
    )

    assert result.summary_count == 7


def test_summary_count_must_match():
    first = make_overview(summary_count=4)
    second = make_overview(summary_count=5)

    with pytest.raises(ValueError, match="same summary_count"):
        build_position_distribution_stability_trend_comparison(
            (first, second)
        )


def test_input_must_be_tuple():
    with pytest.raises(TypeError, match="overviews must be a tuple"):
        build_position_distribution_stability_trend_comparison(
            [make_overview()]
        )


def test_invalid_overview_type_is_rejected():
    with pytest.raises(TypeError, match="Each item must be"):
        build_position_distribution_stability_trend_comparison(
            ("invalid",)
        )


def test_negative_summary_count_is_rejected():
    overview = make_overview(summary_count=-1)

    with pytest.raises(ValueError, match="summary_count"):
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
            (overview,)
        )


def test_strength_percentages_must_sum_to_100():
    overview = make_overview(
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=30.0,
    )

    with pytest.raises(ValueError, match="strength percentages"):
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
            (make_overview(**values),)
        )


def test_minimum_metric_cannot_exceed_maximum_metric():
    overview = make_overview(
        minimum_mean_absolute_percentage_change=5.0,
        maximum_mean_absolute_percentage_change=4.0,
    )

    with pytest.raises(ValueError, match="minimum_mean"):
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
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
        build_position_distribution_stability_trend_comparison(
            (overview,)
        )


def test_wrapper_function_returns_same_result():
    first = make_overview(
        stable_increasing_percentage=20.0,
        stability_decreasing_percentage=30.0,
        stable_percentage=25.0,
        mixed_percentage=25.0,
        low_strength_percentage=30.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=40.0,
    )

    last = make_overview(
        stable_increasing_percentage=30.0,
        stability_decreasing_percentage=20.0,
        stable_percentage=30.0,
        mixed_percentage=20.0,
        low_strength_percentage=20.0,
        medium_strength_percentage=30.0,
        high_strength_percentage=50.0,
    )

    direct = build_position_distribution_stability_trend_comparison(
        (first, last)
    )

    wrapped = compare_position_distribution_stability_trends(
        (first, last)
    )

    assert wrapped == direct