from dataclasses import dataclass
from math import isclose
from typing import Sequence

from .position_distribution_stability_trend_transition_overview import (
    PositionDistributionStabilityTrendTransitionOverview,
)


LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

PERCENTAGE_MIN = 0.0
PERCENTAGE_MAX = 100.0
PERCENTAGE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparison:
    overview_count: int

    low_movement_percentage_start: float
    low_movement_percentage_end: float
    low_movement_percentage_change: float

    medium_movement_percentage_start: float
    medium_movement_percentage_end: float
    medium_movement_percentage_change: float

    high_movement_percentage_start: float
    high_movement_percentage_end: float
    high_movement_percentage_change: float

    average_total_absolute_percentage_change_start: float
    average_total_absolute_percentage_change_end: float
    average_total_absolute_percentage_change_change: float

    minimum_total_absolute_percentage_change_start: float
    minimum_total_absolute_percentage_change_end: float
    minimum_total_absolute_percentage_change_change: float

    maximum_total_absolute_percentage_change_start: float
    maximum_total_absolute_percentage_change_end: float
    maximum_total_absolute_percentage_change_change: float

    total_absolute_percentage_change_start: float
    total_absolute_percentage_change_end: float
    total_absolute_percentage_change_change: float

    total_absolute_percentage_movement: float
    mean_absolute_percentage_movement: float


