from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_conditional_probability import (
    VALID,
    StatisticalConditionalProbabilityBaseline,
    build_statistical_conditional_probability_baseline,
    get_conditional_probability,
    is_statistical_conditional_probability_baseline_valid,
    validate_statistical_conditional_probability_baseline,
    validate_statistical_conditional_probability_baseline_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def dataset():
    rows = (
        (1, 0, 1),
        (2, 0, 2),
        (3, 1, 2),
        (4, 1, 2),
    )
    observations = tuple(
        StatisticalObservation(
            record_date=date(2026, 1, day),
            column_name=column,
            value=value,
        )
        for day, col1, col2 in rows
        for column, value in (("col1", col1), ("col2", col2))
    )
    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        analysis_version="v1",
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result=result,
        observations=observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v18.9",
    )
    return build_statistical_baseline_dataset(
        contract=contract,
        observations=observations,
    )


def test_builds_all_position_pairs():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    assert baseline.pair_count == 2


def test_conditional_probability():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    assert get_conditional_probability(
        baseline, "col1", "col2", 0, 1
    ) == pytest.approx(0.5)
    assert get_conditional_probability(
        baseline, "col1", "col2", 0, 2
    ) == pytest.approx(0.5)
    assert get_conditional_probability(
        baseline, "col1", "col2", 1, 2
    ) == pytest.approx(1.0)


def test_zero_is_valid_condition():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    assert get_conditional_probability(
        baseline, "col1", "col2", 0, 1
    ) > 0


def test_unobserved_condition_is_zero_matrix_row():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    assert get_conditional_probability(
        baseline, "col1", "col2", 9, 9
    ) == 0.0


def test_validation():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    validate_statistical_conditional_probability_baseline(baseline)
    result = validate_statistical_conditional_probability_baseline_result(baseline)
    assert result.status == VALID
    assert result.is_valid
    assert is_statistical_conditional_probability_baseline_valid(baseline)


def test_invalid_type():
    result = validate_statistical_conditional_probability_baseline_result(object())
    assert not result.is_valid


def test_matrix_shape_is_validated():
    baseline = StatisticalConditionalProbabilityBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.9",
        matrices=(),
    )
    validate_statistical_conditional_probability_baseline(baseline)


def test_invalid_digit():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    with pytest.raises(ValueError):
        get_conditional_probability(
            baseline, "col1", "col2", 10, 0
        )


def test_unknown_pair():
    baseline = build_statistical_conditional_probability_baseline(dataset())
    with pytest.raises(ValueError, match="not found"):
        get_conditional_probability(
            baseline, "col1", "col8", 0, 0
        )
