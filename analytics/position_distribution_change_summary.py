from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_change import (
    PositionDistributionDigitChange,
)
from analytics.position_distribution_change_classification import (
    PositionDistributionChangeClassification,
    classify_position_distribution_changes,
)


@dataclass(frozen=True)
class PositionDistributionChangeSummary:
    position: str
    threshold: float
    digit_count: int
    increased_digits: int
    decreased_digits: int
    unchanged_digits: int
    total_absolute_change: float
    mean_absolute_change: float
    classified_changes: tuple[
        PositionDistributionChangeClassification,
        ...,
    ]


def summarize_position_distribution_changes(
    position: str,
    changes: tuple[PositionDistributionDigitChange, ...],
    threshold: float = 0.0,
) -> PositionDistributionChangeSummary:
    if threshold < 0:
        raise ValueError(
            "Threshold must be greater than or equal to zero."
        )

    for change in changes:
        if change.position != position:
            raise ValueError(
                "All changes must belong to the requested position."
            )

    classified_changes = classify_position_distribution_changes(
        changes=changes,
        threshold=threshold,
    )

    increased_digits = sum(
        item.classification == "increased"
        for item in classified_changes
    )

    decreased_digits = sum(
        item.classification == "decreased"
        for item in classified_changes
    )

    unchanged_digits = sum(
        item.classification == "unchanged"
        for item in classified_changes
    )

    total_absolute_change = sum(
        change.absolute_change
        for change in changes
    )

    digit_count = len(changes)

    if digit_count == 0:
        mean_absolute_change = 0.0
    else:
        mean_absolute_change = (
            total_absolute_change / digit_count
        )

    return PositionDistributionChangeSummary(
        position=position,
        threshold=threshold,
        digit_count=digit_count,
        increased_digits=increased_digits,
        decreased_digits=decreased_digits,
        unchanged_digits=unchanged_digits,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=mean_absolute_change,
        classified_changes=classified_changes,
    )