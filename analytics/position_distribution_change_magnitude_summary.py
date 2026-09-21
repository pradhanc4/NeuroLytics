from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_change_magnitude import (
    PositionDistributionChangeMagnitude,
    classify_change_magnitudes,
)


@dataclass(frozen=True)
class PositionDistributionChangeMagnitudeSummary:
    position: str
    low_threshold: float
    high_threshold: float
    digit_count: int
    low_count: int
    medium_count: int
    high_count: int
    classified_count: int
    classifications: tuple[
        PositionDistributionChangeMagnitude,
        ...,
    ]


def summarize_change_magnitudes(
    position: str,
    changes: tuple[float, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionChangeMagnitudeSummary:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    classifications = classify_change_magnitudes(
        position=position,
        changes=changes,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    low_count = sum(
        item.magnitude == "LOW"
        for item in classifications
    )

    medium_count = sum(
        item.magnitude == "MEDIUM"
        for item in classifications
    )

    high_count = sum(
        item.magnitude == "HIGH"
        for item in classifications
    )

    digit_count = len(classifications)

    return PositionDistributionChangeMagnitudeSummary(
        position=position,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        digit_count=digit_count,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        classified_count=(
            low_count
            + medium_count
            + high_count
        ),
        classifications=classifications,
    )