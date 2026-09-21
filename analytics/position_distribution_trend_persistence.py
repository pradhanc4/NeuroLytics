from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionTrendPersistence:
    position: str
    digit: int
    window_count: int
    change_count: int
    increases: int
    decreases: int
    unchanged: int
    dominant_direction: str
    persistence_percentage: float
    longest_streak: int


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


def _build_changes(
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


def _calculate_longest_streak(
    changes: tuple[float, ...],
) -> int:
    if not changes:
        return 0

    longest_streak = 1
    current_streak = 1
    previous_direction = None

    for change in changes:
        if change > 0:
            direction = "INCREASING"
        elif change < 0:
            direction = "DECREASING"
        else:
            direction = "UNCHANGED"

        if previous_direction == direction:
            current_streak += 1
        else:
            current_streak = 1

        longest_streak = max(
            longest_streak,
            current_streak,
        )

        previous_direction = direction

    return longest_streak


def calculate_position_distribution_trend_persistence(
    position: str,
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> PositionDistributionTrendPersistence:
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
        return PositionDistributionTrendPersistence(
            position=position,
            digit=digit,
            window_count=window_count,
            change_count=0,
            increases=0,
            decreases=0,
            unchanged=0,
            dominant_direction="UNCHANGED",
            persistence_percentage=0.0,
            longest_streak=0,
        )

    changes = _build_changes(
        digit=digit,
        windows=windows,
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

    change_count = len(changes)

    if increases > decreases:
        dominant_direction = "INCREASING"
        dominant_count = increases
    elif decreases > increases:
        dominant_direction = "DECREASING"
        dominant_count = decreases
    elif increases == 0 and decreases == 0:
        dominant_direction = "UNCHANGED"
        dominant_count = unchanged
    else:
        dominant_direction = "MIXED"
        dominant_count = max(
            increases,
            decreases,
        )

    persistence_percentage = (
        dominant_count / change_count * 100
    )

    longest_streak = _calculate_longest_streak(
        changes=changes,
    )

    return PositionDistributionTrendPersistence(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=change_count,
        increases=increases,
        decreases=decreases,
        unchanged=unchanged,
        dominant_direction=dominant_direction,
        persistence_percentage=persistence_percentage,
        longest_streak=longest_streak,
    )


def calculate_all_position_distribution_trend_persistence(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[PositionDistributionTrendPersistence, ...]:
    return tuple(
        calculate_position_distribution_trend_persistence(
            position=position,
            digit=digit,
            windows=windows,
        )
        for digit in range(10)
    )