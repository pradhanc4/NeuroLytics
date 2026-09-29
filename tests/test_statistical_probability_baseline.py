from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)
from analytics.statistical_probability_baseline import (
    INVALID,
    VALID,
    PositionProbabilityBaseline,
    StatisticalProbabilityBaseline,
    build_statistical_probability_baseline,
    get_position_probabilities,
    get_position_probability,
    get_probability_positions,
    is_statistical_probability_baseline_valid,
    validate_statistical_probability_baseline,
    validate_statistical_probability_baseline_result,
)


def dataset():
    observations = tuple(
        StatisticalObservation(
            record_date=date(2026, 1, day),
            column_name="col1",
            value=value,
        )
        for day, value in enumerate((0, 1, 1, 2), 1)
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
        analysis_columns=("col1",),
        baseline_version="v18.8",
    )
    return build_statistical_baseline_dataset(
        contract=contract,
        observations=observations,
    )


def test_probability_build():
    baseline = build_statistical_probability_baseline(dataset())
    assert baseline.market_id == 1
    assert baseline.position_names == ("col1",)
    assert get_position_probability(baseline, "col1", 0) == pytest.approx(0.25)
    assert get_position_probability(baseline, "col1", 1) == pytest.approx(0.50)
    assert get_position_probability(baseline, "col1", 2) == pytest.approx(0.25)


def test_probabilities_sum_to_one():
    baseline = build_statistical_probability_baseline(dataset())
    assert sum(get_position_probabilities(baseline, "col1")) == pytest.approx(1.0)


def test_zero_is_preserved():
    baseline = build_statistical_probability_baseline(dataset())
    assert get_position_probability(baseline, "col1", 0) > 0


def test_positions_are_deterministic():
    baseline = build_statistical_probability_baseline(dataset())
    assert get_probability_positions(baseline) == ("col1",)


def test_valid():
    baseline = build_statistical_probability_baseline(dataset())
    validate_statistical_probability_baseline(baseline)
    assert is_statistical_probability_baseline_valid(baseline)
    result = validate_statistical_probability_baseline_result(baseline)
    assert result.status == VALID
    assert result.is_valid


def test_invalid_type():
    result = validate_statistical_probability_baseline_result(object())
    assert result.status == INVALID
    assert not result.is_valid


def test_invalid_probability_count():
    baseline = StatisticalProbabilityBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.8",
        positions=(
            PositionProbabilityBaseline("col1", (0.5,)),
        ),
    )
    with pytest.raises(ValueError, match="exactly 10"):
        validate_statistical_probability_baseline(baseline)


def test_probability_range():
    baseline = StatisticalProbabilityBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.8",
        positions=(
            PositionProbabilityBaseline("col1", (2.0,) + (0.0,) * 9),
        ),
    )
    with pytest.raises(ValueError, match="between 0 and 1"):
        validate_statistical_probability_baseline(baseline)


def test_probability_digit_validation():
    baseline = build_statistical_probability_baseline(dataset())
    with pytest.raises(ValueError, match="0 through 9"):
        get_position_probability(baseline, "col1", 10)


def test_unknown_position():
    baseline = build_statistical_probability_baseline(dataset())
    with pytest.raises(ValueError, match="not found"):
        get_position_probabilities(baseline, "col8")


def test_immutable():
    baseline = build_statistical_probability_baseline(dataset())
    with pytest.raises(AttributeError):
        baseline.market_id = 2
