from dataclasses import dataclass

from analytics.position_distribution_stability_overview import (
    PositionDistributionStabilityOverview,
)


STABLE = "STABLE"
MODERATE = "MODERATE"
UNSTABLE = "UNSTABLE"

STABLE_INCREASING = "STABLE_INCREASING"
STABILITY_DECREASING = "STABILITY_DECREASING"
MIXED = "MIXED"

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

DEFAULT_LOW_TREND_THRESHOLD = 2.0
DEFAULT_HIGH_TREND_THRESHOLD = 5.0

_PERCENTAGE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class PositionDistributionStabilityTrend:
    position_count: int
    window_count: int

    stable_percentage_start: float
    stable_percentage_end: float
    stable_percentage_change: float

    moderate_percentage_start: float
    moderate_percentage_end: float
    moderate_percentage_change: float

    unstable_percentage_start: float
    unstable_percentage_end: float
    unstable_percentage_change: float

    dominant_stability_levels: tuple[str, ...]

    stability_direction: str

    total_absolute_percentage_change: float
    mean_absolute_percentage_change: float

    trend_strength: str


def _validate_overview(
    overview: PositionDistributionStabilityOverview,
) -> None:
    if not isinstance(
        overview,
        PositionDistributionStabilityOverview,
    ):
        raise TypeError(
            "Each overview must be a "
            "PositionDistributionStabilityOverview."
        )

    if overview.position_count < 0:
        raise ValueError(
            "position_count cannot be negative."
        )

    if overview.stable_position_count < 0:
        raise ValueError(
            "stable_position_count cannot be negative."
        )

    if overview.moderate_position_count < 0:
        raise ValueError(
            "moderate_position_count cannot be negative."
        )

    if overview.unstable_position_count < 0:
        raise ValueError(
            "unstable_position_count cannot be negative."
        )

    if (
        overview.stable_position_count
        + overview.moderate_position_count
        + overview.unstable_position_count
        != overview.position_count
    ):
        raise ValueError(
            "Stability classification counts must equal "
            "position_count."
        )

    percentages = (
        overview.stable_percentage,
        overview.moderate_percentage,
        overview.unstable_percentage,
    )

    for percentage in percentages:
        if not 0.0 <= percentage <= 100.0:
            raise ValueError(
                "Stability percentages must be between 0 and 100."
            )

    percentage_total = sum(percentages)

    if overview.position_count > 0:
        if abs(percentage_total - 100.0) > _PERCENTAGE_TOLERANCE:
            raise ValueError(
                "Stability percentages must sum to 100."
            )
    else:
        if abs(percentage_total) > _PERCENTAGE_TOLERANCE:
            raise ValueError(
                "Empty overview percentages must all be zero."
            )

    if overview.total_absolute_change < 0:
        raise ValueError(
            "total_absolute_change cannot be negative."
        )

    if overview.average_mean_absolute_change < 0:
        raise ValueError(
            "average_mean_absolute_change cannot be negative."
        )

    if overview.minimum_mean_absolute_change < 0:
        raise ValueError(
            "minimum_mean_absolute_change cannot be negative."
        )

    if overview.maximum_mean_absolute_change < 0:
        raise ValueError(
            "maximum_mean_absolute_change cannot be negative."
        )

    if (
        overview.minimum_mean_absolute_change
        > overview.maximum_mean_absolute_change
    ):
        raise ValueError(
            "minimum_mean_absolute_change cannot exceed "
            "maximum_mean_absolute_change."
        )

    if overview.overall_stability_level not in (
        STABLE,
        MODERATE,
        UNSTABLE,
    ):
        raise ValueError(
            "overall_stability_level must be STABLE, "
            "MODERATE, or UNSTABLE."
        )


def _validate_overviews(
    overviews: tuple[PositionDistributionStabilityOverview, ...],
) -> None:
    for overview in overviews:
        _validate_overview(overview)

    if not overviews:
        return

    expected_position_count = overviews[0].position_count

    for overview in overviews[1:]:
        if overview.position_count != expected_position_count:
            raise ValueError(
                "All stability overviews must have the same "
                "position_count."
            )


def classify_trend_strength(
    mean_absolute_percentage_change: float,
    low_threshold: float = DEFAULT_LOW_TREND_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_TREND_THRESHOLD,
) -> str:
    if mean_absolute_percentage_change < 0:
        raise ValueError(
            "mean_absolute_percentage_change cannot be negative."
        )

    if low_threshold < 0:
        raise ValueError(
            "low_threshold cannot be negative."
        )

    if high_threshold < 0:
        raise ValueError(
            "high_threshold cannot be negative."
        )

    if low_threshold >= high_threshold:
        raise ValueError(
            "low_threshold must be less than high_threshold."
        )

    if mean_absolute_percentage_change < low_threshold:
        return LOW

    if mean_absolute_percentage_change < high_threshold:
        return MEDIUM

    return HIGH


