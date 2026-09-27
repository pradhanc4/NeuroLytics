from dataclasses import FrozenInstanceError
import pytest

from analytics.position_behavior_profile import build_position_behavior_profile
from analytics.position_behavior_profile_comparison import (
    COMPARISON_NUMERIC_FIELDS,
    COMPARISON_CATEGORICAL_FIELDS,
    PositionBehaviorProfileComparison,
    PositionBehaviorProfileComparisonResult,
    build_position_behavior_profile_comparison,
    build_position_behavior_profile_comparison_result,
    build_position_behavior_profile_comparison_result_from_iterable,
    get_position_behavior_profile_comparison,
)


def make_profile(position="col1", shift=0.0):
    return build_position_behavior_profile(
        position=position,
        observation_count=int(10 + shift),
        frequency_total=int(12 + shift),
        dominant_digit=5 if shift == 0 else 6,
        distribution_mean=1.0 + shift,
        distribution_std=0.5 + shift,
        stability_percentage=80.0 - shift,
        stability_level="STABLE" if shift == 0 else "MODERATE",
        change_count=int(9 + shift),
        increase_count=3,
        decrease_count=3,
        unchanged_count=3,
        change_magnitude=2.0 + shift,
        change_direction="INCREASE" if shift == 0 else "DECREASE",
        trend_direction="INCREASE" if shift == 0 else "DECREASE",
        trend_strength=70.0 + shift,
        trend_consistency=80.0 - shift,
        volatility=1.5 + shift,
        volatility_level="LOW" if shift == 0 else "MEDIUM",
        transition_count=int(9 + shift),
    )


def test_single_comparison_has_expected_metric_counts():
    result = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2", 1)
    )
    assert len(result.numeric_metrics) == len(COMPARISON_NUMERIC_FIELDS)
    assert len(result.categorical_metrics) == len(COMPARISON_CATEGORICAL_FIELDS)


def test_numeric_difference_is_first_minus_second():
    result = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2", 1)
    )
    metric = next(m for m in result.numeric_metrics if m.metric_name == "frequency_total")
    assert metric.first_value == 12
    assert metric.second_value == 13
    assert metric.difference == -1
    assert metric.absolute_difference == 1


def test_categorical_equality_is_reported():
    result = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2", 1)
    )
    stability = next(m for m in result.categorical_metrics if m.field_name == "stability_level")
    assert stability.equal is False


def test_same_categorical_values_are_equal():
    result = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2")
    )
    stability = next(m for m in result.categorical_metrics if m.field_name == "stability_level")
    assert stability.equal is True


def test_result_empty():
    result = build_position_behavior_profile_comparison_result(())
    assert result.profile_count == 0
    assert result.comparison_count == 0
    assert result.comparisons == ()


def test_one_profile_has_zero_comparisons():
    result = build_position_behavior_profile_comparison_result((make_profile(),))
    assert result.profile_count == 1
    assert result.comparison_count == 0


def test_two_profiles_have_one_comparison():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"))
    )
    assert result.profile_count == 2
    assert result.comparison_count == 1


def test_three_profiles_have_three_comparisons():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"), make_profile("col3"))
    )
    assert result.comparison_count == 3


def test_eight_profiles_have_28_unique_comparisons():
    profiles = tuple(make_profile(f"col{i}") for i in range(1, 9))
    result = build_position_behavior_profile_comparison_result(profiles)
    assert result.profile_count == 8
    assert result.comparison_count == 28


def test_caller_order_is_preserved():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col4"), make_profile("col1"), make_profile("col7"))
    )
    assert result.positions == ("col4", "col1", "col7")
    assert result.comparisons[0].first_position == "col4"
    assert result.comparisons[0].second_position == "col1"


def test_no_reverse_duplicate_is_created():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"))
    )
    pairs = {(c.first_position, c.second_position) for c in result.comparisons}
    assert pairs == {("col1", "col2")}


def test_lookup_works():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"))
    )
    found = get_position_behavior_profile_comparison(result, "col1", "col2")
    assert found is not None
    assert found.first_position == "col1"


def test_reverse_lookup_is_not_inferred():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"))
    )
    assert get_position_behavior_profile_comparison(result, "col2", "col1") is None


def test_iterable_wrapper():
    result = build_position_behavior_profile_comparison_result_from_iterable(
        iter((make_profile("col1"), make_profile("col2")))
    )
    assert result.comparison_count == 1


def test_duplicate_positions_rejected():
    profile = make_profile("col1")
    with pytest.raises(ValueError):
        build_position_behavior_profile_comparison_result((profile, profile))


def test_self_comparison_rejected():
    profile = make_profile("col1")
    with pytest.raises(ValueError):
        build_position_behavior_profile_comparison(profile, profile)


def test_invalid_container_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_comparison_result([])


def test_invalid_profile_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_comparison_result((object(),))


def test_result_is_frozen():
    result = build_position_behavior_profile_comparison_result(
        (make_profile("col1"), make_profile("col2"))
    )
    with pytest.raises(FrozenInstanceError):
        result.comparison_count = 0


def test_comparison_is_frozen():
    comparison = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2")
    )
    with pytest.raises(FrozenInstanceError):
        comparison.first_position = "col3"


def test_metric_names_are_complete():
    comparison = build_position_behavior_profile_comparison(
        make_profile("col1"), make_profile("col2")
    )
    assert tuple(m.metric_name for m in comparison.numeric_metrics) == COMPARISON_NUMERIC_FIELDS
    assert tuple(m.field_name for m in comparison.categorical_metrics) == COMPARISON_CATEGORICAL_FIELDS


def test_lookup_invalid_result_rejected():
    with pytest.raises(TypeError):
        get_position_behavior_profile_comparison(object(), "col1", "col2")


def test_lookup_same_position_rejected():
    result = build_position_behavior_profile_comparison_result(())
    with pytest.raises(ValueError):
        get_position_behavior_profile_comparison(result, "col1", "col1")
