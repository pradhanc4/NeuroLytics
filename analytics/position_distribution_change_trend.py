from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionChangeTrend:
    position: str
    digit: int
    window_count: int
    change_count: int
    increases: int
    decreases: int
    unchanged: int
    total_change: float
    mean_change: float
    trend_direction: str


def _validate_distribution(
    position: str,
    distribution: PositionDistribution,
) -> None:
    if distribution.position != position:
        raise ValueError(
            "Distribution position does not match "
            "the requested position."
        )

    if len(distribution.percentages) != 10:
        raise ValueError(
            "Position distribution must contain exactly "
            "10 digit percentages."
        )


def calculate_position_distribution_change_trend(
    position: str,
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> PositionDistributionChangeTrend:
    if digit < 0 or digit > 9:
        raise ValueError(
            "Digit must be between 0 and 9."
        )

    for _, distribution in windows:
        _validate_distribution(
            position=position,
            distribution=distribution,
        )

    window_count = len(windows)

    if window_count < 2:
        return PositionDistributionChangeTrend(
            position=position,
            digit=digit,
            window_count=window_count,
            change_count=0,
            increases=0,
            decreases=0,
            unchanged=0,
            total_change=0.0,
            mean_change=0.0,
            trend_direction="UNCHANGED",
        )

    changes: list[float] = []

    for index in range(window_count - 1):
        _, distribution_a = windows[index]
        _, distribution_b = windows[index + 1]

        percentage_a = distribution_a.percentages[digit]
        percentage_b = distribution_b.percentages[digit]

        changes.append(
            percentage_b - percentage_a
        )

    increases = sum(
        change > 0
        for change in changes
    )

    decreases = sum(
        change < 0
        for change in changes
    )

    unchanged = sum(
        change == 0
        for change in changes
    )

    total_change = sum(changes)

    mean_change = (
        total_change / len(changes)
        if changes
        else 0.0
    )

    if increases == len(changes):
        trend_direction = "INCREASING"
    elif decreases == len(changes):
        trend_direction = "DECREASING"
    elif unchanged == len(changes):
        trend_direction = "UNCHANGED"
    else:
        trend_direction = "MIXED"

    return PositionDistributionChangeTrend(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=len(changes),
        increases=increases,
        decreases=decreases,
        unchanged=unchanged,
        total_change=total_change,
        mean_change=mean_change,
        trend_direction=trend_direction,
    )


def calculate_all_position_distribution_change_trends(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[PositionDistributionChangeTrend, ...]:
    return tuple(
        calculate_position_distribution_change_trend(
            position=position,
            digit=digit,
            windows=windows,
        )
        for digit in range(10)
    )