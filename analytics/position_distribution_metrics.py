from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, pstdev

from analytics.position_distribution import PositionDistribution


@dataclass(frozen=True)
class PositionDistributionComparison:
    position_a: str
    position_b: str
    total_observations_a: int
    total_observations_b: int
    mean_absolute_difference: float


@dataclass(frozen=True)
class PositionDistributionComparisonMatrix:
    positions: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class PositionDistributionComparisonSummary:
    position_count: int
    comparison_count: int
    total_mean_absolute_difference: float
    mean_mean_absolute_difference: float
    median_mean_absolute_difference: float
    minimum_mean_absolute_difference: float
    maximum_mean_absolute_difference: float
    population_standard_deviation: float


def calculate_mean_absolute_difference(
    distribution_a: PositionDistribution,
    distribution_b: PositionDistribution,
) -> float:
    if len(distribution_a.percentages) != 10:
        raise ValueError(
            "First position distribution must contain exactly "
            "10 percentage values."
        )

    if len(distribution_b.percentages) != 10:
        raise ValueError(
            "Second position distribution must contain exactly "
            "10 percentage values."
        )

    differences = tuple(
        abs(
            percentage_a - percentage_b
        )
        for percentage_a, percentage_b in zip(
            distribution_a.percentages,
            distribution_b.percentages,
        )
    )

    return sum(differences) / 10


def compare_position_distributions(
    distribution_a: PositionDistribution,
    distribution_b: PositionDistribution,
) -> PositionDistributionComparison:
    mean_absolute_difference = calculate_mean_absolute_difference(
        distribution_a,
        distribution_b,
    )

    return PositionDistributionComparison(
        position_a=distribution_a.position,
        position_b=distribution_b.position,
        total_observations_a=distribution_a.total_observations,
        total_observations_b=distribution_b.total_observations,
        mean_absolute_difference=mean_absolute_difference,
    )


def compare_all_position_distributions(
    distributions: dict[str, PositionDistribution],
) -> tuple[PositionDistributionComparison, ...]:
    positions = tuple(distributions.keys())

    comparisons: list[PositionDistributionComparison] = []

    for index, position_a in enumerate(positions):
        for position_b in positions[index + 1:]:
            comparisons.append(
                compare_position_distributions(
                    distributions[position_a],
                    distributions[position_b],
                )
            )

    return tuple(comparisons)


def build_position_distribution_comparison_matrix(
    distributions: dict[str, PositionDistribution],
) -> PositionDistributionComparisonMatrix:
    positions = tuple(distributions.keys())

    matrix: list[list[float]] = [
        [0.0 for _ in positions]
        for _ in positions
    ]

    for index_a, position_a in enumerate(positions):
        for index_b in range(index_a + 1, len(positions)):
            position_b = positions[index_b]

            comparison = compare_position_distributions(
                distributions[position_a],
                distributions[position_b],
            )

            value = comparison.mean_absolute_difference

            matrix[index_a][index_b] = value
            matrix[index_b][index_a] = value

    return PositionDistributionComparisonMatrix(
        positions=positions,
        values=tuple(
            tuple(row)
            for row in matrix
        ),
    )


def get_position_distribution_comparison(
    matrix: PositionDistributionComparisonMatrix,
    position_a: str,
    position_b: str,
) -> float:
    try:
        index_a = matrix.positions.index(position_a)
    except ValueError as exc:
        raise ValueError(
            f"Unknown position: {position_a}"
        ) from exc

    try:
        index_b = matrix.positions.index(position_b)
    except ValueError as exc:
        raise ValueError(
            f"Unknown position: {position_b}"
        ) from exc

    return matrix.values[index_a][index_b]


def summarize_position_distribution_comparisons(
    comparisons: tuple[PositionDistributionComparison, ...],
    position_count: int,
) -> PositionDistributionComparisonSummary:
    if position_count < 0:
        raise ValueError(
            "Position count cannot be negative."
        )

    if not comparisons:
        return PositionDistributionComparisonSummary(
            position_count=position_count,
            comparison_count=0,
            total_mean_absolute_difference=0.0,
            mean_mean_absolute_difference=0.0,
            median_mean_absolute_difference=0.0,
            minimum_mean_absolute_difference=0.0,
            maximum_mean_absolute_difference=0.0,
            population_standard_deviation=0.0,
        )

    values = tuple(
        comparison.mean_absolute_difference
        for comparison in comparisons
    )

    return PositionDistributionComparisonSummary(
        position_count=position_count,
        comparison_count=len(values),
        total_mean_absolute_difference=sum(values),
        mean_mean_absolute_difference=mean(values),
        median_mean_absolute_difference=median(values),
        minimum_mean_absolute_difference=min(values),
        maximum_mean_absolute_difference=max(values),
        population_standard_deviation=pstdev(values),
    )


def summarize_all_position_distributions(
    distributions: dict[str, PositionDistribution],
) -> PositionDistributionComparisonSummary:
    comparisons = compare_all_position_distributions(
        distributions
    )

    return summarize_position_distribution_comparisons(
        comparisons=comparisons,
        position_count=len(distributions),
    )