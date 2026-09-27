from __future__ import annotations

from dataclasses import dataclass

import pytest

from analytics.position_analytics_summary import (
    PositionAnalyticsSummary,
    build_position_analytics_summary,
    get_position_analytics_summary_position_count,
    get_position_analytics_summary_positions,
    get_position_analytics_summary_source,
)


@dataclass(frozen=True)
class FakeFrequency:
    total_frequency: int = 24
    total_observations: int = 12


@dataclass(frozen=True)
class FakeFrequencySummary:
    total_frequency: int = 100
    total_observations: int = 40


@dataclass(frozen=True)
class FakeDistribution:
    average_distribution_mean: float = 4.5
    average_distribution_std: float = 2.25


@dataclass(frozen=True)
class FakeStability:
    average_stability_percentage: float = 72.5


@dataclass(frozen=True)
class FakeProfile:
    change_count: int
    increase_count: int
    decrease_count: int
    unchanged_count: int
    change_magnitude: float
    trend_strength: float
    trend_consistency: float
    volatility: float
    transition_count: int


@dataclass(frozen=True)
class FakeBehaviorProfile:
    profiles: tuple[FakeProfile, ...]


@dataclass(frozen=True)
class FakeTemporal:
    observation_count: int
    change_count: int
    increase_count: int
    decrease_count: int
    unchanged_count: int


@dataclass(frozen=True)
class FakeTemporalAnalysis:
    analyses: tuple[FakeTemporal, ...]


@dataclass(frozen=True)
class FakeRelationshipOverview:
    relationship_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    insufficient_data_count: int
    average_correlation: float | None
    average_absolute_correlation: float | None


@dataclass(frozen=True)
class FakeRegimeOverview:
    total_window_count: int
    total_valid_window_count: int
    total_insufficient_window_count: int
    total_transition_count: int
    total_unchanged_count: int
    total_missing_count: int
    high_stability_count: int
    medium_stability_count: int
    low_stability_count: int
    insufficient_stability_count: int


@dataclass(frozen=True)
class FakeConsolidation:
    position_count: int
    positions: tuple[str, ...]

    position_frequency: FakeFrequency
    position_frequency_summary: FakeFrequencySummary
    position_distribution: FakeDistribution
    position_stability: FakeStability
    position_behavior_profile: FakeBehaviorProfile
    temporal_position_analysis: FakeTemporalAnalysis
    cross_position_relationship_overview: FakeRelationshipOverview
    distribution_regime_overview: FakeRegimeOverview


def make_consolidation() -> FakeConsolidation:
    return FakeConsolidation(
        position_count=3,
        positions=("col1", "col2", "col3"),
        position_frequency=FakeFrequency(
            total_frequency=24,
            total_observations=12,
        ),
        position_frequency_summary=FakeFrequencySummary(
            total_frequency=100,
            total_observations=40,
        ),
        position_distribution=FakeDistribution(
            average_distribution_mean=4.5,
            average_distribution_std=2.25,
        ),
        position_stability=FakeStability(
            average_stability_percentage=72.5,
        ),
        position_behavior_profile=FakeBehaviorProfile(
            profiles=(
                FakeProfile(
                    change_count=10,
                    increase_count=4,
                    decrease_count=3,
                    unchanged_count=3,
                    change_magnitude=2.0,
                    trend_strength=0.50,
                    trend_consistency=60.0,
                    volatility=1.5,
                    transition_count=5,
                ),
                FakeProfile(
                    change_count=8,
                    increase_count=5,
                    decrease_count=2,
                    unchanged_count=1,
                    change_magnitude=4.0,
                    trend_strength=0.70,
                    trend_consistency=80.0,
                    volatility=2.5,
                    transition_count=7,
                ),
                FakeProfile(
                    change_count=6,
                    increase_count=2,
                    decrease_count=3,
                    unchanged_count=1,
                    change_magnitude=3.0,
                    trend_strength=0.30,
                    trend_consistency=40.0,
                    volatility=3.0,
                    transition_count=4,
                ),
            )
        ),
        temporal_position_analysis=FakeTemporalAnalysis(
            analyses=(
                FakeTemporal(
                    observation_count=10,
                    change_count=8,
                    increase_count=4,
                    decrease_count=3,
                    unchanged_count=1,
                ),
                FakeTemporal(
                    observation_count=12,
                    change_count=9,
                    increase_count=5,
                    decrease_count=2,
                    unchanged_count=2,
                ),
            )
        ),
        cross_position_relationship_overview=FakeRelationshipOverview(
            relationship_count=8,
            positive_count=3,
            negative_count=2,
            neutral_count=1,
            insufficient_data_count=2,
            average_correlation=0.25,
            average_absolute_correlation=0.45,
        ),
        distribution_regime_overview=FakeRegimeOverview(
            total_window_count=40,
            total_valid_window_count=34,
            total_insufficient_window_count=6,
            total_transition_count=12,
            total_unchanged_count=18,
            total_missing_count=4,
            high_stability_count=1,
            medium_stability_count=1,
            low_stability_count=1,
            insufficient_stability_count=0,
        ),
    )


