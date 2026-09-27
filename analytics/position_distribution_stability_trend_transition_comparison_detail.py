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
class PositionDistributionStabilityTrendTransitionComparisonTransition:
    transition_index: int

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


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonDetail:
    overview_count: int
    transition_count: int
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonTransition,
        ...,
    ]


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

    if not isinstance(overview.transition_count, int):
        raise ValueError("transition_count must be an integer.")

    if isinstance(overview.transition_count, bool):
        raise ValueError("transition_count must be an integer.")

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

    if overview.transition_count == 0:
        if not isclose(
            percentage_total,
            0.0,
            abs_tol=PERCENTAGE_TOLERANCE,
        ):
            raise ValueError(
                "Movement percentages must be zero when transition_count is zero."
            )
    elif not isclose(
        percentage_total,
        100.0,
        abs_tol=PERCENTAGE_TOLERANCE,
    ):
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


def _calculate_change(start: float, end: float) -> float:
    return end - start


def _build_transition(
    transition_index: int,
    start: PositionDistributionStabilityTrendTransitionOverview,
    end: PositionDistributionStabilityTrendTransitionOverview,
) -> PositionDistributionStabilityTrendTransitionComparisonTransition:
    low_change = _calculate_change(
        start.low_movement_percentage,
        end.low_movement_percentage,
    )

    medium_change = _calculate_change(
        start.medium_movement_percentage,
        end.medium_movement_percentage,
    )

    high_change = _calculate_change(
        start.high_movement_percentage,
        end.high_movement_percentage,
    )

    average_change = _calculate_change(
        start.average_total_absolute_percentage_change,
        end.average_total_absolute_percentage_change,
    )

    minimum_change = _calculate_change(
        start.minimum_total_absolute_percentage_change,
        end.minimum_total_absolute_percentage_change,
    )

    maximum_change = _calculate_change(
        start.maximum_total_absolute_percentage_change,
        end.maximum_total_absolute_percentage_change,
    )

    total_change = _calculate_change(
        start.total_absolute_percentage_change,
        end.total_absolute_percentage_change,
    )

    total_absolute_movement = (
        abs(low_change)
        + abs(medium_change)
        + abs(high_change)
    )

    return PositionDistributionStabilityTrendTransitionComparisonTransition(
        transition_index=transition_index,

        low_movement_percentage_start=(
            start.low_movement_percentage
        ),
        low_movement_percentage_end=(
            end.low_movement_percentage
        ),
        low_movement_percentage_change=low_change,

        medium_movement_percentage_start=(
            start.medium_movement_percentage
        ),
        medium_movement_percentage_end=(
            end.medium_movement_percentage
        ),
        medium_movement_percentage_change=medium_change,

        high_movement_percentage_start=(
            start.high_movement_percentage
        ),
        high_movement_percentage_end=(
            end.high_movement_percentage
        ),
        high_movement_percentage_change=high_change,

        average_total_absolute_percentage_change_start=(
            start.average_total_absolute_percentage_change
        ),
        average_total_absolute_percentage_change_end=(
            end.average_total_absolute_percentage_change
        ),
        average_total_absolute_percentage_change_change=average_change,

        minimum_total_absolute_percentage_change_start=(
            start.minimum_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change_end=(
            end.minimum_total_absolute_percentage_change
        ),
        minimum_total_absolute_percentage_change_change=minimum_change,

        maximum_total_absolute_percentage_change_start=(
            start.maximum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change_end=(
            end.maximum_total_absolute_percentage_change
        ),
        maximum_total_absolute_percentage_change_change=maximum_change,

        total_absolute_percentage_change_start=(
            start.total_absolute_percentage_change
        ),
        total_absolute_percentage_change_end=(
            end.total_absolute_percentage_change
        ),
        total_absolute_percentage_change_change=total_change,

        total_absolute_percentage_movement=total_absolute_movement,
    )


def build_position_distribution_stability_trend_transition_comparison_detail(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonDetail:
    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count < 2:
        return PositionDistributionStabilityTrendTransitionComparisonDetail(
            overview_count=overview_count,
            transition_count=0,
            transitions=(),
        )

    transitions = tuple(
        _build_transition(
            transition_index=index,
            start=start,
            end=end,
        )
        for index, (start, end) in enumerate(
            zip(overviews, overviews[1:]),
            start=1,
        )
    )

    return PositionDistributionStabilityTrendTransitionComparisonDetail(
        overview_count=overview_count,
        transition_count=len(transitions),
        transitions=transitions,
    )


def get_position_distribution_stability_trend_transition_comparison_detail(
    overviews: Sequence[
        PositionDistributionStabilityTrendTransitionOverview
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonDetail:
    return build_position_distribution_stability_trend_transition_comparison_detail(
        overviews
    )