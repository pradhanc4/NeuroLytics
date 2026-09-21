from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionDistributionChangeMagnitude:
    position: str
    digit: int
    absolute_change: float
    low_threshold: float
    high_threshold: float
    magnitude: str


def classify_change_magnitude(
    position: str,
    digit: int,
    absolute_change: float,
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionChangeMagnitude:
    if digit < 0 or digit > 9:
        raise ValueError(
            "Digit must be between 0 and 9."
        )

    if absolute_change < 0:
        raise ValueError(
            "Absolute change must be greater than or equal to zero."
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

    if absolute_change < low_threshold:
        magnitude = "LOW"
    elif absolute_change < high_threshold:
        magnitude = "MEDIUM"
    else:
        magnitude = "HIGH"

    return PositionDistributionChangeMagnitude(
        position=position,
        digit=digit,
        absolute_change=absolute_change,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        magnitude=magnitude,
    )


def classify_change_magnitudes(
    position: str,
    changes: tuple[float, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> tuple[PositionDistributionChangeMagnitude, ...]:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    return tuple(
        classify_change_magnitude(
            position=position,
            digit=digit,
            absolute_change=absolute_change,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )
        for digit, absolute_change in enumerate(changes)
    )