from dataclasses import dataclass
from typing import Tuple

from analytics.position_distribution_stability_trend import (
    HIGH,
    LOW,
    MEDIUM,
    MIXED,
    STABLE,
    STABILITY_DECREASING,
    STABLE_INCREASING,
)
from analytics.position_distribution_stability_trend_overview import (
    PositionDistributionStabilityTrendOverview,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransition:
    transition_index: int

    stable_increasing_percentage_start: float
    stable_increasing_percentage_end: float
    stable_increasing_percentage_change: float

    stability_decreasing_percentage_start: float
    stability_decreasing_percentage_end: float
    stability_decreasing_percentage_change: float

    stable_percentage_start: float
    stable_percentage_end: float
    stable_percentage_change: float

    mixed_percentage_start: float
    mixed_percentage_end: float
    mixed_percentage_change: float

    low_strength_percentage_start: float
    low_strength_percentage_end: float
    low_strength_percentage_change: float

    medium_strength_percentage_start: float
    medium_strength_percentage_end: float
    medium_strength_percentage_change: float

    high_strength_percentage_start: float
    high_strength_percentage_end: float
    high_strength_percentage_change: float

    total_absolute_percentage_change: float


@dataclass(frozen=True)
class PositionDistributionStabilityTrendDetail:
    summary_count: int
    transition_count: int
    transitions: Tuple[
        PositionDistributionStabilityTrendTransition,
        ...,
    ]


def _validate_overview(
    overview: PositionDistributionStabilityTrendOverview,
) -> None:
    if not isinstance(overview, PositionDistributionStabilityTrendOverview):
        raise TypeError(
            "Each item must be a PositionDistributionStabilityTrendOverview."
        )

    if overview.summary_count < 0:
        raise ValueError("summary_count must be non-negative.")

    percentage_fields = (
        "stable_increasing_percentage",
        "stability_decreasing_percentage",
        "stable_percentage",
        "mixed_percentage",
        "low_strength_percentage",
        "medium_strength_percentage",
        "high_strength_percentage",
    )

    for field_name in percentage_fields:
        value = getattr(overview, field_name)

        if value < 0 or value > 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

    direction_total = (
        overview.stable_increasing_percentage
        + overview.stability_decreasing_percentage
        + overview.stable_percentage
        + overview.mixed_percentage
    )

    strength_total = (
        overview.low_strength_percentage
        + overview.medium_strength_percentage
        + overview.high_strength_percentage
    )

    if overview.summary_count > 0:
        if abs(direction_total - 100.0) > 1e-9:
            raise ValueError(
                "Trend direction percentages must sum to 100."
            )

        if abs(strength_total - 100.0) > 1e-9:
            raise ValueError(
                "Trend strength percentages must sum to 100."
            )

    metric_fields = (
        "average_mean_absolute_percentage_change",
        "minimum_mean_absolute_percentage_change",
        "maximum_mean_absolute_percentage_change",
        "total_absolute_percentage_change",
    )

    for field_name in metric_fields:
        value = getattr(overview, field_name)

        if value < 0:
            raise ValueError(
                f"{field_name} must be non-negative."
            )

    if (
        overview.minimum_mean_absolute_percentage_change
        > overview.maximum_mean_absolute_percentage_change
    ):
        raise ValueError(
            "minimum_mean_absolute_percentage_change cannot exceed "
            "maximum_mean_absolute_percentage_change."
        )

    valid_directions = {
        STABLE_INCREASING,
        STABILITY_DECREASING,
        STABLE,
        MIXED,
    }

    valid_strengths = {
        LOW,
        MEDIUM,
        HIGH,
    }

    for direction in overview.dominant_trend_directions:
        if direction not in valid_directions:
            raise ValueError(
                f"Invalid trend direction: {direction}."
            )

    for strength in overview.dominant_trend_strengths:
        if strength not in valid_strengths:
            raise ValueError(
                f"Invalid trend strength: {strength}."
            )


def _validate_overviews(
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> None:
    if not isinstance(overviews, tuple):
        raise TypeError("overviews must be a tuple.")

    for overview in overviews:
        _validate_overview(overview)

    if not overviews:
        return

    summary_counts = {
        overview.summary_count
        for overview in overviews
    }

    if len(summary_counts) != 1:
        raise ValueError(
            "All overviews must have the same summary_count."
        )


def _calculate_change(start: float, end: float) -> float:
    return end - start


def _build_transition(
    previous: PositionDistributionStabilityTrendOverview,
    current: PositionDistributionStabilityTrendOverview,
    transition_index: int,
) -> PositionDistributionStabilityTrendTransition:
    stable_increasing_change = _calculate_change(
        previous.stable_increasing_percentage,
        current.stable_increasing_percentage,
    )

    stability_decreasing_change = _calculate_change(
        previous.stability_decreasing_percentage,
        current.stability_decreasing_percentage,
    )

    stable_change = _calculate_change(
        previous.stable_percentage,
        current.stable_percentage,
    )

    mixed_change = _calculate_change(
        previous.mixed_percentage,
        current.mixed_percentage,
    )

    low_strength_change = _calculate_change(
        previous.low_strength_percentage,
        current.low_strength_percentage,
    )

    medium_strength_change = _calculate_change(
        previous.medium_strength_percentage,
        current.medium_strength_percentage,
    )

    high_strength_change = _calculate_change(
        previous.high_strength_percentage,
        current.high_strength_percentage,
    )

    total_absolute_percentage_change = (
        abs(stable_increasing_change)
        + abs(stability_decreasing_change)
        + abs(stable_change)
        + abs(mixed_change)
        + abs(low_strength_change)
        + abs(medium_strength_change)
        + abs(high_strength_change)
    )

    return PositionDistributionStabilityTrendTransition(
        transition_index=transition_index,

        stable_increasing_percentage_start=(
            previous.stable_increasing_percentage
        ),
        stable_increasing_percentage_end=(
            current.stable_increasing_percentage
        ),
        stable_increasing_percentage_change=stable_increasing_change,

        stability_decreasing_percentage_start=(
            previous.stability_decreasing_percentage
        ),
        stability_decreasing_percentage_end=(
            current.stability_decreasing_percentage
        ),
        stability_decreasing_percentage_change=(
            stability_decreasing_change
        ),

        stable_percentage_start=previous.stable_percentage,
        stable_percentage_end=current.stable_percentage,
        stable_percentage_change=stable_change,

        mixed_percentage_start=previous.mixed_percentage,
        mixed_percentage_end=current.mixed_percentage,
        mixed_percentage_change=mixed_change,

        low_strength_percentage_start=(
            previous.low_strength_percentage
        ),
        low_strength_percentage_end=(
            current.low_strength_percentage
        ),
        low_strength_percentage_change=low_strength_change,

        medium_strength_percentage_start=(
            previous.medium_strength_percentage
        ),
        medium_strength_percentage_end=(
            current.medium_strength_percentage
        ),
        medium_strength_percentage_change=medium_strength_change,

        high_strength_percentage_start=(
            previous.high_strength_percentage
        ),
        high_strength_percentage_end=(
            current.high_strength_percentage
        ),
        high_strength_percentage_change=high_strength_change,

        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
    )


def build_position_distribution_stability_trend_detail(
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> PositionDistributionStabilityTrendDetail:
    _validate_overviews(overviews)

    if not overviews:
        return PositionDistributionStabilityTrendDetail(
            summary_count=0,
            transition_count=0,
            transitions=(),
        )

    if len(overviews) == 1:
        return PositionDistributionStabilityTrendDetail(
            summary_count=overviews[0].summary_count,
            transition_count=0,
            transitions=(),
        )

    transitions = tuple(
        _build_transition(
            previous=previous,
            current=current,
            transition_index=index,
        )
        for index, (previous, current)
        in enumerate(zip(overviews, overviews[1:]), start=1)
    )

    return PositionDistributionStabilityTrendDetail(
        summary_count=overviews[0].summary_count,
        transition_count=len(transitions),
        transitions=transitions,
    )


def get_position_distribution_stability_trend_detail(
    detail: PositionDistributionStabilityTrendDetail,
) -> PositionDistributionStabilityTrendDetail:
    if not isinstance(
        detail,
        PositionDistributionStabilityTrendDetail,
    ):
        raise TypeError(
            "detail must be a PositionDistributionStabilityTrendDetail."
        )

    return detail