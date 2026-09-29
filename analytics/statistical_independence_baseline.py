from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class IndependenceMeasure:
    position_a: str
    position_b: str
    total_observations: int
    chi_square: float
    degrees_of_freedom: int
    max_probability_difference: float
    independent: bool


@dataclass(frozen=True)
class StatisticalIndependenceBaseline:
    market_id: int
    analysis_version: str
    baseline_version: str
    measures: tuple[IndependenceMeasure, ...]


@dataclass(frozen=True)
class IndependenceValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _paired_rows(dataset, a, b):
    rows = {}
    for obs in dataset.observations:
        rows.setdefault(obs.record_date, {})[obs.column_name] = obs.value
    return [
        (row[a], row[b])
        for row in rows.values()
        if a in row and b in row
    ]


def _measure(dataset, a, b):
    pairs = _paired_rows(dataset, a, b)
    n = len(pairs)
    counts = [[0 for _ in range(10)] for _ in range(10)]
    row_totals = [0] * 10
    col_totals = [0] * 10
    for x, y in pairs:
        counts[x][y] += 1
        row_totals[x] += 1
        col_totals[y] += 1

    chi_square = 0.0
    max_diff = 0.0
    if n:
        for x in range(10):
            for y in range(10):
                expected = row_totals[x] * col_totals[y] / n
                if expected:
                    chi_square += (counts[x][y] - expected) ** 2 / expected
                joint = counts[x][y] / n
                product = (row_totals[x] / n) * (col_totals[y] / n)
                max_diff = max(max_diff, abs(joint - product))

    return IndependenceMeasure(
        position_a=a,
        position_b=b,
        total_observations=n,
        chi_square=chi_square,
        degrees_of_freedom=81,
        max_probability_difference=max_diff,
        independent=max_diff <= 1e-12,
    )


def build_statistical_independence_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalIndependenceBaseline:
    validate_statistical_baseline_dataset(dataset)
    measures = tuple(
        _measure(dataset, a, b)
        for index, a in enumerate(dataset.columns)
        for b in dataset.columns[index + 1:]
    )
    return StatisticalIndependenceBaseline(
        market_id=dataset.contract.market_id,
        analysis_version=dataset.contract.analysis_version,
        baseline_version=dataset.contract.baseline_version,
        measures=measures,
    )


def validate_statistical_independence_baseline(
    baseline: StatisticalIndependenceBaseline,
) -> None:
    if not isinstance(baseline, StatisticalIndependenceBaseline):
        raise TypeError("baseline must be a StatisticalIndependenceBaseline instance.")
    if baseline.market_id <= 0:
        raise ValueError("market_id must be positive.")
    previous = None
    for item in baseline.measures:
        if not isinstance(item, IndependenceMeasure):
            raise TypeError("measures must contain IndependenceMeasure objects.")
        key = (item.position_a, item.position_b)
        if previous is not None and key <= previous:
            raise ValueError("measures must be in deterministic order.")
        previous = key
        if item.total_observations < 0:
            raise ValueError("total_observations cannot be negative.")
        if item.chi_square < 0:
            raise ValueError("chi_square cannot be negative.")
        if item.degrees_of_freedom < 0:
            raise ValueError("degrees_of_freedom cannot be negative.")
        if not 0.0 <= item.max_probability_difference <= 1.0:
            raise ValueError("max_probability_difference must be between 0 and 1.")


def validate_statistical_independence_baseline_result(
    baseline: StatisticalIndependenceBaseline,
) -> IndependenceValidationResult:
    if not isinstance(baseline, StatisticalIndependenceBaseline):
        return IndependenceValidationResult(INVALID, ("INVALID_BASELINE_TYPE",))
    try:
        validate_statistical_independence_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return IndependenceValidationResult(INVALID, (str(exc),))
    return IndependenceValidationResult(VALID, ())


def get_independence_measure(
    baseline: StatisticalIndependenceBaseline,
    position_a: str,
    position_b: str,
) -> IndependenceMeasure:
    validate_statistical_independence_baseline(baseline)
    for item in baseline.measures:
        if item.position_a == position_a and item.position_b == position_b:
            return item
    raise ValueError(f"Independence measure not found: {position_a}->{position_b}")
