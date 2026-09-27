from dataclasses import dataclass
from typing import Tuple

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
)


DIRECTION_INCREASE = "INCREASE"
DIRECTION_DECREASE = "DECREASE"
DIRECTION_UNCHANGED = "UNCHANGED"

DIRECTION_ORDER = (
    DIRECTION_INCREASE,
    DIRECTION_DECREASE,
    DIRECTION_UNCHANGED,
)


PERCENTAGE_FIELDS = (
    "low_increase_increase_percentage",
    "low_increase_decrease_percentage",
    "low_increase_unchanged_percentage",
    "low_decrease_increase_percentage",
    "low_decrease_decrease_percentage",
    "low_decrease_unchanged_percentage",
    "low_unchanged_increase_percentage",
    "low_unchanged_decrease_percentage",
    "low_unchanged_unchanged_percentage",
    "medium_increase_increase_percentage",
    "medium_increase_decrease_percentage",
    "medium_increase_unchanged_percentage",
    "medium_decrease_increase_percentage",
    "medium_decrease_decrease_percentage",
    "medium_decrease_unchanged_percentage",
    "medium_unchanged_increase_percentage",
    "medium_unchanged_decrease_percentage",
    "medium_unchanged_unchanged_percentage",
    "high_increase_increase_percentage",
    "high_increase_decrease_percentage",
    "high_increase_unchanged_percentage",
    "high_decrease_increase_percentage",
    "high_decrease_decrease_percentage",
    "high_decrease_unchanged_percentage",
    "high_unchanged_increase_percentage",
    "high_unchanged_decrease_percentage",
    "high_unchanged_unchanged_percentage",
)


MOVEMENT_FIELDS = (
    "average_total_absolute_percentage_movement",
    "minimum_total_absolute_percentage_movement",
    "maximum_total_absolute_percentage_movement",
    "total_absolute_percentage_movement",
)


DOMINANT_DIRECTION_FIELDS = (
    "dominant_low_increase_directions",
    "dominant_low_decrease_directions",
    "dominant_low_unchanged_directions",
    "dominant_medium_increase_directions",
    "dominant_medium_decrease_directions",
    "dominant_medium_unchanged_directions",
    "dominant_high_increase_directions",
    "dominant_high_decrease_directions",
    "dominant_high_unchanged_directions",
)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison:
    overview_count: int

    low_increase_increase_percentage_start: float
    low_increase_increase_percentage_end: float
    low_increase_increase_percentage_change: float
    low_increase_decrease_percentage_start: float
    low_increase_decrease_percentage_end: float
    low_increase_decrease_percentage_change: float
    low_increase_unchanged_percentage_start: float
    low_increase_unchanged_percentage_end: float
    low_increase_unchanged_percentage_change: float

    low_decrease_increase_percentage_start: float
    low_decrease_increase_percentage_end: float
    low_decrease_increase_percentage_change: float
    low_decrease_decrease_percentage_start: float
    low_decrease_decrease_percentage_end: float
    low_decrease_decrease_percentage_change: float
    low_decrease_unchanged_percentage_start: float
    low_decrease_unchanged_percentage_end: float
    low_decrease_unchanged_percentage_change: float

    low_unchanged_increase_percentage_start: float
    low_unchanged_increase_percentage_end: float
    low_unchanged_increase_percentage_change: float
    low_unchanged_decrease_percentage_start: float
    low_unchanged_decrease_percentage_end: float
    low_unchanged_decrease_percentage_change: float
    low_unchanged_unchanged_percentage_start: float
    low_unchanged_unchanged_percentage_end: float
    low_unchanged_unchanged_percentage_change: float

    medium_increase_increase_percentage_start: float
    medium_increase_increase_percentage_end: float
    medium_increase_increase_percentage_change: float
    medium_increase_decrease_percentage_start: float
    medium_increase_decrease_percentage_end: float
    medium_increase_decrease_percentage_change: float
    medium_increase_unchanged_percentage_start: float
    medium_increase_unchanged_percentage_end: float
    medium_increase_unchanged_percentage_change: float

    medium_decrease_increase_percentage_start: float
    medium_decrease_increase_percentage_end: float
    medium_decrease_increase_percentage_change: float
    medium_decrease_decrease_percentage_start: float
    medium_decrease_decrease_percentage_end: float
    medium_decrease_decrease_percentage_change: float
    medium_decrease_unchanged_percentage_start: float
    medium_decrease_unchanged_percentage_end: float
    medium_decrease_unchanged_percentage_change: float

    medium_unchanged_increase_percentage_start: float
    medium_unchanged_increase_percentage_end: float
    medium_unchanged_increase_percentage_change: float
    medium_unchanged_decrease_percentage_start: float
    medium_unchanged_decrease_percentage_end: float
    medium_unchanged_decrease_percentage_change: float
    medium_unchanged_unchanged_percentage_start: float
    medium_unchanged_unchanged_percentage_end: float
    medium_unchanged_unchanged_percentage_change: float

    high_increase_increase_percentage_start: float
    high_increase_increase_percentage_end: float
    high_increase_increase_percentage_change: float
    high_increase_decrease_percentage_start: float
    high_increase_decrease_percentage_end: float
    high_increase_decrease_percentage_change: float
    high_increase_unchanged_percentage_start: float
    high_increase_unchanged_percentage_end: float
    high_increase_unchanged_percentage_change: float

    high_decrease_increase_percentage_start: float
    high_decrease_increase_percentage_end: float
    high_decrease_increase_percentage_change: float
    high_decrease_decrease_percentage_start: float
    high_decrease_decrease_percentage_end: float
    high_decrease_decrease_percentage_change: float
    high_decrease_unchanged_percentage_start: float
    high_decrease_unchanged_percentage_end: float
    high_decrease_unchanged_percentage_change: float

    high_unchanged_increase_percentage_start: float
    high_unchanged_increase_percentage_end: float
    high_unchanged_increase_percentage_change: float
    high_unchanged_decrease_percentage_start: float
    high_unchanged_decrease_percentage_end: float
    high_unchanged_decrease_percentage_change: float
    high_unchanged_unchanged_percentage_start: float
    high_unchanged_unchanged_percentage_end: float
    high_unchanged_unchanged_percentage_change: float

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
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")

    if value < 0.0 or value > 100.0:
        raise ValueError(f"{field_name} must be between 0 and 100")


