from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import StatisticalBaselineDataset
from analytics.statistical_baseline_validation import (
    validate_complete_statistical_baseline,
)
from analytics.statistical_central_tendency_dispersion import (
    build_statistical_central_tendency_dispersion_baseline,
)
from analytics.statistical_conditional_probability import (
    build_statistical_conditional_probability_baseline,
)
from analytics.statistical_distribution_baseline import (
    build_statistical_distribution_baseline,
)
from analytics.statistical_independence_baseline import (
    build_statistical_independence_baseline,
)
from analytics.statistical_probability_baseline import (
    build_statistical_probability_baseline,
)
from analytics.statistical_significance_baseline import (
    build_statistical_significance_baseline,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalBaselineReproducibilityResult:
    status: str
    component_results: tuple[tuple[str, bool], ...]

    @property
    def is_reproducible(self) -> bool:
        return self.status == VALID


def check_statistical_baseline_reproducibility(
    dataset: StatisticalBaselineDataset,
) -> StatisticalBaselineReproducibilityResult:
    validate_complete_statistical_baseline(dataset)
    builders = (
        ("distribution", build_statistical_distribution_baseline),
        ("central_tendency_dispersion",
         build_statistical_central_tendency_dispersion_baseline),
        ("probability", build_statistical_probability_baseline),
        ("conditional_probability",
         build_statistical_conditional_probability_baseline),
        ("independence", build_statistical_independence_baseline),
        ("significance", build_statistical_significance_baseline),
    )
    results = []
    for name, builder in builders:
        first = builder(dataset)
        second = builder(dataset)
        results.append((name, first == second))
    return StatisticalBaselineReproducibilityResult(
        status=VALID if all(value for _, value in results) else INVALID,
        component_results=tuple(results),
    )
