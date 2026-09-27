from __future__ import annotations

import pytest

from analytics.position_analytics_consolidation import (
    PositionAnalyticsConsolidation,
    build_position_analytics_consolidation,
    get_position_analytics_component,
    get_position_analytics_position_count,
    get_position_analytics_positions,
    iter_position_analytics_components,
)


def build_sample_consolidation() -> PositionAnalyticsConsolidation:
    return build_position_analytics_consolidation(
        positions=("col1", "col2", "col3"),
        position_frequency={"frequency": "frequency-data"},
        position_frequency_summary={"summary": "frequency-summary"},
        position_distribution={"distribution": "distribution-data"},
        position_stability={"stability": "stability-data"},
        position_behavior_profile={"profile": "behavior-profile"},
        temporal_position_analysis={"temporal": "temporal-data"},
        cross_position_relationship_overview={
            "relationships": "relationship-data"
        },
        distribution_regime_overview={
            "regimes": "regime-data"
        },
    )


def test_build_consolidation_returns_expected_type():
    result = build_sample_consolidation()

    assert isinstance(
        result,
        PositionAnalyticsConsolidation,
    )


def test_build_consolidation_preserves_positions():
    result = build_sample_consolidation()

    assert result.positions == (
        "col1",
        "col2",
        "col3",
    )

    assert result.position_count == 3


def test_build_consolidation_preserves_all_components():
    result = build_sample_consolidation()

    assert result.position_frequency == {
        "frequency": "frequency-data"
    }

    assert result.position_frequency_summary == {
        "summary": "frequency-summary"
    }

    assert result.position_distribution == {
        "distribution": "distribution-data"
    }

    assert result.position_stability == {
        "stability": "stability-data"
    }

    assert result.position_behavior_profile == {
        "profile": "behavior-profile"
    }

    assert result.temporal_position_analysis == {
        "temporal": "temporal-data"
    }

    assert result.cross_position_relationship_overview == {
        "relationships": "relationship-data"
    }

    assert result.distribution_regime_overview == {
        "regimes": "regime-data"
    }


def test_component_getter_returns_frequency():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "position_frequency",
    ) == {
        "frequency": "frequency-data"
    }


def test_component_getter_returns_frequency_summary():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "position_frequency_summary",
    ) == {
        "summary": "frequency-summary"
    }


def test_component_getter_returns_distribution():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "position_distribution",
    ) == {
        "distribution": "distribution-data"
    }


def test_component_getter_returns_stability():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "position_stability",
    ) == {
        "stability": "stability-data"
    }


def test_component_getter_returns_behavior_profile():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "position_behavior_profile",
    ) == {
        "profile": "behavior-profile"
    }


def test_component_getter_returns_temporal_analysis():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "temporal_position_analysis",
    ) == {
        "temporal": "temporal-data"
    }


def test_component_getter_returns_cross_position_overview():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "cross_position_relationship_overview",
    ) == {
        "relationships": "relationship-data"
    }


def test_component_getter_returns_distribution_regime_overview():
    result = build_sample_consolidation()

    assert get_position_analytics_component(
        result,
        "distribution_regime_overview",
    ) == {
        "regimes": "regime-data"
    }


def test_component_getter_unknown_component_raises():
    result = build_sample_consolidation()

    with pytest.raises(KeyError):
        get_position_analytics_component(
            result,
            "unknown_component",
        )


def test_iter_components_returns_all_components():
    result = build_sample_consolidation()

    components = iter_position_analytics_components(
        result
    )

    assert isinstance(components, tuple)

    assert tuple(
        name
        for name, _ in components
    ) == (
        "position_frequency",
        "position_frequency_summary",
        "position_distribution",
        "position_stability",
        "position_behavior_profile",
        "temporal_position_analysis",
        "cross_position_relationship_overview",
        "distribution_regime_overview",
    )


def test_iter_components_preserves_component_values():
    result = build_sample_consolidation()

    components = dict(
        iter_position_analytics_components(result)
    )

    assert components["position_frequency"] == {
        "frequency": "frequency-data"
    }

    assert components["position_distribution"] == {
        "distribution": "distribution-data"
    }

    assert components["position_stability"] == {
        "stability": "stability-data"
    }

    assert components["distribution_regime_overview"] == {
        "regimes": "regime-data"
    }


