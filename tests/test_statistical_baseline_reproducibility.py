from datetime import date

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_baseline_reproducibility import (
    VALID,
    check_statistical_baseline_reproducibility,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def dataset():
    observations = tuple(
        StatisticalObservation(date(2026, 1, day), column, value)
        for day, values in enumerate(((0, 1), (1, 2), (2, 3)), 1)
        for column, value in zip(("col1", "col2"), values)
    )
    request = StatisticalAnalysisRequest(
        1, date(2026, 1, 1), date(2026, 1, 3), "v1"
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result, observations, ("col1", "col2"), "v18.15"
    )
    return build_statistical_baseline_dataset(contract, observations)


def test_all_components_are_reproducible():
    result = check_statistical_baseline_reproducibility(dataset())
    assert result.status == VALID
    assert result.is_reproducible
    assert len(result.component_results) == 6
    assert all(value for _, value in result.component_results)


def test_reproducibility_result_is_deterministic():
    first = check_statistical_baseline_reproducibility(dataset())
    second = check_statistical_baseline_reproducibility(dataset())
    assert first == second