def classify_stability_direction(
    stable_percentage_change: float,
    moderate_percentage_change: float,
    unstable_percentage_change: float,
) -> str:
    if (
        stable_percentage_change > 0
        and unstable_percentage_change < 0
    ):
        return STABLE_INCREASING

    if (
        stable_percentage_change < 0
        and unstable_percentage_change > 0
    ):
        return STABILITY_DECREASING

    if (
        stable_percentage_change == 0
        and moderate_percentage_change == 0
        and unstable_percentage_change == 0
    ):
        return STABLE

    return MIXED


def _calculate_dominant_stability_levels(
    overview: PositionDistributionStabilityOverview,
) -> tuple[str, ...]:
    values = {
        STABLE: overview.stable_percentage,
        MODERATE: overview.moderate_percentage,
        UNSTABLE: overview.unstable_percentage,
    }

    maximum_value = max(values.values())

    return tuple(
        level
        for level, value in values.items()
        if value == maximum_value
    )


def _calculate_total_absolute_percentage_change(
    overviews: tuple[PositionDistributionStabilityOverview, ...],
) -> float:
    if len(overviews) < 2:
        return 0.0

    total = 0.0

    for previous, current in zip(
        overviews,
        overviews[1:],
    ):
        total += abs(
            current.stable_percentage
            - previous.stable_percentage
        )
        total += abs(
            current.moderate_percentage
            - previous.moderate_percentage
        )
        total += abs(
            current.unstable_percentage
            - previous.unstable_percentage
        )

    return total


def _calculate_mean_absolute_percentage_change(
    overviews: tuple[PositionDistributionStabilityOverview, ...],
) -> float:
    if len(overviews) < 2:
        return 0.0

    total = _calculate_total_absolute_percentage_change(
        overviews
    )

    transition_count = len(overviews) - 1

    return total / transition_count


def build_position_distribution_stability_trend(
    overviews: tuple[PositionDistributionStabilityOverview, ...],
    low_threshold: float = DEFAULT_LOW_TREND_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_TREND_THRESHOLD,
) -> PositionDistributionStabilityTrend:
    if not isinstance(overviews, tuple):
        raise TypeError(
            "overviews must be a tuple of "
            "PositionDistributionStabilityOverview objects."
        )

    _validate_overviews(overviews)

    if low_threshold < 0:
        raise ValueError(
            "low_threshold cannot be negative."
        )

    if high_threshold < 0:
        raise ValueError(
            "high_threshold cannot be negative."
        )

    if low_threshold >= high_threshold:
        raise ValueError(
            "low_threshold must be less than high_threshold."
        )

    if not overviews:
        return PositionDistributionStabilityTrend(
            position_count=0,
            window_count=0,
            stable_percentage_start=0.0,
            stable_percentage_end=0.0,
            stable_percentage_change=0.0,
            moderate_percentage_start=0.0,
            moderate_percentage_end=0.0,
            moderate_percentage_change=0.0,
            unstable_percentage_start=0.0,
            unstable_percentage_end=0.0,
            unstable_percentage_change=0.0,
            dominant_stability_levels=(),
            stability_direction=STABLE,
            total_absolute_percentage_change=0.0,
            mean_absolute_percentage_change=0.0,
            trend_strength=LOW,
        )

    first = overviews[0]
    last = overviews[-1]

    stable_percentage_change = (
        last.stable_percentage
        - first.stable_percentage
    )

    moderate_percentage_change = (
        last.moderate_percentage
        - first.moderate_percentage
    )

    unstable_percentage_change = (
        last.unstable_percentage
        - first.unstable_percentage
    )

    total_absolute_percentage_change = (
        _calculate_total_absolute_percentage_change(
            overviews
        )
    )

    mean_absolute_percentage_change = (
        _calculate_mean_absolute_percentage_change(
            overviews
        )
    )

    return PositionDistributionStabilityTrend(
        position_count=first.position_count,
        window_count=len(overviews),
        stable_percentage_start=first.stable_percentage,
        stable_percentage_end=last.stable_percentage,
        stable_percentage_change=stable_percentage_change,
        moderate_percentage_start=first.moderate_percentage,
        moderate_percentage_end=last.moderate_percentage,
        moderate_percentage_change=moderate_percentage_change,
        unstable_percentage_start=first.unstable_percentage,
        unstable_percentage_end=last.unstable_percentage,
        unstable_percentage_change=unstable_percentage_change,
        dominant_stability_levels=(
            _calculate_dominant_stability_levels(last)
        ),
        stability_direction=classify_stability_direction(
            stable_percentage_change,
            moderate_percentage_change,
            unstable_percentage_change,
        ),
        total_absolute_percentage_change=(
            total_absolute_percentage_change
        ),
        mean_absolute_percentage_change=(
            mean_absolute_percentage_change
        ),
        trend_strength=classify_trend_strength(
            mean_absolute_percentage_change,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        ),
    )