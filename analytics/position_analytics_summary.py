from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PositionAnalyticsSummary:
    """
    Aggregate descriptive summary of position analytics.

    The source analytics objects are preserved so downstream layers
    can trace summary values back to their originating analysis.
    """

    position_count: int
    positions: tuple[str, ...]

    total_frequency: int
    total_observations: int

    average_distribution_mean: float
    average_distribution_std: float
    average_stability_percentage: float

    total_change_count: int
    total_increase_count: int
    total_decrease_count: int
    total_unchanged_count: int

    average_change_magnitude: float
    average_trend_strength: float
    average_trend_consistency: float
    average_volatility: float

    total_transition_count: int

    temporal_position_count: int
    temporal_total_observation_count: int
    temporal_total_change_count: int
    temporal_total_increase_count: int
    temporal_total_decrease_count: int
    temporal_total_unchanged_count: int

    relationship_count: int
    relationship_positive_count: int
    relationship_negative_count: int
    relationship_neutral_count: int
    relationship_insufficient_data_count: int

    average_relationship_correlation: float | None
    average_absolute_relationship_correlation: float | None

    regime_window_count: int
    regime_valid_window_count: int
    regime_insufficient_window_count: int
    regime_transition_count: int
    regime_unchanged_count: int
    regime_missing_count: int

    high_regime_stability_count: int
    medium_regime_stability_count: int
    low_regime_stability_count: int
    insufficient_regime_stability_count: int

    source_consolidation: Any


def _read_value(
    obj: Any,
    attribute: str,
    default: Any = None,
) -> Any:
    """Read an attribute safely from a source analytics object."""

    return getattr(obj, attribute, default)


def _average(values: list[float]) -> float:
    """Calculate an arithmetic mean."""

    if not values:
        return 0.0

    return sum(values) / len(values)


