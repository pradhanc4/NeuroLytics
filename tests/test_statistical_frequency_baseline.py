from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    build_statistical_baseline_contract,
)
from analytics.statistical_baseline_dataset import (
    build_statistical_baseline_dataset,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisResult,
    StatisticalObservation,
)
from analytics.statistical_frequency_baseline import (
    INVALID,
    VALID,
    StatisticalFrequencyBaseline,
    StatisticalFrequencyBaselineValidationResult,
    build_statistical_frequency_baseline,
    get_frequency_baseline,
    get_frequency_baseline_columns,
    get_frequency_baseline_observation_count,
    is_statistical_frequency_baseline_valid,
    validate_statistical_frequency_baseline,
    validate_statistical_frequency_baseline_result,
)


def build_dataset():
    observations = (
        StatisticalObservation(date(2026, 1, 1), "col1", 0),
        StatisticalObservation(date(2026, 1, 2), "col1", 1),
        StatisticalObservation(date(2026, 1, 3), "col1", 1),
        StatisticalObservation(date(2026, 1, 4), "col1", 5),
        StatisticalObservation(date(2026, 1, 1), "col2", 2),
        StatisticalObservation(date(2026, 1, 2), "col2", 2),
    )
    result = StatisticalAnalysisResult(
        market_id=1,
        analysis_version="v1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        observation_count=len(observations),
    )
    contract = build_statistical_baseline_contract(
        result,
        observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )
    return build_statistical_baseline_dataset(
        contract,
        observations,
    )


def test_build_frequency_baseline():
    baseline = build_statistical_frequency_baseline(
        build_dataset()    )
    assert baseline.market_id == 1
    assert baseline.analysis_version == "v1"
    assert baseline.baseline_version == "v1"
    assert baseline.columns == ("col1", "col2")
    assert baseline.column_count == 2


def test_frequency_counts_reuse_existing_engine():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    col1 = get_frequency_baseline(baseline, "col1")
    assert col1.total_observations == 4
    assert col1.records[0].count == 1
    assert col1.records[1].count == 2
    assert col1.records[5].count == 1
    assert col1.records[0].percentage == pytest.approx(25.0)
    assert col1.records[1].percentage == pytest.approx(50.0)


def test_zero_is_preserved_in_frequency_baseline():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    assert get_frequency_baseline(
        baseline,
        "col1",
    ).records[0].count == 1

def test_all_digits_are_present_in_each_result():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    for result in baseline.frequencies:
        assert tuple(
            record.digit for record in result.records
        ) == tuple(range(10))


def test_frequency_percentages_sum_to_100():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    for result in baseline.frequencies:
        assert sum(
            record.percentage
            for record in result.records
        ) == pytest.approx(100.0)


def test_empty_column_is_supported():
    observations = (
        StatisticalObservation(date(2026, 1, 1), "col1", 3),
    )
    result = StatisticalAnalysisResult(
        market_id=1,
        analysis_version="v1",
        start_date=date(2026, 1, 1),        end_date=date(2026, 1, 1),
        observation_count=1,
    )
    contract = build_statistical_baseline_contract(
        result,
        observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )
    dataset = build_statistical_baseline_dataset(
        contract,
        observations,
    )
    baseline = build_statistical_frequency_baseline(dataset)
    col2 = get_frequency_baseline(baseline, "col2")
    assert col2.total_observations == 0
    assert all(record.percentage == 0.0 for record in col2.records)


def test_validation_accepts_valid_baseline():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    validate_statistical_frequency_baseline(baseline)
    assert is_statistical_frequency_baseline_valid(baseline)


def test_validation_result_accepts_valid_baseline():
    baseline = build_statistical_frequency_baseline(
        build_dataset()    )
    result = validate_statistical_frequency_baseline_result(
        baseline
    )
    assert result.status == VALID
    assert result.is_valid
    assert result.issue_count == 0


def test_validation_result_rejects_wrong_type():
    result = validate_statistical_frequency_baseline_result(
        object()
    )
    assert result.status == INVALID
    assert not result.is_valid
    assert result.issue_count == 1
    assert result.issues[0].code == "INVALID_BASELINE_TYPE"


def test_validation_rejects_wrong_result_type():
    baseline = build_dataset()
    invalid = StatisticalFrequencyBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        frequencies=(object(),),
    )
    with pytest.raises(TypeError, match="FrequencyAnalysisResult"):
        validate_statistical_frequency_baseline(invalid)

def test_validation_rejects_duplicate_columns():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    invalid = StatisticalFrequencyBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        frequencies=(
            baseline.frequencies[0],
            baseline.frequencies[0],
        ),
    )
    with pytest.raises(ValueError, match="unique"):
        validate_statistical_frequency_baseline(invalid)


def test_validation_rejects_unsupported_column():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    original = baseline.frequencies[0]
    invalid_result = type(original)(
        column_name="invalid",
        total_observations=original.total_observations,
        records=original.records,
    )
    invalid = StatisticalFrequencyBaseline(
        market_id=1,        analysis_version="v1",
        baseline_version="v1",
        frequencies=(invalid_result,),
    )
    with pytest.raises(ValueError, match="unsupported"):
        validate_statistical_frequency_baseline(invalid)


def test_validation_rejects_count_mismatch():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    original = baseline.frequencies[0]
    invalid_result = type(original)(
        column_name=original.column_name,
        total_observations=original.total_observations + 1,
        records=original.records,
    )
    invalid = StatisticalFrequencyBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        frequencies=(invalid_result,),
    )
    with pytest.raises(ValueError, match="counts must equal"):
        validate_statistical_frequency_baseline(invalid)


def test_validation_rejects_percentage_mismatch():
    baseline = build_statistical_frequency_baseline(        build_dataset()
    )
    original = baseline.frequencies[0]
    records = list(original.records)
    record = records[0]
    records[0] = type(record)(
        digit=record.digit,
        count=record.count,
        percentage=record.percentage + 1.0,
    )
    invalid_result = type(original)(
        column_name=original.column_name,
        total_observations=original.total_observations,
        records=tuple(records),
    )
    invalid = StatisticalFrequencyBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        frequencies=(invalid_result,),
    )
    with pytest.raises(ValueError, match="percentage"):
        validate_statistical_frequency_baseline(invalid)


def test_validation_rejects_bad_digit_order():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    original = baseline.frequencies[0]
    records = list(original.records)
    records[0], records[1] = records[1], records[0]
    invalid_result = type(original)(
        column_name=original.column_name,
        total_observations=original.total_observations,
        records=tuple(records),
    )
    invalid = StatisticalFrequencyBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        frequencies=(invalid_result,),
    )
    with pytest.raises(ValueError, match="digits 0-9"):
        validate_statistical_frequency_baseline(invalid)


def test_get_columns():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    assert get_frequency_baseline_columns(baseline) == (
        "col1",
        "col2",
    )


def test_get_observation_count():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    assert get_frequency_baseline_observation_count(
        baseline,
        "col1",
    ) == 4


def test_get_missing_column_raises():
    baseline = build_statistical_frequency_baseline(
        build_dataset()
    )
    with pytest.raises(ValueError, match="not found"):
        get_frequency_baseline(baseline, "col8")


def test_result_is_immutable():
    result = StatisticalFrequencyBaselineValidationResult(
        status=VALID,
        issues=(),
    )
    with pytest.raises(AttributeError):
        result.status = INVALID
