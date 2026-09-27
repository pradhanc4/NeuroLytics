"""
Phase 9.3.46

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Summary.

This module aggregates transition-level comparison records produced by
Phase 9.3.45.

The analysis is descriptive only. It does not perform prediction, ranking,
probability estimation, model training, or SQL mutation.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
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


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary:
    """
    Aggregated summary of Phase 9.3.45 transition records.
    """

    transition_count: int

    low_increase_increase_count: int
    low_increase_decrease_count: int
    low_increase_unchanged_count: int

    low_decrease_increase_count: int
    low_decrease_decrease_count: int
    low_decrease_unchanged_count: int

    low_unchanged_increase_count: int
    low_unchanged_decrease_count: int
    low_unchanged_unchanged_count: int

    medium_increase_increase_count: int
    medium_increase_decrease_count: int
    medium_increase_unchanged_count: int

    medium_decrease_increase_count: int
    medium_decrease_decrease_count: int
    medium_decrease_unchanged_count: int

    medium_unchanged_increase_count: int
    medium_unchanged_decrease_count: int
    medium_unchanged_unchanged_count: int

    high_increase_increase_count: int
    high_increase_decrease_count: int
    high_increase_unchanged_count: int

    high_decrease_increase_count: int
    high_decrease_decrease_count: int
    high_decrease_unchanged_count: int

    high_unchanged_increase_count: int
    high_unchanged_decrease_count: int
    high_unchanged_unchanged_count: int

    average_total_absolute_percentage_movement: float
    minimum_total_absolute_percentage_movement: float
    maximum_total_absolute_percentage_movement: float
    total_absolute_percentage_movement: float

    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
        ...
    ]


def _validate_nonnegative(
    value: float,
    field_name: str,
) -> None:
    """Validate that a numeric value is non-negative."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool.")

    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_percentage(
    value: float,
    field_name: str,
) -> None:
    """Validate a percentage value."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool.")

    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0 or value > 100:
        raise ValueError(
            f"{field_name} must be between 0 and 100."
        )


def _validate_transition(
    transition: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
) -> None:
    """Validate one Phase 9.3.45 transition record."""
    if not isinstance(
        transition,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
    ):
        raise TypeError(
            "Each transition must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition."
        )

    if isinstance(transition.transition_index, bool):
        raise TypeError(
            "transition_index must be an integer, not bool."
        )

    if not isinstance(transition.transition_index, int):
        raise TypeError(
            "transition_index must be an integer."
        )

    if transition.transition_index < 1:
        raise ValueError(
            "transition_index must be greater than or equal to 1."
        )

    for field_name in PERCENTAGE_FIELDS:
        start = getattr(
            transition,
            f"{field_name}_start",
        )
        end = getattr(
            transition,
            f"{field_name}_end",
        )
        change = getattr(
            transition,
            f"{field_name}_change",
        )

        _validate_percentage(
            start,
            f"{field_name}_start",
        )

        _validate_percentage(
            end,
            f"{field_name}_end",
        )

        if isinstance(change, bool):
            raise TypeError(
                f"{field_name}_change must be numeric, not bool."
            )

        if not isinstance(change, (int, float)):
            raise TypeError(
                f"{field_name}_change must be numeric."
            )

        expected_change = end - start

        if change != expected_change:
            raise ValueError(
                f"{field_name}_change must equal end - start."
            )

    for field_name in MOVEMENT_FIELDS:
        start = getattr(
            transition,
            f"{field_name}_start",
        )
        end = getattr(
            transition,
            f"{field_name}_end",
        )
        change = getattr(
            transition,
            f"{field_name}_change",
        )

        _validate_nonnegative(
            start,
            f"{field_name}_start",
        )

        _validate_nonnegative(
            end,
            f"{field_name}_end",
        )

        if isinstance(change, bool):
            raise TypeError(
                f"{field_name}_change must be numeric, not bool."
            )

        if not isinstance(change, (int, float)):
            raise TypeError(
                f"{field_name}_change must be numeric."
            )

        expected_change = end - start

        if change != expected_change:
            raise ValueError(
                f"{field_name}_change must equal end - start."
            )

    if (
        transition.minimum_total_absolute_percentage_movement_start
        > transition.maximum_total_absolute_percentage_movement_start
    ):
        raise ValueError(
            "Minimum starting movement cannot exceed maximum starting movement."
        )

    if (
        transition.minimum_total_absolute_percentage_movement_end
        > transition.maximum_total_absolute_percentage_movement_end
    ):
        raise ValueError(
            "Minimum ending movement cannot exceed maximum ending movement."
        )

    expected_total_movement = sum(
        abs(
            getattr(
                transition,
                f"{field_name}_change",
            )
        )
        for field_name in PERCENTAGE_FIELDS
    )

    if transition.total_absolute_percentage_movement != expected_total_movement:
        raise ValueError(
            "total_absolute_percentage_movement must equal the sum "
            "of absolute percentage changes."
        )


def _validate_detail(
    detail: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
) -> None:
    """Validate the complete Phase 9.3.45 detail object."""
    if not isinstance(
        detail,
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
    ):
        raise TypeError(
            "detail must be a "
            "PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail."
        )

    if isinstance(detail.overview_count, bool):
        raise TypeError(
            "overview_count must be an integer, not bool."
        )

    if not isinstance(detail.overview_count, int):
        raise TypeError(
            "overview_count must be an integer."
        )

    if detail.overview_count < 0:
        raise ValueError(
            "overview_count must be non-negative."
        )

    if isinstance(detail.transition_count, bool):
        raise TypeError(
            "transition_count must be an integer, not bool."
        )

    if not isinstance(detail.transition_count, int):
        raise TypeError(
            "transition_count must be an integer."
        )

    if detail.transition_count < 0:
        raise ValueError(
            "transition_count must be non-negative."
        )

    if not isinstance(detail.transitions, tuple):
        raise TypeError(
            "transitions must be a tuple."
        )

    expected_transition_count = max(
        detail.overview_count - 1,
        0,
    )

    if detail.transition_count != expected_transition_count:
        raise ValueError(
            "transition_count must equal max(overview_count - 1, 0)."
        )

    if len(detail.transitions) != detail.transition_count:
        raise ValueError(
            "The number of transitions must equal transition_count."
        )

    for expected_index, transition in enumerate(
        detail.transitions,
        start=1,
    ):
        _validate_transition(transition)

        if transition.transition_index != expected_index:
            raise ValueError(
                "Transition indexes must be sequential starting at 1."
            )


def _classify_direction(
    change: float,
) -> str:
    """Classify one percentage change."""
    if isinstance(change, bool):
        raise TypeError(
            "change must be numeric, not bool."
        )

    if not isinstance(change, (int, float)):
        raise TypeError(
            "change must be numeric."
        )

    if change > 0:
        return DIRECTION_INCREASE

    if change < 0:
        return DIRECTION_DECREASE

    return DIRECTION_UNCHANGED


def _calculate_direction_counts(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
        ...
    ],
) -> dict[str, int]:
    """
    Calculate INCREASE/DECREASE/UNCHANGED counts for one percentage field.
    """
    counts = {
        DIRECTION_INCREASE: 0,
        DIRECTION_DECREASE: 0,
        DIRECTION_UNCHANGED: 0,
    }

    for transition in transitions:
        direction = _classify_direction(
            getattr(
                transition,
                "change",
            )
        )
        counts[direction] += 1

    return counts


def _calculate_all_direction_counts(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
        ...
    ],
) -> dict[str, dict[str, int]]:
    """Calculate direction counts for all nine percentage fields."""
    results: dict[str, dict[str, int]] = {}

    for field_name in PERCENTAGE_FIELDS:
        counts = {
            DIRECTION_INCREASE: 0,
            DIRECTION_DECREASE: 0,
            DIRECTION_UNCHANGED: 0,
        }

        for transition in transitions:
            change = getattr(
                transition,
                f"{field_name}_change",
            )

            direction = _classify_direction(change)
            counts[direction] += 1

        results[field_name] = counts

    return results


def _calculate_movement_metrics(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
        ...
    ],
) -> tuple[float, float, float, float]:
    """Calculate aggregate movement metrics."""
    if not transitions:
        return (
            0.0,
            0.0,
            0.0,
            0.0,
        )

    values = tuple(
        transition.total_absolute_percentage_movement
        for transition in transitions
    )

    return (
        sum(values) / len(values),
        min(values),
        max(values),
        sum(values),
    )


def summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
    detail: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary:
    """
    Aggregate Phase 9.3.45 transition records into a descriptive summary.
    """
    _validate_detail(detail)

    transitions = detail.transitions

    if not transitions:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary(
                transition_count=0,

                low_increase_increase_count=0,
                low_increase_decrease_count=0,
                low_increase_unchanged_count=0,

                low_decrease_increase_count=0,
                low_decrease_decrease_count=0,
                low_decrease_unchanged_count=0,

                low_unchanged_increase_count=0,
                low_unchanged_decrease_count=0,
                low_unchanged_unchanged_count=0,

                medium_increase_increase_count=0,
                medium_increase_decrease_count=0,
                medium_increase_unchanged_count=0,

                medium_decrease_increase_count=0,
                medium_decrease_decrease_count=0,
                medium_decrease_unchanged_count=0,

                medium_unchanged_increase_count=0,
                medium_unchanged_decrease_count=0,
                medium_unchanged_unchanged_count=0,

                high_increase_increase_count=0,
                high_increase_decrease_count=0,
                high_increase_unchanged_count=0,

                high_decrease_increase_count=0,
                high_decrease_decrease_count=0,
                high_decrease_unchanged_count=0,

                high_unchanged_increase_count=0,
                high_unchanged_decrease_count=0,
                high_unchanged_unchanged_count=0,

                average_total_absolute_percentage_movement=0.0,
                minimum_total_absolute_percentage_movement=0.0,
                maximum_total_absolute_percentage_movement=0.0,
                total_absolute_percentage_movement=0.0,

                transitions=(),
            )
        )

    direction_counts = _calculate_all_direction_counts(
        transitions
    )

    (
        average_movement,
        minimum_movement,
        maximum_movement,
        total_movement,
    ) = _calculate_movement_metrics(
        transitions
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary(
            transition_count=len(transitions),

            low_increase_increase_count=direction_counts[
                "low_increase_percentage"
            ][DIRECTION_INCREASE],
            low_increase_decrease_count=direction_counts[
                "low_increase_percentage"
            ][DIRECTION_DECREASE],
            low_increase_unchanged_count=direction_counts[
                "low_increase_percentage"
            ][DIRECTION_UNCHANGED],

            low_decrease_increase_count=direction_counts[
                "low_decrease_percentage"
            ][DIRECTION_INCREASE],
            low_decrease_decrease_count=direction_counts[
                "low_decrease_percentage"
            ][DIRECTION_DECREASE],
            low_decrease_unchanged_count=direction_counts[
                "low_decrease_percentage"
            ][DIRECTION_UNCHANGED],

            low_unchanged_increase_count=direction_counts[
                "low_unchanged_percentage"
            ][DIRECTION_INCREASE],
            low_unchanged_decrease_count=direction_counts[
                "low_unchanged_percentage"
            ][DIRECTION_DECREASE],
            low_unchanged_unchanged_count=direction_counts[
                "low_unchanged_percentage"
            ][DIRECTION_UNCHANGED],

            medium_increase_increase_count=direction_counts[
                "medium_increase_percentage"
            ][DIRECTION_INCREASE],
            medium_increase_decrease_count=direction_counts[
                "medium_increase_percentage"
            ][DIRECTION_DECREASE],
            medium_increase_unchanged_count=direction_counts[
                "medium_increase_percentage"
            ][DIRECTION_UNCHANGED],

            medium_decrease_increase_count=direction_counts[
                "medium_decrease_percentage"
            ][DIRECTION_INCREASE],
            medium_decrease_decrease_count=direction_counts[
                "medium_decrease_percentage"
            ][DIRECTION_DECREASE],
            medium_decrease_unchanged_count=direction_counts[
                "medium_decrease_percentage"
            ][DIRECTION_UNCHANGED],

            medium_unchanged_increase_count=direction_counts[
                "medium_unchanged_percentage"
            ][DIRECTION_INCREASE],
            medium_unchanged_decrease_count=direction_counts[
                "medium_unchanged_percentage"
            ][DIRECTION_DECREASE],
            medium_unchanged_unchanged_count=direction_counts[
                "medium_unchanged_percentage"
            ][DIRECTION_UNCHANGED],

            high_increase_increase_count=direction_counts[
                "high_increase_percentage"
            ][DIRECTION_INCREASE],
            high_increase_decrease_count=direction_counts[
                "high_increase_percentage"
            ][DIRECTION_DECREASE],
            high_increase_unchanged_count=direction_counts[
                "high_increase_percentage"
            ][DIRECTION_UNCHANGED],

            high_decrease_increase_count=direction_counts[
                "high_decrease_percentage"
            ][DIRECTION_INCREASE],
            high_decrease_decrease_count=direction_counts[
                "high_decrease_percentage"
            ][DIRECTION_DECREASE],
            high_decrease_unchanged_count=direction_counts[
                "high_decrease_percentage"
            ][DIRECTION_UNCHANGED],

            high_unchanged_increase_count=direction_counts[
                "high_unchanged_percentage"
            ][DIRECTION_INCREASE],
            high_unchanged_decrease_count=direction_counts[
                "high_unchanged_percentage"
            ][DIRECTION_DECREASE],
            high_unchanged_unchanged_count=direction_counts[
                "high_unchanged_percentage"
            ][DIRECTION_UNCHANGED],

            average_total_absolute_percentage_movement=average_movement,
            minimum_total_absolute_percentage_movement=minimum_movement,
            maximum_total_absolute_percentage_movement=maximum_movement,
            total_absolute_percentage_movement=total_movement,

            transitions=transitions,
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary(
    detail: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummary:
    """
    Getter wrapper for the Phase 9.3.46 summary.
    """
    return (
        summarize_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison(
            detail
        )
    )