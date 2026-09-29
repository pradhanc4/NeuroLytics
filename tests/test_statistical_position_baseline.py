from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_descriptive import DescriptiveStatistics
from analytics.statistical_foundation import StatisticalAnalysisResult, StatisticalObservation
from analytics.statistical_position_baseline import (
    INVALID,
    VALID,
    PositionStatisticalBaseline,
    StatisticalPositionBaseline,
    StatisticalPositionBaselineValidationResult,
    build_statistical_position_baseline,
    get_position_statistical_baseline,
    get_position_statistical_baseline_positions,
    get_position_statistics,
    is_statistical_position_baseline_valid,
    validate_statistical_position_baseline,
    validate_statistical_position_baseline_result,
)


def build_dataset():
    observations = (
        StatisticalObservation(date(2026, 1, 1), "col1", 0),
        StatisticalObservation(date(2026, 1, 2), "col1", 2),
        StatisticalObservation(date(2026, 1, 3), "col1", 2),
        StatisticalObservation(date(2026, 1, 4), "col1", 8),
        StatisticalObservation(date(2026, 1, 1), "col2", 1),
        StatisticalObservation(date(2026, 1, 2), "col2", 5),
    )
    result = StatisticalAnalysisResult(
        1, "v1", date(2026, 1, 1), date(2026, 1, 4), 6
    )
    contract = build_statistical_baseline_contract(
        result, observations, analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )
    return build_statistical_baseline_dataset(contract, observations)


def test_build_position_baseline():
    baseline = build_statistical_position_baseline(build_dataset())
    assert baseline.market_id == 1
    assert baseline.position_names == ("col1", "col2")
    assert baseline.position_count == 2


def test_position_statistics_reuse_phase_18_3():
    stats = get_position_statistics(
        build_statistical_position_baseline(build_dataset()), "col1"
    )
    assert isinstance(stats, DescriptiveStatistics)
    assert stats.count == 4
    assert stats.minimum == 0
    assert stats.maximum == 8
    assert stats.range == 8
    assert stats.mean == pytest.approx(3.0)
    assert stats.median == pytest.approx(2.0)
    assert stats.mode == (2,)
    assert stats.variance == pytest.approx(9.0)
    assert stats.standard_deviation == pytest.approx(3.0)


def test_zero_is_preserved():
    stats = get_position_statistics(
        build_statistical_position_baseline(build_dataset()), "col1"
    )
    assert stats.minimum == 0


def test_positions_are_independent():
    baseline = build_statistical_position_baseline(build_dataset())
    assert get_position_statistics(baseline, "col1").count == 4
    assert get_position_statistics(baseline, "col2").count == 2


def test_empty_declared_position_is_supported():
    observations = (StatisticalObservation(date(2026, 1, 1), "col1", 3),)
    result = StatisticalAnalysisResult(
        1, "v1", date(2026, 1, 1), date(2026, 1, 1), 1
    )
    contract = build_statistical_baseline_contract(
        result, observations, analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )
    baseline = build_statistical_position_baseline(
        build_statistical_baseline_dataset(contract, observations)
    )
    stats = get_position_statistics(baseline, "col2")
    assert stats.count == 0
    assert stats.minimum is None
    assert stats.mode == ()


def test_validation_accepts_valid_baseline():
    baseline = build_statistical_position_baseline(build_dataset())
    validate_statistical_position_baseline(baseline)
    assert is_statistical_position_baseline_valid(baseline)


def test_validation_result_accepts_valid_baseline():
    result = validate_statistical_position_baseline_result(
        build_statistical_position_baseline(build_dataset())
    )
    assert result.status == VALID
    assert result.is_valid
    assert result.issue_count == 0


def test_validation_result_rejects_wrong_type():
    result = validate_statistical_position_baseline_result(object())
    assert result.status == INVALID
    assert not result.is_valid
    assert result.issue_count == 1
    assert result.issues[0].code == "INVALID_BASELINE_TYPE"


def test_validation_rejects_wrong_item_type():
    invalid = StatisticalPositionBaseline(1, "v1", "v1", (object(),))
    with pytest.raises(TypeError, match="PositionStatisticalBaseline"):
        validate_statistical_position_baseline(invalid)


def test_validation_rejects_duplicate_positions():
    baseline = build_statistical_position_baseline(build_dataset())
    invalid = StatisticalPositionBaseline(
        1, "v1", "v1", (baseline.positions[0], baseline.positions[0])
    )
    with pytest.raises(ValueError, match="unique"):
        validate_statistical_position_baseline(invalid)


def test_validation_rejects_statistics_mismatch():
    baseline = build_statistical_position_baseline(build_dataset())
    item = baseline.positions[0]
    bad_stats = DescriptiveStatistics(
        "col2", item.statistics.count, item.statistics.minimum,
        item.statistics.maximum, item.statistics.range, item.statistics.mean,
        item.statistics.median, item.statistics.mode, item.statistics.variance,
        item.statistics.standard_deviation,
    )
    invalid = StatisticalPositionBaseline(
        1, "v1", "v1", (PositionStatisticalBaseline("col1", bad_stats),)
    )
    with pytest.raises(ValueError, match="must match"):
        validate_statistical_position_baseline(invalid)


def test_getters_and_invalid_positions():
    baseline = build_statistical_position_baseline(build_dataset())
    assert get_position_statistical_baseline_positions(baseline) == (
        "col1", "col2",
    )
    assert get_position_statistical_baseline(baseline, "col1").position == "col1"
    with pytest.raises(ValueError, match="not found"):
        get_position_statistical_baseline(baseline, "col8")
    with pytest.raises(ValueError, match="Unsupported"):
        get_position_statistical_baseline(baseline, "invalid")


def test_results_are_immutable():
    validation = StatisticalPositionBaselineValidationResult(VALID, ())
    with pytest.raises(AttributeError):
        validation.status = INVALID
    item = build_statistical_position_baseline(build_dataset()).positions[0]
    with pytest.raises(AttributeError):
        item.position = "col8"
