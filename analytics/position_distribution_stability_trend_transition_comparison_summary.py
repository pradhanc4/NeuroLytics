from dataclasses import dataclass
from math import isclose

from .position_distribution_stability_trend_transition_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonTransition,
)


INCREASE = "INCREASE"
DECREASE = "DECREASE"
UNCHANGED = "UNCHANGED"

MOVEMENT_TOLERANCE = 1e-9


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonSummary:
    transition_count: int

    low_increase_count: int
    low_decrease_count: int
    low_unchanged_count: int

    medium_increase_count: int
    medium_decrease_count: int
    medium_unchanged_count: int

    high_increase_count: int
    high_decrease_count: int
    high_unchanged_count: int

    average_total_absolute_percentage_movement: float
    minimum_total_absolute_percentage_movement: float
    maximum_total_absolute_percentage_movement: float
    total_absolute_percentage_movement: float

    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonTransition,
        ...,
    ]


def _validate_nonnegative(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_transition(
    transition: PositionDistributionStabilityTrendTransitionComparisonTransition,
) -> None:
    if not isinstance(
        transition,
        PositionDistributionStabilityTrendTransitionComparisonTransition,
    ):
        raise TypeError(
            "transition must be a "
            "PositionDistributionStabilityTrendTransitionComparisonTransition."
        )

    if not isinstance(transition.transition_index, int):
        raise ValueError("transition_index must be an integer.")

    if isinstance(transition.transition_index, bool):
        raise ValueError("transition_index must be an integer.")

    if transition.transition_index < 1:
        raise ValueError("transition_index must be greater than or equal to 1.")

    for field_name in (
        "low_movement_percentage_start",
        "low_movement_percentage_end",
        "medium_movement_percentage_start",
        "medium_movement_percentage_end",
        "high_movement_percentage_start",
        "high_movement_percentage_end",
    ):
        value = getattr(transition, field_name)

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be numeric.")

        if value < 0 or value > 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

    for field_name in (
        "average_total_absolute_percentage_change_start",
        "average_total_absolute_percentage_change_end",
        "minimum_total_absolute_percentage_change_start",
        "minimum_total_absolute_percentage_change_end",
        "maximum_total_absolute_percentage_change_start",
        "maximum_total_absolute_percentage_change_end",
        "total_absolute_percentage_change_start",
        "total_absolute_percentage_change_end",
        "total_absolute_percentage_movement",
    ):
        _validate_nonnegative(
            getattr(transition, field_name),
            field_name,
        )

    if (
        transition.minimum_total_absolute_percentage_change_start
        > transition.maximum_total_absolute_percentage_change_start
    ):
        raise ValueError(
            "Starting minimum movement cannot exceed starting maximum movement."
        )

    if (
        transition.minimum_total_absolute_percentage_change_end
        > transition.maximum_total_absolute_percentage_change_end
    ):
        raise ValueError(
            "Ending minimum movement cannot exceed ending maximum movement."
        )

    expected_low_change = (
        transition.low_movement_percentage_end
        - transition.low_movement_percentage_start
    )

    expected_medium_change = (
        transition.medium_movement_percentage_end
        - transition.medium_movement_percentage_start
    )

    expected_high_change = (
        transition.high_movement_percentage_end
        - transition.high_movement_percentage_start
    )

    if not isclose(
        transition.low_movement_percentage_change,
        expected_low_change,
        abs_tol=MOVEMENT_TOLERANCE,
    ):
        raise ValueError(
            "low_movement_percentage_change is inconsistent."
        )

    if not isclose(
        transition.medium_movement_percentage_change,
        expected_medium_change,
        abs_tol=MOVEMENT_TOLERANCE,
    ):
        raise ValueError(
            "medium_movement_percentage_change is inconsistent."
        )

    if not isclose(
        transition.high_movement_percentage_change,
        expected_high_change,
        abs_tol=MOVEMENT_TOLERANCE,
    ):
        raise ValueError(
            "high_movement_percentage_change is inconsistent."
        )

    expected_movement = (
        abs(expected_low_change)
        + abs(expected_medium_change)
        + abs(expected_high_change)
    )

    if not isclose(
        transition.total_absolute_percentage_movement,
        expected_movement,
        abs_tol=MOVEMENT_TOLERANCE,
    ):
        raise ValueError(
            "total_absolute_percentage_movement is inconsistent."
        )


def _validate_detail(
    detail: PositionDistributionStabilityTrendTransitionComparisonDetail,
) -> None:
    if not isinstance(
        detail,
        PositionDistributionStabilityTrendTransitionComparisonDetail,
    ):
        raise TypeError(
            "detail must be a "
            "PositionDistributionStabilityTrendTransitionComparisonDetail."
        )

    if not isinstance(detail.overview_count, int):
        raise ValueError("overview_count must be an integer.")

    if isinstance(detail.overview_count, bool):
        raise ValueError("overview_count must be an integer.")

    if detail.overview_count < 0:
        raise ValueError("overview_count must be non-negative.")

    if not isinstance(detail.transition_count, int):
        raise ValueError("transition_count must be an integer.")

    if isinstance(detail.transition_count, bool):
        raise ValueError("transition_count must be an integer.")

    if detail.transition_count < 0:
        raise ValueError("transition_count must be non-negative.")

    if detail.transition_count != max(detail.overview_count - 1, 0):
        raise ValueError(
            "transition_count must equal max(overview_count - 1, 0)."
        )

    if not isinstance(detail.transitions, tuple):
        raise TypeError("transitions must be a tuple.")

    if len(detail.transitions) != detail.transition_count:
        raise ValueError(
            "The number of transitions must match transition_count."
        )

    expected_index = 1

    for transition in detail.transitions:
        _validate_transition(transition)

        if transition.transition_index != expected_index:
            raise ValueError(
                "Transition indexes must be sequential starting at 1."
            )

        expected_index += 1


def _classify_direction(change: float) -> str:
    if change > MOVEMENT_TOLERANCE:
        return INCREASE

    if change < -MOVEMENT_TOLERANCE:
        return DECREASE

    return UNCHANGED


def _calculate_direction_counts(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonTransition,
        ...,
    ],
) -> tuple[int, ...]:
    low_increase = 0
    low_decrease = 0
    low_unchanged = 0

    medium_increase = 0
    medium_decrease = 0
    medium_unchanged = 0

    high_increase = 0
    high_decrease = 0
    high_unchanged = 0

    for transition in transitions:
        low_direction = _classify_direction(
            transition.low_movement_percentage_change
        )

        if low_direction == INCREASE:
            low_increase += 1
        elif low_direction == DECREASE:
            low_decrease += 1
        else:
            low_unchanged += 1

        medium_direction = _classify_direction(
            transition.medium_movement_percentage_change
        )

        if medium_direction == INCREASE:
            medium_increase += 1
        elif medium_direction == DECREASE:
            medium_decrease += 1
        else:
            medium_unchanged += 1

        high_direction = _classify_direction(
            transition.high_movement_percentage_change
        )

        if high_direction == INCREASE:
            high_increase += 1
        elif high_direction == DECREASE:
            high_decrease += 1
        else:
            high_unchanged += 1

    return (
        low_increase,
        low_decrease,
        low_unchanged,
        medium_increase,
        medium_decrease,
        medium_unchanged,
        high_increase,
        high_decrease,
        high_unchanged,
    )


