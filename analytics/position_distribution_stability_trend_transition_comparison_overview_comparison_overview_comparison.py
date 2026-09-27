"""
Phase 9.3.44

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison.

This module compares multiple Phase 9.3.43 overview observations.

The supplied observation order is authoritative. No dates or chronology
are inferred by this module.

This module is descriptive only. It does not perform prediction,
ranking, probability generation, model training, database mutation,
or SQL operations.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison:
    """
    Descriptive comparison across multiple Phase 9.3.43 overview observations.
    """

    overview_count: int

    low_increase_percentage_start: float
    low_increase_percentage_end: float
    low_increase_percentage_change: float

    low_decrease_percentage_start: float
    low_decrease_percentage_end: float
    low_decrease_percentage_change: float

    low_unchanged_percentage_start: float
    low_unchanged_percentage_end: float
    low_unchanged_percentage_change: float

    medium_increase_percentage_start: float
    medium_increase_percentage_end: float
    medium_increase_percentage_change: float

    medium_decrease_percentage_start: float
    medium_decrease_percentage_end: float
    medium_decrease_percentage_change: float

    medium_unchanged_percentage_start: float
    medium_unchanged_percentage_end: float
    medium_unchanged_percentage_change: float

    high_increase_percentage_start: float
    high_increase_percentage_end: float
    high_increase_percentage_change: float

    high_decrease_percentage_start: float
    high_decrease_percentage_end: float
    high_decrease_percentage_change: float

    high_unchanged_percentage_start: float
    high_unchanged_percentage_end: float
    high_unchanged_percentage_change: float

    average_total_absolute_percentage_movement_start: float
    average_total_absolute_percentage_movement_end: float
    average_total_absolute_percentage_movement_change: float

    minimum_total_absolute_percentage_movement_start: float
    minimum_total_absolute_percentage_movement_end: float
    minimum_total_absolute_percentage_movement_change: float

    maximum_total_absolute_percentage_movement_start: float
    maximum_total_absolute_percentage_movement_end: float
    maximum_total_absolute_percentage_movement_change: float

    total_absolute_percentage_movement_start: float
    total_absolute_percentage_movement_end: float
    total_absolute_percentage_movement_change: float

    total_absolute_percentage_movement: float
    mean_absolute_percentage_movement: float


PERCENTAGE_FIELDS = (
    "low_increase_percentage",
    "low_decrease_percentage",
    "low_unchanged_percentage",
    "medium_increase_percentage",
    "medium_decrease_percentage",
    "medium_unchanged_percentage",
    "high_increase_percentage",
    "high_decrease_percentage",
    "high_unchanged_percentage",
)

MOVEMENT_FIELDS = (
    "average_total_absolute_percentage_movement",
    "minimum_total_absolute_percentage_movement",
    "maximum_total_absolute_percentage_movement",
    "total_absolute_percentage_movement",
)


def _validate_percentage(
    value: float,
    field_name: str,
) -> None:
    """Validate a percentage value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{field_name} must be numeric."
        )

    if value < 0.0 or value > 100.0:
        raise ValueError(
            f"{field_name} must be between 0.0 and 100.0."
        )