def _average_optional(
    values: list[float | None],
) -> float | None:
    """Calculate a mean while excluding missing values."""

    valid_values = [
        value
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return sum(valid_values) / len(valid_values)


def _extract_position_profiles(
    consolidation: Any,
) -> tuple[Any, ...]:
    """Extract position behavior profiles from consolidation."""

    profile_result = _read_value(
        consolidation,
        "position_behavior_profile",
    )

    profiles = _read_value(
        profile_result,
        "profiles",
        (),
    )

    return tuple(profiles)


def _extract_temporal_analyses(
    consolidation: Any,
) -> tuple[Any, ...]:
    """Extract temporal position analyses."""

    temporal_result = _read_value(
        consolidation,
        "temporal_position_analysis",
    )

    analyses = _read_value(
        temporal_result,
        "analyses",
        (),
    )

    if not analyses:
        analyses = _read_value(
            temporal_result,
            "results",
            (),
        )

    return tuple(analyses)


def _extract_relationship_overview(
    consolidation: Any,
) -> Any:
    """Extract cross-position relationship overview."""

    return _read_value(
        consolidation,
        "cross_position_relationship_overview",
    )


def _extract_regime_overview(
    consolidation: Any,
) -> Any:
    """Extract distribution-regime overview."""

    return _read_value(
        consolidation,
        "distribution_regime_overview",
    )


def build_position_analytics_summary(
    consolidation: Any,
) -> PositionAnalyticsSummary:
    """
    Build an aggregate descriptive summary from the consolidated
    position analytics object.

    Missing optional source attributes are treated as unavailable
    descriptive information rather than fabricated values.
    """

    if consolidation is None:
        raise TypeError(
            "consolidation must be a position analytics "
            "consolidation object"
        )

    positions = tuple(
        _read_value(
            consolidation,
            "positions",
            (),
        )
    )

    position_count = int(
        _read_value(
            consolidation,
            "position_count",
            len(positions),
        )
    )

    frequency_result = _read_value(
        consolidation,
        "position_frequency",
    )

    frequency_summary = _read_value(
        consolidation,
        "position_frequency_summary",
    )

    distribution_result = _read_value(
        consolidation,
        "position_distribution",
    )

    stability_result = _read_value(
        consolidation,
        "position_stability",
    )

    profile_objects = _extract_position_profiles(
        consolidation
    )

    temporal_objects = _extract_temporal_analyses(
        consolidation
    )

    relationship_overview = _extract_relationship_overview(
        consolidation
    )

    regime_overview = _extract_regime_overview(
        consolidation
    )

    total_frequency = int(
        _read_value(
            frequency_summary,
            "total_frequency",
            _read_value(
                frequency_result,
                "total_frequency",
                0,
            ),
        )
        or 0
    )

    total_observations = int(
        _read_value(
            frequency_summary,
            "total_observations",
            _read_value(
                frequency_result,
                "total_observations",
                0,
            ),
        )
        or 0
    )

    distribution_means = [
        float(value)
        for value in (
            _read_value(
                distribution_result,
                "distribution_means",
                (),
            )
            or ()
        )
    ]

    distribution_stds = [
        float(value)
        for value in (
            _read_value(
                distribution_result,
                "distribution_stds",
                (),
            )
            or ()
        )
    ]

    stability_percentages = [
        float(value)
        for value in (
            _read_value(
                stability_result,
                "stability_percentages",
                (),
            )
            or ()
        )
    ]

    average_distribution_mean = (
        _read_value(
            distribution_result,
            "average_distribution_mean",
            None,
        )
    )

    if average_distribution_mean is None:
        average_distribution_mean = _average(
            distribution_means
        )

    average_distribution_std = _read_value(
        distribution_result,
        "average_distribution_std",
        None,
    )

    if average_distribution_std is None:
        average_distribution_std = _average(
            distribution_stds
        )

    average_stability_percentage = _read_value(
        stability_result,
        "average_stability_percentage",
        None,
    )

    if average_stability_percentage is None:
        average_stability_percentage = _average(
            stability_percentages
        )

    total_change_count = sum(
        int(_read_value(profile, "change_count", 0) or 0)
        for profile in profile_objects
    )

    total_increase_count = sum(
        int(_read_value(profile, "increase_count", 0) or 0)
        for profile in profile_objects
    )

    total_decrease_count = sum(
        int(_read_value(profile, "decrease_count", 0) or 0)
        for profile in profile_objects
    )

    total_unchanged_count = sum(
        int(_read_value(profile, "unchanged_count", 0) or 0)
        for profile in profile_objects
    )

    average_change_magnitude = _average(
        [
            float(
                _read_value(
                    profile,
                    "change_magnitude",
                    0.0,
                )
                or 0.0
            )
            for profile in profile_objects
        ]
    )

    average_trend_strength = _average(
        [
            float(
                _read_value(
                    profile,
                    "trend_strength",
                    0.0,
                )
                or 0.0
            )
            for profile in profile_objects
        ]
    )

    average_trend_consistency = _average(
        [
            float(
                _read_value(
                    profile,
                    "trend_consistency",
                    0.0,
                )
                or 0.0
            )
            for profile in profile_objects
        ]
    )

    average_volatility = _average(
        [
            float(
                _read_value(
                    profile,
                    "volatility",
                    0.0,
                )
                or 0.0
            )
            for profile in profile_objects
        ]
    )

    total_transition_count = sum(
        int(
            _read_value(
                profile,
                "transition_count",
                0,
            )
            or 0
        )
        for profile in profile_objects
    )

    temporal_position_count = len(temporal_objects)

    temporal_total_observation_count = sum(
        int(
            _read_value(
                item,
                "observation_count",
                0,
            )
            or 0
        )
        for item in temporal_objects
    )

    temporal_total_change_count = sum(
        int(
            _read_value(
                item,
                "change_count",
                0,
            )
            or 0
        )
        for item in temporal_objects
    )

    temporal_total_increase_count = sum(
        int(
            _read_value(
                item,
                "increase_count",
                0,
            )
            or 0
        )
        for item in temporal_objects
    )

    temporal_total_decrease_count = sum(
        int(
            _read_value(
                item,
                "decrease_count",
                0,
            )
            or 0
        )
        for item in temporal_objects
    )

    temporal_total_unchanged_count = sum(
        int(
            _read_value(
                item,
                "unchanged_count",
                0,
            )
            or 0
        )
        for item in temporal_objects
    )

    relationship_count = int(
        _read_value(
            relationship_overview,
            "relationship_count",
            0,
        )
        or 0
    )

    relationship_positive_count = int(
        _read_value(
            relationship_overview,
            "positive_count",
            0,
        )
        or 0
    )

    relationship_negative_count = int(
        _read_value(
            relationship_overview,
            "negative_count",
            0,
        )
        or 0
    )

    relationship_neutral_count = int(
        _read_value(
            relationship_overview,
            "neutral_count",
            0,
        )
        or 0
    )

    relationship_insufficient_data_count = int(
        _read_value(
            relationship_overview,
            "insufficient_data_count",
            0,
        )
        or 0
    )

    average_relationship_correlation = _read_value(
        relationship_overview,
        "average_correlation",
        None,
    )

    average_absolute_relationship_correlation = _read_value(
        relationship_overview,
        "average_absolute_correlation",
        None,
    )

    regime_window_count = int(
        _read_value(
            regime_overview,
            "total_window_count",
            0,
        )
        or 0
    )

    regime_valid_window_count = int(
        _read_value(
            regime_overview,
            "total_valid_window_count",
            0,
        )
        or 0
    )

    regime_insufficient_window_count = int(
        _read_value(
            regime_overview,
            "total_insufficient_window_count",
            0,
        )
        or 0
    )

    regime_transition_count = int(
        _read_value(
            regime_overview,
            "total_transition_count",
            0,
        )
        or 0
    )

    regime_unchanged_count = int(
        _read_value(
            regime_overview,
            "total_unchanged_count",
            0,
        )
        or 0
    )

    regime_missing_count = int(
        _read_value(
            regime_overview,
            "total_missing_count",
            0,
        )
        or 0
    )

    high_regime_stability_count = int(
        _read_value(
            regime_overview,
            "high_stability_count",
            0,
        )
        or 0
    )

    medium_regime_stability_count = int(
        _read_value(
            regime_overview,
            "medium_stability_count",
            0,
        )
        or 0
    )

    low_regime_stability_count = int(
        _read_value(
            regime_overview,
            "low_stability_count",
            0,
        )
        or 0
    )

    insufficient_regime_stability_count = int(
        _read_value(
            regime_overview,
            "insufficient_stability_count",
            0,
        )
        or 0
    )

    return PositionAnalyticsSummary(
        position_count=position_count,
        positions=positions,
        total_frequency=total_frequency,
        total_observations=total_observations,
        average_distribution_mean=float(
            average_distribution_mean
        ),
        average_distribution_std=float(
            average_distribution_std
        ),
        average_stability_percentage=float(
            average_stability_percentage
        ),
        total_change_count=total_change_count,
        total_increase_count=total_increase_count,
        total_decrease_count=total_decrease_count,
        total_unchanged_count=total_unchanged_count,
        average_change_magnitude=average_change_magnitude,
        average_trend_strength=average_trend_strength,
        average_trend_consistency=average_trend_consistency,
        average_volatility=average_volatility,
        total_transition_count=total_transition_count,
        temporal_position_count=temporal_position_count,
        temporal_total_observation_count=(
            temporal_total_observation_count
        ),
        temporal_total_change_count=(
            temporal_total_change_count
        ),
        temporal_total_increase_count=(
            temporal_total_increase_count
        ),
        temporal_total_decrease_count=(
            temporal_total_decrease_count
        ),
        temporal_total_unchanged_count=(
            temporal_total_unchanged_count
        ),
        relationship_count=relationship_count,
        relationship_positive_count=(
            relationship_positive_count
        ),
        relationship_negative_count=(
            relationship_negative_count
        ),
        relationship_neutral_count=(
            relationship_neutral_count
        ),
        relationship_insufficient_data_count=(
            relationship_insufficient_data_count
        ),
        average_relationship_correlation=(
            average_relationship_correlation
        ),
        average_absolute_relationship_correlation=(
            average_absolute_relationship_correlation
        ),
        regime_window_count=regime_window_count,
        regime_valid_window_count=(
            regime_valid_window_count
        ),
        regime_insufficient_window_count=(
            regime_insufficient_window_count
        ),
        regime_transition_count=(
            regime_transition_count
        ),
        regime_unchanged_count=(
            regime_unchanged_count
        ),
        regime_missing_count=regime_missing_count,
        high_regime_stability_count=(
            high_regime_stability_count
        ),
        medium_regime_stability_count=(
            medium_regime_stability_count
        ),
        low_regime_stability_count=(
            low_regime_stability_count
        ),
        insufficient_regime_stability_count=(
            insufficient_regime_stability_count
        ),
        source_consolidation=consolidation,
    )


def get_position_analytics_summary_positions(
    summary: PositionAnalyticsSummary,
) -> tuple[str, ...]:
    """Return positions from the aggregate summary."""

    if not isinstance(
        summary,
        PositionAnalyticsSummary,
    ):
        raise TypeError(
            "summary must be a PositionAnalyticsSummary"
        )

    return summary.positions


def get_position_analytics_summary_position_count(
    summary: PositionAnalyticsSummary,
) -> int:
    """Return the number of positions."""

    if not isinstance(
        summary,
        PositionAnalyticsSummary,
    ):
        raise TypeError(
            "summary must be a PositionAnalyticsSummary"
        )

    return summary.position_count


def get_position_analytics_summary_source(
    summary: PositionAnalyticsSummary,
) -> Any:
    """Return the source consolidation object."""

    if not isinstance(
        summary,
        PositionAnalyticsSummary,
    ):
        raise TypeError(
            "summary must be a PositionAnalyticsSummary"
        )

    return summary.source_consolidation