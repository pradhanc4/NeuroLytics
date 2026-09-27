from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverview,
)


INCREASE = "INCREASE"
DECREASE = "DECREASE"
UNCHANGED = "UNCHANGED"

DIRECTION_ORDER = (
    INCREASE,
    DECREASE,
    UNCHANGED,
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparison:
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


def _validate_percentage(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < 0 or value > 100:
        raise ValueError(
            f"{field_name} must be between 0 and 100."
        )


def _validate_nonnegative(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )


def _validate_overview(
    overview: PositionDistributionStabilityTrendTransitionComparisonOverview,
) -> None:
    if not isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionComparisonOverview,
    ):
        raise TypeError(
            "Each item must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverview."
        )

    if (
        not isinstance(overview.transition_count, int)
        or isinstance(overview.transition_count, bool)
    ):
        raise ValueError("transition_count must be a non-negative integer.")

    if overview.transition_count < 0:
        raise ValueError("transition_count cannot be negative.")

    percentage_fields = (
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

    for field_name in percentage_fields:
        _validate_percentage(
            getattr(overview, field_name),
            field_name,
        )

    direction_groups = (
        (
            overview.low_increase_percentage,
            overview.low_decrease_percentage,
            overview.low_unchanged_percentage,
        ),
        (
            overview.medium_increase_percentage,
            overview.medium_decrease_percentage,
            overview.medium_unchanged_percentage,
        ),
        (
            overview.high_increase_percentage,
            overview.high_decrease_percentage,
            overview.high_unchanged_percentage,
        ),
    )

    for group in direction_groups:
        group_total = sum(group)

        if overview.transition_count == 0:
            if abs(group_total) > 1e-9:
                raise ValueError(
                    "Direction percentages must be zero when "
                    "transition_count is zero."
                )
        elif abs(group_total - 100.0) > 1e-6:
            raise ValueError(
                "Each movement-level direction percentage group "
                "must sum to 100."
            )

    metric_fields = (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    )

    for field_name in metric_fields:
        _validate_nonnegative(
            getattr(overview, field_name),
            field_name,
        )

    if (
        overview.minimum_total_absolute_percentage_movement
        > overview.maximum_total_absolute_percentage_movement
    ):
        raise ValueError(
            "Minimum total absolute percentage movement cannot "
            "exceed maximum total absolute percentage movement."
        )

    if not isinstance(overview.dominant_low_directions, tuple):
        raise TypeError("dominant_low_directions must be a tuple.")

    if not isinstance(overview.dominant_medium_directions, tuple):
        raise TypeError("dominant_medium_directions must be a tuple.")

    if not isinstance(overview.dominant_high_directions, tuple):
        raise TypeError("dominant_high_directions must be a tuple.")

    for direction_group in (
        overview.dominant_low_directions,
        overview.dominant_medium_directions,
        overview.dominant_high_directions,
    ):
        for direction in direction_group:
            if direction not in DIRECTION_ORDER:
                raise ValueError(
                    f"Invalid direction: {direction}."
                )


def _validate_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> None:
    if not isinstance(overviews, tuple):
        raise TypeError("overviews must be a tuple.")

    for overview in overviews:
        _validate_overview(overview)


def _percentage_change(start: float, end: float) -> float:
    return end - start


def _calculate_total_absolute_percentage_movement(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> float:
    if len(overviews) <= 1:
        return 0.0

    total_movement = 0.0

    percentage_fields = (
        (
            "low_increase_percentage",
            "low_decrease_percentage",
            "low_unchanged_percentage",
        ),
        (
            "medium_increase_percentage",
            "medium_decrease_percentage",
            "medium_unchanged_percentage",
        ),
        (
            "high_increase_percentage",
            "high_decrease_percentage",
            "high_unchanged_percentage",
        ),
    )

    for previous, current in zip(
        overviews,
        overviews[1:],
    ):
        for field_group in percentage_fields:
            for field_name in field_group:
                total_movement += abs(
                    getattr(current, field_name)
                    - getattr(previous, field_name)
                )

    return total_movement


def _calculate_mean_absolute_percentage_movement(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> float:
    transition_count = max(len(overviews) - 1, 0)

    if transition_count == 0:
        return 0.0

    total_movement = _calculate_total_absolute_percentage_movement(
        overviews
    )

    return total_movement / transition_count


def build_position_distribution_stability_trend_transition_comparison_overview_comparison(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparison:
    _validate_overviews(overviews)

    if not overviews:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparison(
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

    first = overviews[0]
    last = overviews[-1]

    def change(field_name: str) -> float:
        return _percentage_change(
            getattr(first, field_name),
            getattr(last, field_name),
        )

    total_movement = _calculate_total_absolute_percentage_movement(
        overviews
    )

    mean_movement = _calculate_mean_absolute_percentage_movement(
        overviews
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparison(
            overview_count=len(overviews),

            low_increase_percentage_start=first.low_increase_percentage,
            low_increase_percentage_end=last.low_increase_percentage,
            low_increase_percentage_change=change(
                "low_increase_percentage"
            ),

            low_decrease_percentage_start=first.low_decrease_percentage,
            low_decrease_percentage_end=last.low_decrease_percentage,
            low_decrease_percentage_change=change(
                "low_decrease_percentage"
            ),

            low_unchanged_percentage_start=first.low_unchanged_percentage,
            low_unchanged_percentage_end=last.low_unchanged_percentage,
            low_unchanged_percentage_change=change(
                "low_unchanged_percentage"
            ),

            medium_increase_percentage_start=first.medium_increase_percentage,
            medium_increase_percentage_end=last.medium_increase_percentage,
            medium_increase_percentage_change=change(
                "medium_increase_percentage"
            ),

            medium_decrease_percentage_start=first.medium_decrease_percentage,
            medium_decrease_percentage_end=last.medium_decrease_percentage,
            medium_decrease_percentage_change=change(
                "medium_decrease_percentage"
            ),

            medium_unchanged_percentage_start=first.medium_unchanged_percentage,
            medium_unchanged_percentage_end=last.medium_unchanged_percentage,
            medium_unchanged_percentage_change=change(
                "medium_unchanged_percentage"
            ),

            high_increase_percentage_start=first.high_increase_percentage,
            high_increase_percentage_end=last.high_increase_percentage,
            high_increase_percentage_change=change(
                "high_increase_percentage"
            ),

            high_decrease_percentage_start=first.high_decrease_percentage,
            high_decrease_percentage_end=last.high_decrease_percentage,
            high_decrease_percentage_change=change(
                "high_decrease_percentage"
            ),

            high_unchanged_percentage_start=first.high_unchanged_percentage,
            high_unchanged_percentage_end=last.high_unchanged_percentage,
            high_unchanged_percentage_change=change(
                "high_unchanged_percentage"
            ),

            average_total_absolute_percentage_movement_start=(
                first.average_total_absolute_percentage_movement
            ),
            average_total_absolute_percentage_movement_end=(
                last.average_total_absolute_percentage_movement
            ),
            average_total_absolute_percentage_movement_change=(
                last.average_total_absolute_percentage_movement
                - first.average_total_absolute_percentage_movement
            ),

            minimum_total_absolute_percentage_movement_start=(
                first.minimum_total_absolute_percentage_movement
            ),
            minimum_total_absolute_percentage_movement_end=(
                last.minimum_total_absolute_percentage_movement
            ),
            minimum_total_absolute_percentage_movement_change=(
                last.minimum_total_absolute_percentage_movement
                - first.minimum_total_absolute_percentage_movement
            ),

            maximum_total_absolute_percentage_movement_start=(
                first.maximum_total_absolute_percentage_movement
            ),
            maximum_total_absolute_percentage_movement_end=(
                last.maximum_total_absolute_percentage_movement
            ),
            maximum_total_absolute_percentage_movement_change=(
                last.maximum_total_absolute_percentage_movement
                - first.maximum_total_absolute_percentage_movement
            ),

            total_absolute_percentage_movement_start=(
                first.total_absolute_percentage_movement
            ),
            total_absolute_percentage_movement_end=(
                last.total_absolute_percentage_movement
            ),
            total_absolute_percentage_movement_change=(
                last.total_absolute_percentage_movement
                - first.total_absolute_percentage_movement
            ),

            total_absolute_percentage_movement=total_movement,
            mean_absolute_percentage_movement=mean_movement,
        )
    )


def compare_position_distribution_stability_trend_transition_comparison_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparison:
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison(
            overviews
        )
    )