def _validate_nonnegative(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")

    if value < 0.0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_dominant_directions(
    directions: tuple[str, ...],
    field_name: str,
) -> None:
    if not isinstance(directions, tuple):
        raise TypeError(f"{field_name} must be a tuple")

    if len(set(directions)) != len(directions):
        raise ValueError(f"{field_name} must not contain duplicates")

    for direction in directions:
        if direction not in DIRECTION_ORDER:
            raise ValueError(
                f"{field_name} contains invalid direction: {direction}"
            )


def _validate_overview(
    overview: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
) -> None:
    if not isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
    ):
        raise TypeError(
            "Each overview must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview"
        )

    if isinstance(overview.transition_count, bool) or not isinstance(
        overview.transition_count,
        int,
    ):
        raise TypeError("transition_count must be an integer")

    if overview.transition_count < 0:
        raise ValueError("transition_count must be non-negative")

    for field in PERCENTAGE_FIELDS:
        _validate_percentage(
            getattr(overview, field),
            field,
        )

    for field in MOVEMENT_FIELDS:
        _validate_nonnegative(
            getattr(overview, field),
            field,
        )

    if (
        overview.minimum_total_absolute_percentage_movement
        > overview.maximum_total_absolute_percentage_movement
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_movement "
            "must not exceed maximum_total_absolute_percentage_movement"
        )

    for field in DOMINANT_DIRECTION_FIELDS:
        _validate_dominant_directions(
            getattr(overview, field),
            field,
        )

    if overview.transition_count == 0:
        for field in PERCENTAGE_FIELDS:
            if getattr(overview, field) != 0.0:
                raise ValueError(
                    f"{field} must be zero when transition_count is zero"
                )

        for field in MOVEMENT_FIELDS:
            if getattr(overview, field) != 0.0:
                raise ValueError(
                    f"{field} must be zero when transition_count is zero"
                )

        for field in DOMINANT_DIRECTION_FIELDS:
            if getattr(overview, field) != ():
                raise ValueError(
                    f"{field} must be empty when transition_count is zero"
                )


def _validate_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
        ...,
    ],
) -> None:
    if not isinstance(overviews, tuple):
        raise TypeError("overviews must be a tuple")

    for overview in overviews:
        _validate_overview(overview)


def _calculate_change(start: float, end: float) -> float:
    return end - start


def _calculate_total_absolute_percentage_movement(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
        ...,
    ],
) -> float:
    if len(overviews) < 2:
        return 0.0

    total = 0.0

    for index in range(1, len(overviews)):
        previous = overviews[index - 1]
        current = overviews[index]

        for field in PERCENTAGE_FIELDS:
            total += abs(
                getattr(current, field)
                - getattr(previous, field)
            )

    return total


def _calculate_mean_absolute_percentage_movement(
    total_absolute_percentage_movement: float,
    overview_count: int,
) -> float:
    transition_count = max(overview_count - 1, 0)

    if transition_count == 0:
        return 0.0

    return total_absolute_percentage_movement / transition_count


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison:
    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count == 0:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison(
                overview_count=0,
                **{
                    f"{field}_start": 0.0
                    for field in PERCENTAGE_FIELDS
                },
                **{
                    f"{field}_end": 0.0
                    for field in PERCENTAGE_FIELDS
                },
                **{
                    f"{field}_change": 0.0
                    for field in PERCENTAGE_FIELDS
                },
                **{
                    f"{field}_start": 0.0
                    for field in MOVEMENT_FIELDS
                },
                **{
                    f"{field}_end": 0.0
                    for field in MOVEMENT_FIELDS
                },
                **{
                    f"{field}_change": 0.0
                    for field in MOVEMENT_FIELDS
                },
                total_absolute_percentage_movement=0.0,
                mean_absolute_percentage_movement=0.0,
            )
        )

    first = overviews[0]
    last = overviews[-1]

    values = {
        "overview_count": overview_count,
    }

    for field in PERCENTAGE_FIELDS:
        start = getattr(first, field)
        end = getattr(last, field)

        values[f"{field}_start"] = start
        values[f"{field}_end"] = end
        values[f"{field}_change"] = _calculate_change(
            start,
            end,
        )

    for field in MOVEMENT_FIELDS:
        start = getattr(first, field)
        end = getattr(last, field)

        values[f"{field}_start"] = start
        values[f"{field}_end"] = end
        values[f"{field}_change"] = _calculate_change(
            start,
            end,
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
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison(
            **values
        )
    )


def compare_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overviews(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparison:
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison(
            overviews
        )
    )