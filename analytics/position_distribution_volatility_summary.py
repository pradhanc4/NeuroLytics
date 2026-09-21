from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


@dataclass(frozen=True)
class PositionDistributionVolatilitySummary:
    position: str
    digit_count: int
    low_count: int
    medium_count: int
    high_count: int
    total_absolute_change: float
    average_mean_absolute_change: float
    volatility_results: tuple[PositionDistributionVolatility, ...]


def summarize_position_distribution_volatility(
    position: str,
    results: tuple[PositionDistributionVolatility, ...],
) -> PositionDistributionVolatilitySummary:
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

    low_count = sum(
        1
        for result in results
        if result.volatility_level == "LOW"
    )

    medium_count = sum(
        1
        for result in results
        if result.volatility_level == "MEDIUM"
    )

    high_count = sum(
        1
        for result in results
        if result.volatility_level == "HIGH"
    )

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

    return PositionDistributionVolatilitySummary(
        position=position,
        digit_count=digit_count,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        volatility_results=results,
    )


def summarize_all_position_distribution_volatility(
    results: tuple[PositionDistributionVolatility, ...],
) -> PositionDistributionVolatilitySummary:
    if not results:
        return PositionDistributionVolatilitySummary(
            position="",
            digit_count=0,
            low_count=0,
            medium_count=0,
            high_count=0,
            total_absolute_change=0.0,
            average_mean_absolute_change=0.0,
            volatility_results=(),
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

    return summarize_position_distribution_volatility(
        position=position,
        results=results,
    )