def test_build_summary_returns_expected_type():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert isinstance(
        result,
        PositionAnalyticsSummary,
    )


def test_summary_preserves_positions_and_count():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.position_count == 3
    assert result.positions == (
        "col1",
        "col2",
        "col3",
    )


def test_summary_uses_frequency_summary_totals():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.total_frequency == 100
    assert result.total_observations == 40


def test_summary_preserves_distribution_averages():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.average_distribution_mean == 4.5
    assert result.average_distribution_std == 2.25


def test_summary_preserves_stability_average():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.average_stability_percentage == 72.5


def test_summary_aggregates_behavior_profile_changes():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.total_change_count == 24
    assert result.total_increase_count == 11
    assert result.total_decrease_count == 8
    assert result.total_unchanged_count == 5


def test_summary_aggregates_behavior_profile_averages():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.average_change_magnitude == pytest.approx(3.0)
    assert result.average_trend_strength == pytest.approx(0.5)
    assert result.average_trend_consistency == pytest.approx(60.0)
    assert result.average_volatility == pytest.approx(7.0 / 3.0)


def test_summary_aggregates_transition_count():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.total_transition_count == 16


def test_summary_aggregates_temporal_analysis():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.temporal_position_count == 2
    assert result.temporal_total_observation_count == 22
    assert result.temporal_total_change_count == 17
    assert result.temporal_total_increase_count == 9
    assert result.temporal_total_decrease_count == 5
    assert result.temporal_total_unchanged_count == 3


def test_summary_preserves_relationship_metrics():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.relationship_count == 8
    assert result.relationship_positive_count == 3
    assert result.relationship_negative_count == 2
    assert result.relationship_neutral_count == 1
    assert result.relationship_insufficient_data_count == 2

    assert result.average_relationship_correlation == 0.25
    assert (
        result.average_absolute_relationship_correlation
        == 0.45
    )


def test_summary_preserves_regime_metrics():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert result.regime_window_count == 40
    assert result.regime_valid_window_count == 34
    assert result.regime_insufficient_window_count == 6

    assert result.regime_transition_count == 12
    assert result.regime_unchanged_count == 18
    assert result.regime_missing_count == 4

    assert result.high_regime_stability_count == 1
    assert result.medium_regime_stability_count == 1
    assert result.low_regime_stability_count == 1
    assert result.insufficient_regime_stability_count == 0


def test_summary_preserves_source_consolidation():
    consolidation = make_consolidation()

    result = build_position_analytics_summary(
        consolidation
    )

    assert result.source_consolidation is consolidation


def test_summary_positions_getter():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert get_position_analytics_summary_positions(
        result
    ) == (
        "col1",
        "col2",
        "col3",
    )


