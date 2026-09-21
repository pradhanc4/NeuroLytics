from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionVolatility:
    position: str
    digit: int
    window_count: int
    change_count: int
    total_absolute_change: float
    mean_absolute_change: float
    maximum_absolute_change: float
    minimum_absolute_change: float
    volatility_level: str


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


def _calculate_absolute_changes(
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[float, ...]:
    absolute_changes: list[float] = []

    for index in range(len(windows) - 1):
        _, distribution_a = windows[index]
        _, distribution_b = windows[index + 1]

        percentage_a = distribution_a.percentages[digit]
        percentage_b = distribution_b.percentages[digit]

        change = percentage_b - percentage_a

        absolute_changes.append(abs(change))

    return tuple(absolute_changes)


def _classify_volatility(
    mean_absolute_change: float,
    low_threshold: float,
    high_threshold: float,
) -> str:
    if mean_absolute_change < low_threshold:
        return "LOW"

    if mean_absolute_change < high_threshold:
        return "MEDIUM"

    return "HIGH"


def calculate_position_distribution_volatility(
    position: str,
    digit: int,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionVolatility:
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
        return PositionDistributionVolatility(
            position=position,
            digit=digit,
            window_count=window_count,
            change_count=0,
            total_absolute_change=0.0,
            mean_absolute_change=0.0,
            maximum_absolute_change=0.0,
            minimum_absolute_change=0.0,
            volatility_level="LOW",
        )

    absolute_changes = _calculate_absolute_changes(
        digit=digit,
        windows=windows,
    )

    change_count = len(absolute_changes)

    total_absolute_change = sum(
        absolute_changes
    )

    mean_absolute_change = (
        total_absolute_change / change_count
    )

    maximum_absolute_change = max(
        absolute_changes
    )

    minimum_absolute_change = min(
        absolute_changes
    )

    volatility_level = _classify_volatility(
        mean_absolute_change=mean_absolute_change,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    return PositionDistributionVolatility(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=change_count,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=mean_absolute_change,
        maximum_absolute_change=maximum_absolute_change,
        minimum_absolute_change=minimum_absolute_change,
        volatility_level=volatility_level,
    )


def calculate_all_position_distribution_volatility(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> tuple[PositionDistributionVolatility, ...]:
    return tuple(
        calculate_position_distribution_volatility(
            position=position,
            digit=digit,
            windows=windows,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )
        for digit in range(10)
    )