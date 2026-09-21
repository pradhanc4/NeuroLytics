from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_metrics import (
    calculate_mean_absolute_difference,
)


@dataclass(frozen=True)
class PositionDistributionStabilityComparison:
    position: str
    window_a: str
    window_b: str
    mean_absolute_difference: float


@dataclass(frozen=True)
class PositionDistributionStabilitySummary:
    position: str
    window_count: int
    comparison_count: int
    total_mean_absolute_difference: float
    mean_mean_absolute_difference: float
    minimum_mean_absolute_difference: float
    maximum_mean_absolute_difference: float


def compare_position_distribution_window_pair(
    position: str,
    window_a: str,
    distribution_a: PositionDistribution,
    window_b: str,
    distribution_b: PositionDistribution,
) -> PositionDistributionStabilityComparison:
    if distribution_a.position != position:
        raise ValueError(
            "First distribution position does not match "
            "the requested position."
        )

    if distribution_b.position != position:
        raise ValueError(
            "Second distribution position does not match "
            "the requested position."
        )

    mean_absolute_difference = calculate_mean_absolute_difference(
        distribution_a,
        distribution_b,
    )

    return PositionDistributionStabilityComparison(
        position=position,
        window_a=window_a,
        window_b=window_b,
        mean_absolute_difference=mean_absolute_difference,
    )


def compare_position_distribution_windows(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> tuple[PositionDistributionStabilityComparison, ...]:
    if not windows:
        return ()

    for _, distribution in windows:
        if distribution.position != position:
            raise ValueError(
                "All distributions must belong to the "
                "requested position."
            )

    comparisons: list[
        PositionDistributionStabilityComparison
    ] = []

    for index in range(len(windows) - 1):
        window_a, distribution_a = windows[index]
        window_b, distribution_b = windows[index + 1]

        comparisons.append(
            compare_position_distribution_window_pair(
                position=position,
                window_a=window_a,
                distribution_a=distribution_a,
                window_b=window_b,
                distribution_b=distribution_b,
            )
        )

    return tuple(comparisons)


def summarize_position_distribution_stability(
    position: str,
    windows: tuple[
        tuple[str, PositionDistribution],
        ...,
    ],
) -> PositionDistributionStabilitySummary:
    comparisons = compare_position_distribution_windows(
        position=position,
        windows=windows,
    )

    if not comparisons:
        return PositionDistributionStabilitySummary(
            position=position,
            window_count=len(windows),
            comparison_count=0,
            total_mean_absolute_difference=0.0,
            mean_mean_absolute_difference=0.0,
            minimum_mean_absolute_difference=0.0,
            maximum_mean_absolute_difference=0.0,
        )

    values = tuple(
        comparison.mean_absolute_difference
        for comparison in comparisons
    )

    return PositionDistributionStabilitySummary(
        position=position,
        window_count=len(windows),
        comparison_count=len(comparisons),
        total_mean_absolute_difference=sum(values),
        mean_mean_absolute_difference=sum(values) / len(values),
        minimum_mean_absolute_difference=min(values),
        maximum_mean_absolute_difference=max(values),
    )