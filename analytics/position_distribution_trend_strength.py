from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionTrendStrength:
    position: str
    digit: int
    window_count: int
    change_count: int
    total_change: float
    mean_change: float
    absolute_total_change: float
    mean_absolute_change: float
    trend_direction: str
    strength: str


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


def _calculate_changes(
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[float, ...]:
    changes: list[float] = []

    for index in range(len(windows) - 1):
        _, distribution_a = windows[index]
        _, distribution_b = windows[index + 1]

        percentage_a = distribution_a.percentages[digit]
        percentage_b = distribution_b.percentages[digit]

        changes.append(
            percentage_b - percentage_a
        )

    return tuple(changes)


def _determine_trend_direction(
    changes: tuple[float, ...],
) -> str:
    if not changes:
        return "UNCHANGED"

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

    if increases == len(changes):
        return "INCREASING"

    if decreases == len(changes):
        return "DECREASING"

    if unchanged == len(changes):
        return "UNCHANGED"

    return "MIXED"


def _classify_strength(
    mean_absolute_change: float,
    low_threshold: float,
    high_threshold: float,
) -> str:
    if mean_absolute_change < low_threshold:
        return "LOW"

    if mean_absolute_change < high_threshold:
        return "MEDIUM"

    return "HIGH"


def calculate_position_distribution_trend_strength(
    position: str,
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionTrendStrength:
    if digit < 0 or digit > 9:
        raise ValueError(
            "Digit must be between 0 and 9."
        )

    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    for _, distribution in windows:
        _validate_distribution(
            position=position,
            distribution=distribution,
        )

    window_count = len(windows)

    if window_count < 2:
        return PositionDistributionTrendStrength(
            position=position,
            digit=digit,
            window_count=window_count,
            change_count=0,
            total_change=0.0,
            mean_change=0.0,
            absolute_total_change=0.0,
            mean_absolute_change=0.0,
            trend_direction="UNCHANGED",
            strength="LOW",
        )

    changes = _calculate_changes(
        digit=digit,
        windows=windows,
    )

    change_count = len(changes)

    total_change = sum(changes)

    mean_change = total_change / change_count

    absolute_total_change = sum(
        abs(change)
        for change in changes
    )

    mean_absolute_change = (
        absolute_total_change / change_count
    )

    trend_direction = _determine_trend_direction(
        changes=changes,
    )

    strength = _classify_strength(
        mean_absolute_change=mean_absolute_change,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    return PositionDistributionTrendStrength(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=change_count,
        total_change=total_change,
        mean_change=mean_change,
        absolute_total_change=absolute_total_change,
        mean_absolute_change=mean_absolute_change,
        trend_direction=trend_direction,
        strength=strength,
    )


def calculate_all_position_distribution_trend_strength(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> tuple[PositionDistributionTrendStrength, ...]:
    return tuple(
        calculate_position_distribution_trend_strength(
            position=position,
            digit=digit,
            windows=windows,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )
        for digit in range(10)
    )