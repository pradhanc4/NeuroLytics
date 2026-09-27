"""
Phase 9.3.47

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Summary Overview.

This module converts the count-based descriptive summary produced by
Phase 9.3.46 into percentage-based descriptive overview metrics.

The analysis is descriptive only. It does not perform prediction, ranking,
probability estimation, model training, or SQL mutation.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary,
)


DIRECTION_INCREASE = "INCREASE"
DIRECTION_DECREASE = "DECREASE"
DIRECTION_UNCHANGED = "UNCHANGED"

DIRECTION_ORDER = (
    DIRECTION_INCREASE,
    DIRECTION_DECREASE,
    DIRECTION_UNCHANGED,
)

SERIES_NAMES = (
    "low_increase",
    "low_decrease",
    "low_unchanged",
    "medium_increase",
    "medium_decrease",
    "medium_unchanged",
    "high_increase",
    "high_decrease",
    "high_unchanged",
)

DIRECTION_SUFFIXES = (
    "increase",
    "decrease",
    "unchanged",
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview:
    """
    Percentage-based overview of the Phase 9.3.46 transition summary.
    """

    transition_count: int

    low_increase_increase_percentage: float
    low_increase_decrease_percentage: float
    low_increase_unchanged_percentage: float

    low_decrease_increase_percentage: float
    low_decrease_decrease_percentage: float
    low_decrease_unchanged_percentage: float

    low_unchanged_increase_percentage: float
    low_unchanged_decrease_percentage: float
    low_unchanged_unchanged_percentage: float

    medium_increase_increase_percentage: float
    medium_increase_decrease_percentage: float
    medium_increase_unchanged_percentage: float

    medium_decrease_increase_percentage: float
    medium_decrease_decrease_percentage: float
    medium_decrease_unchanged_percentage: float

    medium_unchanged_increase_percentage: float
    medium_unchanged_decrease_percentage: float
    medium_unchanged_unchanged_percentage: float

    high_increase_increase_percentage: float
    high_increase_decrease_percentage: float
    high_increase_unchanged_percentage: float

    high_decrease_increase_percentage: float
    high_decrease_decrease_percentage: float
    high_decrease_unchanged_percentage: float

    high_unchanged_increase_percentage: float
    high_unchanged_decrease_percentage: float
    high_unchanged_unchanged_percentage: float

    average_total_absolute_percentage_movement: float
    minimum_total_absolute_percentage_movement: float
    maximum_total_absolute_percentage_movement: float
    total_absolute_percentage_movement: float

    dominant_low_increase_directions: tuple[str, ...]
    dominant_low_decrease_directions: tuple[str, ...]
    dominant_low_unchanged_directions: tuple[str, ...]

    dominant_medium_increase_directions: tuple[str, ...]
    dominant_medium_decrease_directions: tuple[str, ...]
    dominant_medium_unchanged_directions: tuple[str, ...]

    dominant_high_increase_directions: tuple[str, ...]
    dominant_high_decrease_directions: tuple[str, ...]
    dominant_high_unchanged_directions: tuple[str, ...]


def _validate_nonnegative(
    value: float,
    field_name: str,
) -> None:
    """Validate a non-negative numeric value."""
    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be numeric, not bool."
        )

    if not isinstance(value, (int, float)):
        raise TypeError(
            f"{field_name} must be numeric."
        )

    if value < 0:
        raise ValueError(
            f"{field_name} must be non-negative."
        )


def _validate_nonnegative_integer(
    value: int,
    field_name: str,
) -> None:
    """Validate a non-negative integer."""
    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be an integer, not bool."
        )

    if not isinstance(value, int):
        raise TypeError(
            f"{field_name} must be an integer."
        )

    if value < 0:
        raise ValueError(
            f"{field_name} must be non-negative."
        )


def _validate_direction_counts(
    summary: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    ),
) -> None:
    """Validate every direction count in the Phase 9.3.46 summary."""
    for series_name in SERIES_NAMES:
        for direction in DIRECTION_SUFFIXES:
            field_name = (
                f"{series_name}_{direction}_count"
            )

            value = getattr(
                summary,
                field_name,
            )

            _validate_nonnegative_integer(
                value,
                field_name,
            )

            if value > summary.transition_count:
                raise ValueError(
                    f"{field_name} cannot exceed transition_count."
                )


def _validate_summary(
    summary: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    ),
) -> None:
    """Validate the complete Phase 9.3.46 summary."""
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary."
        )

    _validate_nonnegative_integer(
        summary.transition_count,
        "transition_count",
    )

    _validate_direction_counts(
        summary
    )

    movement_fields = (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    )

    for field_name in movement_fields:
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

    if summary.transition_count == 0:
        for series_name in SERIES_NAMES:
            for direction in DIRECTION_SUFFIXES:
                field_name = (
                    f"{series_name}_{direction}_count"
                )

                if getattr(summary, field_name) != 0:
                    raise ValueError(
                        f"{field_name} must be zero when transition_count is zero."
                    )

        for field_name in movement_fields:
            if getattr(summary, field_name) != 0:
                raise ValueError(
                    f"{field_name} must be zero when transition_count is zero."
                )


def _calculate_percentage(
    count: int,
    transition_count: int,
) -> float:
    """Convert a count into a percentage."""
    if transition_count == 0:
        return 0.0

    return (
        count
        / transition_count
        * 100.0
    )


def _calculate_dominant_directions(
    increase_count: int,
    decrease_count: int,
    unchanged_count: int,
) -> tuple[str, ...]:
    """
    Calculate dominant directions while preserving deterministic tie order.
    """
    counts = {
        DIRECTION_INCREASE: increase_count,
        DIRECTION_DECREASE: decrease_count,
        DIRECTION_UNCHANGED: unchanged_count,
    }

    maximum_count = max(
        counts.values()
    )

    if maximum_count == 0:
        return ()

    return tuple(
        direction
        for direction in DIRECTION_ORDER
        if counts[direction] == maximum_count
    )


def _build_series_values(
    summary: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    ),
    series_name: str,
) -> tuple[float, float, float, tuple[str, ...]]:
    """Build percentages and dominant directions for one series."""
    increase_count = getattr(
        summary,
        f"{series_name}_increase_count",
    )

    decrease_count = getattr(
        summary,
        f"{series_name}_decrease_count",
    )

    unchanged_count = getattr(
        summary,
        f"{series_name}_unchanged_count",
    )

    increase_percentage = _calculate_percentage(
        increase_count,
        summary.transition_count,
    )

    decrease_percentage = _calculate_percentage(
        decrease_count,
        summary.transition_count,
    )

    unchanged_percentage = _calculate_percentage(
        unchanged_count,
        summary.transition_count,
    )

    dominant_directions = _calculate_dominant_directions(
        increase_count,
        decrease_count,
        unchanged_count,
    )

    return (
        increase_percentage,
        decrease_percentage,
        unchanged_percentage,
        dominant_directions,
    )


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
    summary: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    ),
) -> (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview
):
    """
    Build the Phase 9.3.47 percentage-based overview.
    """
    _validate_summary(
        summary
    )

    (
        low_increase_increase_percentage,
        low_increase_decrease_percentage,
        low_increase_unchanged_percentage,
        dominant_low_increase_directions,
    ) = _build_series_values(
        summary,
        "low_increase",
    )

    (
        low_decrease_increase_percentage,
        low_decrease_decrease_percentage,
        low_decrease_unchanged_percentage,
        dominant_low_decrease_directions,
    ) = _build_series_values(
        summary,
        "low_decrease",
    )

    (
        low_unchanged_increase_percentage,
        low_unchanged_decrease_percentage,
        low_unchanged_unchanged_percentage,
        dominant_low_unchanged_directions,
    ) = _build_series_values(
        summary,
        "low_unchanged",
    )

    (
        medium_increase_increase_percentage,
        medium_increase_decrease_percentage,
        medium_increase_unchanged_percentage,
        dominant_medium_increase_directions,
    ) = _build_series_values(
        summary,
        "medium_increase",
    )

    (
        medium_decrease_increase_percentage,
        medium_decrease_decrease_percentage,
        medium_decrease_unchanged_percentage,
        dominant_medium_decrease_directions,
    ) = _build_series_values(
        summary,
        "medium_decrease",
    )

    (
        medium_unchanged_increase_percentage,
        medium_unchanged_decrease_percentage,
        medium_unchanged_unchanged_percentage,
        dominant_medium_unchanged_directions,
    ) = _build_series_values(
        summary,
        "medium_unchanged",
    )

    (
        high_increase_increase_percentage,
        high_increase_decrease_percentage,
        high_increase_unchanged_percentage,
        dominant_high_increase_directions,
    ) = _build_series_values(
        summary,
        "high_increase",
    )

    (
        high_decrease_increase_percentage,
        high_decrease_decrease_percentage,
        high_decrease_unchanged_percentage,
        dominant_high_decrease_directions,
    ) = _build_series_values(
        summary,
        "high_decrease",
    )

    (
        high_unchanged_increase_percentage,
        high_unchanged_decrease_percentage,
        high_unchanged_unchanged_percentage,
        dominant_high_unchanged_directions,
    ) = _build_series_values(
        summary,
        "high_unchanged",
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview(
            transition_count=summary.transition_count,

            low_increase_increase_percentage=low_increase_increase_percentage,
            low_increase_decrease_percentage=low_increase_decrease_percentage,
            low_increase_unchanged_percentage=low_increase_unchanged_percentage,

            low_decrease_increase_percentage=low_decrease_increase_percentage,
            low_decrease_decrease_percentage=low_decrease_decrease_percentage,
            low_decrease_unchanged_percentage=low_decrease_unchanged_percentage,

            low_unchanged_increase_percentage=low_unchanged_increase_percentage,
            low_unchanged_decrease_percentage=low_unchanged_decrease_percentage,
            low_unchanged_unchanged_percentage=low_unchanged_unchanged_percentage,

            medium_increase_increase_percentage=medium_increase_increase_percentage,
            medium_increase_decrease_percentage=medium_increase_decrease_percentage,
            medium_increase_unchanged_percentage=medium_increase_unchanged_percentage,

            medium_decrease_increase_percentage=medium_decrease_increase_percentage,
            medium_decrease_decrease_percentage=medium_decrease_decrease_percentage,
            medium_decrease_unchanged_percentage=medium_decrease_unchanged_percentage,

            medium_unchanged_increase_percentage=medium_unchanged_increase_percentage,
            medium_unchanged_decrease_percentage=medium_unchanged_decrease_percentage,
            medium_unchanged_unchanged_percentage=medium_unchanged_unchanged_percentage,

            high_increase_increase_percentage=high_increase_increase_percentage,
            high_increase_decrease_percentage=high_increase_decrease_percentage,
            high_increase_unchanged_percentage=high_increase_unchanged_percentage,

            high_decrease_increase_percentage=high_decrease_increase_percentage,
            high_decrease_decrease_percentage=high_decrease_decrease_percentage,
            high_decrease_unchanged_percentage=high_decrease_unchanged_percentage,

            high_unchanged_increase_percentage=high_unchanged_increase_percentage,
            high_unchanged_decrease_percentage=high_unchanged_decrease_percentage,
            high_unchanged_unchanged_percentage=high_unchanged_unchanged_percentage,

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

            dominant_low_increase_directions=(
                dominant_low_increase_directions
            ),
            dominant_low_decrease_directions=(
                dominant_low_decrease_directions
            ),
            dominant_low_unchanged_directions=(
                dominant_low_unchanged_directions
            ),

            dominant_medium_increase_directions=(
                dominant_medium_increase_directions
            ),
            dominant_medium_decrease_directions=(
                dominant_medium_decrease_directions
            ),
            dominant_medium_unchanged_directions=(
                dominant_medium_unchanged_directions
            ),

            dominant_high_increase_directions=(
                dominant_high_increase_directions
            ),
            dominant_high_decrease_directions=(
                dominant_high_decrease_directions
            ),
            dominant_high_unchanged_directions=(
                dominant_high_unchanged_directions
            ),
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
    summary: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary
    ),
) -> (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview
):
    """
    Getter wrapper for the Phase 9.3.47 overview.
    """
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview(
            summary
        )
    )