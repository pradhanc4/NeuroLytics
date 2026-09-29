from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)
from analytics.statistical_significance_baseline import (
    VALID,
    StatisticalSignificanceBaseline,
    build_statistical_significance_baseline,
    get_digit_significance,
    validate_statistical_significance_baseline,
    validate_statistical_significance_baseline_result,
)


def dataset():
    observations = tuple(
        StatisticalObservation(date(2026, 1, day), "col1", value)
        for day, value in enumerate((0, 0, 0, 1, 2), 1)
    )
    request = StatisticalAnalysisRequest(
        1, date(2026, 1, 1), date(2026, 1, 5), "v1"
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result, observations, ("col1",), "v18.11"
    )
    return build_statistical_baseline_dataset(contract, observations)


def test_builds_ten_digit_results():
    baseline = build_statistical_significance_baseline(dataset())
    assert len(baseline.results) == 10


def test_zero_is_an_observed_digit():
    baseline = build_statistical_significance_baseline(dataset())
    item = get_digit_significance(baseline, "col1", 0)
    assert item.observation_count == 5
    assert item.observed_probability == pytest.approx(0.6)


def test_uniform_expected_probability():
    baseline = build_statistical_significance_baseline(dataset())
    assert all(item.expected_probability == 0.1 for item in baseline.results)


def test_p_values_are_bounded():
    baseline = build_statistical_significance_baseline(dataset())
    assert all(0.0 <= item.p_value <= 1.0 for item in baseline.results)


def test_validation():
    baseline = build_statistical_significance_baseline(dataset())
    validate_statistical_significance_baseline(baseline)
    result = validate_statistical_significance_baseline_result(baseline)
    assert result.status == VALID
    assert result.is_valid


def test_invalid_type():
    result = validate_statistical_significance_baseline_result(object())
    assert not result.is_valid


def test_empty_baseline_is_valid():
    baseline = StatisticalSignificanceBaseline(1, "v1", "v18.11", ())
    validate_statistical_significance_baseline(baseline)


def test_unknown_digit():
    baseline = build_statistical_significance_baseline(dataset())
    with pytest.raises(ValueError, match="not found"):
        get_digit_significance(baseline, "col1", 10)
