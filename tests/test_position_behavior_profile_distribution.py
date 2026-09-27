import math

import pytest

from analytics.position_behavior_profile import PositionBehaviorProfile
from analytics.position_behavior_profile_distribution import (
    CATEGORICAL_DISTRIBUTION_FIELDS,
    NUMERIC_DISTRIBUTION_METRICS,
    PositionBehaviorProfileCategoricalDistribution,
    PositionBehaviorProfileDistribution,
    PositionBehaviorProfileNumericDistribution,
    build_position_behavior_profile_distribution,
    build_position_behavior_profile_distribution_result,
    get_categorical_distribution,
    get_numeric_distribution,
    iter_categorical_distributions,
    iter_numeric_distributions,
)


def make_profile(
    position: str,
    *,
    observation_count: int = 10,
    frequency_total: int = 20,
    distribution_mean: float = 2.5,
    distribution_std: float = 1.5,
    stability_percentage: float = 80.0,
    change_count: int = 4,
    increase_count: int = 2,
    decrease_count: int = 1,
    unchanged_count: int = 1,
    change_magnitude: float = 3.0,
    trend_direction: str = "INCREASE",
    trend_strength: float = 0.75,
    trend_consistency: float = 70.0,
    volatility: float = 1.2,
    volatility_level: str = "LOW",
    transition_count: int = 5,
    dominant_digit: int | None = 3,
    stability_level: str = "STABLE",
    change_direction: str = "INCREASE",
) -> PositionBehaviorProfile:
    return PositionBehaviorProfile(
        position=position,
        observation_count=observation_count,
        frequency_total=frequency_total,
        dominant_digit=dominant_digit,
        distribution_mean=distribution_mean,
        distribution_std=distribution_std,
        stability_percentage=stability_percentage,
        stability_level=stability_level,
        change_count=change_count,
        increase_count=increase_count,
        decrease_count=decrease_count,
        unchanged_count=unchanged_count,
        change_magnitude=change_magnitude,
        change_direction=change_direction,
        trend_direction=trend_direction,
        trend_strength=trend_strength,
        trend_consistency=trend_consistency,
        volatility=volatility,
        volatility_level=volatility_level,
        transition_count=transition_count,
    )


def test_expected_numeric_metrics_are_defined():
    assert NUMERIC_DISTRIBUTION_METRICS == (
        "observation_count",
        "frequency_total",
        "distribution_mean",
        "distribution_std",
        "stability_percentage",
        "change_count",
        "increase_count",
        "decrease_count",
        "unchanged_count",
        "change_magnitude",
        "trend_strength",
        "trend_consistency",
        "volatility",
        "transition_count",
    )


def test_expected_categorical_fields_are_defined():
    assert CATEGORICAL_DISTRIBUTION_FIELDS == (
        "dominant_digit",
        "stability_level",
        "change_direction",
        "trend_direction",
        "volatility_level",
    )


def test_empty_profiles_produce_empty_distribution():
    result = build_position_behavior_profile_distribution([])

    assert result.profile_count == 0
    assert result.positions == ()
    assert len(result.numeric_distributions) == 14
    assert len(result.categorical_distributions) == 5

    for distribution in result.numeric_distributions:
        assert distribution.observation_count == 0
        assert distribution.total == 0.0
        assert distribution.minimum == 0.0
        assert distribution.maximum == 0.0
        assert distribution.mean == 0.0
        assert distribution.standard_deviation == 0.0

    for distribution in result.categorical_distributions:
        assert distribution.observation_count == 0
        assert distribution.entries == ()


