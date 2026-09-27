"""
Phase 9.3.42
Position Distribution Stability Trend Transition Comparison Overview Comparison Summary

Aggregates transition-level comparison records produced by Phase 9.3.41.

Descriptive statistical analysis only.
No prediction, ranking, probability generation, SQL mutation, or model training.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
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
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary:
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
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
        ...,
    ]


def _validate_nonnegative(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0:
        raise ValueError(f"{field_name} must be nonnegative.")


def _validate_percentage(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0 or value > 100.0:
        raise ValueError(f"{field_name} must be between 0 and 100.")


def _classify_direction(change: float) -> str:
    if isinstance(change, bool) or not isinstance(change, (int, float)):
        raise TypeError("change must be numeric.")

    if change > 0.0:
        return INCREASE

    if change < 0.0:
        return DECREASE

    return UNCHANGED


def _validate_transition(
    transition: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition
    ),
) -> None:
    if not isinstance(
        transition,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
    ):
        raise TypeError(
            "Each transition must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition."
        )

    if isinstance(transition.transition_index, bool) or not isinstance(
        transition.transition_index,
        int,
    ):
        raise TypeError("transition_index must be an integer.")

    if transition.transition_index < 1:
        raise ValueError("transition_index must be positive.")

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
        start_field = f"{field_name}_start"
        end_field = f"{field_name}_end"
        change_field = f"{field_name}_change"

        start_value = getattr(transition, start_field)
        end_value = getattr(transition, end_field)
        change_value = getattr(transition, change_field)

        _validate_percentage(start_value, start_field)
        _validate_percentage(end_value, end_field)

        if isinstance(change_value, bool) or not isinstance(
            change_value,
            (int, float),
        ):
            raise TypeError(f"{change_field} must be numeric.")

        expected_change = end_value - start_value

        if abs(change_value - expected_change) > 1e-9:
            raise ValueError(
                f"{change_field} must equal end minus start."
            )

    movement_fields = (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    )

    for field_name in movement_fields:
        start_field = f"{field_name}_start"
        end_field = f"{field_name}_end"
        change_field = f"{field_name}_change"

        start_value = getattr(transition, start_field)
        end_value = getattr(transition, end_field)
        change_value = getattr(transition, change_field)

        _validate_nonnegative(start_value, start_field)
        _validate_nonnegative(end_value, end_field)

        if isinstance(change_value, bool) or not isinstance(
            change_value,
            (int, float),
        ):
            raise TypeError(f"{change_field} must be numeric.")

        expected_change = end_value - start_value

        if abs(change_value - expected_change) > 1e-9:
            raise ValueError(
                f"{change_field} must equal end minus start."
            )

    if (
        transition.minimum_total_absolute_percentage_movement_start
        > transition.maximum_total_absolute_percentage_movement_start
    ):
        raise ValueError(
            "Starting minimum movement cannot exceed starting maximum movement."
        )

    if (
        transition.minimum_total_absolute_percentage_movement_end
        > transition.maximum_total_absolute_percentage_movement_end
    ):
        raise ValueError(
            "Ending minimum movement cannot exceed ending maximum movement."
        )

    _validate_nonnegative(
        transition.total_absolute_percentage_movement,
        "total_absolute_percentage_movement",
    )

    expected_total_movement = sum(
        abs(
            getattr(transition, f"{field_name}_change")
        )
        for field_name in percentage_fields
    )

    if (
        abs(
            transition.total_absolute_percentage_movement
            - expected_total_movement
        )
        > 1e-9
    ):
        raise ValueError(
            "total_absolute_percentage_movement is inconsistent "
            "with the direction percentage changes."
        )


def _validate_detail(
    detail: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail
    ),
) -> None:
    if not isinstance(
        detail,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail,
    ):
        raise TypeError(
            "detail must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail."
        )

    if isinstance(detail.overview_count, bool) or not isinstance(
        detail.overview_count,
        int,
    ):
        raise TypeError("overview_count must be an integer.")

    if detail.overview_count < 0:
        raise ValueError("overview_count must be nonnegative.")

    if isinstance(detail.transition_count, bool) or not isinstance(
        detail.transition_count,
        int,
    ):
        raise TypeError("transition_count must be an integer.")

    if detail.transition_count < 0:
        raise ValueError("transition_count must be nonnegative.")

    expected_transition_count = max(detail.overview_count - 1, 0)

    if detail.transition_count != expected_transition_count:
        raise ValueError(
            "transition_count must equal max(overview_count - 1, 0)."
        )

    if not isinstance(detail.transitions, tuple):
        raise TypeError("transitions must be a tuple.")

    if len(detail.transitions) != detail.transition_count:
        raise ValueError(
            "transitions length must equal transition_count."
        )

    for expected_index, transition in enumerate(
        detail.transitions,
        start=1,
    ):
        _validate_transition(transition)

        if transition.transition_index != expected_index:
            raise ValueError(
                "transition indexes must be sequential starting at 1."
            )


def _calculate_direction_counts(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
        ...,
    ],
) -> dict[str, int]:
    counts = {
        "low_increase_count": 0,
        "low_decrease_count": 0,
        "low_unchanged_count": 0,
        "medium_increase_count": 0,
        "medium_decrease_count": 0,
        "medium_unchanged_count": 0,
        "high_increase_count": 0,
        "high_decrease_count": 0,
        "high_unchanged_count": 0,
    }

    for transition in transitions:
        for prefix in ("low", "medium", "high"):
            change = getattr(
                transition,
                f"{prefix}_increase_percentage_change",
            )
            direction = _classify_direction(change)
            counts[f"{prefix}_{direction.lower()}_count"] += 1

            change = getattr(
                transition,
                f"{prefix}_decrease_percentage_change",
            )
            direction = _classify_direction(change)
            counts[f"{prefix}_{direction.lower()}_count"] += 1

            change = getattr(
                transition,
                f"{prefix}_unchanged_percentage_change",
            )
            direction = _classify_direction(change)
            counts[f"{prefix}_{direction.lower()}_count"] += 1

    return counts


def _calculate_movement_metrics(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
        ...,
    ],
) -> tuple[float, float, float, float]:
    if not transitions:
        return 0.0, 0.0, 0.0, 0.0

    movements = tuple(
        transition.total_absolute_percentage_movement
        for transition in transitions
    )

    return (
        sum(movements) / len(movements),
        min(movements),
        max(movements),
        sum(movements),
    )


def summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
    detail: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail
    ),
) -> (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary
):
    """
    Aggregate transition-level comparison detail into a descriptive summary.

    The supplied transition order is preserved.
    """

    _validate_detail(detail)

    transitions = detail.transitions

    if not transitions:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
                transition_count=0,
                low_increase_count=0,
                low_decrease_count=0,
                low_unchanged_count=0,
                medium_increase_count=0,
                medium_decrease_count=0,
                medium_unchanged_count=0,
                high_increase_count=0,
                high_decrease_count=0,
                high_unchanged_count=0,
                average_total_absolute_percentage_movement=0.0,
                minimum_total_absolute_percentage_movement=0.0,
                maximum_total_absolute_percentage_movement=0.0,
                total_absolute_percentage_movement=0.0,
                transitions=(),
            )
        )

    direction_counts = _calculate_direction_counts(transitions)

    (
        average_movement,
        minimum_movement,
        maximum_movement,
        total_movement,
    ) = _calculate_movement_metrics(transitions)

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary(
            transition_count=len(transitions),
            low_increase_count=direction_counts["low_increase_count"],
            low_decrease_count=direction_counts["low_decrease_count"],
            low_unchanged_count=direction_counts["low_unchanged_count"],
            medium_increase_count=direction_counts["medium_increase_count"],
            medium_decrease_count=direction_counts["medium_decrease_count"],
            medium_unchanged_count=direction_counts["medium_unchanged_count"],
            high_increase_count=direction_counts["high_increase_count"],
            high_decrease_count=direction_counts["high_decrease_count"],
            high_unchanged_count=direction_counts["high_unchanged_count"],
            average_total_absolute_percentage_movement=average_movement,
            minimum_total_absolute_percentage_movement=minimum_movement,
            maximum_total_absolute_percentage_movement=maximum_movement,
            total_absolute_percentage_movement=total_movement,
            transitions=transitions,
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_summary(
    detail: (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail
    ),
) -> (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonSummary
):
    """
    Convenience getter for the transition comparison summary.
    """

    return (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison(
            detail
        )
    )