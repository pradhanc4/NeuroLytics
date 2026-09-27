from dataclasses import FrozenInstanceError
import pytest

from analytics.position_behavior_profile import (
    POSITIONS,
    PositionBehaviorProfile,
    PositionBehaviorProfileResult,
    build_position_behavior_profile,
    build_position_behavior_profile_result,
    build_position_behavior_profile_result_from_iterable,
    get_position_behavior_profile,
    validate_position_behavior_profile,
)


def make_profile(position="col1", shift=0.0):
    return build_position_behavior_profile(
        position=position,
        observation_count=10,
        frequency_total=10,
        dominant_digit=5,
        distribution_mean=1.25 + shift,
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
        trend_strength=75.0,
        trend_consistency=80.0,
        volatility=1.5,
        volatility_level="LOW",
        transition_count=9,
    )


def test_profile_is_frozen():
    profile = make_profile()
    with pytest.raises(FrozenInstanceError):
        profile.position = "col2"


def test_result_is_frozen():
    result = build_position_behavior_profile_result((make_profile(),))
    with pytest.raises(FrozenInstanceError):
        result.profile_count = 2


def test_all_eight_positions_are_supported():
    assert POSITIONS == ("col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8")


def test_profile_values_are_preserved():
    profile = make_profile("col3")
    assert profile.position == "col3"
    assert profile.observation_count == 10
    assert profile.dominant_digit == 5
    assert profile.stability_percentage == 80.0
    assert profile.trend_strength == 75.0
    assert profile.volatility == 1.5


def test_result_preserves_caller_order():
    first = make_profile("col3")
    second = make_profile("col1")
    result = build_position_behavior_profile_result((first, second))
    assert result.profiles == (first, second)


def test_result_count_matches_profiles():
    result = build_position_behavior_profile_result(
        tuple(make_profile(position) for position in POSITIONS)
    )
    assert result.profile_count == 8


def test_empty_result_is_valid():
    result = build_position_behavior_profile_result(())
    assert result.profile_count == 0
    assert result.profiles == ()


def test_iterable_wrapper():
    result = build_position_behavior_profile_result_from_iterable(
        iter((make_profile("col2"), make_profile("col4")))
    )
    assert result.profile_count == 2
    assert result.profiles[0].position == "col2"


def test_get_profile():
    profile = make_profile("col6")
    result = build_position_behavior_profile_result((profile,))
    assert get_position_behavior_profile(result, "col6") == profile


def test_get_missing_profile_returns_none():
    result = build_position_behavior_profile_result((make_profile("col6"),))
    assert get_position_behavior_profile(result, "col7") is None


def test_invalid_position_rejected():
    with pytest.raises(ValueError):
        make_profile("bad")


def test_negative_observation_count_rejected():
    with pytest.raises(ValueError):
        make_profile("col1") if False else build_position_behavior_profile(
            position="col1", observation_count=-1, frequency_total=0,
            dominant_digit=None, distribution_mean=0, distribution_std=0,
            stability_percentage=0, stability_level="STABLE",
            change_count=0, increase_count=0, decrease_count=0,
            unchanged_count=0, change_magnitude=0, change_direction="UNCHANGED",
            trend_direction="UNCHANGED", trend_strength=0, trend_consistency=0,
            volatility=0, volatility_level="LOW", transition_count=0,
        )


def test_invalid_percentage_rejected():
    with pytest.raises(ValueError):
        make_profile("col1") if False else build_position_behavior_profile(
            position="col1", observation_count=1, frequency_total=1,
            dominant_digit=0, distribution_mean=0, distribution_std=0,
            stability_percentage=101, stability_level="STABLE",
            change_count=0, increase_count=0, decrease_count=0,
            unchanged_count=0, change_magnitude=0, change_direction="UNCHANGED",
            trend_direction="UNCHANGED", trend_strength=0, trend_consistency=0,
            volatility=0, volatility_level="LOW", transition_count=0,
        )


def test_invalid_digit_rejected():
    with pytest.raises(ValueError):
        make_profile("col1") if False else build_position_behavior_profile(
            position="col1", observation_count=1, frequency_total=1,
            dominant_digit=10, distribution_mean=0, distribution_std=0,
            stability_percentage=0, stability_level="STABLE",
            change_count=0, increase_count=0, decrease_count=0,
            unchanged_count=0, change_magnitude=0, change_direction="UNCHANGED",
            trend_direction="UNCHANGED", trend_strength=0, trend_consistency=0,
            volatility=0, volatility_level="LOW", transition_count=0,
        )


def test_duplicate_positions_rejected():
    profile = make_profile("col1")
    with pytest.raises(ValueError):
        build_position_behavior_profile_result((profile, profile))


def test_invalid_result_input_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_result([])


def test_invalid_result_for_lookup_rejected():
    with pytest.raises(TypeError):
        get_position_behavior_profile(object(), "col1")


def test_invalid_stability_level_rejected():
    with pytest.raises(ValueError):
        make_profile("col1") if False else build_position_behavior_profile(
            position="col1", observation_count=1, frequency_total=1,
            dominant_digit=0, distribution_mean=0, distribution_std=0,
            stability_percentage=0, stability_level="BAD",
            change_count=0, increase_count=0, decrease_count=0,
            unchanged_count=0, change_magnitude=0, change_direction="UNCHANGED",
            trend_direction="UNCHANGED", trend_strength=0, trend_consistency=0,
            volatility=0, volatility_level="LOW", transition_count=0,
        )


def test_change_direction_counts_cannot_exceed_change_count():
    with pytest.raises(ValueError):
        build_position_behavior_profile(
            position="col1", observation_count=1, frequency_total=1,
            dominant_digit=0, distribution_mean=0, distribution_std=0,
            stability_percentage=0, stability_level="STABLE",
            change_count=1, increase_count=1, decrease_count=1,
            unchanged_count=0, change_magnitude=0, change_direction="INCREASE",
            trend_direction="INCREASE", trend_strength=0, trend_consistency=0,
            volatility=0, volatility_level="LOW", transition_count=0,
        )
