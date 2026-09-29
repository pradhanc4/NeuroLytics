from __future__ import annotations

from dataclasses import dataclass
from math import erfc, sqrt

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class DigitSignificance:
    position: str
    digit: int
    observation_count: int
    observed_probability: float
    expected_probability: float
    z_score: float
    p_value: float
    significant_at_05: bool


@dataclass(frozen=True)
class StatisticalSignificanceBaseline:
    market_id: int
    analysis_version: str
    baseline_version: str
    results: tuple[DigitSignificance, ...]


@dataclass(frozen=True)
class SignificanceValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _normal_two_sided_p(z_score: float) -> float:
    return erfc(abs(z_score) / sqrt(2.0))


def build_statistical_significance_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalSignificanceBaseline:
    validate_statistical_baseline_dataset(dataset)
    grouped = {column: [] for column in dataset.columns}
    for observation in dataset.observations:
        grouped[observation.column_name].append(observation.value)

    results = []
    for position in dataset.columns:
        values = grouped[position]
        n = len(values)
        counts = [0] * 10
        for value in values:
            counts[value] += 1

        for digit in range(10):
            observed = counts[digit] / n if n else 0.0
            expected = 0.1
            standard_error = (
                sqrt(expected * (1.0 - expected) / n)
                if n
                else 0.0
            )
            z = (
                (observed - expected) / standard_error
                if standard_error
                else 0.0
            )
            p_value = _normal_two_sided_p(z) if n else 1.0
            results.append(
                DigitSignificance(
                    position=position,
                    digit=digit,
                    observation_count=n,
                    observed_probability=observed,
                    expected_probability=expected,
                    z_score=z,
                    p_value=p_value,
                    significant_at_05=p_value < 0.05,
                )
            )

    return StatisticalSignificanceBaseline(
        market_id=dataset.contract.market_id,
        analysis_version=dataset.contract.analysis_version,
        baseline_version=dataset.contract.baseline_version,
        results=tuple(results),
    )


def validate_statistical_significance_baseline(
    baseline: StatisticalSignificanceBaseline,
) -> None:
    if not isinstance(baseline, StatisticalSignificanceBaseline):
        raise TypeError(
            "baseline must be a StatisticalSignificanceBaseline instance."
        )
    if baseline.market_id <= 0:
        raise ValueError("market_id must be positive.")
    previous = None
    for item in baseline.results:
        if not isinstance(item, DigitSignificance):
            raise TypeError("results must contain DigitSignificance objects.")
        key = (item.position, item.digit)
        if previous is not None and key <= previous:
            raise ValueError("results must be in deterministic order.")
        previous = key
        if not 0 <= item.digit <= 9:
            raise ValueError("digit must be from 0 through 9.")
        if item.observation_count < 0:
            raise ValueError("observation_count cannot be negative.")
        if not 0.0 <= item.observed_probability <= 1.0:
            raise ValueError("observed_probability must be between 0 and 1.")
        if item.expected_probability != 0.1:
            raise ValueError("expected_probability must be 0.1.")
        if item.p_value < 0.0 or item.p_value > 1.0:
            raise ValueError("p_value must be between 0 and 1.")


def validate_statistical_significance_baseline_result(
    baseline: StatisticalSignificanceBaseline,
) -> SignificanceValidationResult:
    if not isinstance(baseline, StatisticalSignificanceBaseline):
        return SignificanceValidationResult(INVALID, ("INVALID_BASELINE_TYPE",))
    try:
        validate_statistical_significance_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return SignificanceValidationResult(INVALID, (str(exc),))
    return SignificanceValidationResult(VALID, ())


def get_digit_significance(
    baseline: StatisticalSignificanceBaseline,
    position: str,
    digit: int,
) -> DigitSignificance:
    validate_statistical_significance_baseline(baseline)
    for item in baseline.results:
        if item.position == position and item.digit == digit:
            return item
    raise ValueError(f"Significance result not found: {position}/{digit}")
