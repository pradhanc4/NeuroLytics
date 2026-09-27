from dataclasses import dataclass

from analytics.position_distribution_stability_trend import (
    HIGH,
    LOW,
    MEDIUM,
    MIXED,
    STABLE,
    STABLE_INCREASING,
    STABILITY_DECREASING,
)
from analytics.position_distribution_stability_trend_summary import (
    PositionDistributionStabilityTrendSummary,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendOverview:
    summary_count: int

    stable_increasing_percentage: float
    stability_decreasing_percentage: float
    stable_percentage: float
    mixed_percentage: float

    low_strength_percentage: float
    medium_strength_percentage: float
    high_strength_percentage: float

    average_mean_absolute_percentage_change: float
    minimum_mean_absolute_percentage_change: float
    maximum_mean_absolute_percentage_change: float

    total_absolute_percentage_change: float

    dominant_trend_directions: tuple[str, ...]
    dominant_trend_strengths: tuple[str, ...]


def _validate_summary(
    summary: PositionDistributionStabilityTrendSummary,
) -> None:
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendSummary,
    ):
        raise TypeError(
            "Each summary must be a "
            "PositionDistributionStabilityTrendSummary."
        )

    if summary.trend_count < 0:
        raise ValueError(
            "trend_count cannot be negative."
        )

    direction_count = (
        summary.stable_increasing_count
        + summary.stability_decreasing_count
        + summary.stable_count
        + summary.mixed_count
    )

    if direction_count != summary.trend_count:
        raise ValueError(
            "Direction counts must equal trend_count."
        )

    strength_count = (
        summary.low_strength_count
        + summary.medium_strength_count
        + summary.high_strength_count
    )

    if strength_count != summary.trend_count:
        raise ValueError(
            "Strength counts must equal trend_count."
        )

    counts = (
        summary.stable_increasing_count,
        summary.stability_decreasing_count,
        summary.stable_count,
        summary.mixed_count,
        summary.low_strength_count,
        summary.medium_strength_count,
        summary.high_strength_count,
    )

    for count in counts:
        if count < 0:
            raise ValueError(
                "Summary counts cannot be negative."
            )

    if (
        summary.average_mean_absolute_percentage_change
        < 0
    ):
        raise ValueError(
            "average_mean_absolute_percentage_change "
            "cannot be negative."
        )

    if (
        summary.minimum_mean_absolute_percentage_change
        < 0
    ):
        raise ValueError(
            "minimum_mean_absolute_percentage_change "
            "cannot be negative."
        )

    if (
        summary.maximum_mean_absolute_percentage_change
        < 0
    ):
        raise ValueError(
            "maximum_mean_absolute_percentage_change "
            "cannot be negative."
        )

    if summary.total_absolute_percentage_change < 0:
        raise ValueError(
            "total_absolute_percentage_change "
            "cannot be negative."
        )


def _validate_summaries(
    summaries: tuple[
        PositionDistributionStabilityTrendSummary,
        ...,
    ],
) -> None:
    for summary in summaries:
        _validate_summary(summary)


