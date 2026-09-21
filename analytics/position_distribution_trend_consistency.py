from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionTrendConsistency:
    position: str
    digit: int
    window_count: int
    change_count: int
    positive_changes: int
    negative_changes: int
    unchanged_changes: int
    consistency_percentage: float
    direction_switches: int
    maximum_direction_streak: int
    consistency_level: str


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


def _calculate_direction_switches(
    changes: tuple[float, ...],
) -> int:
    if len(changes) < 2:
        return 0

    directions: list[str] = []

    for change in changes:
        if change > 0:
            directions.append("INCREASING")
        elif change < 0:
            directions.append("DECREASING")
        else:
            directions.append("UNCHANGED")

    direction_switches = 0

    for index in range(1, len(directions)):
        previous_direction = directions[index - 1]
        current_direction = directions[index]

        if (
            previous_direction != "UNCHANGED"
            and current_direction != "UNCHANGED"
            and previous_direction != current_direction
        ):
            direction_switches += 1

    return direction_switches


def _calculate_maximum_direction_streak(
    changes: tuple[float, ...],
) -> int:
    if not changes:
        return 0

    maximum_direction_streak = 1
    current_direction_streak = 1
    previous_direction = None

    for change in changes:
        if change > 0:
            direction = "INCREASING"
        elif change < 0:
            direction = "DECREASING"
        else:
            direction = "UNCHANGED"

        if previous_direction == direction:
            current_direction_streak += 1
        else:
            current_direction_streak = 1

        maximum_direction_streak = max(
            maximum_direction_streak,
            current_direction_streak,
        )

        previous_direction = direction

    return maximum_direction_streak


def _classify_consistency(
    consistency_percentage: float,
) -> str:
    if consistency_percentage >= 80.0:
        return "HIGH"

    if consistency_percentage >= 50.0:
        return "MEDIUM"

    return "LOW"


def calculate_position_distribution_trend_consistency(
    position: str,
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> PositionDistributionTrendConsistency:
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
        return PositionDistributionTrendConsistency(
            position=position,
            digit=digit,
            window_count=window_count,
            change_count=0,
            positive_changes=0,
            negative_changes=0,
            unchanged_changes=0,
            consistency_percentage=0.0,
            direction_switches=0,
            maximum_direction_streak=0,
            consistency_level="LOW",
        )

    changes = _calculate_changes(
        digit=digit,
        windows=windows,
    )

    change_count = len(changes)

    positive_changes = sum(
        change > 0
        for change in changes
    )

    negative_changes = sum(
        change < 0
        for change in changes
    )

    unchanged_changes = sum(
        change == 0
        for change in changes
    )

    dominant_direction_count = max(
        positive_changes,
        negative_changes,
        unchanged_changes,
    )

    consistency_percentage = (
        dominant_direction_count
        / change_count
        * 100
    )

    direction_switches = _calculate_direction_switches(
        changes=changes,
    )

    maximum_direction_streak = (
        _calculate_maximum_direction_streak(
            changes=changes,
        )
    )

    consistency_level = _classify_consistency(
        consistency_percentage=consistency_percentage,
    )

    return PositionDistributionTrendConsistency(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=change_count,
        positive_changes=positive_changes,
        negative_changes=negative_changes,
        unchanged_changes=unchanged_changes,
        consistency_percentage=consistency_percentage,
        direction_switches=direction_switches,
        maximum_direction_streak=maximum_direction_streak,
        consistency_level=consistency_level,
    )


def calculate_all_position_distribution_trend_consistency(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[PositionDistributionTrendConsistency, ...]:
    return tuple(
        calculate_position_distribution_trend_consistency(
            position=position,
            digit=digit,
            windows=windows,
        )
        for digit in range(10)
    )