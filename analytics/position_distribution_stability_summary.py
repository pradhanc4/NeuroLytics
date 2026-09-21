from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


@dataclass(frozen=True)
class PositionDistributionStabilitySummary:
    position: str
    digit_count: int
    stable_digit_count: int
    moderate_digit_count: int
    unstable_digit_count: int
    total_absolute_change: float
    average_mean_absolute_change: float
    stability_results: tuple[PositionDistributionVolatility, ...]


def _classify_stability(
    mean_absolute_change: float,
    low_threshold: float,
    high_threshold: float,
) -> str:
    if mean_absolute_change < low_threshold:
        return "STABLE"

    if mean_absolute_change < high_threshold:
        return "MODERATE"

    return "UNSTABLE"


def summarize_position_distribution_stability(
    position: str,
    results: tuple[PositionDistributionVolatility, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionStabilitySummary:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    for result in results:
        if result.position != position:
            raise ValueError(
                "Volatility result position does not match "
                "the requested position."
            )

        if result.digit < 0 or result.digit > 9:
            raise ValueError(
                "Volatility result digit must be between 0 and 9."
            )

    digit_count = len(results)

    stable_digit_count = 0
    moderate_digit_count = 0
    unstable_digit_count = 0

    for result in results:
        stability = _classify_stability(
            mean_absolute_change=result.mean_absolute_change,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )

        if stability == "STABLE":
            stable_digit_count += 1
        elif stability == "MODERATE":
            moderate_digit_count += 1
        else:
            unstable_digit_count += 1

    total_absolute_change = sum(
        result.total_absolute_change
        for result in results
    )

    if digit_count == 0:
        average_mean_absolute_change = 0.0
    else:
        average_mean_absolute_change = (
            sum(
                result.mean_absolute_change
                for result in results
            )
            / digit_count
        )

    return PositionDistributionStabilitySummary(
        position=position,
        digit_count=digit_count,
        stable_digit_count=stable_digit_count,
        moderate_digit_count=moderate_digit_count,
        unstable_digit_count=unstable_digit_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        stability_results=results,
    )


def summarize_all_position_distribution_stability(
    results: tuple[PositionDistributionVolatility, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionStabilitySummary:
    if not results:
        return PositionDistributionStabilitySummary(
            position="",
            digit_count=0,
            stable_digit_count=0,
            moderate_digit_count=0,
            unstable_digit_count=0,
            total_absolute_change=0.0,
            average_mean_absolute_change=0.0,
            stability_results=(),
        )

    positions = {
        result.position
        for result in results
    }

    if len(positions) != 1:
        raise ValueError(
            "All volatility results must belong to the same position."
        )

    position = next(iter(positions))

    return summarize_position_distribution_stability(
        position=position,
        results=results,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )