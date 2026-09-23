from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_stability_comparison_summary import (
    PositionDistributionStabilityComparisonSummary,
)


STABLE = "STABLE"
MODERATE = "MODERATE"
UNSTABLE = "UNSTABLE"

DEFAULT_STABLE_THRESHOLD = 2.0
DEFAULT_MODERATE_THRESHOLD = 5.0


@dataclass(frozen=True)
class PositionDistributionStabilityOverview:
    position_count: int
    stable_position_count: int
    moderate_position_count: int
    unstable_position_count: int
    stable_percentage: float
    moderate_percentage: float
    unstable_percentage: float
    total_absolute_change: float
    average_mean_absolute_change: float
    minimum_mean_absolute_change: float
    maximum_mean_absolute_change: float
    overall_stability_level: str


def _validate_summary(
    summary: PositionDistributionStabilityComparisonSummary,
) -> None:
    if not isinstance(
        summary,
        PositionDistributionStabilityComparisonSummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionDistributionStabilityComparisonSummary."
        )

    if summary.position_count < 0:
        raise ValueError("position_count cannot be negative.")

    if summary.stable_position_count < 0:
        raise ValueError(
            "stable_position_count cannot be negative."
        )

    if summary.moderate_position_count < 0:
        raise ValueError(
            "moderate_position_count cannot be negative."
        )

    if summary.unstable_position_count < 0:
        raise ValueError(
            "unstable_position_count cannot be negative."
        )

    if (
        summary.stable_position_count
        + summary.moderate_position_count
        + summary.unstable_position_count
        != summary.position_count
    ):
        raise ValueError(
            "Stability classification counts must equal "
            "position_count."
        )

    if summary.total_absolute_change < 0:
        raise ValueError(
            "total_absolute_change cannot be negative."
        )

    if summary.average_mean_absolute_change < 0:
        raise ValueError(
            "average_mean_absolute_change cannot be negative."
        )

    if summary.minimum_mean_absolute_change < 0:
        raise ValueError(
            "minimum_mean_absolute_change cannot be negative."
        )

    if summary.maximum_mean_absolute_change < 0:
        raise ValueError(
            "maximum_mean_absolute_change cannot be negative."
        )

    if (
        summary.minimum_mean_absolute_change
        > summary.maximum_mean_absolute_change
    ):
        raise ValueError(
            "minimum_mean_absolute_change cannot exceed "
            "maximum_mean_absolute_change."
        )


def classify_overall_stability(
    average_mean_absolute_change: float,
    stable_threshold: float = DEFAULT_STABLE_THRESHOLD,
    unstable_threshold: float = DEFAULT_MODERATE_THRESHOLD,
) -> str:
    if average_mean_absolute_change < 0:
        raise ValueError(
            "average_mean_absolute_change cannot be negative."
        )

    if stable_threshold < 0:
        raise ValueError(
            "stable_threshold cannot be negative."
        )

    if unstable_threshold < stable_threshold:
        raise ValueError(
            "unstable_threshold cannot be below "
            "stable_threshold."
        )

    if average_mean_absolute_change < stable_threshold:
        return STABLE

    if average_mean_absolute_change < unstable_threshold:
        return MODERATE

    return UNSTABLE


def _calculate_percentage(
    count: int,
    total: int,
) -> float:
    if count < 0:
        raise ValueError("count cannot be negative.")

    if total < 0:
        raise ValueError("total cannot be negative.")

    if total == 0:
        return 0.0

    return (count / total) * 100.0


def build_position_distribution_stability_overview(
    summary: PositionDistributionStabilityComparisonSummary,
    stable_threshold: float = DEFAULT_STABLE_THRESHOLD,
    unstable_threshold: float = DEFAULT_MODERATE_THRESHOLD,
) -> PositionDistributionStabilityOverview:
    _validate_summary(summary)

    if stable_threshold < 0:
        raise ValueError(
            "stable_threshold cannot be negative."
        )

    if unstable_threshold < stable_threshold:
        raise ValueError(
            "unstable_threshold cannot be below "
            "stable_threshold."
        )

    stable_percentage = _calculate_percentage(
        summary.stable_position_count,
        summary.position_count,
    )

    moderate_percentage = _calculate_percentage(
        summary.moderate_position_count,
        summary.position_count,
    )

    unstable_percentage = _calculate_percentage(
        summary.unstable_position_count,
        summary.position_count,
    )

    overall_stability_level = classify_overall_stability(
        summary.average_mean_absolute_change,
        stable_threshold=stable_threshold,
        unstable_threshold=unstable_threshold,
    )

    return PositionDistributionStabilityOverview(
        position_count=summary.position_count,
        stable_position_count=summary.stable_position_count,
        moderate_position_count=summary.moderate_position_count,
        unstable_position_count=summary.unstable_position_count,
        stable_percentage=stable_percentage,
        moderate_percentage=moderate_percentage,
        unstable_percentage=unstable_percentage,
        total_absolute_change=summary.total_absolute_change,
        average_mean_absolute_change=(
            summary.average_mean_absolute_change
        ),
        minimum_mean_absolute_change=(
            summary.minimum_mean_absolute_change
        ),
        maximum_mean_absolute_change=(
            summary.maximum_mean_absolute_change
        ),
        overall_stability_level=overall_stability_level,
    )