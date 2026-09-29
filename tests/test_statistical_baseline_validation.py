from datetime import date

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_baseline_validation import (
    INVALID,
    VALID,
    validate_complete_statistical_baseline,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def dataset():
    observations = tuple(
        StatisticalObservation(date(2026, 1, day), column, value)
        for day, values in enumerate(
            ((0, 1), (1, 2), (2, 3), (2, 4)), 1
        )
        for column, value in zip(("col1", "col2"), values)
    )
    request = StatisticalAnalysisRequest(
        1, date(2026, 1, 1), date(2026, 1, 4), "v1"
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result, observations, ("col1", "col2"), "v18.13"
    )
    return build_statistical_baseline_dataset(contract, observations)


def test_complete_validation():
    report = validate_complete_statistical_baseline(dataset())
    assert report.status == VALID
    assert report.is_valid
    assert len(report.checked_components) == 6
    assert report.issues == ()


def test_validation_is_repeatable():
    first = validate_complete_statistical_baseline(dataset())
    second = validate_complete_statistical_baseline(dataset())
    assert first == second


def test_report_is_immutable():
    report = validate_complete_statistical_baseline(dataset())
    try:
        report.status = INVALID
        assert False
    except AttributeError:
        pass
