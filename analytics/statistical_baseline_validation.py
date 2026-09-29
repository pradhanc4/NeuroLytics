from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import StatisticalBaselineDataset
from analytics.statistical_central_tendency_dispersion import (
    build_statistical_central_tendency_dispersion_baseline,
    validate_statistical_central_tendency_dispersion_baseline,
)
from analytics.statistical_conditional_probability import (
    build_statistical_conditional_probability_baseline,
    validate_statistical_conditional_probability_baseline,
)
from analytics.statistical_distribution_baseline import (
    build_statistical_distribution_baseline,
    validate_statistical_distribution_baseline,
)
from analytics.statistical_independence_baseline import (
    build_statistical_independence_baseline,
    validate_statistical_independence_baseline,
)
from analytics.statistical_probability_baseline import (
    build_statistical_probability_baseline,
    validate_statistical_probability_baseline,
)
from analytics.statistical_significance_baseline import (
    build_statistical_significance_baseline,
    validate_statistical_significance_baseline,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalBaselineValidationReport:
    status: str
    checked_components: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def validate_complete_statistical_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalBaselineValidationReport:
    components = (
        (
            "distribution",
            build_statistical_distribution_baseline,
            validate_statistical_distribution_baseline,
        ),
        (
            "central_tendency_dispersion",
            build_statistical_central_tendency_dispersion_baseline,
            validate_statistical_central_tendency_dispersion_baseline,
        ),
        (
            "probability",
            build_statistical_probability_baseline,
            validate_statistical_probability_baseline,
        ),
        (
            "conditional_probability",
            build_statistical_conditional_probability_baseline,
            validate_statistical_conditional_probability_baseline,
        ),
        (
            "independence",
            build_statistical_independence_baseline,
            validate_statistical_independence_baseline,
        ),
        (
            "significance",
            build_statistical_significance_baseline,
            validate_statistical_significance_baseline,
        ),
    )
    checked = []
    issues = []
    for name, builder, validator in components:
        try:
            baseline = builder(dataset)
            validator(baseline)
            checked.append(name)
        except (TypeError, ValueError) as exc:
            issues.append(f"{name}: {exc}")
    return StatisticalBaselineValidationReport(
        status=VALID if not issues else INVALID,
        checked_components=tuple(checked),
        issues=tuple(issues),
    )
