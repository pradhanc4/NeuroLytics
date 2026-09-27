import pytest
from dataclasses import FrozenInstanceError

from analytics.position_behavior_profile import build_position_behavior_profile
from analytics.position_behavior_profile_ranking import (
    RANKABLE_METRICS,
    PositionBehaviorProfileRanking,
    PositionBehaviorProfileRankingResult,
    build_position_behavior_profile_ranking,
    build_position_behavior_profile_ranking_result,
    build_position_behavior_profile_ranking_result_from_iterable,
    get_position_behavior_profile_ranking,
)


def make_profile(position, stability, volatility, frequency):
    return build_position_behavior_profile(
        position=position,
        observation_count=10,
        frequency_total=frequency,
        dominant_digit=5,
        distribution_mean=1.0,
        distribution_std=0.5,
        stability_percentage=stability,
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
        volatility=volatility,
        volatility_level="LOW",
        transition_count=9,
    )


def test_all_expected_rankable_metrics_exist():
    assert len(RANKABLE_METRICS) == 14


def test_single_metric_ranking_is_descending():
    profiles = (
        make_profile("col1", 60, 2, 10),
        make_profile("col2", 90, 1, 20),
        make_profile("col3", 75, 3, 15),
    )
    result = build_position_behavior_profile_ranking(profiles, "stability_percentage")
    assert tuple(e.position for e in result.entries) == ("col2", "col3", "col1")
    assert tuple(e.rank for e in result.entries) == (1, 2, 3)


def test_metric_values_are_preserved():
    profiles = (make_profile("col1", 60, 2, 10), make_profile("col2", 90, 1, 20))
    result = build_position_behavior_profile_ranking(profiles, "frequency_total")
    assert result.entries[0].metric_value == 20
    assert result.entries[1].metric_value == 10


def test_ties_use_competition_ranks():
    profiles = (
        make_profile("col1", 80, 2, 10),
        make_profile("col2", 80, 1, 20),
        make_profile("col3", 60, 3, 15),
    )
    result = build_position_behavior_profile_ranking(profiles, "stability_percentage")
    assert tuple(e.rank for e in result.entries) == (1, 1, 3)


def test_equal_value_ties_preserve_caller_order():
    profiles = (
        make_profile("col3", 80, 2, 10),
        make_profile("col1", 80, 1, 20),
    )
    result = build_position_behavior_profile_ranking(profiles, "stability_percentage")
    assert tuple(e.position for e in result.entries) == ("col3", "col1")


def test_empty_ranking():
    result = build_position_behavior_profile_ranking((), "stability_percentage")
    assert result.entries == ()


def test_result_contains_all_metrics_by_default():
    profiles = (
        make_profile("col1", 80, 2, 10),
        make_profile("col2", 60, 1, 20),
    )
    result = build_position_behavior_profile_ranking_result(profiles)
    assert result.profile_count == 2
    assert len(result.rankings) == len(RANKABLE_METRICS)
    assert tuple(r.metric_name for r in result.rankings) == RANKABLE_METRICS


def test_selected_metrics_are_supported():
    profiles = (make_profile("col1", 80, 2, 10), make_profile("col2", 60, 1, 20))
    result = build_position_behavior_profile_ranking_result(
        profiles, ("stability_percentage", "volatility")
    )
    assert tuple(r.metric_name for r in result.rankings) == (
        "stability_percentage", "volatility"
    )


def test_result_positions_preserve_caller_order():
    profiles = (make_profile("col4", 80, 2, 10), make_profile("col2", 60, 1, 20))
    result = build_position_behavior_profile_ranking_result(profiles)
    assert result.positions == ("col4", "col2")


def test_eight_positions():
    profiles = tuple(
        make_profile(f"col{i}", 50 + i, i, 10 + i) for i in range(1, 9)
    )
    result = build_position_behavior_profile_ranking_result(profiles)
    assert result.profile_count == 8
    assert all(len(r.entries) == 8 for r in result.rankings)


def test_iterable_wrapper():
    profiles = (make_profile("col1", 80, 2, 10), make_profile("col2", 60, 1, 20))
    result = build_position_behavior_profile_ranking_result_from_iterable(iter(profiles))
    assert result.profile_count == 2


def test_lookup():
    profiles = (make_profile("col1", 80, 2, 10), make_profile("col2", 60, 1, 20))
    result = build_position_behavior_profile_ranking_result(profiles)
    ranking = get_position_behavior_profile_ranking(result, "stability_percentage")
    assert ranking is not None


def test_unknown_lookup_returns_none():
    result = build_position_behavior_profile_ranking_result(())
    assert get_position_behavior_profile_ranking(result, "missing") is None


def test_invalid_metric_rejected():
    with pytest.raises(ValueError):
        build_position_behavior_profile_ranking((), "missing")


def test_invalid_metric_names_container_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_ranking_result((), ["stability_percentage"])


def test_invalid_profile_container_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_ranking_result([])


def test_duplicate_positions_rejected():
    profile = make_profile("col1", 80, 2, 10)
    with pytest.raises(ValueError):
        build_position_behavior_profile_ranking_result((profile, profile))


def test_invalid_profile_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_ranking_result((object(),))


def test_result_is_frozen():
    result = build_position_behavior_profile_ranking_result(())
    with pytest.raises(FrozenInstanceError):
        result.profile_count = 1


def test_ranking_is_frozen():
    ranking = build_position_behavior_profile_ranking((), "stability_percentage")
    with pytest.raises(FrozenInstanceError):
        ranking.metric_name = "volatility"


def test_no_overall_score_is_present():
    result = build_position_behavior_profile_ranking_result(())
    assert not hasattr(result, "overall_score")
    assert not hasattr(result, "best_position")
