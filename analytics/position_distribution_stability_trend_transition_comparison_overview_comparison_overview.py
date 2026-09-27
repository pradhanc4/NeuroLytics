"""
Phase 9.3.43

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview.

This module provides a descriptive overview of the Phase 9.3.42
PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary.

The module does not perform prediction, ranking, probability generation,
model training, database mutation, or SQL operations.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary import (
    DECREASE,
    INCREASE,
    UNCHANGED,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
)


DIRECTION_ORDER = (
    INCREASE,
    DECREASE,
    UNCHANGED,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview:
    """
    High-level descriptive overview of a Phase 9.3.42 summary.
    """

    transition_count: int

    low_increase_percentage: float
    low_decrease_percentage: float
    low_unchanged_percentage: float

    medium_increase_percentage: float
    medium_decrease_percentage: float
    medium_unchanged_percentage: float

    high_increase_percentage: float
    high_decrease_percentage: float
    high_unchanged_percentage: float

    average_total_absolute_percentage_movement: float
    minimum_total_absolute_percentage_movement: float
    maximum_total_absolute_percentage_movement: float
    total_absolute_percentage_movement: float

    dominant_low_directions: tuple[str, ...]
    dominant_medium_directions: tuple[str, ...]
    dominant_high_directions: tuple[str, ...]


def _validate_percentage(value: float, field_name: str) -> None:
    """Validate a percentage value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0 or value > 100.0:
        raise ValueError(
            f"{field_name} must be between 0.0 and 100.0."
        )


def _validate_nonnegative(value: float, field_name: str) -> None:
    """Validate a non-negative numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0:
        raise ValueError(
            f"{field_name} must be non-negative."
        )


def _validate_direction_count(
    value: int,
    field_name: str,
    transition_count: int,
) -> None:
    """Validate an individual direction count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(
            f"{field_name} must be non-negative."
        )

    if value > transition_count:
        raise ValueError(
            f"{field_name} cannot exceed transition_count."
        )


def _validate_directions(
    directions: tuple[str, ...],
    field_name: str,
) -> None:
    """Validate a dominant-direction tuple."""
    if not isinstance(directions, tuple):
        raise TypeError(
            f"{field_name} must be a tuple."
        )

    if len(directions) == 0:
        raise ValueError(
            f"{field_name} cannot be empty for a non-empty summary."
        )

    if len(set(directions)) != len(directions):
        raise ValueError(
            f"{field_name} cannot contain duplicate directions."
        )

    for direction in directions:
        if direction not in DIRECTION_ORDER:
            raise ValueError(
                f"{field_name} contains an invalid direction: {direction!r}."
            )


def _validate_summary(
    summary: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
) -> None:
    """Validate the Phase 9.3.42 source summary."""
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary."
        )

    if isinstance(summary.transition_count, bool) or not isinstance(
        summary.transition_count,
        int,
    ):
        raise TypeError(
            "transition_count must be an integer."
        )

    if summary.transition_count < 0:
        raise ValueError(
            "transition_count must be non-negative."
        )

    count_fields = (
        "low_increase_count",
        "low_decrease_count",
        "low_unchanged_count",
        "medium_increase_count",
        "medium_decrease_count",
        "medium_unchanged_count",
        "high_increase_count",
        "high_decrease_count",
        "high_unchanged_count",
    )

    for field_name in count_fields:
        _validate_direction_count(
            getattr(summary, field_name),
            field_name,
            summary.transition_count,
        )

    metric_fields = (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    )

    for field_name in metric_fields:
        _validate_nonnegative(
            getattr(summary, field_name),
            field_name,
        )

    if (
        summary.minimum_total_absolute_percentage_movement
        > summary.maximum_total_absolute_percentage_movement
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_movement cannot exceed "
            "maximum_total_absolute_percentage_movement."
        )

    if not isinstance(summary.transitions, tuple):
        raise TypeError(
            "transitions must be a tuple."
        )

    if len(summary.transitions) != summary.transition_count:
        raise ValueError(
            "transitions length must match transition_count."
        )


