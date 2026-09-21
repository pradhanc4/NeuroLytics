from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_stability_summary import (
    PositionDistributionStabilitySummary,
)


@dataclass(frozen=True)
class PositionDistributionStabilityComparison:
    position: str
    digit_count: int
    stable_digit_count: int
    moderate_digit_count: int
    unstable_digit_count: int
    total_absolute_change: float
    average_mean_absolute_change: float
    minimum_mean_absolute_change: float
    maximum_mean_absolute_change: float
    stability_level: str


def _validate_summary(
    summary: PositionDistributionStabilitySummary,
) -> None:
    if summary.position == "":
        raise ValueError(
            "Position must not be empty."
        )

    if summary.digit_count < 0:
        raise ValueError(
            "Digit count must be greater than or equal to zero."
        )

    if summary.stable_digit_count < 0:
        raise ValueError(
            "Stable digit count must be greater than or equal to zero."
        )

    if summary.moderate_digit_count < 0:
        raise ValueError(
            "Moderate digit count must be greater than or equal to zero."
        )

    if summary.unstable_digit_count < 0:
        raise ValueError(
            "Unstable digit count must be greater than or equal to zero."
        )

    classified_count = (
        summary.stable_digit_count
        + summary.moderate_digit_count
        + summary.unstable_digit_count
    )

    if classified_count != summary.digit_count:
        raise ValueError(
            "Stability classification counts must equal digit count."
        )

    if summary.total_absolute_change < 0:
        raise ValueError(
            "Total absolute change must be greater than or equal to zero."
        )

    if summary.average_mean_absolute_change < 0:
        raise ValueError(
            "Average mean absolute change must be greater than "
            "or equal to zero."
        )

    for result in summary.stability_results:
        if result.digit < 0 or result.digit > 9:
            raise ValueError(
                "Stability result digit must be between 0 and 9."
            )

        if result.position != summary.position:
            raise ValueError(
                "Stability result position does not match "
                "the summary position."
            )

        if result.mean_absolute_change < 0:
            raise ValueError(
                "Mean absolute change must be greater than "
                "or equal to zero."
            )


def _calculate_minimum_mean_absolute_change(
    summary: PositionDistributionStabilitySummary,
) -> float:
    if not summary.stability_results:
        return 0.0

    return min(
        result.mean_absolute_change
        for result in summary.stability_results
    )


def _calculate_maximum_mean_absolute_change(
    summary: PositionDistributionStabilitySummary,
) -> float:
    if not summary.stability_results:
        return 0.0

    return max(
        result.mean_absolute_change
        for result in summary.stability_results
    )


def _classify_position_stability(
    average_mean_absolute_change: float,
    low_threshold: float,
    high_threshold: float,
) -> str:
    if average_mean_absolute_change < low_threshold:
        return "STABLE"

    if average_mean_absolute_change < high_threshold:
        return "MODERATE"

    return "UNSTABLE"


def compare_position_distribution_stability(
    summary: PositionDistributionStabilitySummary,
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionStabilityComparison:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    _validate_summary(summary)

    minimum_mean_absolute_change = (
        _calculate_minimum_mean_absolute_change(summary)
    )

    maximum_mean_absolute_change = (
        _calculate_maximum_mean_absolute_change(summary)
    )

    stability_level = _classify_position_stability(
        average_mean_absolute_change=summary.average_mean_absolute_change,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    return PositionDistributionStabilityComparison(
        position=summary.position,
        digit_count=summary.digit_count,
        stable_digit_count=summary.stable_digit_count,
        moderate_digit_count=summary.moderate_digit_count,
        unstable_digit_count=summary.unstable_digit_count,
        total_absolute_change=summary.total_absolute_change,
        average_mean_absolute_change=summary.average_mean_absolute_change,
        minimum_mean_absolute_change=minimum_mean_absolute_change,
        maximum_mean_absolute_change=maximum_mean_absolute_change,
        stability_level=stability_level,
    )


def compare_all_position_distribution_stability(
    summaries: tuple[PositionDistributionStabilitySummary, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> tuple[PositionDistributionStabilityComparison, ...]:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    positions: set[str] = set()

    comparisons = []

    for summary in summaries:
        _validate_summary(summary)

        if summary.position in positions:
            raise ValueError(
                "Duplicate position summaries are not allowed."
            )

        positions.add(summary.position)

        comparisons.append(
            compare_position_distribution_stability(
                summary=summary,
                low_threshold=low_threshold,
                high_threshold=high_threshold,
            )
        )

    return tuple(comparisons)


def get_position_distribution_stability_comparison(
    comparisons: tuple[
        PositionDistributionStabilityComparison,
        ...,
    ],
    position: str,
) -> PositionDistributionStabilityComparison | None:
    if position == "":
        raise ValueError(
            "Position must not be empty."
        )

    for comparison in comparisons:
        if comparison.position == position:
            return comparison

    return None