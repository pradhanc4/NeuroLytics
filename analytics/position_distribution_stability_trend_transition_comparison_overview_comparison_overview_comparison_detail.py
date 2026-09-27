"""
Phase 9.3.45

Position Distribution Stability Trend Transition Comparison
Overview Comparison Overview Comparison Detail.

This module preserves transition-by-transition comparisons between
consecutive Phase 9.3.43 overview observations.

The supplied observation order is authoritative. No dates or chronology
are inferred.

This module is descriptive only. It does not perform prediction,
ranking, probability generation, model training, database mutation,
or SQL operations.
"""

from dataclasses import dataclass

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
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
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition:
    """
    One transition between two consecutive Phase 9.3.43 overviews.
    """

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
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail:
    """
    Transition-by-transition detail across ordered Phase 9.3.43 overviews.
    """

    overview_count: int
    transition_count: int

    transitions: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition,
        ...,
    ]


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


def _validate_dominant_directions(
    directions: tuple[str, ...],
    field_name: str,
    transition_count: int,
) -> None:
    """Validate dominant direction information."""
    if not isinstance(directions, tuple):
        raise TypeError(
            f"{field_name} must be a tuple."
        )

    if len(directions) == 0:
        if transition_count > 0:
            raise ValueError(
                f"{field_name} cannot be empty when transition_count "
                "is greater than zero."
            )
        return

    if len(set(directions)) != len(directions):
        raise ValueError(
            f"{field_name} cannot contain duplicate directions."
        )

    valid_directions = {
        "INCREASE",
        "DECREASE",
        "UNCHANGED",
    }

    for direction in directions:
        if direction not in valid_directions:
            raise ValueError(
                f"{field_name} contains invalid direction: "
                f"{direction!r}."
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

    _validate_dominant_directions(
        overview.dominant_low_directions,
        "dominant_low_directions",
        overview.transition_count,
    )

    _validate_dominant_directions(
        overview.dominant_medium_directions,
        "dominant_medium_directions",
        overview.transition_count,
    )

    _validate_dominant_directions(
        overview.dominant_high_directions,
        "dominant_high_directions",
        overview.transition_count,
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
    start: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
    end: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
) -> float:
    """
    Calculate absolute movement across all nine percentage fields
    for one transition.
    """
    return sum(
        abs(
            getattr(end, field_name)
            - getattr(start, field_name)
        )
        for field_name in PERCENTAGE_FIELDS
    )


def _build_transition(
    transition_index: int,
    start: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
    end: PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition:
    """Build one transition record."""
    values = {
        "transition_index": transition_index,
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

    values["total_absolute_percentage_movement"] = (
        _calculate_total_absolute_percentage_movement(
            start,
            end,
        )
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonTransition(
            **values
        )
    )


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail:
    """
    Build transition-by-transition comparison detail.

    For A, B, C:

        transition 1 = A -> B
        transition 2 = B -> C
    """
    _validate_overviews(overviews)

    overview_count = len(overviews)

    if overview_count < 2:
        return (
            PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail(
                overview_count=overview_count,
                transition_count=0,
                transitions=(),
            )
        )

    transitions = tuple(
        _build_transition(
            transition_index=index,
            start=overviews[index - 1],
            end=overviews[index],
        )
        for index in range(1, overview_count)
    )

    return (
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail(
            overview_count=overview_count,
            transition_count=len(transitions),
            transitions=transitions,
        )
    )


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
    overviews: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverview,
        ...,
    ],
) -> PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonDetail:
    """
    Convenience getter for Phase 9.3.45 detail.
    """
    return (
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail(
            overviews
        )
    )