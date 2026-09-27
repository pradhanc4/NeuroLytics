from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from analytics.position_behavior_profile import PositionBehaviorProfile


NUMERIC_DISTRIBUTION_METRICS: tuple[str, ...] = (
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

CATEGORICAL_DISTRIBUTION_FIELDS: tuple[str, ...] = (
    "dominant_digit",
    "stability_level",
    "change_direction",
    "trend_direction",
    "volatility_level",
)


@dataclass(frozen=True)
class PositionBehaviorProfileNumericDistribution:
    metric_name: str
    observation_count: int
    total: float
    minimum: float
    maximum: float
    mean: float
    standard_deviation: float


@dataclass(frozen=True)
class PositionBehaviorProfileCategoricalDistributionEntry:
    field_name: str
    value: str | int | None
    count: int
    percentage: float


@dataclass(frozen=True)
class PositionBehaviorProfileCategoricalDistribution:
    field_name: str
    observation_count: int
    entries: tuple[
        PositionBehaviorProfileCategoricalDistributionEntry, ...
    ]


@dataclass(frozen=True)
class PositionBehaviorProfileDistribution:
    profile_count: int
    positions: tuple[str, ...]
    numeric_distributions: tuple[
        PositionBehaviorProfileNumericDistribution, ...
    ]
    categorical_distributions: tuple[
        PositionBehaviorProfileCategoricalDistribution, ...
    ]


def _validate_profile(profile: PositionBehaviorProfile) -> None:
    if not isinstance(profile, PositionBehaviorProfile):
        raise TypeError(
            "profiles must contain only PositionBehaviorProfile instances"
        )


def _validate_profiles(
    profiles: Iterable[PositionBehaviorProfile],
) -> tuple[PositionBehaviorProfile, ...]:
    if isinstance(profiles, (str, bytes)):
        raise TypeError("profiles must be an iterable of PositionBehaviorProfile")

    try:
        materialized = tuple(profiles)
    except TypeError as exc:
        raise TypeError(
            "profiles must be an iterable of PositionBehaviorProfile"
        ) from exc

    for profile in materialized:
        _validate_profile(profile)

    positions = [profile.position for profile in materialized]

    if len(set(positions)) != len(positions):
        raise ValueError("profiles must not contain duplicate positions")

    return materialized


def _numeric_values(
    profiles: tuple[PositionBehaviorProfile, ...],
    metric_name: str,
) -> tuple[float, ...]:
    return tuple(
        float(getattr(profile, metric_name))
        for profile in profiles
    )


def _population_standard_deviation(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return sqrt(variance)


def _build_numeric_distribution(
    profiles: tuple[PositionBehaviorProfile, ...],
    metric_name: str,
) -> PositionBehaviorProfileNumericDistribution:
    values = _numeric_values(profiles, metric_name)

    if not values:
        return PositionBehaviorProfileNumericDistribution(
            metric_name=metric_name,
            observation_count=0,
            total=0.0,
            minimum=0.0,
            maximum=0.0,
            mean=0.0,
            standard_deviation=0.0,
        )

    total = sum(values)
    mean = total / len(values)

    return PositionBehaviorProfileNumericDistribution(
        metric_name=metric_name,
        observation_count=len(values),
        total=total,
        minimum=min(values),
        maximum=max(values),
        mean=mean,
        standard_deviation=_population_standard_deviation(values),
    )


def _build_categorical_distribution(
    profiles: tuple[PositionBehaviorProfile, ...],
    field_name: str,
) -> PositionBehaviorProfileCategoricalDistribution:
    counts: dict[str | int | None, int] = {}
    ordered_values: list[str | int | None] = []

    for profile in profiles:
        value = getattr(profile, field_name)

        if value not in counts:
            counts[value] = 0
            ordered_values.append(value)

        counts[value] += 1

    observation_count = len(profiles)

    entries = tuple(
        PositionBehaviorProfileCategoricalDistributionEntry(
            field_name=field_name,
            value=value,
            count=counts[value],
            percentage=(
                (counts[value] / observation_count) * 100.0
                if observation_count
                else 0.0
            ),
        )
        for value in ordered_values
    )

    return PositionBehaviorProfileCategoricalDistribution(
        field_name=field_name,
        observation_count=observation_count,
        entries=entries,
    )


def build_position_behavior_profile_distribution(
    profiles: Iterable[PositionBehaviorProfile],
) -> PositionBehaviorProfileDistribution:
    materialized = _validate_profiles(profiles)

    positions = tuple(
        profile.position
        for profile in materialized
    )

    numeric_distributions = tuple(
        _build_numeric_distribution(
            materialized,
            metric_name,
        )
        for metric_name in NUMERIC_DISTRIBUTION_METRICS
    )

    categorical_distributions = tuple(
        _build_categorical_distribution(
            materialized,
            field_name,
        )
        for field_name in CATEGORICAL_DISTRIBUTION_FIELDS
    )

    return PositionBehaviorProfileDistribution(
        profile_count=len(materialized),
        positions=positions,
        numeric_distributions=numeric_distributions,
        categorical_distributions=categorical_distributions,
    )


def build_position_behavior_profile_distribution_result(
    profiles: Iterable[PositionBehaviorProfile],
) -> PositionBehaviorProfileDistribution:
    return build_position_behavior_profile_distribution(profiles)


def get_numeric_distribution(
    result: PositionBehaviorProfileDistribution,
    metric_name: str,
) -> PositionBehaviorProfileNumericDistribution:
    if not isinstance(result, PositionBehaviorProfileDistribution):
        raise TypeError(
            "result must be a PositionBehaviorProfileDistribution"
        )

    if metric_name not in NUMERIC_DISTRIBUTION_METRICS:
        raise ValueError(
            f"Unknown numeric distribution metric: {metric_name}"
        )

    for distribution in result.numeric_distributions:
        if distribution.metric_name == metric_name:
            return distribution

    raise ValueError(
        f"Numeric distribution not found: {metric_name}"
    )


def get_categorical_distribution(
    result: PositionBehaviorProfileDistribution,
    field_name: str,
) -> PositionBehaviorProfileCategoricalDistribution:
    if not isinstance(result, PositionBehaviorProfileDistribution):
        raise TypeError(
            "result must be a PositionBehaviorProfileDistribution"
        )

    if field_name not in CATEGORICAL_DISTRIBUTION_FIELDS:
        raise ValueError(
            f"Unknown categorical distribution field: {field_name}"
        )

    for distribution in result.categorical_distributions:
        if distribution.field_name == field_name:
            return distribution

    raise ValueError(
        f"Categorical distribution not found: {field_name}"
    )


def iter_numeric_distributions(
    result: PositionBehaviorProfileDistribution,
) -> tuple[PositionBehaviorProfileNumericDistribution, ...]:
    if not isinstance(result, PositionBehaviorProfileDistribution):
        raise TypeError(
            "result must be a PositionBehaviorProfileDistribution"
        )

    return result.numeric_distributions


def iter_categorical_distributions(
    result: PositionBehaviorProfileDistribution,
) -> tuple[PositionBehaviorProfileCategoricalDistribution, ...]:
    if not isinstance(result, PositionBehaviorProfileDistribution):
        raise TypeError(
            "result must be a PositionBehaviorProfileDistribution"
        )

    return result.categorical_distributions