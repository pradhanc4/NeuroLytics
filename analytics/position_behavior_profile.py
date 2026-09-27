"""Phase 9.3.51 - Position Behavior Profile.

Consolidates established descriptive position-level metrics into one immutable
behavior profile per position.

This module does not calculate predictions, rankings, or ML outputs. It accepts
already-computed descriptive metrics and preserves caller-provided values.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

POSITIONS: tuple[str, ...] = (
    "col1", "col2", "col3", "col4",
    "col5", "col6", "col7", "col8",
)

STABILITY_LEVELS = ("STABLE", "MODERATE", "UNSTABLE")
CHANGE_DIRECTIONS = ("INCREASE", "DECREASE", "UNCHANGED")
TREND_DIRECTIONS = ("INCREASE", "DECREASE", "UNCHANGED")
VOLATILITY_LEVELS = ("LOW", "MEDIUM", "HIGH")


@dataclass(frozen=True)
class PositionBehaviorProfile:
    """Immutable descriptive profile for one position."""

    position: str
    observation_count: int

    frequency_total: int
    dominant_digit: int | None

    distribution_mean: float
    distribution_std: float

    stability_percentage: float
    stability_level: str

    change_count: int
    increase_count: int
    decrease_count: int
    unchanged_count: int
    change_magnitude: float
    change_direction: str

    trend_direction: str
    trend_strength: float
    trend_consistency: float

    volatility: float
    volatility_level: str

    transition_count: int


@dataclass(frozen=True)
class PositionBehaviorProfileResult:
    """Immutable collection of position behavior profiles."""

    profile_count: int
    profiles: tuple[PositionBehaviorProfile, ...]


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError("position must be a string.")
    if position not in POSITIONS:
        raise ValueError(f"position must be one of {POSITIONS}.")


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


def _validate_digit(value: int | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None.")
    if not 0 <= value <= 9:
        raise ValueError(f"{field_name} must be between 0 and 9.")


def validate_position_behavior_profile(profile: PositionBehaviorProfile) -> None:
    """Validate one Phase 9.3.51 profile."""
    if not isinstance(profile, PositionBehaviorProfile):
        raise TypeError("profile must be a PositionBehaviorProfile.")

    _validate_position(profile.position)
    _validate_nonnegative_integer(profile.observation_count, "observation_count")
    _validate_nonnegative_integer(profile.frequency_total, "frequency_total")
    _validate_digit(profile.dominant_digit, "dominant_digit")

    _validate_number(profile.distribution_mean, "distribution_mean")
    _validate_number(profile.distribution_std, "distribution_std")
    if profile.distribution_std < 0:
        raise ValueError("distribution_std must be non-negative.")

    _validate_percentage(profile.stability_percentage, "stability_percentage")
    if profile.stability_level not in STABILITY_LEVELS:
        raise ValueError("stability_level is invalid.")

    _validate_nonnegative_integer(profile.change_count, "change_count")
    _validate_nonnegative_integer(profile.increase_count, "increase_count")
    _validate_nonnegative_integer(profile.decrease_count, "decrease_count")
    _validate_nonnegative_integer(profile.unchanged_count, "unchanged_count")
    _validate_number(profile.change_magnitude, "change_magnitude")
    if profile.change_magnitude < 0:
        raise ValueError("change_magnitude must be non-negative.")
    if profile.change_direction not in CHANGE_DIRECTIONS:
        raise ValueError("change_direction is invalid.")

    _validate_direction(profile.trend_direction, "trend_direction")
    _validate_percentage(profile.trend_strength, "trend_strength")
    _validate_percentage(profile.trend_consistency, "trend_consistency")

    _validate_number(profile.volatility, "volatility")
    if profile.volatility < 0:
        raise ValueError("volatility must be non-negative.")
    if profile.volatility_level not in VOLATILITY_LEVELS:
        raise ValueError("volatility_level is invalid.")

    _validate_nonnegative_integer(profile.transition_count, "transition_count")

    if profile.increase_count + profile.decrease_count + profile.unchanged_count > profile.change_count:
        raise ValueError("change direction counts cannot exceed change_count.")


def _validate_direction(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if value not in TREND_DIRECTIONS:
        raise ValueError(f"{field_name} is invalid.")


def build_position_behavior_profile(
    *,
    position: str,
    observation_count: int,
    frequency_total: int,
    dominant_digit: int | None,
    distribution_mean: float,
    distribution_std: float,
    stability_percentage: float,
    stability_level: str,
    change_count: int,
    increase_count: int,
    decrease_count: int,
    unchanged_count: int,
    change_magnitude: float,
    change_direction: str,
    trend_direction: str,
    trend_strength: float,
    trend_consistency: float,
    volatility: float,
    volatility_level: str,
    transition_count: int,
) -> PositionBehaviorProfile:
    """Build and validate one descriptive position profile."""
    profile = PositionBehaviorProfile(
        position=position,
        observation_count=observation_count,
        frequency_total=frequency_total,
        dominant_digit=dominant_digit,
        distribution_mean=float(distribution_mean),
        distribution_std=float(distribution_std),
        stability_percentage=float(stability_percentage),
        stability_level=stability_level,
        change_count=change_count,
        increase_count=increase_count,
        decrease_count=decrease_count,
        unchanged_count=unchanged_count,
        change_magnitude=float(change_magnitude),
        change_direction=change_direction,
        trend_direction=trend_direction,
        trend_strength=float(trend_strength),
        trend_consistency=float(trend_consistency),
        volatility=float(volatility),
        volatility_level=volatility_level,
        transition_count=transition_count,
    )
    validate_position_behavior_profile(profile)
    return profile


def build_position_behavior_profile_result(
    profiles: tuple[PositionBehaviorProfile, ...],
) -> PositionBehaviorProfileResult:
    """Build a validated profile collection in caller order."""
    if not isinstance(profiles, tuple):
        raise TypeError("profiles must be a tuple.")

    seen: set[str] = set()
    for profile in profiles:
        validate_position_behavior_profile(profile)
        if profile.position in seen:
            raise ValueError(f"Duplicate position: {profile.position}.")
        seen.add(profile.position)

    return PositionBehaviorProfileResult(
        profile_count=len(profiles),
        profiles=profiles,
    )


def build_position_behavior_profile_result_from_iterable(
    profiles: Iterable[PositionBehaviorProfile],
) -> PositionBehaviorProfileResult:
    """Build a result from any iterable while preserving iteration order."""
    return build_position_behavior_profile_result(tuple(profiles))


def get_position_behavior_profile(
    result: PositionBehaviorProfileResult,
    position: str,
) -> PositionBehaviorProfile | None:
    """Return a profile by position, or None when absent."""
    if not isinstance(result, PositionBehaviorProfileResult):
        raise TypeError("result must be a PositionBehaviorProfileResult.")
    _validate_position(position)

    for profile in result.profiles:
        if profile.position == position:
            return profile
    return None
