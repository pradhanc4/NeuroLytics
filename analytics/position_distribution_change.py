from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionDigitChange:
    position: str
    digit: int
    percentage_a: float
    percentage_b: float
    absolute_change: float
    direction: str


@dataclass(frozen=True)
class PositionDistributionChangeSummary:
    position: str
    total_absolute_change: float
    mean_absolute_change: float
    increased_digits: int
    decreased_digits: int
    unchanged_digits: int
    changes: tuple[PositionDistributionDigitChange, ...]


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


def calculate_position_distribution_digit_changes(
    position: str,
    distribution_a: PositionDistribution,
    distribution_b: PositionDistribution,
) -> tuple[PositionDistributionDigitChange, ...]:
    _validate_distribution(position, distribution_a)
    _validate_distribution(position, distribution_b)

    changes: list[PositionDistributionDigitChange] = []

    for digit in range(10):
        percentage_a = distribution_a.percentages[digit]
        percentage_b = distribution_b.percentages[digit]

        change = percentage_b - percentage_a

        if change > 0:
            direction = "increased"
        elif change < 0:
            direction = "decreased"
        else:
            direction = "unchanged"

        changes.append(
            PositionDistributionDigitChange(
                position=position,
                digit=digit,
                percentage_a=percentage_a,
                percentage_b=percentage_b,
                absolute_change=abs(change),
                direction=direction,
            )
        )

    return tuple(changes)


def summarize_position_distribution_change(
    position: str,
    distribution_a: PositionDistribution,
    distribution_b: PositionDistribution,
) -> PositionDistributionChangeSummary:
    changes = calculate_position_distribution_digit_changes(
        position=position,
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    absolute_changes = tuple(
        change.absolute_change
        for change in changes
    )

    increased_digits = sum(
        change.direction == "increased"
        for change in changes
    )

    decreased_digits = sum(
        change.direction == "decreased"
        for change in changes
    )

    unchanged_digits = sum(
        change.direction == "unchanged"
        for change in changes
    )

    total_absolute_change = sum(absolute_changes)

    return PositionDistributionChangeSummary(
        position=position,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=total_absolute_change / 10,
        increased_digits=increased_digits,
        decreased_digits=decreased_digits,
        unchanged_digits=unchanged_digits,
        changes=changes,
    )