def test_positions_preserve_caller_order():
    profiles = (
        make_profile("col3"),
        make_profile("col1"),
        make_profile("col2"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    assert result.positions == ("col3", "col1", "col2")


def test_profile_count_is_correct():
    profiles = (
        make_profile("col1"),
        make_profile("col2"),
        make_profile("col3"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    assert result.profile_count == 3


def test_all_numeric_distributions_are_created():
    profiles = (
        make_profile("col1"),
        make_profile("col2"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    assert tuple(
        item.metric_name
        for item in result.numeric_distributions
    ) == NUMERIC_DISTRIBUTION_METRICS


def test_all_categorical_distributions_are_created():
    profiles = (
        make_profile("col1"),
        make_profile("col2"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    assert tuple(
        item.field_name
        for item in result.categorical_distributions
    ) == CATEGORICAL_DISTRIBUTION_FIELDS


def test_numeric_distribution_calculates_statistics():
    profiles = (
        make_profile("col1", observation_count=10),
        make_profile("col2", observation_count=20),
        make_profile("col3", observation_count=30),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_numeric_distribution(
        result,
        "observation_count",
    )

    assert distribution.observation_count == 3
    assert distribution.total == 60.0
    assert distribution.minimum == 10.0
    assert distribution.maximum == 30.0
    assert distribution.mean == 20.0
    assert math.isclose(
        distribution.standard_deviation,
        math.sqrt(200.0 / 3.0),
    )


def test_numeric_distribution_handles_float_metrics():
    profiles = (
        make_profile("col1", volatility=1.0),
        make_profile("col2", volatility=2.0),
        make_profile("col3", volatility=4.0),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_numeric_distribution(
        result,
        "volatility",
    )

    assert distribution.total == 7.0
    assert distribution.minimum == 1.0
    assert distribution.maximum == 4.0
    assert distribution.mean == 7.0 / 3.0


def test_numeric_distribution_dataclass_is_frozen():
    item = PositionBehaviorProfileNumericDistribution(
        metric_name="volatility",
        observation_count=1,
        total=1.0,
        minimum=1.0,
        maximum=1.0,
        mean=1.0,
        standard_deviation=0.0,
    )

    with pytest.raises((AttributeError, TypeError)):
        item.total = 2.0


def test_categorical_distribution_counts_values():
    profiles = (
        make_profile("col1", stability_level="STABLE"),
        make_profile("col2", stability_level="STABLE"),
        make_profile("col3", stability_level="UNSTABLE"),
        make_profile("col4", stability_level="MODERATE"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_categorical_distribution(
        result,
        "stability_level",
    )

    assert distribution.observation_count == 4

    values = {
        entry.value: (entry.count, entry.percentage)
        for entry in distribution.entries
    }

    assert values["STABLE"] == (2, 50.0)
    assert values["UNSTABLE"] == (1, 25.0)
    assert values["MODERATE"] == (1, 25.0)


def test_categorical_distribution_preserves_first_seen_order():
    profiles = (
        make_profile("col1", volatility_level="HIGH"),
        make_profile("col2", volatility_level="LOW"),
        make_profile("col3", volatility_level="HIGH"),
        make_profile("col4", volatility_level="MEDIUM"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_categorical_distribution(
        result,
        "volatility_level",
    )

    assert tuple(
        entry.value
        for entry in distribution.entries
    ) == ("HIGH", "LOW", "MEDIUM")


def test_categorical_distribution_percentages_sum_to_100():
    profiles = (
        make_profile("col1", change_direction="INCREASE"),
        make_profile("col2", change_direction="DECREASE"),
        make_profile("col3", change_direction="UNCHANGED"),
        make_profile("col4", change_direction="INCREASE"),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_categorical_distribution(
        result,
        "change_direction",
    )

    assert math.isclose(
        sum(entry.percentage for entry in distribution.entries),
        100.0,
    )


def test_categorical_distribution_supports_none_values():
    profiles = (
        make_profile("col1", dominant_digit=None),
        make_profile("col2", dominant_digit=4),
        make_profile("col3", dominant_digit=None),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_categorical_distribution(
        result,
        "dominant_digit",
    )

    values = {
        entry.value: entry.count
        for entry in distribution.entries
    }

    assert values[None] == 2
    assert values[4] == 1


def test_categorical_distribution_dataclass_is_frozen():
    item = PositionBehaviorProfileCategoricalDistribution(
        field_name="stability_level",
        observation_count=1,
        entries=(),
    )

    with pytest.raises((AttributeError, TypeError)):
        item.observation_count = 2


def test_distribution_result_is_frozen():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    with pytest.raises((AttributeError, TypeError)):
        result.profile_count = 10


def test_duplicate_positions_are_rejected():
    profiles = (
        make_profile("col1"),
        make_profile("col1"),
    )

    with pytest.raises(ValueError, match="duplicate positions"):
        build_position_behavior_profile_distribution(profiles)


def test_invalid_profile_container_is_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_distribution("invalid")


def test_invalid_profile_item_is_rejected():
    with pytest.raises(TypeError):
        build_position_behavior_profile_distribution(
            [make_profile("col1"), object()]
        )


def test_numeric_getter_returns_requested_metric():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1", volatility=7.5)]
    )

    distribution = get_numeric_distribution(
        result,
        "volatility",
    )

    assert distribution.metric_name == "volatility"
    assert distribution.mean == 7.5


def test_categorical_getter_returns_requested_field():
    result = build_position_behavior_profile_distribution(
        [
            make_profile(
                "col1",
                stability_level="MODERATE",
            )
        ]
    )

    distribution = get_categorical_distribution(
        result,
        "stability_level",
    )

    assert distribution.field_name == "stability_level"
    assert distribution.entries[0].value == "MODERATE"


def test_unknown_numeric_metric_is_rejected():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    with pytest.raises(ValueError, match="Unknown numeric distribution metric"):
        get_numeric_distribution(result, "unknown_metric")


def test_unknown_categorical_field_is_rejected():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    with pytest.raises(
        ValueError,
        match="Unknown categorical distribution field",
    ):
        get_categorical_distribution(result, "unknown_field")


def test_iter_numeric_distributions_returns_all_distributions():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    distributions = iter_numeric_distributions(result)

    assert isinstance(distributions, tuple)
    assert len(distributions) == 14


def test_iter_categorical_distributions_returns_all_distributions():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    distributions = iter_categorical_distributions(result)

    assert isinstance(distributions, tuple)
    assert len(distributions) == 5


def test_result_builder_matches_primary_builder():
    profiles = (
        make_profile("col1"),
        make_profile("col2"),
    )

    first = build_position_behavior_profile_distribution(profiles)
    second = build_position_behavior_profile_distribution_result(profiles)

    assert first == second


def test_distribution_is_descriptive_only():
    result = build_position_behavior_profile_distribution(
        [make_profile("col1")]
    )

    assert not hasattr(result, "overall_score")
    assert not hasattr(result, "best_position")
    assert not hasattr(result, "prediction")
    assert not hasattr(result, "recommended_position")


def test_numeric_distribution_uses_population_standard_deviation():
    profiles = (
        make_profile("col1", frequency_total=10),
        make_profile("col2", frequency_total=20),
    )

    result = build_position_behavior_profile_distribution(profiles)

    distribution = get_numeric_distribution(
        result,
        "frequency_total",
    )

    assert distribution.standard_deviation == 5.0