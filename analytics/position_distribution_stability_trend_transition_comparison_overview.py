from dataclasses import dataclass

from .position_distribution_stability_trend_transition_comparison_summary import (
    PositionDistributionStabilityTrendTransitionComparisonSummary,
)


INCREASE = "INCREASE"
DECREASE = "DECREASE"
UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverview:
    transition_count: int

    low_increase_percentage: float
    low_decrease_percentage: float
    low_unchanged_percentage: float

    medium_increase_percentage: float
    medium_decrease_percentage: float
    medium_unchanged_percentage: float

    high_increase_percentage: float
    high_decrease_percentage: float
    high_unchanged_percentage: float

    average_total_absolute_percentage_movement: float
    minimum_total_absolute_percentage_movement: float
    maximum_total_absolute_percentage_movement: float
    total_absolute_percentage_movement: float

    dominant_low_directions: tuple[str, ...]
    dominant_medium_directions: tuple[str, ...]
    dominant_high_directions: tuple[str, ...]


def _validate_nonnegative(value: float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


def _validate_summary(
    summary: PositionDistributionStabilityTrendTransitionComparisonSummary,
) -> None:
    if not isinstance(
        summary,
        PositionDistributionStabilityTrendTransitionComparisonSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityTrendTransitionComparisonSummary."
        )

    if not isinstance(summary.transition_count, int):
        raise ValueError("transition_count must be an integer.")

    if isinstance(summary.transition_count, bool):
        raise ValueError("transition_count must be an integer.")

    if summary.transition_count < 0:
        raise ValueError("transition_count must be non-negative.")

    count_fields = (
        "low_increase_count",
        "low_decrease_count",
        "low_unchanged_count",
        "medium_increase_count",
        "medium_decrease_count",
        "medium_unchanged_count",
        "high_increase_count",
        "high_decrease_count",
        "high_unchanged_count",
    )

    for field_name in count_fields:
        value = getattr(summary, field_name)

        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer.")

        if value < 0:
            raise ValueError(f"{field_name} must be non-negative.")

    low_total = (
        summary.low_increase_count
        + summary.low_decrease_count
        + summary.low_unchanged_count
    )

    medium_total = (
        summary.medium_increase_count
        + summary.medium_decrease_count
        + summary.medium_unchanged_count
    )

    high_total = (
        summary.high_increase_count
        + summary.high_decrease_count
        + summary.high_unchanged_count
    )

    if low_total != summary.transition_count:
        raise ValueError(
            "LOW direction counts must sum to transition_count."
        )

    if medium_total != summary.transition_count:
        raise ValueError(
            "MEDIUM direction counts must sum to transition_count."
        )

    if high_total != summary.transition_count:
        raise ValueError(
            "HIGH direction counts must sum to transition_count."
        )

    for field_name in (
        "average_total_absolute_percentage_movement",
        "minimum_total_absolute_percentage_movement",
        "maximum_total_absolute_percentage_movement",
        "total_absolute_percentage_movement",
    ):
        _validate_nonnegative(
            getattr(summary, field_name),
            field_name,
        )

    if (
        summary.minimum_total_absolute_percentage_movement
        > summary.maximum_total_absolute_percentage_movement
    ):
        raise ValueError(
            "minimum_total_absolute_percentage_movement "
            "cannot exceed maximum_total_absolute_percentage_movement."
        )

    if not isinstance(summary.transitions, tuple):
        raise TypeError("transitions must be a tuple.")

    if len(summary.transitions) != summary.transition_count:
        raise ValueError(
            "The number of transitions must match transition_count."
        )


def _calculate_percentage(
    count: int,
    transition_count: int,
) -> float:
    if transition_count == 0:
        return 0.0

    return (count / transition_count) * 100.0


def _calculate_dominant_directions(
    increase_count: int,
    decrease_count: int,
    unchanged_count: int,
) -> tuple[str, ...]:
    maximum_count = max(
        increase_count,
        decrease_count,
        unchanged_count,
    )

    if maximum_count == 0:
        return ()

    directions = []

    if increase_count == maximum_count:
        directions.append(INCREASE)

    if decrease_count == maximum_count:
        directions.append(DECREASE)

    if unchanged_count == maximum_count:
        directions.append(UNCHANGED)

    return tuple(directions)


def build_position_distribution_stability_trend_transition_comparison_overview(
    summary: PositionDistributionStabilityTrendTransitionComparisonSummary,
) -> PositionDistributionStabilityTrendTransitionComparisonOverview:
    _validate_summary(summary)

    transition_count = summary.transition_count

    if transition_count == 0:
        return PositionDistributionStabilityTrendTransitionComparisonOverview(
            transition_count=0,

            low_increase_percentage=0.0,
            low_decrease_percentage=0.0,
            low_unchanged_percentage=0.0,

            medium_increase_percentage=0.0,
            medium_decrease_percentage=0.0,
            medium_unchanged_percentage=0.0,

            high_increase_percentage=0.0,
            high_decrease_percentage=0.0,
            high_unchanged_percentage=0.0,

            average_total_absolute_percentage_movement=0.0,
            minimum_total_absolute_percentage_movement=0.0,
            maximum_total_absolute_percentage_movement=0.0,
            total_absolute_percentage_movement=0.0,

            dominant_low_directions=(),
            dominant_medium_directions=(),
            dominant_high_directions=(),
        )

    return PositionDistributionStabilityTrendTransitionComparisonOverview(
        transition_count=transition_count,

        low_increase_percentage=_calculate_percentage(
            summary.low_increase_count,
            transition_count,
        ),
        low_decrease_percentage=_calculate_percentage(
            summary.low_decrease_count,
            transition_count,
        ),
        low_unchanged_percentage=_calculate_percentage(
            summary.low_unchanged_count,
            transition_count,
        ),

        medium_increase_percentage=_calculate_percentage(
            summary.medium_increase_count,
            transition_count,
        ),
        medium_decrease_percentage=_calculate_percentage(
            summary.medium_decrease_count,
            transition_count,
        ),
        medium_unchanged_percentage=_calculate_percentage(
            summary.medium_unchanged_count,
            transition_count,
        ),

        high_increase_percentage=_calculate_percentage(
            summary.high_increase_count,
            transition_count,
        ),
        high_decrease_percentage=_calculate_percentage(
            summary.high_decrease_count,
            transition_count,
        ),
        high_unchanged_percentage=_calculate_percentage(
            summary.high_unchanged_count,
            transition_count,
        ),

        average_total_absolute_percentage_movement=(
            summary.average_total_absolute_percentage_movement
        ),
        minimum_total_absolute_percentage_movement=(
            summary.minimum_total_absolute_percentage_movement
        ),
        maximum_total_absolute_percentage_movement=(
            summary.maximum_total_absolute_percentage_movement
        ),
        total_absolute_percentage_movement=(
            summary.total_absolute_percentage_movement
        ),

        dominant_low_directions=_calculate_dominant_directions(
            summary.low_increase_count,
            summary.low_decrease_count,
            summary.low_unchanged_count,
        ),
        dominant_medium_directions=_calculate_dominant_directions(
            summary.medium_increase_count,
            summary.medium_decrease_count,
            summary.medium_unchanged_count,
        ),
        dominant_high_directions=_calculate_dominant_directions(
            summary.high_increase_count,
            summary.high_decrease_count,
            summary.high_unchanged_count,
        ),
    )


def get_position_distribution_stability_trend_transition_comparison_overview(
    summary: PositionDistributionStabilityTrendTransitionComparisonSummary,
) -> PositionDistributionStabilityTrendTransitionComparisonOverview:
    return (
        build_position_distribution_stability_trend_transition_comparison_overview(
            summary
        )
    )