def _calculate_percentage(
    count: int,
    transition_count: int,
) -> float:
    """Convert a direction count into a percentage."""
    if transition_count == 0:
        return 0.0

    return (count / transition_count) * 100.0


def _calculate_dominant_directions(
    counts: tuple[tuple[str, int], ...],
) -> tuple[str, ...]:
    """
    Return all dominant directions while preserving DIRECTION_ORDER.
    """
    maximum_count = max(
        count
        for _, count in counts
    )

    return tuple(
        direction
        for direction, count in counts
        if count == maximum_count
    )


def _calculate_dominant_directions_from_summary(
    summary: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
    prefix: str,
) -> tuple[str, ...]:
    """Calculate dominant directions for LOW, MEDIUM, or HIGH."""
    counts = (
        (
            INCREASE,
            getattr(summary, f"{prefix}_increase_count"),
        ),
        (
            DECREASE,
            getattr(summary, f"{prefix}_decrease_count"),
        ),
        (
            UNCHANGED,
            getattr(summary, f"{prefix}_unchanged_count"),
        ),
    )

    return _calculate_dominant_directions(counts)


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
    summary: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview:
    """
    Build a descriptive overview from a Phase 9.3.42 summary.
    """
    _validate_summary(summary)

    if summary.transition_count == 0:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview(
                transition_count=0,
                low_increase_percentage=0.0,
                low_decrease_percentage=0.0,
                low_unchanged_percentage=0.0,
                medium_increase_percentage=0.0,
                medium_decrease_percentage=0.0,
                medium_unchanged_percentage=0.0,
                high_increase_percentage=0.0,
                high_decrease_percentage=0.0,
                high_unchanged_percentage=0.0,
                average_total_absolute_percentage_movement=0.0,
                minimum_total_absolute_percentage_movement=0.0,
                maximum_total_absolute_percentage_movement=0.0,
                total_absolute_percentage_movement=0.0,
                dominant_low_directions=(),
                dominant_medium_directions=(),
                dominant_high_directions=(),
            )
        )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview(
            transition_count=summary.transition_count,

            low_increase_percentage=_calculate_percentage(
                summary.low_increase_count,
                summary.transition_count,
            ),
            low_decrease_percentage=_calculate_percentage(
                summary.low_decrease_count,
                summary.transition_count,
            ),
            low_unchanged_percentage=_calculate_percentage(
                summary.low_unchanged_count,
                summary.transition_count,
            ),

            medium_increase_percentage=_calculate_percentage(
                summary.medium_increase_count,
                summary.transition_count,
            ),
            medium_decrease_percentage=_calculate_percentage(
                summary.medium_decrease_count,
                summary.transition_count,
            ),
            medium_unchanged_percentage=_calculate_percentage(
                summary.medium_unchanged_count,
                summary.transition_count,
            ),

            high_increase_percentage=_calculate_percentage(
                summary.high_increase_count,
                summary.transition_count,
            ),
            high_decrease_percentage=_calculate_percentage(
                summary.high_decrease_count,
                summary.transition_count,
            ),
            high_unchanged_percentage=_calculate_percentage(
                summary.high_unchanged_count,
                summary.transition_count,
            ),

            average_total_absolute_percentage_movement=(
                summary.average_total_absolute_percentage_movement
            ),
            minimum_total_absolute_percentage_movement=(
                summary.minimum_total_absolute_percentage_movement
            ),
            maximum_total_absolute_percentage_movement=(
                summary.maximum_total_absolute_percentage_movement
            ),
            total_absolute_percentage_movement=(
                summary.total_absolute_percentage_movement
            ),

            dominant_low_directions=(
                _calculate_dominant_directions_from_summary(
                    summary,
                    "low",
                )
            ),
            dominant_medium_directions=(
                _calculate_dominant_directions_from_summary(
                    summary,
                    "medium",
                )
            ),
            dominant_high_directions=(
                _calculate_dominant_directions_from_summary(
                    summary,
                    "high",
                )
            ),
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
    summary: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview:
    """
    Convenience getter for the Phase 9.3.43 overview.
    """
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview(
            summary
        )
    )