def test_get_positions_returns_caller_order():
    result = build_sample_consolidation()

    assert get_position_analytics_positions(
        result
    ) == (
        "col1",
        "col2",
        "col3",
    )


def test_get_position_count_returns_count():
    result = build_sample_consolidation()

    assert get_position_analytics_position_count(
        result
    ) == 3


def test_duplicate_positions_raise():
    with pytest.raises(ValueError):
        build_position_analytics_consolidation(
            positions=("col1", "col1"),
            position_frequency=None,
            position_frequency_summary=None,
            position_distribution=None,
            position_stability=None,
            position_behavior_profile=None,
            temporal_position_analysis=None,
            cross_position_relationship_overview=None,
            distribution_regime_overview=None,
        )


def test_empty_position_name_raises():
    with pytest.raises(ValueError):
        build_position_analytics_consolidation(
            positions=("col1", ""),
            position_frequency=None,
            position_frequency_summary=None,
            position_distribution=None,
            position_stability=None,
            position_behavior_profile=None,
            temporal_position_analysis=None,
            cross_position_relationship_overview=None,
            distribution_regime_overview=None,
        )


def test_non_string_position_raises():
    with pytest.raises(TypeError):
        build_position_analytics_consolidation(
            positions=("col1", 2),
            position_frequency=None,
            position_frequency_summary=None,
            position_distribution=None,
            position_stability=None,
            position_behavior_profile=None,
            temporal_position_analysis=None,
            cross_position_relationship_overview=None,
            distribution_regime_overview=None,
        )


def test_list_positions_are_normalized_to_tuple():
    result = build_position_analytics_consolidation(
        positions=["col1", "col2"],
        position_frequency=None,
        position_frequency_summary=None,
        position_distribution=None,
        position_stability=None,
        position_behavior_profile=None,
        temporal_position_analysis=None,
        cross_position_relationship_overview=None,
        distribution_regime_overview=None,
    )

    assert result.positions == (
        "col1",
        "col2",
    )

    assert isinstance(
        result.positions,
        tuple,
    )


def test_empty_positions_are_supported():
    result = build_position_analytics_consolidation(
        positions=(),
        position_frequency=None,
        position_frequency_summary=None,
        position_distribution=None,
        position_stability=None,
        position_behavior_profile=None,
        temporal_position_analysis=None,
        cross_position_relationship_overview=None,
        distribution_regime_overview=None,
    )

    assert result.position_count == 0
    assert result.positions == ()


def test_invalid_consolidation_type_for_component_getter():
    with pytest.raises(TypeError):
        get_position_analytics_component(
            "invalid",
            "position_frequency",
        )


def test_invalid_consolidation_type_for_iterator():
    with pytest.raises(TypeError):
        iter_position_analytics_components(
            "invalid",
        )


def test_invalid_consolidation_type_for_positions_getter():
    with pytest.raises(TypeError):
        get_position_analytics_positions(
            "invalid",
        )


def test_invalid_consolidation_type_for_count_getter():
    with pytest.raises(TypeError):
        get_position_analytics_position_count(
            "invalid",
        )


def test_component_objects_are_preserved_by_identity():
    frequency = object()
    summary = object()
    distribution = object()
    stability = object()
    behavior = object()
    temporal = object()
    relationships = object()
    regimes = object()

    result = build_position_analytics_consolidation(
        positions=("col1",),
        position_frequency=frequency,
        position_frequency_summary=summary,
        position_distribution=distribution,
        position_stability=stability,
        position_behavior_profile=behavior,
        temporal_position_analysis=temporal,
        cross_position_relationship_overview=relationships,
        distribution_regime_overview=regimes,
    )

    assert result.position_frequency is frequency
    assert result.position_frequency_summary is summary
    assert result.position_distribution is distribution
    assert result.position_stability is stability
    assert result.position_behavior_profile is behavior
    assert result.temporal_position_analysis is temporal
    assert (
        result.cross_position_relationship_overview
        is relationships
    )
    assert result.distribution_regime_overview is regimes