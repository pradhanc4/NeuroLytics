from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_foundation import ANALYSIS_COLUMNS

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class ConditionalProbabilityMatrix:
    """P(target digit | conditioning digit) for two positions."""

    condition_position: str
    target_position: str
    probabilities: tuple[tuple[float, ...], ...]

    def probability(self, condition_digit: int, target_digit: int) -> float:
        if not 0 <= condition_digit <= 9:
            raise ValueError("condition_digit must be from 0 through 9.")
        if not 0 <= target_digit <= 9:
            raise ValueError("target_digit must be from 0 through 9.")
        return self.probabilities[condition_digit][target_digit]


@dataclass(frozen=True)
class StatisticalConditionalProbabilityBaseline:
    market_id: int
    analysis_version: str
    baseline_version: str
    matrices: tuple[ConditionalProbabilityMatrix, ...]

    @property
    def pair_count(self) -> int:
        return len(self.matrices)


@dataclass(frozen=True)
class ConditionalProbabilityValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class ConditionalProbabilityValidationResult:
    status: str
    issues: tuple[ConditionalProbabilityValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _issue(code: str, message: str):
    return ConditionalProbabilityValidationIssue(code, message)


def _matrix_for(
    dataset: StatisticalBaselineDataset,
    condition_position: str,
    target_position: str,
) -> ConditionalProbabilityMatrix:
    if condition_position == target_position:
        raise ValueError("condition and target positions must differ.")
    observations = {}
    for observation in dataset.observations:
        observations.setdefault(observation.record_date, {})[
            observation.column_name
        ] = observation.value

    counts = [[0 for _ in range(10)] for _ in range(10)]
    totals = [0 for _ in range(10)]

    for row in observations.values():
        if condition_position not in row or target_position not in row:
            continue
        condition = row[condition_position]
        target = row[target_position]
        counts[condition][target] += 1
        totals[condition] += 1

    probabilities = tuple(
        tuple(
            (
                counts[condition][target] / totals[condition]
                if totals[condition]
                else 0.0
            )
            for target in range(10)
        )
        for condition in range(10)
    )
    return ConditionalProbabilityMatrix(
        condition_position=condition_position,
        target_position=target_position,
        probabilities=probabilities,
    )


def build_statistical_conditional_probability_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalConditionalProbabilityBaseline:
    validate_statistical_baseline_dataset(dataset)
    matrices = tuple(
        _matrix_for(dataset, condition, target)
        for condition in dataset.columns
        for target in dataset.columns
        if condition != target
    )
    return StatisticalConditionalProbabilityBaseline(
        market_id=dataset.contract.market_id,
        analysis_version=dataset.contract.analysis_version,
        baseline_version=dataset.contract.baseline_version,
        matrices=matrices,
    )


def validate_statistical_conditional_probability_baseline(
    baseline: StatisticalConditionalProbabilityBaseline,
) -> None:
    if not isinstance(baseline, StatisticalConditionalProbabilityBaseline):
        raise TypeError(
            "baseline must be a StatisticalConditionalProbabilityBaseline instance."
        )
    if baseline.market_id <= 0:
        raise ValueError("market_id must be positive.")
    if not baseline.analysis_version.strip():
        raise ValueError("analysis_version must be non-empty.")
    if not baseline.baseline_version.strip():
        raise ValueError("baseline_version must be non-empty.")
    previous = None
    for matrix in baseline.matrices:
        if not isinstance(matrix, ConditionalProbabilityMatrix):
            raise TypeError("matrices must contain ConditionalProbabilityMatrix objects.")
        if matrix.condition_position not in ANALYSIS_COLUMNS:
            raise ValueError("unsupported condition position.")
        if matrix.target_position not in ANALYSIS_COLUMNS:
            raise ValueError("unsupported target position.")
        if matrix.condition_position == matrix.target_position:
            raise ValueError("condition and target positions must differ.")
        if len(matrix.probabilities) != 10 or any(
            len(row) != 10 for row in matrix.probabilities
        ):
            raise ValueError("probability matrices must be 10 by 10.")
        for row in matrix.probabilities:
            if any(value < 0.0 or value > 1.0 for value in row):
                raise ValueError("probabilities must be between 0 and 1.")
            total = sum(row)
            if total and abs(total - 1.0) > 1e-9:
                raise ValueError("conditional probability rows must sum to 1.")
        key = (matrix.condition_position, matrix.target_position)
        if previous is not None and key <= previous:
            raise ValueError("matrices must be in deterministic order.")
        previous = key


def validate_statistical_conditional_probability_baseline_result(
    baseline: StatisticalConditionalProbabilityBaseline,
) -> ConditionalProbabilityValidationResult:
    if not isinstance(baseline, StatisticalConditionalProbabilityBaseline):
        return ConditionalProbabilityValidationResult(
            INVALID,
            (_issue("INVALID_BASELINE_TYPE", "Invalid conditional baseline type."),),
        )
    try:
        validate_statistical_conditional_probability_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return ConditionalProbabilityValidationResult(
            INVALID,
            (_issue("INVALID_BASELINE", str(exc)),),
        )
    return ConditionalProbabilityValidationResult(VALID, ())


def get_conditional_probability(
    baseline: StatisticalConditionalProbabilityBaseline,
    condition_position: str,
    target_position: str,
    condition_digit: int,
    target_digit: int,
) -> float:
    validate_statistical_conditional_probability_baseline(baseline)
    for matrix in baseline.matrices:
        if (
            matrix.condition_position == condition_position
            and matrix.target_position == target_position
        ):
            return matrix.probability(condition_digit, target_digit)
    raise ValueError(
        f"Conditional probability not found: {condition_position}->{target_position}"
    )


def is_statistical_conditional_probability_baseline_valid(
    baseline: StatisticalConditionalProbabilityBaseline,
) -> bool:
    return validate_statistical_conditional_probability_baseline_result(
        baseline
    ).is_valid
