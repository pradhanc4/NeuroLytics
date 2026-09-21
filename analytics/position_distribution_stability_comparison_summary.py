from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_stability_comparison import (
    PositionDistributionStabilityComparison,
)


@dataclass(frozen=True)
class PositionDistributionStabilityComparisonSummary:
    position_count: int
    stable_position_count: int
    moderate_position_count: int
    unstable_position_count: int
    total_absolute_change: float
    average_mean_absolute_change: float
    minimum_mean_absolute_change: float
    maximum_mean_absolute_change: float
    comparisons: tuple[PositionDistributionStabilityComparison, ...]


def _validate_comparison(
    comparison: PositionDistributionStabilityComparison,
) -> None:
    if comparison.position == "":
        raise ValueError(
            "Position must not be empty."
        )

    if comparison.digit_count < 0:
        raise ValueError(
            "Digit count must be greater than or equal to zero."
        )

    if comparison.stable_digit_count < 0:
        raise ValueError(
            "Stable digit count must be greater than or equal to zero."
        )

    if comparison.moderate_digit_count < 0:
        raise ValueError(
            "Moderate digit count must be greater than or equal to zero."
        )

    if comparison.unstable_digit_count < 0:
        raise ValueError(
            "Unstable digit count must be greater than or equal to zero."
        )

    classified_digit_count = (
        comparison.stable_digit_count
        + comparison.moderate_digit_count
        + comparison.unstable_digit_count
    )

    if classified_digit_count != comparison.digit_count:
        raise ValueError(
            "Stability classification counts must equal digit count."
        )

    if comparison.total_absolute_change < 0:
        raise ValueError(
            "Total absolute change must be greater than or equal to zero."
        )

    if comparison.average_mean_absolute_change < 0:
        raise ValueError(
            "Average mean absolute change must be greater than "
            "or equal to zero."
        )

    if comparison.minimum_mean_absolute_change < 0:
        raise ValueError(
            "Minimum mean absolute change must be greater than "
            "or equal to zero."
        )

    if comparison.maximum_mean_absolute_change < 0:
        raise ValueError(
            "Maximum mean absolute change must be greater than "
            "or equal to zero."
        )

    if (
        comparison.minimum_mean_absolute_change
        > comparison.maximum_mean_absolute_change
    ):
        raise ValueError(
            "Minimum mean absolute change must not exceed "
            "maximum mean absolute change."
        )

    if comparison.stability_level not in {
        "STABLE",
        "MODERATE",
        "UNSTABLE",
    }:
        raise ValueError(
            "Stability level must be STABLE, MODERATE, or UNSTABLE."
        )


def summarize_position_distribution_stability_comparisons(
    comparisons: tuple[
        PositionDistributionStabilityComparison,
        ...,
    ],
) -> PositionDistributionStabilityComparisonSummary:
    positions: set[str] = set()

    stable_position_count = 0
    moderate_position_count = 0
    unstable_position_count = 0

    total_absolute_change = 0.0
    total_mean_absolute_change = 0.0

    minimum_mean_absolute_change = 0.0
    maximum_mean_absolute_change = 0.0

    for comparison in comparisons:
        _validate_comparison(comparison)

        if comparison.position in positions:
            raise ValueError(
                "Duplicate position comparisons are not allowed."
            )

        positions.add(comparison.position)

        if comparison.stability_level == "STABLE":
            stable_position_count += 1
        elif comparison.stability_level == "MODERATE":
            moderate_position_count += 1
        else:
            unstable_position_count += 1

        total_absolute_change += (
            comparison.total_absolute_change
        )

        total_mean_absolute_change += (
            comparison.average_mean_absolute_change
        )

        if len(positions) == 1:
            minimum_mean_absolute_change = (
                comparison.average_mean_absolute_change
            )
            maximum_mean_absolute_change = (
                comparison.average_mean_absolute_change
            )
        else:
            minimum_mean_absolute_change = min(
                minimum_mean_absolute_change,
                comparison.average_mean_absolute_change,
            )
            maximum_mean_absolute_change = max(
                maximum_mean_absolute_change,
                comparison.average_mean_absolute_change,
            )

    position_count = len(comparisons)

    if position_count == 0:
        average_mean_absolute_change = 0.0
    else:
        average_mean_absolute_change = (
            total_mean_absolute_change
            / position_count
        )

    return PositionDistributionStabilityComparisonSummary(
        position_count=position_count,
        stable_position_count=stable_position_count,
        moderate_position_count=moderate_position_count,
        unstable_position_count=unstable_position_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        minimum_mean_absolute_change=minimum_mean_absolute_change,
        maximum_mean_absolute_change=maximum_mean_absolute_change,
        comparisons=comparisons,
    )


def get_position_distribution_stability_comparison_summary(
    summary: PositionDistributionStabilityComparisonSummary,
    position: str,
) -> PositionDistributionStabilityComparison | None:
    if position == "":
        raise ValueError(
            "Position must not be empty."
        )

    for comparison in summary.comparisons:
        if comparison.position == position:
            return comparison

    return None