def _calculate_percentage(
    count: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return (count / total) * 100.0


def _calculate_dominant_values(
    values: tuple[tuple[str, int], ...],
) -> tuple[str, ...]:
    if not values:
        return ()

    maximum_count = max(
        count
        for _, count in values
    )

    if maximum_count == 0:
        return ()

    return tuple(
        label
        for label, count in values
        if count == maximum_count
    )


def build_position_distribution_stability_trend_overview(
    summaries: tuple[
        PositionDistributionStabilityTrendSummary,
        ...,
    ],
) -> PositionDistributionStabilityTrendOverview:
    if not isinstance(summaries, tuple):
        raise TypeError(
            "summaries must be a tuple of "
            "PositionDistributionStabilityTrendSummary "
            "objects."
        )

    _validate_summaries(summaries)

    if not summaries:
        return PositionDistributionStabilityTrendOverview(
            summary_count=0,
            stable_increasing_percentage=0.0,
            stability_decreasing_percentage=0.0,
            stable_percentage=0.0,
            mixed_percentage=0.0,
            low_strength_percentage=0.0,
            medium_strength_percentage=0.0,
            high_strength_percentage=0.0,
            average_mean_absolute_percentage_change=0.0,
            minimum_mean_absolute_percentage_change=0.0,
            maximum_mean_absolute_percentage_change=0.0,
            total_absolute_percentage_change=0.0,
            dominant_trend_directions=(),
            dominant_trend_strengths=(),
        )

    summary_count = len(summaries)

    stable_increasing_count = sum(
        summary.stable_increasing_count
        for summary in summaries
    )

    stability_decreasing_count = sum(
        summary.stability_decreasing_count
        for summary in summaries
    )

    stable_count = sum(
        summary.stable_count
        for summary in summaries
    )

    mixed_count = sum(
        summary.mixed_count
        for summary in summaries
    )

    low_strength_count = sum(
        summary.low_strength_count
        for summary in summaries
    )

    medium_strength_count = sum(
        summary.medium_strength_count
        for summary in summaries
    )

    high_strength_count = sum(
        summary.high_strength_count
        for summary in summaries
    )

    stable_increasing_percentage = _calculate_percentage(
        stable_increasing_count,
        stable_increasing_count
        + stability_decreasing_count
        + stable_count
        + mixed_count,
    )

    stability_decreasing_percentage = _calculate_percentage(
        stability_decreasing_count,
        stable_increasing_count
        + stability_decreasing_count
        + stable_count
        + mixed_count,
    )

    stable_percentage = _calculate_percentage(
        stable_count,
        stable_increasing_count
        + stability_decreasing_count
        + stable_count
        + mixed_count,
    )

    mixed_percentage = _calculate_percentage(
        mixed_count,
        stable_increasing_count
        + stability_decreasing_count
        + stable_count
        + mixed_count,
    )

    low_strength_percentage = _calculate_percentage(
        low_strength_count,
        low_strength_count
        + medium_strength_count
        + high_strength_count,
    )

    medium_strength_percentage = _calculate_percentage(
        medium_strength_count,
        low_strength_count
        + medium_strength_count
        + high_strength_count,
    )

    high_strength_percentage = _calculate_percentage(
        high_strength_count,
        low_strength_count
        + medium_strength_count
        + high_strength_count,
    )

    average_values = tuple(
        summary.average_mean_absolute_percentage_change
        for summary in summaries
    )

    minimum_values = tuple(
        summary.minimum_mean_absolute_percentage_change
        for summary in summaries
    )

    maximum_values = tuple(
        summary.maximum_mean_absolute_percentage_change
        for summary in summaries
    )

    average_mean_absolute_percentage_change = (
        sum(average_values) / summary_count
    )

    minimum_mean_absolute_percentage_change = min(
        minimum_values
    )

    maximum_mean_absolute_percentage_change = max(
        maximum_values
    )

    total_absolute_percentage_change = sum(
        summary.total_absolute_percentage_change
        for summary in summaries
    )

    dominant_trend_directions = _calculate_dominant_values(
        (
            (
                STABLE_INCREASING,
                stable_increasing_count,
            ),
            (
                STABILITY_DECREASING,
                stability_decreasing_count,
            ),
            (
                STABLE,
                stable_count,
            ),
            (
                MIXED,
                mixed_count,
            ),
        )
    )

    dominant_trend_strengths = _calculate_dominant_values(
        (
            (
                LOW,
                low_strength_count,
            ),
            (
                MEDIUM,
                medium_strength_count,
            ),
            (
                HIGH,
                high_strength_count,
            ),
        )
    )

    return PositionDistributionStabilityTrendOverview(
        summary_count=summary_count,
        stable_increasing_percentage=(
            stable_increasing_percentage
        ),
        stability_decreasing_percentage=(
            stability_decreasing_percentage
        ),
        stable_percentage=stable_percentage,
        mixed_percentage=mixed_percentage,
        low_strength_percentage=low_strength_percentage,
        medium_strength_percentage=medium_strength_percentage,
        high_strength_percentage=high_strength_percentage,
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
        dominant_trend_directions=(
            dominant_trend_directions
        ),
        dominant_trend_strengths=(
            dominant_trend_strengths
        ),
    )