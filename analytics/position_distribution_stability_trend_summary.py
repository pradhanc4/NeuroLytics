from dataclasses import dataclass

from analytics.position_distribution_stability_trend import (
    HIGH,
    LOW,
    MEDIUM,
    MIXED,
    STABLE,
    STABLE_INCREASING,
    STABILITY_DECREASING,
    PositionDistributionStabilityTrend,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendSummary:
    trend_count: int

    stable_increasing_count: int
    stability_decreasing_count: int
    stable_count: int
    mixed_count: int

    low_strength_count: int
    medium_strength_count: int
    high_strength_count: int

    average_mean_absolute_percentage_change: float
    minimum_mean_absolute_percentage_change: float
    maximum_mean_absolute_percentage_change: float

    total_absolute_percentage_change: float

    trends: tuple[PositionDistributionStabilityTrend, ...]


def _validate_trend(
    trend: PositionDistributionStabilityTrend,
) -> None:
    if not isinstance(
        trend,
        PositionDistributionStabilityTrend,
    ):
        raise TypeError(
            "Each trend must be a "
            "PositionDistributionStabilityTrend."
        )

    if trend.position_count < 0:
        raise ValueError(
            "position_count cannot be negative."
        )

    if trend.window_count < 0:
        raise ValueError(
            "window_count cannot be negative."
        )

    if trend.stable_percentage_start < 0:
        raise ValueError(
            "stable_percentage_start cannot be negative."
        )

    if trend.stable_percentage_end < 0:
        raise ValueError(
            "stable_percentage_end cannot be negative."
        )

    if trend.moderate_percentage_start < 0:
        raise ValueError(
            "moderate_percentage_start cannot be negative."
        )

    if trend.moderate_percentage_end < 0:
        raise ValueError(
            "moderate_percentage_end cannot be negative."
        )

    if trend.unstable_percentage_start < 0:
        raise ValueError(
            "unstable_percentage_start cannot be negative."
        )

    if trend.unstable_percentage_end < 0:
        raise ValueError(
            "unstable_percentage_end cannot be negative."
        )

    percentage_values = (
        trend.stable_percentage_start,
        trend.stable_percentage_end,
        trend.moderate_percentage_start,
        trend.moderate_percentage_end,
        trend.unstable_percentage_start,
        trend.unstable_percentage_end,
    )

    for percentage in percentage_values:
        if percentage > 100:
            raise ValueError(
                "Percentage values cannot exceed 100."
            )

    if trend.total_absolute_percentage_change < 0:
        raise ValueError(
            "total_absolute_percentage_change cannot be negative."
        )

    if trend.mean_absolute_percentage_change < 0:
        raise ValueError(
            "mean_absolute_percentage_change cannot be negative."
        )

    if trend.stability_direction not in (
        STABLE_INCREASING,
        STABILITY_DECREASING,
        STABLE,
        MIXED,
    ):
        raise ValueError(
            "Invalid stability_direction."
        )

    if trend.trend_strength not in (
        LOW,
        MEDIUM,
        HIGH,
    ):
        raise ValueError(
            "Invalid trend_strength."
        )


def _validate_trends(
    trends: tuple[PositionDistributionStabilityTrend, ...],
) -> None:
    for trend in trends:
        _validate_trend(trend)


def summarize_position_distribution_stability_trends(
    trends: tuple[PositionDistributionStabilityTrend, ...],
) -> PositionDistributionStabilityTrendSummary:
    if not isinstance(trends, tuple):
        raise TypeError(
            "trends must be a tuple of "
            "PositionDistributionStabilityTrend objects."
        )

    _validate_trends(trends)

    if not trends:
        return PositionDistributionStabilityTrendSummary(
            trend_count=0,
            stable_increasing_count=0,
            stability_decreasing_count=0,
            stable_count=0,
            mixed_count=0,
            low_strength_count=0,
            medium_strength_count=0,
            high_strength_count=0,
            average_mean_absolute_percentage_change=0.0,
            minimum_mean_absolute_percentage_change=0.0,
            maximum_mean_absolute_percentage_change=0.0,
            total_absolute_percentage_change=0.0,
            trends=(),
        )

    stable_increasing_count = sum(
        1
        for trend in trends
        if trend.stability_direction == STABLE_INCREASING
    )

    stability_decreasing_count = sum(
        1
        for trend in trends
        if trend.stability_direction == STABILITY_DECREASING
    )

    stable_count = sum(
        1
        for trend in trends
        if trend.stability_direction == STABLE
    )

    mixed_count = sum(
        1
        for trend in trends
        if trend.stability_direction == MIXED
    )

    low_strength_count = sum(
        1
        for trend in trends
        if trend.trend_strength == LOW
    )

    medium_strength_count = sum(
        1
        for trend in trends
        if trend.trend_strength == MEDIUM
    )

    high_strength_count = sum(
        1
        for trend in trends
        if trend.trend_strength == HIGH
    )

    mean_values = tuple(
        trend.mean_absolute_percentage_change
        for trend in trends
    )

    average_mean_absolute_percentage_change = (
        sum(mean_values) / len(mean_values)
    )

    minimum_mean_absolute_percentage_change = min(
        mean_values
    )

    maximum_mean_absolute_percentage_change = max(
        mean_values
    )

    total_absolute_percentage_change = sum(
        trend.total_absolute_percentage_change
        for trend in trends
    )

    return PositionDistributionStabilityTrendSummary(
        trend_count=len(trends),
        stable_increasing_count=stable_increasing_count,
        stability_decreasing_count=stability_decreasing_count,
        stable_count=stable_count,
        mixed_count=mixed_count,
        low_strength_count=low_strength_count,
        medium_strength_count=medium_strength_count,
        high_strength_count=high_strength_count,
        average_mean_absolute_percentage_change=(
            average_mean_absolute_percentage_change
        ),
        minimum_mean_absolute_percentage_change=(
            minimum_mean_absolute_percentage_change
        ),
        maximum_mean_absolute_percentage_change=(
            maximum_mean_absolute_percentage_change
        ),
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        trends=trends,
    )


def get_position_distribution_stability_trend_summary(
    summary: PositionDistributionStabilityTrendSummary,
) -> PositionDistributionStabilityTrendSummary:
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendSummary."
        )

    return summary