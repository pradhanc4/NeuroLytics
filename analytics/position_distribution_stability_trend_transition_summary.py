from dataclasses import dataclass
from typing import Tuple

from analytics.position_distribution_stability_trend_detail import (
    PositionDistributionStabilityTrendDetail,
    PositionDistributionStabilityTrendTransition,
)


LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

DEFAULT_LOW_MOVEMENT_THRESHOLD = 2.0
DEFAULT_HIGH_MOVEMENT_THRESHOLD = 5.0


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionSummary:
    transition_count: int

    low_movement_count: int
    medium_movement_count: int
    high_movement_count: int

    average_total_absolute_percentage_change: float
    minimum_total_absolute_percentage_change: float
    maximum_total_absolute_percentage_change: float
    total_absolute_percentage_change: float

    transitions: Tuple[
        PositionDistributionStabilityTrendTransition,
        ...,
    ]


def _validate_transition(
    transition: PositionDistributionStabilityTrendTransition,
) -> None:
    if not isinstance(
        transition,
        PositionDistributionStabilityTrendTransition,
    ):
        raise TypeError(
            "Each item must be a "
            "PositionDistributionStabilityTrendTransition."
        )

    if transition.transition_index < 1:
        raise ValueError(
            "transition_index must be at least 1."
        )

    if transition.total_absolute_percentage_change < 0:
        raise ValueError(
            "total_absolute_percentage_change must be non-negative."
        )


def _validate_detail(
    detail: PositionDistributionStabilityTrendDetail,
) -> None:
    if not isinstance(
        detail,
        PositionDistributionStabilityTrendDetail,
    ):
        raise TypeError(
            "detail must be a "
            "PositionDistributionStabilityTrendDetail."
        )

    if detail.summary_count < 0:
        raise ValueError(
            "summary_count must be non-negative."
        )

    if detail.transition_count < 0:
        raise ValueError(
            "transition_count must be non-negative."
        )

    if not isinstance(detail.transitions, tuple):
        raise TypeError(
            "transitions must be a tuple."
        )

    if len(detail.transitions) != detail.transition_count:
        raise ValueError(
            "transition_count must equal the number of transitions."
        )

    for transition in detail.transitions:
        _validate_transition(transition)

    expected_indexes = tuple(
        range(1, detail.transition_count + 1)
    )

    actual_indexes = tuple(
        transition.transition_index
        for transition in detail.transitions
    )

    if actual_indexes != expected_indexes:
        raise ValueError(
            "transition indexes must be sequential starting at 1."
        )


def classify_transition_movement(
    total_absolute_percentage_change: float,
    low_threshold: float = DEFAULT_LOW_MOVEMENT_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_MOVEMENT_THRESHOLD,
) -> str:
    if total_absolute_percentage_change < 0:
        raise ValueError(
            "total_absolute_percentage_change must be non-negative."
        )

    if low_threshold < 0:
        raise ValueError(
            "low_threshold must be non-negative."
        )

    if high_threshold <= low_threshold:
        raise ValueError(
            "high_threshold must be greater than low_threshold."
        )

    if total_absolute_percentage_change < low_threshold:
        return LOW

    if total_absolute_percentage_change < high_threshold:
        return MEDIUM

    return HIGH


def _calculate_movement_counts(
    transitions: Tuple[
        PositionDistributionStabilityTrendTransition,
        ...,
    ],
    low_threshold: float,
    high_threshold: float,
) -> Tuple[int, int, int]:
    low_count = 0
    medium_count = 0
    high_count = 0

    for transition in transitions:
        movement_level = classify_transition_movement(
            transition.total_absolute_percentage_change,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )

        if movement_level == LOW:
            low_count += 1
        elif movement_level == MEDIUM:
            medium_count += 1
        else:
            high_count += 1

    return low_count, medium_count, high_count


def _calculate_metrics(
    transitions: Tuple[
        PositionDistributionStabilityTrendTransition,
        ...,
    ],
) -> Tuple[float, float, float, float]:
    if not transitions:
        return 0.0, 0.0, 0.0, 0.0

    values = tuple(
        transition.total_absolute_percentage_change
        for transition in transitions
    )

    total = sum(values)
    average = total / len(values)
    minimum = min(values)
    maximum = max(values)

    return average, minimum, maximum, total


def summarize_position_distribution_stability_trend_transitions(
    detail: PositionDistributionStabilityTrendDetail,
    low_threshold: float = DEFAULT_LOW_MOVEMENT_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_MOVEMENT_THRESHOLD,
) -> PositionDistributionStabilityTrendTransitionSummary:
    _validate_detail(detail)

    if low_threshold < 0:
        raise ValueError(
            "low_threshold must be non-negative."
        )

    if high_threshold <= low_threshold:
        raise ValueError(
            "high_threshold must be greater than low_threshold."
        )

    transitions = detail.transitions

    low_count, medium_count, high_count = (
        _calculate_movement_counts(
            transitions,
            low_threshold,
            high_threshold,
        )
    )

    (
        average,
        minimum,
        maximum,
        total,
    ) = _calculate_metrics(transitions)

    return PositionDistributionStabilityTrendTransitionSummary(
        transition_count=detail.transition_count,
        low_movement_count=low_count,
        medium_movement_count=medium_count,
        high_movement_count=high_count,
        average_total_absolute_percentage_change=average,
        minimum_total_absolute_percentage_change=minimum,
        maximum_total_absolute_percentage_change=maximum,
        total_absolute_percentage_change=total,
        transitions=transitions,
    )


def get_position_distribution_stability_trend_transition_summary(
    summary: PositionDistributionStabilityTrendTransitionSummary,
) -> PositionDistributionStabilityTrendTransitionSummary:
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendTransitionSummary."
        )

    return summary