from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)
from analytics.statistical_independence_baseline import (
    VALID,
    StatisticalIndependenceBaseline,
    build_statistical_independence_baseline,
    get_independence_measure,
    validate_statistical_independence_baseline,
    validate_statistical_independence_baseline_result,
)


def dataset():
    observations = tuple(
        StatisticalObservation(date(2026, 1, day), column, value)
        for day, a, b in (
            (1, 0, 0), (2, 0, 0), (3, 1, 1), (4, 1, 1)
        )
        for column, value in (("col1", a), ("col2", b))
    )
    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        analysis_version="v1",
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result, observations, ("col1", "col2"), "v18.10"
    )
    return build_statistical_baseline_dataset(contract, observations)


def test_builds_pair_measure():
    baseline = build_statistical_independence_baseline(dataset())
    assert len(baseline.measures) == 1


def test_perfect_dependence_is_detected():
    baseline = build_statistical_independence_baseline(dataset())
    item = get_independence_measure(baseline, "col1", "col2")
    assert item.total_observations == 4
    assert item.max_probability_difference > 0
    assert item.chi_square > 0
    assert not item.independent


def test_deterministic_pair_lookup():
    baseline = build_statistical_independence_baseline(dataset())
    assert get_independence_measure(
        baseline, "col1", "col2"
    ).position_a == "col1"


def test_validation():
    baseline = build_statistical_independence_baseline(dataset())
    validate_statistical_independence_baseline(baseline)
    result = validate_statistical_independence_baseline_result(baseline)
    assert result.status == VALID
    assert result.is_valid


def test_invalid_type():
    result = validate_statistical_independence_baseline_result(object())
    assert not result.is_valid


def test_empty_baseline_is_valid():
    baseline = StatisticalIndependenceBaseline(1, "v1", "v18.10", ())
    validate_statistical_independence_baseline(baseline)


def test_unknown_pair():
    baseline = build_statistical_independence_baseline(dataset())
    with pytest.raises(ValueError, match="not found"):
        get_independence_measure(baseline, "col2", "col1")
