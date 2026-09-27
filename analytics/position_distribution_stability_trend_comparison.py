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
    PositionDistributionStabilityTrend,
)
from analytics.position_distribution_stability_trend_overview import (
    PositionDistributionStabilityTrendOverview,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendComparison:
    summary_count: int

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
    mean_absolute_percentage_change: float


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

    if overview.average_mean_absolute_percentage_change < 0:
        raise ValueError(
            "average_mean_absolute_percentage_change must be non-negative."
        )

    if overview.minimum_mean_absolute_percentage_change < 0:
        raise ValueError(
            "minimum_mean_absolute_percentage_change must be non-negative."
        )

    if overview.maximum_mean_absolute_percentage_change < 0:
        raise ValueError(
            "maximum_mean_absolute_percentage_change must be non-negative."
        )

    if overview.total_absolute_percentage_change < 0:
        raise ValueError(
            "total_absolute_percentage_change must be non-negative."
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


def _percentage_change(start: float, end: float) -> float:
    return end - start


def _calculate_total_absolute_percentage_change(
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> float:
    if len(overviews) < 2:
        return 0.0

    total = 0.0

    for previous, current in zip(overviews, overviews[1:]):
        total += abs(
            current.stable_increasing_percentage
            - previous.stable_increasing_percentage
        )
        total += abs(
            current.stability_decreasing_percentage
            - previous.stability_decreasing_percentage
        )
        total += abs(
            current.stable_percentage
            - previous.stable_percentage
        )
        total += abs(
            current.mixed_percentage
            - previous.mixed_percentage
        )
        total += abs(
            current.low_strength_percentage
            - previous.low_strength_percentage
        )
        total += abs(
            current.medium_strength_percentage
            - previous.medium_strength_percentage
        )
        total += abs(
            current.high_strength_percentage
            - previous.high_strength_percentage
        )

    return total


def _calculate_mean_absolute_percentage_change(
    total_absolute_percentage_change: float,
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> float:
    transition_count = len(overviews) - 1

    if transition_count <= 0:
        return 0.0

    return total_absolute_percentage_change / transition_count


def build_position_distribution_stability_trend_comparison(
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> PositionDistributionStabilityTrendComparison:
    _validate_overviews(overviews)

    if not overviews:
        return PositionDistributionStabilityTrendComparison(
            summary_count=0,

            stable_increasing_percentage_start=0.0,
            stable_increasing_percentage_end=0.0,
            stable_increasing_percentage_change=0.0,

            stability_decreasing_percentage_start=0.0,
            stability_decreasing_percentage_end=0.0,
            stability_decreasing_percentage_change=0.0,

            stable_percentage_start=0.0,
            stable_percentage_end=0.0,
            stable_percentage_change=0.0,

            mixed_percentage_start=0.0,
            mixed_percentage_end=0.0,
            mixed_percentage_change=0.0,

            low_strength_percentage_start=0.0,
            low_strength_percentage_end=0.0,
            low_strength_percentage_change=0.0,

            medium_strength_percentage_start=0.0,
            medium_strength_percentage_end=0.0,
            medium_strength_percentage_change=0.0,

            high_strength_percentage_start=0.0,
            high_strength_percentage_end=0.0,
            high_strength_percentage_change=0.0,

            total_absolute_percentage_change=0.0,
            mean_absolute_percentage_change=0.0,
        )

    first = overviews[0]
    last = overviews[-1]

    total_absolute_percentage_change = (
        _calculate_total_absolute_percentage_change(overviews)
    )

    mean_absolute_percentage_change = (
        _calculate_mean_absolute_percentage_change(
            total_absolute_percentage_change,
            overviews,
        )
    )

    return PositionDistributionStabilityTrendComparison(
        summary_count=first.summary_count,

        stable_increasing_percentage_start=(
            first.stable_increasing_percentage
        ),
        stable_increasing_percentage_end=(
            last.stable_increasing_percentage
        ),
        stable_increasing_percentage_change=_percentage_change(
            first.stable_increasing_percentage,
            last.stable_increasing_percentage,
        ),

        stability_decreasing_percentage_start=(
            first.stability_decreasing_percentage
        ),
        stability_decreasing_percentage_end=(
            last.stability_decreasing_percentage
        ),
        stability_decreasing_percentage_change=_percentage_change(
            first.stability_decreasing_percentage,
            last.stability_decreasing_percentage,
        ),

        stable_percentage_start=first.stable_percentage,
        stable_percentage_end=last.stable_percentage,
        stable_percentage_change=_percentage_change(
            first.stable_percentage,
            last.stable_percentage,
        ),

        mixed_percentage_start=first.mixed_percentage,
        mixed_percentage_end=last.mixed_percentage,
        mixed_percentage_change=_percentage_change(
            first.mixed_percentage,
            last.mixed_percentage,
        ),

        low_strength_percentage_start=first.low_strength_percentage,
        low_strength_percentage_end=last.low_strength_percentage,
        low_strength_percentage_change=_percentage_change(
            first.low_strength_percentage,
            last.low_strength_percentage,
        ),

        medium_strength_percentage_start=first.medium_strength_percentage,
        medium_strength_percentage_end=last.medium_strength_percentage,
        medium_strength_percentage_change=_percentage_change(
            first.medium_strength_percentage,
            last.medium_strength_percentage,
        ),

        high_strength_percentage_start=first.high_strength_percentage,
        high_strength_percentage_end=last.high_strength_percentage,
        high_strength_percentage_change=_percentage_change(
            first.high_strength_percentage,
            last.high_strength_percentage,
        ),

        total_absolute_percentage_change=total_absolute_percentage_change,
        mean_absolute_percentage_change=mean_absolute_percentage_change,
    )


def compare_position_distribution_stability_trends(
    overviews: Tuple[PositionDistributionStabilityTrendOverview, ...],
) -> PositionDistributionStabilityTrendComparison:
    return build_position_distribution_stability_trend_comparison(
        overviews
    )