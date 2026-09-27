from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PositionAnalyticsConsolidation:
    """
    Consolidated descriptive container for position analytics.

    The individual analytics objects are preserved without modifying
    their underlying calculations.
    """

    position_count: int
    positions: tuple[str, ...]

    position_frequency: Any
    position_frequency_summary: Any
    position_distribution: Any
    position_stability: Any
    position_behavior_profile: Any
    temporal_position_analysis: Any
    cross_position_relationship_overview: Any
    distribution_regime_overview: Any


def _validate_positions(
    positions: tuple[str, ...],
) -> None:
    """Validate the consolidated position list."""

    if len(set(positions)) != len(positions):
        raise ValueError(
            "positions must not contain duplicates"
        )

    for position in positions:
        if not isinstance(position, str):
            raise TypeError(
                "each position must be a string"
            )

        if not position:
            raise ValueError(
                "position names must not be empty"
            )


def build_position_analytics_consolidation(
    positions: tuple[str, ...],
    position_frequency: Any,
    position_frequency_summary: Any,
    position_distribution: Any,
    position_stability: Any,
    position_behavior_profile: Any,
    temporal_position_analysis: Any,
    cross_position_relationship_overview: Any,
    distribution_regime_overview: Any,
) -> PositionAnalyticsConsolidation:
    """
    Build the consolidated position analytics container.

    This function intentionally does not recalculate or alter any
    underlying analytics result.
    """

    if not isinstance(positions, tuple):
        positions = tuple(positions)

    _validate_positions(positions)

    return PositionAnalyticsConsolidation(
        position_count=len(positions),
        positions=positions,
        position_frequency=position_frequency,
        position_frequency_summary=position_frequency_summary,
        position_distribution=position_distribution,
        position_stability=position_stability,
        position_behavior_profile=position_behavior_profile,
        temporal_position_analysis=temporal_position_analysis,
        cross_position_relationship_overview=(
            cross_position_relationship_overview
        ),
        distribution_regime_overview=(
            distribution_regime_overview
        ),
    )


def get_position_analytics_component(
    consolidation: PositionAnalyticsConsolidation,
    component_name: str,
) -> Any:
    """
    Return one named analytics component.

    Supported component names:

    - position_frequency
    - position_frequency_summary
    - position_distribution
    - position_stability
    - position_behavior_profile
    - temporal_position_analysis
    - cross_position_relationship_overview
    - distribution_regime_overview
    """

    if not isinstance(
        consolidation,
        PositionAnalyticsConsolidation,
    ):
        raise TypeError(
            "consolidation must be a "
            "PositionAnalyticsConsolidation"
        )

    supported_components = {
        "position_frequency",
        "position_frequency_summary",
        "position_distribution",
        "position_stability",
        "position_behavior_profile",
        "temporal_position_analysis",
        "cross_position_relationship_overview",
        "distribution_regime_overview",
    }

    if component_name not in supported_components:
        raise KeyError(
            f"Unknown analytics component: {component_name}"
        )

    return getattr(
        consolidation,
        component_name,
    )


def iter_position_analytics_components(
    consolidation: PositionAnalyticsConsolidation,
) -> tuple[tuple[str, Any], ...]:
    """
    Return all consolidated analytics components in stable order.
    """

    if not isinstance(
        consolidation,
        PositionAnalyticsConsolidation,
    ):
        raise TypeError(
            "consolidation must be a "
            "PositionAnalyticsConsolidation"
        )

    return (
        (
            "position_frequency",
            consolidation.position_frequency,
        ),
        (
            "position_frequency_summary",
            consolidation.position_frequency_summary,
        ),
        (
            "position_distribution",
            consolidation.position_distribution,
        ),
        (
            "position_stability",
            consolidation.position_stability,
        ),
        (
            "position_behavior_profile",
            consolidation.position_behavior_profile,
        ),
        (
            "temporal_position_analysis",
            consolidation.temporal_position_analysis,
        ),
        (
            "cross_position_relationship_overview",
            consolidation.cross_position_relationship_overview,
        ),
        (
            "distribution_regime_overview",
            consolidation.distribution_regime_overview,
        ),
    )


def get_position_analytics_positions(
    consolidation: PositionAnalyticsConsolidation,
) -> tuple[str, ...]:
    """Return consolidated positions in caller order."""

    if not isinstance(
        consolidation,
        PositionAnalyticsConsolidation,
    ):
        raise TypeError(
            "consolidation must be a "
            "PositionAnalyticsConsolidation"
        )

    return consolidation.positions


def get_position_analytics_position_count(
    consolidation: PositionAnalyticsConsolidation,
) -> int:
    """Return the number of consolidated positions."""

    if not isinstance(
        consolidation,
        PositionAnalyticsConsolidation,
    ):
        raise TypeError(
            "consolidation must be a "
            "PositionAnalyticsConsolidation"
        )

    return consolidation.position_count