def test_summary_position_count_getter():
    result = build_position_analytics_summary(
        make_consolidation()
    )

    assert (
        get_position_analytics_summary_position_count(
            result
        )
        == 3
    )


def test_summary_source_getter():
    consolidation = make_consolidation()

    result = build_position_analytics_summary(
        consolidation
    )

    assert (
        get_position_analytics_summary_source(result)
        is consolidation
    )


def test_invalid_summary_getter_type_raises():
    with pytest.raises(TypeError):
        get_position_analytics_summary_positions(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_position_analytics_summary_position_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_position_analytics_summary_source(
            "invalid"
        )


def test_none_consolidation_raises():
    with pytest.raises(TypeError):
        build_position_analytics_summary(None)


def test_empty_consolidation_is_supported():
    consolidation = FakeConsolidation(
        position_count=0,
        positions=(),
        position_frequency=FakeFrequency(
            total_frequency=0,
            total_observations=0,
        ),
        position_frequency_summary=FakeFrequencySummary(
            total_frequency=0,
            total_observations=0,
        ),
        position_distribution=FakeDistribution(
            average_distribution_mean=0.0,
            average_distribution_std=0.0,
        ),
        position_stability=FakeStability(
            average_stability_percentage=0.0,
        ),
        position_behavior_profile=FakeBehaviorProfile(
            profiles=(),
        ),
        temporal_position_analysis=FakeTemporalAnalysis(
            analyses=(),
        ),
        cross_position_relationship_overview=(
            FakeRelationshipOverview(
                relationship_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                insufficient_data_count=0,
                average_correlation=None,
                average_absolute_correlation=None,
            )
        ),
        distribution_regime_overview=FakeRegimeOverview(
            total_window_count=0,
            total_valid_window_count=0,
            total_insufficient_window_count=0,
            total_transition_count=0,
            total_unchanged_count=0,
            total_missing_count=0,
            high_stability_count=0,
            medium_stability_count=0,
            low_stability_count=0,
            insufficient_stability_count=0,
        ),
    )

    result = build_position_analytics_summary(
        consolidation
    )

    assert result.position_count == 0
    assert result.positions == ()

    assert result.total_frequency == 0
    assert result.total_observations == 0

    assert result.average_distribution_mean == 0.0
    assert result.average_distribution_std == 0.0
    assert result.average_stability_percentage == 0.0

    assert result.total_change_count == 0
    assert result.total_transition_count == 0

    assert result.temporal_position_count == 0
    assert result.relationship_count == 0
    assert result.regime_window_count == 0

    assert result.average_relationship_correlation is None
    assert (
        result.average_absolute_relationship_correlation
        is None
    )


def test_missing_optional_source_attributes_use_safe_defaults():
    class MinimalConsolidation:
        position_count = 1
        positions = ("col1",)

        position_frequency = None
        position_frequency_summary = None
        position_distribution = None
        position_stability = None
        position_behavior_profile = None
        temporal_position_analysis = None
        cross_position_relationship_overview = None
        distribution_regime_overview = None

    result = build_position_analytics_summary(
        MinimalConsolidation()
    )

    assert result.position_count == 1
    assert result.positions == ("col1",)

    assert result.total_frequency == 0
    assert result.total_observations == 0

    assert result.average_distribution_mean == 0.0
    assert result.average_distribution_std == 0.0
    assert result.average_stability_percentage == 0.0

    assert result.total_change_count == 0
    assert result.total_increase_count == 0
    assert result.total_decrease_count == 0
    assert result.total_unchanged_count == 0

    assert result.average_change_magnitude == 0.0
    assert result.average_trend_strength == 0.0
    assert result.average_trend_consistency == 0.0
    assert result.average_volatility == 0.0

    assert result.total_transition_count == 0
    assert result.temporal_position_count == 0

    assert result.relationship_count == 0
    assert result.average_relationship_correlation is None
    assert (
        result.average_absolute_relationship_correlation
        is None
    )

    assert result.regime_window_count == 0
    assert result.high_regime_stability_count == 0