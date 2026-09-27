from dataclasses import FrozenInstanceError
import pytest

from analytics.position_behavior_profile import (
    PositionBehaviorProfile,
    build_position_behavior_profile,
)
from analytics.position_behavior_profile_summary import (
    PositionBehaviorProfileSummary,
    build_position_behavior_profile_summary,
    build_position_behavior_profile_summary_from_iterable,
    get_change_direction_count,
    get_stability_level_count,
    get_trend_direction_count,
    get_volatility_level_count,
)


def make_profile(position="col1", shift=0.0):
    return build_position_behavior_profile(
        position=position,
        observation_count=10,
        frequency_total=12,
        dominant_digit=5,
        distribution_mean=1.0 + shift,
        distribution_std=0.5,
        stability_percentage=80.0,
        stability_level="STABLE",
        change_count=9,
        increase_count=3,
        decrease_count=3,
        unchanged_count=3,
        change_magnitude=2.0,
        change_direction="INCREASE",
        trend_direction="INCREASE",
        trend_strength=70.0,
        trend_consistency=80.0,
        volatility=1.5,
        volatility_level="LOW",
        transition_count=9,
    )


def test_summary_is_frozen():
    summary = build_position_behavior_profile_summary((make_profile(),))
    with pytest.raises(FrozenInstanceError):
        summary.profile_count = 2


def test_empty_summary():
    summary = build_position_behavior_profile_summary(())
    assert summary.profile_count == 0
    assert summary.positions == ()
    assert summary.total_observations == 0
    assert summary.total_frequency == 0
    assert summary.total_change_count == 0
    assert summary.total_transition_count == 0


def test_single_profile_summary():
    summary = build_position_behavior_profile_summary((make_profile("col1"),))
    assert summary.profile_count == 1
    assert summary.positions == ("col1",)
    assert summary.total_observations == 10
    assert summary.total_frequency == 12
    assert summary.average_stability_percentage == 80.0
    assert summary.total_change_count == 9
    assert summary.total_transition_count == 9


def test_multiple_profiles_are_aggregated():
    first = make_profile("col1", 0.0)
    second = make_profile("col2", 2.0)
    summary = build_position_behavior_profile_summary((first, second))
    assert summary.profile_count == 2
    assert summary.total_observations == 20
    assert summary.total_frequency == 24
    assert summary.total_change_count == 18
    assert summary.total_increase_count == 6
    assert summary.total_decrease_count == 6
    assert summary.total_unchanged_count == 6
    assert summary.total_transition_count == 18


def test_averages_are_calculated():
    first = make_profile("col1", 0.0)
    second = make_profile("col2", 2.0)
    summary = build_position_behavior_profile_summary((first, second))
    assert summary.average_distribution_mean == 2.0
    assert summary.average_distribution_std == 0.5
    assert summary.average_stability_percentage == 80.0
    assert summary.average_change_magnitude == 2.0
    assert summary.average_trend_strength == 70.0
    assert summary.average_trend_consistency == 80.0
    assert summary.average_volatility == 1.5


def test_positions_preserve_caller_order():
    result = build_position_behavior_profile_summary(
        (make_profile("col4"), make_profile("col2"), make_profile("col8"))
    )
    assert result.positions == ("col4", "col2", "col8")


def test_stability_counts():
    a = make_profile("col1")
    b = build_position_behavior_profile(
        position="col2", observation_count=1, frequency_total=1,
        dominant_digit=0, distribution_mean=0, distribution_std=0,
        stability_percentage=50, stability_level="MODERATE",
        change_count=0, increase_count=0, decrease_count=0,
        unchanged_count=0, change_magnitude=0, change_direction="UNCHANGED",
        trend_direction="UNCHANGED", trend_strength=0, trend_consistency=0,
        volatility=0, volatility_level="MEDIUM", transition_count=0,
    )
    summary = build_position_behavior_profile_summary((a, b))
    assert dict(summary.stability_level_counts) == {
        "STABLE": 1, "MODERATE": 1, "UNSTABLE": 0
    }


def test_change_direction_counts():
    summary = build_position_behavior_profile_summary(
        (make_profile("col1"), make_profile("col2"))
    )
    assert get_change_direction_count(summary, "INCREASE") == 2
    assert get_change_direction_count(summary, "DECREASE") == 0
    assert get_change_direction_count(summary, "UNCHANGED") == 0


def test_trend_direction_counts():
    summary = build_position_behavior_profile_summary(
        (make_profile("col1"), make_profile("col2"))
    )
    assert get_trend_direction_count(summary, "INCREASE") == 2


def test_volatility_level_counts():
    summary = build_position_behavior_profile_summary(
        (make_profile("col1"), make_profile("col2"))
    )
    assert get_volatility_level_count(summary, "LOW") == 2


def test_stability_level_lookup():
    summary = build_position_behavior_profile_summary((make_profile(),))
    assert get_stability_level_count(summary, "STABLE") == 1


def test_iterable_wrapper():
    summary = build_position_behavior_profile_summary_from_iterable(
        iter((make_profile("col3"), make_profile("col5")))
    )
    assert summary.profile_count == 2
    assert summary.positions == ("col3", "col5")


def test_non_tuple_input_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_summary([make_profile()])


def test_duplicate_positions_rejected():
    profile = make_profile("col1")
    with pytest.raises(ValueError):
        build_position_behavior_profile_summary((profile, profile))


def test_invalid_profile_type_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_summary((object(),))


def test_invalid_lookup_summary_rejected():
    with pytest.raises(TypeError):
        get_stability_level_count(object(), "STABLE")


def test_invalid_lookup_category_rejected():
    summary = build_position_behavior_profile_summary((make_profile(),))
    with pytest.raises(ValueError):
        get_change_direction_count(summary, "BAD")
    with pytest.raises(ValueError):
        get_trend_direction_count(summary, "BAD")
    with pytest.raises(ValueError):
        get_volatility_level_count(summary, "BAD")
    with pytest.raises(ValueError):
        get_stability_level_count(summary, "BAD")


def test_all_eight_positions_can_be_summarized():
    positions = tuple(
        make_profile(position) for position in
        ("col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8")
    )
    summary = build_position_behavior_profile_summary(positions)
    assert summary.profile_count == 8
    assert summary.positions == (
        "col1", "col2", "col3", "col4",
        "col5", "col6", "col7", "col8",
    )
