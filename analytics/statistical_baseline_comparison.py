from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_probability_baseline import (
    StatisticalProbabilityBaseline,
    validate_statistical_probability_baseline,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class ProbabilityChange:
    position: str
    digit: int
    previous_probability: float
    current_probability: float
    absolute_change: float
    changed: bool


@dataclass(frozen=True)
class StatisticalBaselineComparison:
    market_id: int
    previous_baseline_version: str
    current_baseline_version: str
    changes: tuple[ProbabilityChange, ...]

    @property
    def change_count(self) -> int:
        return sum(item.changed for item in self.changes)


@dataclass(frozen=True)
class BaselineComparisonValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def compare_statistical_probability_baselines(
    previous: StatisticalProbabilityBaseline,
    current: StatisticalProbabilityBaseline,
    tolerance: float = 1e-12,
) -> StatisticalBaselineComparison:
    validate_statistical_probability_baseline(previous)
    validate_statistical_probability_baseline(current)
    if previous.market_id != current.market_id:
        raise ValueError("baseline market IDs must match.")
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative.")

    previous_positions = {
        item.position: item for item in previous.positions
    }
    current_positions = {
        item.position: item for item in current.positions
    }
    if set(previous_positions) != set(current_positions):
        raise ValueError("baseline positions must match.")

    changes = []
    for position in sorted(current_positions):
        old = previous_positions[position].probabilities
        new = current_positions[position].probabilities
        for digit in range(10):
            delta = new[digit] - old[digit]
            changes.append(
                ProbabilityChange(
                    position=position,
                    digit=digit,
                    previous_probability=old[digit],
                    current_probability=new[digit],
                    absolute_change=abs(delta),
                    changed=abs(delta) > tolerance,
                )
            )

    return StatisticalBaselineComparison(
        market_id=current.market_id,
        previous_baseline_version=previous.baseline_version,
        current_baseline_version=current.baseline_version,
        changes=tuple(changes),
    )


def validate_statistical_baseline_comparison(
    comparison: StatisticalBaselineComparison,
) -> None:
    if not isinstance(comparison, StatisticalBaselineComparison):
        raise TypeError(
            "comparison must be a StatisticalBaselineComparison instance."
        )
    if comparison.market_id <= 0:
        raise ValueError("market_id must be positive.")
    previous = None
    for item in comparison.changes:
        if not isinstance(item, ProbabilityChange):
            raise TypeError("changes must contain ProbabilityChange objects.")
        key = (item.position, item.digit)
        if previous is not None and key <= previous:
            raise ValueError("changes must be in deterministic order.")
        previous = key
        if not 0 <= item.digit <= 9:
            raise ValueError("digit must be from 0 through 9.")
        if item.previous_probability < 0 or item.current_probability < 0:
            raise ValueError("probabilities cannot be negative.")
        if item.absolute_change < 0:
            raise ValueError("absolute_change cannot be negative.")


def validate_statistical_baseline_comparison_result(
    comparison: StatisticalBaselineComparison,
) -> BaselineComparisonValidationResult:
    if not isinstance(comparison, StatisticalBaselineComparison):
        return BaselineComparisonValidationResult(
            INVALID, ("INVALID_COMPARISON_TYPE",)
        )
    try:
        validate_statistical_baseline_comparison(comparison)
    except (TypeError, ValueError) as exc:
        return BaselineComparisonValidationResult(INVALID, (str(exc),))
    return BaselineComparisonValidationResult(VALID, ())


def get_probability_changes_for_position(
    comparison: StatisticalBaselineComparison,
    position: str,
) -> tuple[ProbabilityChange, ...]:
    validate_statistical_baseline_comparison(comparison)
    return tuple(
        item for item in comparison.changes
        if item.position == position
    )
