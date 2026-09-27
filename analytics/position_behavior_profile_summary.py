"""Phase 9.3.52 - Position Behavior Profile Summary.

Aggregates the descriptive PositionBehaviorProfile records produced by
Phase 9.3.51. This module performs descriptive aggregation only; it does not
produce predictions, rankings, or ML scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from analytics.position_behavior_profile import (
    POSITIONS,
    PositionBehaviorProfile,
    STABILITY_LEVELS,
    VOLATILITY_LEVELS,
    CHANGE_DIRECTIONS,
    TREND_DIRECTIONS,
)


@dataclass(frozen=True)
class PositionBehaviorProfileSummary:
    """Immutable aggregate summary of supplied position behavior profiles."""

    profile_count: int
    positions: tuple[str, ...]

    total_observations: int
    total_frequency: int

    average_distribution_mean: float
    average_distribution_std: float

    average_stability_percentage: float
    stability_level_counts: tuple[tuple[str, int], ...]

    total_change_count: int
    total_increase_count: int
    total_decrease_count: int
    total_unchanged_count: int
    average_change_magnitude: float
    change_direction_counts: tuple[tuple[str, int], ...]

    average_trend_strength: float
    average_trend_consistency: float
    trend_direction_counts: tuple[tuple[str, int], ...]

    average_volatility: float
    volatility_level_counts: tuple[tuple[str, int], ...]

    total_transition_count: int


def _validate_nonnegative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_number(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    if not isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite.")


def _validate_percentage(value: float, field_name: str) -> None:
    _validate_number(value, field_name)
    if not 0 <= float(value) <= 100:
        raise ValueError(f"{field_name} must be between 0 and 100.")


def _validate_profile(profile: PositionBehaviorProfile) -> None:
    if not isinstance(profile, PositionBehaviorProfile):
        raise TypeError("Each profile must be a PositionBehaviorProfile.")

    if profile.position not in POSITIONS:
        raise ValueError(f"Invalid position: {profile.position}.")

    _validate_nonnegative_integer(profile.observation_count, "observation_count")
    _validate_nonnegative_integer(profile.frequency_total, "frequency_total")

    _validate_number(profile.distribution_mean, "distribution_mean")
    _validate_number(profile.distribution_std, "distribution_std")
    if profile.distribution_std < 0:
        raise ValueError("distribution_std must be non-negative.")

    _validate_percentage(profile.stability_percentage, "stability_percentage")
    if profile.stability_level not in STABILITY_LEVELS:
        raise ValueError("stability_level is invalid.")

    for name in (
        "change_count",
        "increase_count",
        "decrease_count",
        "unchanged_count",
        "transition_count",
    ):
        _validate_nonnegative_integer(getattr(profile, name), name)

    if (
        profile.increase_count
        + profile.decrease_count
        + profile.unchanged_count
        > profile.change_count
    ):
        raise ValueError("Change direction counts cannot exceed change_count.")

    _validate_number(profile.change_magnitude, "change_magnitude")
    if profile.change_magnitude < 0:
        raise ValueError("change_magnitude must be non-negative.")
    if profile.change_direction not in CHANGE_DIRECTIONS:
        raise ValueError("change_direction is invalid.")

    _validate_percentage(profile.trend_strength, "trend_strength")
    _validate_percentage(profile.trend_consistency, "trend_consistency")
    if profile.trend_direction not in TREND_DIRECTIONS:
        raise ValueError("trend_direction is invalid.")

    _validate_number(profile.volatility, "volatility")
    if profile.volatility < 0:
        raise ValueError("volatility must be non-negative.")
    if profile.volatility_level not in VOLATILITY_LEVELS:
        raise ValueError("volatility_level is invalid.")


def _validate_profiles(
    profiles: tuple[PositionBehaviorProfile, ...],
) -> None:
    if not isinstance(profiles, tuple):
        raise TypeError("profiles must be a tuple.")

    seen: set[str] = set()
    for profile in profiles:
        _validate_profile(profile)
        if profile.position in seen:
            raise ValueError(f"Duplicate position: {profile.position}.")
        seen.add(profile.position)


def _count_categories(
    profiles: tuple[PositionBehaviorProfile, ...],
    field_name: str,
    categories: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    counts = {category: 0 for category in categories}
    for profile in profiles:
        counts[getattr(profile, field_name)] += 1
    return tuple((category, counts[category]) for category in categories)


def _average(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def build_position_behavior_profile_summary(
    profiles: tuple[PositionBehaviorProfile, ...],
) -> PositionBehaviorProfileSummary:
    """Build a descriptive aggregate summary in caller order."""
    _validate_profiles(profiles)

    if not profiles:
        return PositionBehaviorProfileSummary(
            profile_count=0,
            positions=(),
            total_observations=0,
            total_frequency=0,
            average_distribution_mean=0.0,
            average_distribution_std=0.0,
            average_stability_percentage=0.0,
            stability_level_counts=tuple((level, 0) for level in STABILITY_LEVELS),
            total_change_count=0,
            total_increase_count=0,
            total_decrease_count=0,
            total_unchanged_count=0,
            average_change_magnitude=0.0,
            change_direction_counts=tuple((direction, 0) for direction in CHANGE_DIRECTIONS),
            average_trend_strength=0.0,
            average_trend_consistency=0.0,
            trend_direction_counts=tuple((direction, 0) for direction in TREND_DIRECTIONS),
            average_volatility=0.0,
            volatility_level_counts=tuple((level, 0) for level in VOLATILITY_LEVELS),
            total_transition_count=0,
        )

    return PositionBehaviorProfileSummary(
        profile_count=len(profiles),
        positions=tuple(profile.position for profile in profiles),
        total_observations=sum(profile.observation_count for profile in profiles),
        total_frequency=sum(profile.frequency_total for profile in profiles),
        average_distribution_mean=_average(
            tuple(profile.distribution_mean for profile in profiles)
        ),
        average_distribution_std=_average(
            tuple(profile.distribution_std for profile in profiles)
        ),
        average_stability_percentage=_average(
            tuple(profile.stability_percentage for profile in profiles)
        ),
        stability_level_counts=_count_categories(
            profiles, "stability_level", STABILITY_LEVELS
        ),
        total_change_count=sum(profile.change_count for profile in profiles),
        total_increase_count=sum(profile.increase_count for profile in profiles),
        total_decrease_count=sum(profile.decrease_count for profile in profiles),
        total_unchanged_count=sum(profile.unchanged_count for profile in profiles),
        average_change_magnitude=_average(
            tuple(profile.change_magnitude for profile in profiles)
        ),
        change_direction_counts=_count_categories(
            profiles, "change_direction", CHANGE_DIRECTIONS
        ),
        average_trend_strength=_average(
            tuple(profile.trend_strength for profile in profiles)
        ),
        average_trend_consistency=_average(
            tuple(profile.trend_consistency for profile in profiles)
        ),
        trend_direction_counts=_count_categories(
            profiles, "trend_direction", TREND_DIRECTIONS
        ),
        average_volatility=_average(
            tuple(profile.volatility for profile in profiles)
        ),
        volatility_level_counts=_count_categories(
            profiles, "volatility_level", VOLATILITY_LEVELS
        ),
        total_transition_count=sum(
            profile.transition_count for profile in profiles
        ),
    )


def build_position_behavior_profile_summary_from_iterable(
    profiles,
) -> PositionBehaviorProfileSummary:
    """Build a summary from an iterable while preserving iteration order."""
    return build_position_behavior_profile_summary(tuple(profiles))


def get_stability_level_count(
    summary: PositionBehaviorProfileSummary,
    level: str,
) -> int:
    if not isinstance(summary, PositionBehaviorProfileSummary):
        raise TypeError("summary must be a PositionBehaviorProfileSummary.")
    if level not in STABILITY_LEVELS:
        raise ValueError("Invalid stability level.")
    return dict(summary.stability_level_counts)[level]


def get_change_direction_count(
    summary: PositionBehaviorProfileSummary,
    direction: str,
) -> int:
    if not isinstance(summary, PositionBehaviorProfileSummary):
        raise TypeError("summary must be a PositionBehaviorProfileSummary.")
    if direction not in CHANGE_DIRECTIONS:
        raise ValueError("Invalid change direction.")
    return dict(summary.change_direction_counts)[direction]


def get_trend_direction_count(
    summary: PositionBehaviorProfileSummary,
    direction: str,
) -> int:
    if not isinstance(summary, PositionBehaviorProfileSummary):
        raise TypeError("summary must be a PositionBehaviorProfileSummary.")
    if direction not in TREND_DIRECTIONS:
        raise ValueError("Invalid trend direction.")
    return dict(summary.trend_direction_counts)[direction]


def get_volatility_level_count(
    summary: PositionBehaviorProfileSummary,
    level: str,
) -> int:
    if not isinstance(summary, PositionBehaviorProfileSummary):
        raise TypeError("summary must be a PositionBehaviorProfileSummary.")
    if level not in VOLATILITY_LEVELS:
        raise ValueError("Invalid volatility level.")
    return dict(summary.volatility_level_counts)[level]
