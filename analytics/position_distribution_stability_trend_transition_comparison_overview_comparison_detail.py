"""
Phase 9.3.41
Position Distribution Stability Trend Transition Comparison Overview Comparison Detail

Descriptive statistical analysis only.
No prediction, ranking, probability generation, SQL mutation, or model training.
"""

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
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition:
    transition_index: int

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


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail:
    overview_count: int
    transition_count: int
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
        ...,
    ]


def _validate_percentage(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0 or value > 100.0:
        raise ValueError(f"{field_name} must be between 0 and 100.")


def _validate_nonnegative(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if value < 0.0:
        raise ValueError(f"{field_name} must be nonnegative.")


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

    if isinstance(overview.transition_count, bool) or not isinstance(
        overview.transition_count,
        int,
    ):
        raise TypeError("transition_count must be an integer.")

    if overview.transition_count < 0:
        raise ValueError("transition_count must be nonnegative.")

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

    if overview.transition_count == 0:
        for field_name in percentage_fields:
            if getattr(overview, field_name) != 0.0:
                raise ValueError(
                    f"{field_name} must be zero when transition_count is zero."
                )
    else:
        for prefix in ("low", "medium", "high"):
            total = (
                getattr(overview, f"{prefix}_increase_percentage")
                + getattr(overview, f"{prefix}_decrease_percentage")
                + getattr(overview, f"{prefix}_unchanged_percentage")
            )

            if abs(total - 100.0) > 1e-9:
                raise ValueError(
                    f"{prefix} direction percentages must sum to 100."
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
            "minimum_total_absolute_percentage_movement "
            "cannot exceed maximum_total_absolute_percentage_movement."
        )

    if not isinstance(overview.dominant_low_directions, tuple):
        raise TypeError("dominant_low_directions must be a tuple.")

    if not isinstance(overview.dominant_medium_directions, tuple):
        raise TypeError("dominant_medium_directions must be a tuple.")

    if not isinstance(overview.dominant_high_directions, tuple):
        raise TypeError("dominant_high_directions must be a tuple.")

    for field_name in (
        "dominant_low_directions",
        "dominant_medium_directions",
        "dominant_high_directions",
    ):
        directions = getattr(overview, field_name)

        for direction in directions:
            if direction not in DIRECTION_ORDER:
                raise ValueError(
                    f"{field_name} contains an invalid direction: {direction}."
                )

        if len(set(directions)) != len(directions):
            raise ValueError(
                f"{field_name} must not contain duplicate directions."
            )

    if overview.transition_count == 0:
        if overview.dominant_low_directions:
            raise ValueError(
                "dominant_low_directions must be empty when "
                "transition_count is zero."
            )

        if overview.dominant_medium_directions:
            raise ValueError(
                "dominant_medium_directions must be empty when "
                "transition_count is zero."
            )

        if overview.dominant_high_directions:
            raise ValueError(
                "dominant_high_directions must be empty when "
                "transition_count is zero."
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


def _calculate_change(start: float, end: float) -> float:
    return end - start


def _build_transition(
    start: PositionDistributionStabilityTrendTransitionComparisonOverview,
    end: PositionDistributionStabilityTrendTransitionComparisonOverview,
    transition_index: int,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition:

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

    values = {
        "transition_index": transition_index,
    }

    for field_name in percentage_fields:
        start_value = getattr(start, field_name)
        end_value = getattr(end, field_name)

        values[f"{field_name}_start"] = start_value
        values[f"{field_name}_end"] = end_value
        values[f"{field_name}_change"] = _calculate_change(
            start_value,
            end_value,
        )

    metric_fields = (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    )

    for field_name in metric_fields:
        start_value = getattr(start, field_name)
        end_value = getattr(end, field_name)

        values[f"{field_name}_start"] = start_value
        values[f"{field_name}_end"] = end_value
        values[f"{field_name}_change"] = _calculate_change(
            start_value,
            end_value,
        )

    movement = sum(
        abs(
            getattr(end, field_name)
            - getattr(start, field_name)
        )
        for field_name in percentage_fields
    )

    values["total_absolute_percentage_movement"] = movement

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition(
            **values
        )
    )


def _calculate_total_absolute_percentage_movement(
    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonTransition,
        ...,
    ],
) -> float:
    return sum(
        transition.total_absolute_percentage_movement
        for transition in transitions
    )


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail:
    """
    Build transition-by-transition comparison detail for supplied overviews.

    The caller controls the ordering of the supplied observations.
    No dates or temporal ordering are inferred.
    """

    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count == 0:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail(
                overview_count=0,
                transition_count=0,
                transitions=(),
            )
        )

    transitions = tuple(
        _build_transition(
            start=overviews[index],
            end=overviews[index + 1],
            transition_index=index + 1,
        )
        for index in range(overview_count - 1)
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail(
            overview_count=overview_count,
            transition_count=len(transitions),
            transitions=transitions,
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonDetail:
    """
    Convenience getter for transition comparison detail.
    """

    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_detail(
            overviews
        )
    )