def _validate_percentage(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < PERCENTAGE_MIN or value > PERCENTAGE_MAX:
        raise ValueError(
            f"{field_name} must be between "
            f"{PERCENTAGE_MIN} and {PERCENTAGE_MAX}."
        )


def _validate_nonnegative(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_overview(
    overview: PositionDistributionStabilityTrendTransitionOverview,
) -> None:
    if not isinstance(
        overview,
        PositionDistributionStabilityTrendTransitionOverview,
    ):
        raise TypeError(
            "overview must be a "
            "PositionDistributionStabilityTrendTransitionOverview."
        )

    if overview.transition_count < 0:
        raise ValueError("transition_count must be non-negative.")

    for field_name in (
        "low_movement_percentage",
        "medium_movement_percentage",
        "high_movement_percentage",
    ):
        _validate_percentage(
            getattr(overview, field_name),
            field_name,
        )

    percentage_total = (
        overview.low_movement_percentage
        + overview.medium_movement_percentage
        + overview.high_movement_percentage
    )

    if not isclose(
        percentage_total,
        100.0,
        abs_tol=PERCENTAGE_TOLERANCE,
    ):
        if overview.transition_count != 0:
            raise ValueError(
                "Movement percentages must sum to 100."
            )

    for field_name in (
        "average_total_absolute_percentage_change",
        "minimum_total_absolute_percentage_change",
        "maximum_total_absolute_percentage_change",
        "total_absolute_percentage_change",
    ):
        _validate_nonnegative(
            getattr(overview, field_name),
            field_name,
        )

    if (
        overview.minimum_total_absolute_percentage_change
        > overview.maximum_total_absolute_percentage_change
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_change "
            "cannot exceed maximum_total_absolute_percentage_change."
        )


def _validate_overviews(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> None:
    if not isinstance(overviews, (tuple, list)):
        raise TypeError("overviews must be a tuple or list.")

    for overview in overviews:
        _validate_overview(overview)


def _percentage_change(start: float, end: float) -> float:
    return end - start


def _calculate_total_absolute_percentage_movement(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> float:
    if len(overviews) < 2:
        return 0.0

    total = 0.0

    for previous, current in zip(overviews, overviews[1:]):
        total += abs(
            current.low_movement_percentage
            - previous.low_movement_percentage
        )
        total += abs(
            current.medium_movement_percentage
            - previous.medium_movement_percentage
        )
        total += abs(
            current.high_movement_percentage
            - previous.high_movement_percentage
        )

    return total


def _calculate_mean_absolute_percentage_movement(
    total_movement: float,
    overview_count: int,
) -> float:
    transition_count = max(overview_count - 1, 0)

    if transition_count == 0:
        return 0.0

    return total_movement / transition_count


def build_position_distribution_stability_trend_transition_comparison(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> PositionDistributionStabilityTrendTransitionComparison:
    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count == 0:
        return PositionDistributionStabilityTrendTransitionComparison(
            overview_count=0,
            low_movement_percentage_start=0.0,
            low_movement_percentage_end=0.0,
            low_movement_percentage_change=0.0,
            medium_movement_percentage_start=0.0,
            medium_movement_percentage_end=0.0,
            medium_movement_percentage_change=0.0,
            high_movement_percentage_start=0.0,
            high_movement_percentage_end=0.0,
            high_movement_percentage_change=0.0,
            average_total_absolute_percentage_change_start=0.0,
            average_total_absolute_percentage_change_end=0.0,
            average_total_absolute_percentage_change_change=0.0,
            minimum_total_absolute_percentage_change_start=0.0,
            minimum_total_absolute_percentage_change_end=0.0,
            minimum_total_absolute_percentage_change_change=0.0,
            maximum_total_absolute_percentage_change_start=0.0,
            maximum_total_absolute_percentage_change_end=0.0,
            maximum_total_absolute_percentage_change_change=0.0,
            total_absolute_percentage_change_start=0.0,
            total_absolute_percentage_change_end=0.0,
            total_absolute_percentage_change_change=0.0,
            total_absolute_percentage_movement=0.0,
            mean_absolute_percentage_movement=0.0,
        )

    start = overviews[0]
    end = overviews[-1]

    total_movement = _calculate_total_absolute_percentage_movement(
        overviews
    )

    mean_movement = _calculate_mean_absolute_percentage_movement(
        total_movement,
        overview_count,
    )

    return PositionDistributionStabilityTrendTransitionComparison(
        overview_count=overview_count,

        low_movement_percentage_start=(
            start.low_movement_percentage
        ),
        low_movement_percentage_end=(
            end.low_movement_percentage
        ),
        low_movement_percentage_change=_percentage_change(
            start.low_movement_percentage,
            end.low_movement_percentage,
        ),

        medium_movement_percentage_start=(
            start.medium_movement_percentage
        ),
        medium_movement_percentage_end=(
            end.medium_movement_percentage
        ),
        medium_movement_percentage_change=_percentage_change(
            start.medium_movement_percentage,
            end.medium_movement_percentage,
        ),

        high_movement_percentage_start=(
            start.high_movement_percentage
        ),
        high_movement_percentage_end=(
            end.high_movement_percentage
        ),
        high_movement_percentage_change=_percentage_change(
            start.high_movement_percentage,
            end.high_movement_percentage,
        ),

        average_total_absolute_percentage_change_start=(
            start.average_total_absolute_percentage_change
        ),
        average_total_absolute_percentage_change_end=(
            end.average_total_absolute_percentage_change
        ),
        average_total_absolute_percentage_change_change=_percentage_change(
            start.average_total_absolute_percentage_change,
            end.average_total_absolute_percentage_change,
        ),

        minimum_total_absolute_percentage_change_start=(
            start.minimum_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change_end=(
            end.minimum_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change_change=_percentage_change(
            start.minimum_total_absolute_percentage_change,
            end.minimum_total_absolute_percentage_change,
        ),

        maximum_total_absolute_percentage_change_start=(
            start.maximum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change_end=(
            end.maximum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change_change=_percentage_change(
            start.maximum_total_absolute_percentage_change,
            end.maximum_total_absolute_percentage_change,
        ),

        total_absolute_percentage_change_start=(
            start.total_absolute_percentage_change
        ),
        total_absolute_percentage_change_end=(
            end.total_absolute_percentage_change
        ),
        total_absolute_percentage_change_change=_percentage_change(
            start.total_absolute_percentage_change,
            end.total_absolute_percentage_change,
        ),

        total_absolute_percentage_movement=total_movement,
        mean_absolute_percentage_movement=mean_movement,
    )


def compare_position_distribution_stability_trend_transitions(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> PositionDistributionStabilityTrendTransitionComparison:
    return build_position_distribution_stability_trend_transition_comparison(
        overviews
    )