"""Phase 9.3.53 - Position Behavior Profile Comparison.

Provides descriptive pairwise comparisons between Phase 9.3.51 position
behavior profiles. Comparisons preserve caller order and do not rank, score,
or predict positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite

from analytics.position_behavior_profile import (
    POSITIONS,
    PositionBehaviorProfile,
    STABILITY_LEVELS,
    CHANGE_DIRECTIONS,
    TREND_DIRECTIONS,
    VOLATILITY_LEVELS,
)


COMPARISON_NUMERIC_FIELDS: tuple[str, ...] = (
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

COMPARISON_CATEGORICAL_FIELDS: tuple[str, ...] = (
    "dominant_digit",
    "stability_level",
    "change_direction",
    "trend_direction",
    "volatility_level",
)


@dataclass(frozen=True)
class PositionBehaviorProfileMetricComparison:
    """One numeric metric comparison between two positions."""

    metric_name: str
    first_value: float
    second_value: float
    difference: float
    absolute_difference: float


@dataclass(frozen=True)
class PositionBehaviorProfileCategoricalComparison:
    """One categorical comparison between two positions."""

    field_name: str
    first_value: str | int | None
    second_value: str | int | None
    equal: bool


@dataclass(frozen=True)
class PositionBehaviorProfileComparison:
    """Immutable descriptive comparison for one position pair."""

    first_position: str
    second_position: str
    numeric_metrics: tuple[PositionBehaviorProfileMetricComparison, ...]
    categorical_metrics: tuple[PositionBehaviorProfileCategoricalComparison, ...]


@dataclass(frozen=True)
class PositionBehaviorProfileComparisonResult:
    """Immutable collection of pairwise profile comparisons."""

    profile_count: int
    comparison_count: int
    positions: tuple[str, ...]
    comparisons: tuple[PositionBehaviorProfileComparison, ...]


def _validate_number(value, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    if not isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite.")


def _validate_profile(profile: PositionBehaviorProfile) -> None:
    if not isinstance(profile, PositionBehaviorProfile):
        raise TypeError("Each profile must be a PositionBehaviorProfile.")
    if profile.position not in POSITIONS:
        raise ValueError("Invalid profile position.")

    for name in (
        "observation_count",
        "frequency_total",
        "change_count",
        "increase_count",
        "decrease_count",
        "unchanged_count",
        "transition_count",
    ):
        value = getattr(profile, name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")
        if value < 0:
            raise ValueError(f"{name} must be non-negative.")

    if profile.dominant_digit is not None and not 0 <= profile.dominant_digit <= 9:
        raise ValueError("dominant_digit must be between 0 and 9 or None.")

    for name in (
        "distribution_mean",
        "distribution_std",
        "stability_percentage",
        "change_magnitude",
        "trend_strength",
        "trend_consistency",
        "volatility",
    ):
        _validate_number(getattr(profile, name), name)

    if not 0 <= profile.stability_percentage <= 100:
        raise ValueError("stability_percentage must be between 0 and 100.")
    if profile.distribution_std < 0 or profile.change_magnitude < 0 or profile.volatility < 0:
        raise ValueError("distribution_std, change_magnitude, and volatility must be non-negative.")
    if not 0 <= profile.trend_strength <= 100 or not 0 <= profile.trend_consistency <= 100:
        raise ValueError("trend strength and consistency must be between 0 and 100.")

    if profile.stability_level not in STABILITY_LEVELS:
        raise ValueError("Invalid stability_level.")
    if profile.change_direction not in CHANGE_DIRECTIONS:
        raise ValueError("Invalid change_direction.")
    if profile.trend_direction not in TREND_DIRECTIONS:
        raise ValueError("Invalid trend_direction.")
    if profile.volatility_level not in VOLATILITY_LEVELS:
        raise ValueError("Invalid volatility_level.")

    if profile.increase_count + profile.decrease_count + profile.unchanged_count > profile.change_count:
        raise ValueError("Change direction counts cannot exceed change_count.")


def _validate_profiles(profiles: tuple[PositionBehaviorProfile, ...]) -> None:
    if not isinstance(profiles, tuple):
        raise TypeError("profiles must be a tuple.")
    seen: set[str] = set()
    for profile in profiles:
        _validate_profile(profile)
        if profile.position in seen:
            raise ValueError(f"Duplicate position: {profile.position}.")
        seen.add(profile.position)


def _build_pair(first: PositionBehaviorProfile, second: PositionBehaviorProfile) -> PositionBehaviorProfileComparison:
    numeric = tuple(
        PositionBehaviorProfileMetricComparison(
            metric_name=name,
            first_value=float(getattr(first, name)),
            second_value=float(getattr(second, name)),
            difference=float(getattr(first, name) - getattr(second, name)),
            absolute_difference=float(abs(getattr(first, name) - getattr(second, name))),
        )
        for name in COMPARISON_NUMERIC_FIELDS
    )
    categorical = tuple(
        PositionBehaviorProfileCategoricalComparison(
            field_name=name,
            first_value=getattr(first, name),
            second_value=getattr(second, name),
            equal=getattr(first, name) == getattr(second, name),
        )
        for name in COMPARISON_CATEGORICAL_FIELDS
    )
    return PositionBehaviorProfileComparison(
        first_position=first.position,
        second_position=second.position,
        numeric_metrics=numeric,
        categorical_metrics=categorical,
    )


def build_position_behavior_profile_comparison(
    first: PositionBehaviorProfile,
    second: PositionBehaviorProfile,
) -> PositionBehaviorProfileComparison:
    """Build one caller-ordered pairwise comparison."""
    _validate_profile(first)
    _validate_profile(second)
    if first.position == second.position:
        raise ValueError("A profile cannot be compared with itself.")
    return _build_pair(first, second)


def build_position_behavior_profile_comparison_result(
    profiles: tuple[PositionBehaviorProfile, ...],
) -> PositionBehaviorProfileComparisonResult:
    """Build every unique caller-ordered pair without ranking."""
    _validate_profiles(profiles)
    comparisons = tuple(
        _build_pair(first, second)
        for first, second in combinations(profiles, 2)
    )
    return PositionBehaviorProfileComparisonResult(
        profile_count=len(profiles),
        comparison_count=len(comparisons),
        positions=tuple(profile.position for profile in profiles),
        comparisons=comparisons,
    )


def build_position_behavior_profile_comparison_result_from_iterable(
    profiles,
) -> PositionBehaviorProfileComparisonResult:
    return build_position_behavior_profile_comparison_result(tuple(profiles))


def get_position_behavior_profile_comparison(
    result: PositionBehaviorProfileComparisonResult,
    first_position: str,
    second_position: str,
) -> PositionBehaviorProfileComparison | None:
    if not isinstance(result, PositionBehaviorProfileComparisonResult):
        raise TypeError("result must be a PositionBehaviorProfileComparisonResult.")
    if first_position == second_position:
        raise ValueError("Positions must be different.")
    for comparison in result.comparisons:
        if (
            comparison.first_position == first_position
            and comparison.second_position == second_position
        ):
            return comparison
    return None