def _validate_nonnegative(
    value: float,
    field_name: str,
) -> None:
    """Validate a non-negative numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"{field_name} must be numeric."
        )

    if value < 0.0:
        raise ValueError(
            f"{field_name} must be non-negative."
        )


def _validate_overview(
    overview: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
) -> None:
    """Validate one Phase 9.3.43 overview."""
    if not isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
    ):
        raise TypeError(
            "Each overview must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview."
        )

    if isinstance(overview.transition_count, bool) or not isinstance(
        overview.transition_count,
        int,
    ):
        raise TypeError(
            "transition_count must be an integer."
        )

    if overview.transition_count < 0:
        raise ValueError(
            "transition_count must be non-negative."
        )

    for field_name in PERCENTAGE_FIELDS:
        _validate_percentage(
            getattr(overview, field_name),
            field_name,
        )

    for field_name in MOVEMENT_FIELDS:
        _validate_nonnegative(
            getattr(overview, field_name),
            field_name,
        )

    if (
        overview.minimum_total_absolute_percentage_movement
        > overview.maximum_total_absolute_percentage_movement
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_movement cannot exceed "
            "maximum_total_absolute_percentage_movement."
        )

    dominant_direction_fields = (
        "dominant_low_directions",
        "dominant_medium_directions",
        "dominant_high_directions",
    )

    valid_directions = {
        "INCREASE",
        "DECREASE",
        "UNCHANGED",
    }

    for field_name in dominant_direction_fields:
        directions = getattr(overview, field_name)

        if not isinstance(directions, tuple):
            raise TypeError(
                f"{field_name} must be a tuple."
            )

        if len(directions) == 0:
            if overview.transition_count > 0:
                raise ValueError(
                    f"{field_name} cannot be empty when transition_count "
                    "is greater than zero."
                )
            continue

        if len(set(directions)) != len(directions):
            raise ValueError(
                f"{field_name} cannot contain duplicate directions."
            )

        for direction in directions:
            if direction not in valid_directions:
                raise ValueError(
                    f"{field_name} contains invalid direction: "
                    f"{direction!r}."
                )


def _validate_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> None:
    """Validate the complete ordered overview collection."""
    if not isinstance(overviews, tuple):
        raise TypeError(
            "overviews must be a tuple."
        )

    for overview in overviews:
        _validate_overview(overview)


def _calculate_change(
    start: float,
    end: float,
) -> float:
    """Calculate end-minus-start change."""
    return end - start


def _calculate_total_absolute_percentage_movement(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> float:
    """
    Calculate total absolute movement across consecutive observations.

    Movement is calculated across all nine percentage series.
    """
    if len(overviews) < 2:
        return 0.0

    total = 0.0

    for previous, current in zip(
        overviews,
        overviews[1:],
    ):
        for field_name in PERCENTAGE_FIELDS:
            previous_value = getattr(previous, field_name)
            current_value = getattr(current, field_name)

            total += abs(
                current_value - previous_value
            )

    return total


def _calculate_mean_absolute_percentage_movement(
    total_absolute_percentage_movement: float,
    overview_count: int,
) -> float:
    """Calculate mean movement per transition."""
    transition_count = max(
        overview_count - 1,
        0,
    )

    if transition_count == 0:
        return 0.0

    return total_absolute_percentage_movement / transition_count


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison:
    """
    Compare multiple ordered Phase 9.3.43 overview observations.

    The first observation supplies the start values and the final
    observation supplies the end values.

    Changes are calculated as:

        end - start

    Total absolute percentage movement is calculated across every
    consecutive observation and all nine percentage fields.
    """
    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count == 0:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison(
                overview_count=0,

                low_increase_percentage_start=0.0,
                low_increase_percentage_end=0.0,
                low_increase_percentage_change=0.0,

                low_decrease_percentage_start=0.0,
                low_decrease_percentage_end=0.0,
                low_decrease_percentage_change=0.0,

                low_unchanged_percentage_start=0.0,
                low_unchanged_percentage_end=0.0,
                low_unchanged_percentage_change=0.0,

                medium_increase_percentage_start=0.0,
                medium_increase_percentage_end=0.0,
                medium_increase_percentage_change=0.0,

                medium_decrease_percentage_start=0.0,
                medium_decrease_percentage_end=0.0,
                medium_decrease_percentage_change=0.0,

                medium_unchanged_percentage_start=0.0,
                medium_unchanged_percentage_end=0.0,
                medium_unchanged_percentage_change=0.0,

                high_increase_percentage_start=0.0,
                high_increase_percentage_end=0.0,
                high_increase_percentage_change=0.0,

                high_decrease_percentage_start=0.0,
                high_decrease_percentage_end=0.0,
                high_decrease_percentage_change=0.0,

                high_unchanged_percentage_start=0.0,
                high_unchanged_percentage_end=0.0,
                high_unchanged_percentage_change=0.0,

                average_total_absolute_percentage_movement_start=0.0,
                average_total_absolute_percentage_movement_end=0.0,
                average_total_absolute_percentage_movement_change=0.0,

                minimum_total_absolute_percentage_movement_start=0.0,
                minimum_total_absolute_percentage_movement_end=0.0,
                minimum_total_absolute_percentage_movement_change=0.0,

                maximum_total_absolute_percentage_movement_start=0.0,
                maximum_total_absolute_percentage_movement_end=0.0,
                maximum_total_absolute_percentage_movement_change=0.0,

                total_absolute_percentage_movement_start=0.0,
                total_absolute_percentage_movement_end=0.0,
                total_absolute_percentage_movement_change=0.0,

                total_absolute_percentage_movement=0.0,
                mean_absolute_percentage_movement=0.0,
            )
        )

    start = overviews[0]
    end = overviews[-1]

    values = {
        "overview_count": overview_count,
    }

    for field_name in PERCENTAGE_FIELDS:
        start_value = getattr(start, field_name)
        end_value = getattr(end, field_name)

        values[f"{field_name}_start"] = start_value
        values[f"{field_name}_end"] = end_value
        values[f"{field_name}_change"] = _calculate_change(
            start_value,
            end_value,
        )

    for field_name in MOVEMENT_FIELDS:
        start_value = getattr(start, field_name)
        end_value = getattr(end, field_name)

        values[f"{field_name}_start"] = start_value
        values[f"{field_name}_end"] = end_value
        values[f"{field_name}_change"] = _calculate_change(
            start_value,
            end_value,
        )

    total_absolute_percentage_movement = (
        _calculate_total_absolute_percentage_movement(
            overviews
        )
    )

    mean_absolute_percentage_movement = (
        _calculate_mean_absolute_percentage_movement(
            total_absolute_percentage_movement,
            overview_count,
        )
    )

    values["total_absolute_percentage_movement"] = (
        total_absolute_percentage_movement
    )

    values["mean_absolute_percentage_movement"] = (
        mean_absolute_percentage_movement
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison(
            **values
        )
    )


def compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparison:
    """
    Convenience wrapper for Phase 9.3.44 comparison.
    """
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            overviews
        )
    )