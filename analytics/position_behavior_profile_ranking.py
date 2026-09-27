"""Phase 9.3.54 - Position Behavior Profile Ranking.

Provides metric-specific descriptive ordering of PositionBehaviorProfile
records. This module does not create an overall score, prediction, or
"best position" conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from analytics.position_behavior_profile import PositionBehaviorProfile, POSITIONS


RANKABLE_METRICS: tuple[str, ...] = (
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


@dataclass(frozen=True)
class PositionBehaviorProfileRankEntry:
    """One descriptive metric-order entry."""

    position: str
    metric_name: str
    metric_value: float
    rank: int


@dataclass(frozen=True)
class PositionBehaviorProfileRanking:
    """Immutable metric-specific descriptive ranking."""

    metric_name: str
    entries: tuple[PositionBehaviorProfileRankEntry, ...]
    tied_rank_policy: str


@dataclass(frozen=True)
class PositionBehaviorProfileRankingResult:
    """Immutable collection of metric-specific rankings."""

    profile_count: int
    positions: tuple[str, ...]
    rankings: tuple[PositionBehaviorProfileRanking, ...]


def _validate_profile(profile: PositionBehaviorProfile) -> None:
    if not isinstance(profile, PositionBehaviorProfile):
        raise TypeError("Each profile must be a PositionBehaviorProfile.")
    if profile.position not in POSITIONS:
        raise ValueError("Invalid profile position.")
    for name in RANKABLE_METRICS:
        value = getattr(profile, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")
        if not isfinite(float(value)):
            raise ValueError(f"{name} must be finite.")


def _validate_profiles(profiles: tuple[PositionBehaviorProfile, ...]) -> None:
    if not isinstance(profiles, tuple):
        raise TypeError("profiles must be a tuple.")
    seen: set[str] = set()
    for profile in profiles:
        _validate_profile(profile)
        if profile.position in seen:
            raise ValueError(f"Duplicate position: {profile.position}.")
        seen.add(profile.position)


def _rank_metric(
    profiles: tuple[PositionBehaviorProfile, ...],
    metric_name: str,
) -> PositionBehaviorProfileRanking:
    if metric_name not in RANKABLE_METRICS:
        raise ValueError("metric_name is not rankable.")

    # Descending descriptive order. Equal values share the same competition
    # rank (1, 1, 3), and original caller order breaks display ties.
    ordered = sorted(
        enumerate(profiles),
        key=lambda item: (-float(getattr(item[1], metric_name)), item[0]),
    )

    entries: list[PositionBehaviorProfileRankEntry] = []
    previous_value: float | None = None
    previous_rank = 0

    for index, (_, profile) in enumerate(ordered, start=1):
        value = float(getattr(profile, metric_name))
        if previous_value is None or value != previous_value:
            previous_rank = index
        entries.append(
            PositionBehaviorProfileRankEntry(
                position=profile.position,
                metric_name=metric_name,
                metric_value=value,
                rank=previous_rank,
            )
        )
        previous_value = value

    return PositionBehaviorProfileRanking(
        metric_name=metric_name,
        entries=tuple(entries),
        tied_rank_policy="competition_rank_descending;caller_order_for_equal_values",
    )


def build_position_behavior_profile_ranking(
    profiles: tuple[PositionBehaviorProfile, ...],
    metric_name: str,
) -> PositionBehaviorProfileRanking:
    """Build one metric-specific descriptive ranking."""
    _validate_profiles(profiles)
    return _rank_metric(profiles, metric_name)


def build_position_behavior_profile_ranking_result(
    profiles: tuple[PositionBehaviorProfile, ...],
    metric_names: tuple[str, ...] = RANKABLE_METRICS,
) -> PositionBehaviorProfileRankingResult:
    """Build metric-specific rankings without combining metrics."""
    _validate_profiles(profiles)

    if not isinstance(metric_names, tuple):
        raise TypeError("metric_names must be a tuple.")

    for name in metric_names:
        if name not in RANKABLE_METRICS:
            raise ValueError(f"Unsupported ranking metric: {name}.")

    rankings = tuple(
        _rank_metric(profiles, metric_name) for metric_name in metric_names
    )

    return PositionBehaviorProfileRankingResult(
        profile_count=len(profiles),
        positions=tuple(profile.position for profile in profiles),
        rankings=rankings,
    )


def build_position_behavior_profile_ranking_result_from_iterable(
    profiles,
    metric_names: tuple[str, ...] = RANKABLE_METRICS,
) -> PositionBehaviorProfileRankingResult:
    return build_position_behavior_profile_ranking_result(
        tuple(profiles), metric_names
    )


def get_position_behavior_profile_ranking(
    result: PositionBehaviorProfileRankingResult,
    metric_name: str,
) -> PositionBehaviorProfileRanking | None:
    if not isinstance(result, PositionBehaviorProfileRankingResult):
        raise TypeError("result must be a PositionBehaviorProfileRankingResult.")
    for ranking in result.rankings:
        if ranking.metric_name == metric_name:
            return ranking
    return None
