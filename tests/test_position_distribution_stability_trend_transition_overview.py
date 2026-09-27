import pytest

from analytics.position_distribution_stability_trend_transition_summary import (
    HIGH,
    LOW,
    MEDIUM,
    PositionDistributionStabilityTrendTransitionSummary,
)
from analytics.position_distribution_stability_trend_transition_overview import (
    PositionDistributionStabilityTrendTransitionOverview,
    build_position_distribution_stability_trend_transition_overview,
    get_position_distribution_stability_trend_transition_overview,
)


def make_summary(
    transition_count=4,
    low_movement_count=1,
    medium_movement_count=1,
    high_movement_count=2,
    average_total_absolute_percentage_change=3.0,
    minimum_total_absolute_percentage_change=1.0,
    maximum_total_absolute_percentage_change=7.0,
    total_absolute_percentage_change=12.0,
    transitions=None,
):
    if transitions is None:
        transitions = tuple(
            object() for _ in range(transition_count)
        )

    return PositionDistributionStabilityTrendTransitionSummary(
        transition_count=transition_count,
        low_movement_count=low_movement_count,
        medium_movement_count=medium_movement_count,
        high_movement_count=high_movement_count,
        average_total_absolute_percentage_change=(
            average_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change=(
            minimum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change=(
            maximum_total_absolute_percentage_change
        ),
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        transitions=tuple(transitions),
    )


def test_overview_is_frozen_dataclass():
    overview = build_position_distribution_stability_trend_transition_overview(
        make_summary()
    )

    assert isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionOverview,
    )

    with pytest.raises(Exception):
        overview.transition_count = 10


def test_empty_summary_returns_zero_overview():
    summary = make_summary(
        transition_count=0,
        low_movement_count=0,
        medium_movement_count=0,
        high_movement_count=0,
        average_total_absolute_percentage_change=0.0,
        minimum_total_absolute_percentage_change=0.0,
        maximum_total_absolute_percentage_change=0.0,
        total_absolute_percentage_change=0.0,
        transitions=(),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.transition_count == 0

    assert result.low_movement_percentage == 0.0
    assert result.medium_movement_percentage == 0.0
    assert result.high_movement_percentage == 0.0

    assert result.average_total_absolute_percentage_change == 0.0
    assert result.minimum_total_absolute_percentage_change == 0.0
    assert result.maximum_total_absolute_percentage_change == 0.0
    assert result.total_absolute_percentage_change == 0.0

    assert result.dominant_movement_levels == ()


def test_percentages_are_calculated_correctly():
    summary = make_summary(
        transition_count=10,
        low_movement_count=2,
        medium_movement_count=5,
        high_movement_count=3,
        transitions=tuple(object() for _ in range(10)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.low_movement_percentage == 20.0
    assert result.medium_movement_percentage == 50.0
    assert result.high_movement_percentage == 30.0


def test_percentages_sum_to_100_for_non_empty_summary():
    summary = make_summary(
        transition_count=8,
        low_movement_count=2,
        medium_movement_count=3,
        high_movement_count=3,
        transitions=tuple(object() for _ in range(8)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    total = (
        result.low_movement_percentage
        + result.medium_movement_percentage
        + result.high_movement_percentage
    )

    assert total == pytest.approx(100.0)


def test_dominant_high_movement_level():
    summary = make_summary(
        transition_count=10,
        low_movement_count=2,
        medium_movement_count=3,
        high_movement_count=5,
        transitions=tuple(object() for _ in range(10)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.dominant_movement_levels == (HIGH,)


def test_dominant_medium_movement_level():
    summary = make_summary(
        transition_count=10,
        low_movement_count=2,
        medium_movement_count=6,
        high_movement_count=2,
        transitions=tuple(object() for _ in range(10)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.dominant_movement_levels == (MEDIUM,)


def test_dominant_low_movement_level():
    summary = make_summary(
        transition_count=10,
        low_movement_count=6,
        medium_movement_count=2,
        high_movement_count=2,
        transitions=tuple(object() for _ in range(10)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.dominant_movement_levels == (LOW,)


def test_dominant_tie_is_preserved_in_level_order():
    summary = make_summary(
        transition_count=6,
        low_movement_count=3,
        medium_movement_count=3,
        high_movement_count=0,
        transitions=tuple(object() for _ in range(6)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.dominant_movement_levels == (
        LOW,
        MEDIUM,
    )


def test_all_three_levels_can_be_tied():
    summary = make_summary(
        transition_count=6,
        low_movement_count=2,
        medium_movement_count=2,
        high_movement_count=2,
        transitions=tuple(object() for _ in range(6)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.dominant_movement_levels == (
        LOW,
        MEDIUM,
        HIGH,
    )


def test_aggregate_metrics_are_preserved():
    summary = make_summary(
        average_total_absolute_percentage_change=3.75,
        minimum_total_absolute_percentage_change=1.25,
        maximum_total_absolute_percentage_change=8.5,
        total_absolute_percentage_change=15.0,
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.average_total_absolute_percentage_change == 3.75
    assert result.minimum_total_absolute_percentage_change == 1.25
    assert result.maximum_total_absolute_percentage_change == 8.5
    assert result.total_absolute_percentage_change == 15.0


def test_transition_count_is_preserved():
    summary = make_summary(
        transition_count=7,
        low_movement_count=2,
        medium_movement_count=2,
        high_movement_count=3,
        transitions=tuple(object() for _ in range(7)),
    )

    result = build_position_distribution_stability_trend_transition_overview(
        summary
    )

    assert result.transition_count == 7


def test_summary_type_is_required():
    with pytest.raises(
        TypeError,
        match="PositionDistributionStabilityTrendTransitionSummary",
    ):
        build_position_distribution_stability_trend_transition_overview(
            "invalid"
        )


def test_negative_transition_count_is_rejected():
    summary = make_summary(
        transition_count=-1,
        low_movement_count=0,
        medium_movement_count=0,
        high_movement_count=0,
        transitions=(),
    )

    with pytest.raises(
        ValueError,
        match="transition_count must be non-negative",
    ):
        build_position_distribution_stability_trend_transition_overview(
            summary
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "low_movement_count",
        "medium_movement_count",
        "high_movement_count",
    ],
)
def test_negative_movement_count_is_rejected(field_name):
    values = {
        "transition_count": 4,
        "low_movement_count": 1,
        "medium_movement_count": 1,
        "high_movement_count": 2,
        "transitions": tuple(object() for _ in range(4)),
    }

    values[field_name] = -1

    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        build_position_distribution_stability_trend_transition_overview(
            make_summary(**values)
        )


def test_movement_counts_must_equal_transition_count():
    summary = make_summary(
        transition_count=10,
        low_movement_count=2,
        medium_movement_count=2,
        high_movement_count=2,
        transitions=tuple(object() for _ in range(10)),
    )

    with pytest.raises(
        ValueError,
        match="Movement counts must equal transition_count",
    ):
        build_position_distribution_stability_trend_transition_overview(
            summary
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "average_total_absolute_percentage_change",
        "minimum_total_absolute_percentage_change",
        "maximum_total_absolute_percentage_change",
        "total_absolute_percentage_change",
    ],
)
def test_negative_metric_is_rejected(field_name):
    values = {
        "average_total_absolute_percentage_change": 3.0,
        "minimum_total_absolute_percentage_change": 1.0,
        "maximum_total_absolute_percentage_change": 7.0,
        "total_absolute_percentage_change": 12.0,
        "transitions": tuple(object() for _ in range(4)),
    }

    values[field_name] = -1.0

    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        build_position_distribution_stability_trend_transition_overview(
            make_summary(**values)
        )


def test_minimum_metric_cannot_exceed_maximum_metric():
    summary = make_summary(
        minimum_total_absolute_percentage_change=8.0,
        maximum_total_absolute_percentage_change=7.0,
    )

    with pytest.raises(
        ValueError,
        match="minimum_total_absolute_percentage_change",
    ):
        build_position_distribution_stability_trend_transition_overview(
            summary
        )


def test_transitions_must_be_tuple():
    summary = make_summary()

    object.__setattr__(
        summary,
        "transitions",
        [object(), object(), object(), object()],
    )

    with pytest.raises(
        TypeError,
        match="transitions must be a tuple",
    ):
        build_position_distribution_stability_trend_transition_overview(
            summary
        )


def test_transition_count_must_match_transition_length():
    summary = make_summary(
        transition_count=4,
        low_movement_count=1,
        medium_movement_count=1,
        high_movement_count=2,
        transitions=tuple(object() for _ in range(3)),
    )

    with pytest.raises(
        ValueError,
        match="transition_count must equal the number of transitions",
    ):
        build_position_distribution_stability_trend_transition_overview(
            summary
        )


def test_get_overview_returns_same_object():
    summary = make_summary()

    overview = (
        build_position_distribution_stability_trend_transition_overview(
            summary
        )
    )

    result = (
        get_position_distribution_stability_trend_transition_overview(
            overview
        )
    )

    assert result is overview


def test_get_overview_rejects_invalid_type():
    with pytest.raises(
        TypeError,
        match="PositionDistributionStabilityTrendTransitionOverview",
    ):
        get_position_distribution_stability_trend_transition_overview(
            "invalid"
        )