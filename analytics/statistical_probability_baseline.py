from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_distribution_baseline import (
    StatisticalDistributionBaseline,
    build_statistical_distribution_baseline,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class PositionProbabilityBaseline:
    """Probability baseline for digits 0-9 at one position."""

    position: str
    probabilities: tuple[float, ...]

    @property
    def total_probability(self) -> float:
        return sum(self.probabilities)


@dataclass(frozen=True)
class StatisticalProbabilityBaseline:
    """Immutable Phase 18.8 marginal probability baseline."""

    market_id: int
    analysis_version: str
    baseline_version: str
    positions: tuple[PositionProbabilityBaseline, ...]

    @property
    def position_names(self) -> tuple[str, ...]:
        return tuple(item.position for item in self.positions)


@dataclass(frozen=True)
class StatisticalProbabilityValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class StatisticalProbabilityValidationResult:
    status: str
    issues: tuple[StatisticalProbabilityValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _issue(code: str, message: str):
    return StatisticalProbabilityValidationIssue(code, message)


def build_statistical_probability_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalProbabilityBaseline:
    """
    Build marginal digit probabilities from the existing
    Phase 18.6 distribution baseline.
    """
    validate_statistical_baseline_dataset(dataset)
    distribution = build_statistical_distribution_baseline(dataset)

    positions = tuple(
        PositionProbabilityBaseline(
            position=item.position,
            probabilities=tuple(
                percentage / 100.0
                for percentage in item.percentages
            ),
        )
        for item in distribution.distributions
    )

    return StatisticalProbabilityBaseline(
        market_id=distribution.market_id,
        analysis_version=distribution.analysis_version,
        baseline_version=distribution.baseline_version,
        positions=positions,
    )


def validate_statistical_probability_baseline(
    baseline: StatisticalProbabilityBaseline,
) -> None:
    if not isinstance(baseline, StatisticalProbabilityBaseline):
        raise TypeError(
            "baseline must be a StatisticalProbabilityBaseline instance."
        )

    if (
        not isinstance(baseline.market_id, int)
        or isinstance(baseline.market_id, bool)
        or baseline.market_id <= 0
    ):
        raise ValueError("market_id must be a positive integer.")

    if not isinstance(baseline.analysis_version, str) or not baseline.analysis_version.strip():
        raise ValueError("analysis_version must be a non-empty string.")

    if not isinstance(baseline.baseline_version, str) or not baseline.baseline_version.strip():
        raise ValueError("baseline_version must be a non-empty string.")

    if not isinstance(baseline.positions, tuple):
        raise TypeError("positions must be a tuple.")

    previous = None
    for item in baseline.positions:
        if not isinstance(item, PositionProbabilityBaseline):
            raise TypeError(
                "positions must contain PositionProbabilityBaseline objects."
            )
        if not item.position.strip():
            raise ValueError("position must be a non-empty string.")
        if previous is not None and item.position <= previous:
            raise ValueError("positions must be in deterministic order.")
        previous = item.position

        if not isinstance(item.probabilities, tuple):
            raise TypeError("probabilities must be a tuple.")
        if len(item.probabilities) != 10:
            raise ValueError("probabilities must contain exactly 10 values.")

        for probability in item.probabilities:
            if not isinstance(probability, (int, float)) or isinstance(probability, bool):
                raise TypeError("probabilities must be numeric.")
            if probability < 0.0 or probability > 1.0:
                raise ValueError("probabilities must be between 0 and 1.")

        total = item.total_probability
        if abs(total - 1.0) > 1e-9 and total != 0.0:
            raise ValueError(
                "non-empty probabilities must sum to 1."
            )


def validate_statistical_probability_baseline_result(
    baseline: StatisticalProbabilityBaseline,
) -> StatisticalProbabilityValidationResult:
    if not isinstance(baseline, StatisticalProbabilityBaseline):
        return StatisticalProbabilityValidationResult(
            INVALID,
            (_issue("INVALID_BASELINE_TYPE", "Invalid probability baseline type."),),
        )
    try:
        validate_statistical_probability_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return StatisticalProbabilityValidationResult(
            INVALID,
            (_issue("INVALID_BASELINE", str(exc)),),
        )
    return StatisticalProbabilityValidationResult(VALID, ())


def is_statistical_probability_baseline_valid(
    baseline: StatisticalProbabilityBaseline,
) -> bool:
    return validate_statistical_probability_baseline_result(baseline).is_valid


def get_position_probability(
    baseline: StatisticalProbabilityBaseline,
    position: str,
    digit: int,
) -> float:
    validate_statistical_probability_baseline(baseline)
    if not isinstance(digit, int) or isinstance(digit, bool) or not 0 <= digit <= 9:
        raise ValueError("digit must be an integer from 0 through 9.")
    for item in baseline.positions:
        if item.position == position:
            return item.probabilities[digit]
    raise ValueError(f"Probability baseline not found: {position}")


def get_position_probabilities(
    baseline: StatisticalProbabilityBaseline,
    position: str,
) -> tuple[float, ...]:
    validate_statistical_probability_baseline(baseline)
    for item in baseline.positions:
        if item.position == position:
            return item.probabilities
    raise ValueError(f"Probability baseline not found: {position}")
def get_probability_positions(
    baseline: StatisticalProbabilityBaseline,
) -> tuple[str, ...]:
    validate_statistical_probability_baseline(baseline)
    return baseline.position_names
