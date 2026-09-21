from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_change import (
    PositionDistributionDigitChange,
)


@dataclass(frozen=True)
class PositionDistributionChangeClassification:
    position: str
    digit: int
    absolute_change: float
    threshold: float
    classification: str


def classify_position_distribution_change(
    change: PositionDistributionDigitChange,
    threshold: float = 0.0,
) -> PositionDistributionChangeClassification:
    if threshold < 0:
        raise ValueError(
            "Threshold must be greater than or equal to zero."
        )

    if change.absolute_change > threshold:
        classification = change.direction
    else:
        classification = "unchanged"

    return PositionDistributionChangeClassification(
        position=change.position,
        digit=change.digit,
        absolute_change=change.absolute_change,
        threshold=threshold,
        classification=classification,
    )


def classify_position_distribution_changes(
    changes: tuple[PositionDistributionDigitChange, ...],
    threshold: float = 0.0,
) -> tuple[PositionDistributionChangeClassification, ...]:
    if threshold < 0:
        raise ValueError(
            "Threshold must be greater than or equal to zero."
        )

    return tuple(
        classify_position_distribution_change(
            change=change,
            threshold=threshold,
        )
        for change in changes
    )