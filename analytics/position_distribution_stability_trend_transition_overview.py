from dataclasses import dataclass
from typing import Tuple

from analytics.position_distribution_stability_trend_transition_summary import (
    HIGH,
    LOW,
    MEDIUM,
    PositionDistributionStabilityTrendTransitionSummary,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionOverview:
    transition_count: int

    low_movement_percentage: float
    medium_movement_percentage: float
    high_movement_percentage: float

    average_total_absolute_percentage_change: float
    minimum_total_absolute_percentage_change: float
    maximum_total_absolute_percentage_change: float
    total_absolute_percentage_change: float

    dominant_movement_levels: Tuple[str, ...]


def _validate_summary(
    summary: PositionDistributionStabilityTrendTransitionSummary,
) -> None:
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendTransitionSummary."
        )

    if summary.transition_count < 0:
        raise ValueError(
            "transition_count must be non-negative."
        )

    if summary.low_movement_count < 0:
        raise ValueError(
            "low_movement_count must be non-negative."
        )

    if summary.medium_movement_count < 0:
        raise ValueError(
            "medium_movement_count must be non-negative."
        )

    if summary.high_movement_count < 0:
        raise ValueError(
            "high_movement_count must be non-negative."
        )

    movement_count_total = (
        summary.low_movement_count
        + summary.medium_movement_count
        + summary.high_movement_count
    )

    if movement_count_total != summary.transition_count:
        raise ValueError(
            "Movement counts must equal transition_count."
        )

    metric_fields = (
        "average_total_absolute_percentage_change",
        "minimum_total_absolute_percentage_change",
        "maximum_total_absolute_percentage_change",
        "total_absolute_percentage_change",
    )

    for field_name in metric_fields:
        value = getattr(summary, field_name)

        if value < 0:
            raise ValueError(
                f"{field_name} must be non-negative."
            )

    if (
        summary.minimum_total_absolute_percentage_change
        > summary.maximum_total_absolute_percentage_change
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_change cannot exceed "
            "maximum_total_absolute_percentage_change."
        )

    if not isinstance(summary.transitions, tuple):
        raise TypeError(
            "transitions must be a tuple."
        )

    if len(summary.transitions) != summary.transition_count:
        raise ValueError(
            "transition_count must equal the number of transitions."
        )


def _calculate_percentage(
    count: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return (count / total) * 100.0


def _calculate_dominant_movement_levels(
    summary: PositionDistributionStabilityTrendTransitionSummary,
) -> Tuple[str, ...]:
    counts = {
        LOW: summary.low_movement_count,
        MEDIUM: summary.medium_movement_count,
        HIGH: summary.high_movement_count,
    }

    if summary.transition_count == 0:
        return ()

    maximum_count = max(counts.values())

    return tuple(
        level
        for level in (LOW, MEDIUM, HIGH)
        if counts[level] == maximum_count
    )


def build_position_distribution_stability_trend_transition_overview(
    summary: PositionDistributionStabilityTrendTransitionSummary,
) -> PositionDistributionStabilityTrendTransitionOverview:
    _validate_summary(summary)

    return PositionDistributionStabilityTrendTransitionOverview(
        transition_count=summary.transition_count,

        low_movement_percentage=_calculate_percentage(
            summary.low_movement_count,
            summary.transition_count,
        ),
        medium_movement_percentage=_calculate_percentage(
            summary.medium_movement_count,
            summary.transition_count,
        ),
        high_movement_percentage=_calculate_percentage(
            summary.high_movement_count,
            summary.transition_count,
        ),

        average_total_absolute_percentage_change=(
            summary.average_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change=(
            summary.minimum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change=(
            summary.maximum_total_absolute_percentage_change
        ),
        total_absolute_percentage_change=(
            summary.total_absolute_percentage_change
        ),

        dominant_movement_levels=(
            _calculate_dominant_movement_levels(summary)
        ),
    )


def get_position_distribution_stability_trend_transition_overview(
    overview: PositionDistributionStabilityTrendTransitionOverview,
) -> PositionDistributionStabilityTrendTransitionOverview:
    if not isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionOverview,
    ):
        raise TypeError(
            "overview must be a "
            "PositionDistributionStabilityTrendTransitionOverview."
        )

    return overview