def _calculate_movement_metrics(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonTransition,
        ...,
    ],
) -> tuple[float, float, float, float]:
    if not transitions:
        return 0.0, 0.0, 0.0, 0.0

    movements = tuple(
        transition.total_absolute_percentage_movement
        for transition in transitions
    )

    total = sum(movements)
    minimum = min(movements)
    maximum = max(movements)
    average = total / len(movements)

    return average, minimum, maximum, total


def summarize_position_distribution_stability_trend_transition_comparisons(
    detail: PositionDistributionStabilityTrendTransitionComparisonDetail,
) -> PositionDistributionStabilityTrendTransitionComparisonSummary:
    _validate_detail(detail)

    transitions = detail.transitions

    (
        low_increase,
        low_decrease,
        low_unchanged,
        medium_increase,
        medium_decrease,
        medium_unchanged,
        high_increase,
        high_decrease,
        high_unchanged,
    ) = _calculate_direction_counts(transitions)

    (
        average_movement,
        minimum_movement,
        maximum_movement,
        total_movement,
    ) = _calculate_movement_metrics(transitions)

    return PositionDistributionStabilityTrendTransitionComparisonSummary(
        transition_count=detail.transition_count,

        low_increase_count=low_increase,
        low_decrease_count=low_decrease,
        low_unchanged_count=low_unchanged,

        medium_increase_count=medium_increase,
        medium_decrease_count=medium_decrease,
        medium_unchanged_count=medium_unchanged,

        high_increase_count=high_increase,
        high_decrease_count=high_decrease,
        high_unchanged_count=high_unchanged,

        average_total_absolute_percentage_movement=average_movement,
        minimum_total_absolute_percentage_movement=minimum_movement,
        maximum_total_absolute_percentage_movement=maximum_movement,
        total_absolute_percentage_movement=total_movement,

        transitions=transitions,
    )


def get_position_distribution_stability_trend_transition_comparison_summary(
    detail: PositionDistributionStabilityTrendTransitionComparisonDetail,
) -> PositionDistributionStabilityTrendTransitionComparisonSummary:
    return (
        summarize_position_distribution_stability_trend_transition_comparisons(
            detail
        )
    )