from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_trend_strength import (
    PositionDistributionTrendStrength,
)


@dataclass(frozen=True)
class PositionDistributionTrendStrengthSummary:
    position: str
    digit_count: int
    low_count: int
    medium_count: int
    high_count: int
    increasing_count: int
    decreasing_count: int
    mixed_count: int
    unchanged_count: int
    total_absolute_change: float
    average_mean_absolute_change: float
    strength_results: tuple[
        PositionDistributionTrendStrength,
        ...,
    ]


def summarize_position_distribution_trend_strength(
    position: str,
    results: tuple[
        PositionDistributionTrendStrength,
        ...,
    ],
) -> PositionDistributionTrendStrengthSummary:
    for result in results:
        if result.position != position:
            raise ValueError(
                "All trend strength results must belong "
                "to the requested position."
            )

        if result.digit < 0 or result.digit > 9:
            raise ValueError(
                "Digit must be between 0 and 9."
            )

    low_count = sum(
        result.strength == "LOW"
        for result in results
    )

    medium_count = sum(
        result.strength == "MEDIUM"
        for result in results
    )

    high_count = sum(
        result.strength == "HIGH"
        for result in results
    )

    increasing_count = sum(
        result.trend_direction == "INCREASING"
        for result in results
    )

    decreasing_count = sum(
        result.trend_direction == "DECREASING"
        for result in results
    )

    mixed_count = sum(
        result.trend_direction == "MIXED"
        for result in results
    )

    unchanged_count = sum(
        result.trend_direction == "UNCHANGED"
        for result in results
    )

    total_absolute_change = sum(
        result.absolute_total_change
        for result in results
    )

    digit_count = len(results)

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

    return PositionDistributionTrendStrengthSummary(
        position=position,
        digit_count=digit_count,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        increasing_count=increasing_count,
        decreasing_count=decreasing_count,
        mixed_count=mixed_count,
        unchanged_count=unchanged_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=(
            average_mean_absolute_change
        ),
        strength_results=results,
    )


def summarize_all_position_distribution_trend_strength(
    results: tuple[
        PositionDistributionTrendStrength,
        ...,
    ],
) -> PositionDistributionTrendStrengthSummary:
    if not results:
        return summarize_position_distribution_trend_strength(
            position="",
            results=(),
        )

    positions = {
        result.position
        for result in results
    }

    if len(positions) != 1:
        raise ValueError(
            "All trend strength results must belong "
            "to the same position."
        )

    position = next(iter(positions))

    return summarize_position_distribution_trend_strength(
        position=position,
        results=results,
    )