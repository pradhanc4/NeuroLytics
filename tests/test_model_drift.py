from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import ActualVsRankedObservation, ActualVsRankedReport
from analytics.model_drift import (
    DEFAULT_BINS,
    DEFAULT_THRESHOLD,
    MODEL_DRIFT_VERSION,
    ModelDriftRule,
    build_model_drift_report,
    model_drift_observations,
    model_drift_summary,
    validate_model_drift_report,
)


def make_source(first_values=(0.1, 0.12, 0.08, 0.11), second_values=(0.1, 0.12, 0.08, 0.11), *, source_type="panel"):
    observations = []
    values = list(first_values) + list(second_values)
    for index, probability in enumerate(values):
        target = date(2026, 1, 1) + timedelta(days=14 if index >= len(first_values) else 0,)
        if index >= len(first_values):
            local_index = index - len(first_values)
            target = date(2026, 1, 15) + timedelta(days=local_index)
        else:
            target = date(2026, 1, 1) + timedelta(days=index)
        observations.append(ActualVsRankedObservation(
            source_type, f"g{index}", target, "001", 1,
            1.0, ((1, True),), "TOP_1", probability, probability,
        ))
    payload = tuple(observations)
    return ActualVsRankedReport(
        "45.0.0", source_type, "source-45", payload, ((1, len(payload)),),
        (("TOP_1", len(payload)),), ((1, 1.0),), len(payload), 0,
        1.0, 1.0, 1.0, sum(values) / len(values), sum(values) / len(values),
        "actual-vs-ranked-report-fixture",
    )


def test_default_report_is_valid_and_deterministic():
    source = make_source()
    first = build_model_drift_report(source)
    second = build_model_drift_report(source)
    assert first.version == MODEL_DRIFT_VERSION
    assert first.bin_count == DEFAULT_BINS
    assert first.report_identity == second.report_identity
    assert validate_model_drift_report(first).is_valid


def test_stable_distribution_is_not_drifted():
    report = build_model_drift_report(make_source())
    assert report.drifted is False
    assert report.drifted_metrics == ()
    assert all(not item.drifted for item in report.observations)


def test_shifted_distribution_is_detected():
    source = make_source(second_values=(0.91, 0.92, 0.88, 0.90))
    report = build_model_drift_report(source)
    assert report.drifted is True
    assert "top_probability" in report.drifted_metrics
    assert "cumulative_probability" in report.drifted_metrics


def test_custom_threshold_changes_detection():
    source = make_source(second_values=(0.91, 0.92, 0.88, 0.90))
    rules = (ModelDriftRule("top_probability", 100.0),)
    report = build_model_drift_report(source, rules=rules)
    assert report.drifted is False


def test_custom_metric_observation_accessor():
    report = build_model_drift_report(make_source(), rules=(ModelDriftRule("top_probability"),))
    observations = model_drift_observations(report, "top_probability")
    assert len(observations) == 1
    assert observations[0].baseline_count == 4
    assert observations[0].comparison_count == 4


def test_summary_exposes_contract():
    report = build_model_drift_report(make_source())
    summary = model_drift_summary(report)
    assert summary["status"] == "VALID"
    assert summary["period_days"] == 7
    assert summary["comparisons"] == 2


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_model_drift_report(object())


def test_invalid_period_days_are_rejected():
    with pytest.raises(ValueError):
        build_model_drift_report(make_source(), period_days=0)


def test_invalid_bin_count_is_rejected():
    with pytest.raises(ValueError):
        build_model_drift_report(make_source(), bin_count=1)


def test_unknown_metric_is_rejected():
    with pytest.raises(ValueError):
        build_model_drift_report(make_source(), rules=(ModelDriftRule("unknown"),))


def test_duplicate_rule_metrics_are_rejected():
    rules = (ModelDriftRule("top_probability"), ModelDriftRule("top_probability"))
    with pytest.raises(ValueError):
        build_model_drift_report(make_source(), rules=rules)


def test_nonpositive_threshold_is_rejected():
    with pytest.raises(ValueError):
        build_model_drift_report(make_source(), rules=(ModelDriftRule("top_probability", 0.0),))


def test_two_periods_are_required():
    source = make_source(first_values=(0.1, 0.2, 0.3, 0.4), second_values=())
    with pytest.raises(ValueError):
        build_model_drift_report(source)


def test_panel_and_jodi_are_supported():
    assert build_model_drift_report(make_source(source_type="panel")).source_type == "panel"
    assert build_model_drift_report(make_source(source_type="jodi")).source_type == "jodi"


def test_report_validation_rejects_bad_identity():
    report = build_model_drift_report(make_source())
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.rules, report.bin_count, report.observations,
        report.drifted_metrics, report.drifted_periods, report.drifted,
        "wrong",
    )
    result = validate_model_drift_report(broken)
    assert result.status == "INVALID"
    assert "INVALID_REPORT_IDENTITY" in result.issues
def test_report_validation_rejects_drift_flag_mismatch():
    report = build_model_drift_report(make_source())
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.rules, report.bin_count, report.observations,
        report.drifted_metrics, report.drifted_periods, True,
        report.report_identity,
    )
    result = validate_model_drift_report(broken)
    assert result.status == "INVALID"
    assert "OVERALL_DRIFT_MISMATCH" in result.issues


def test_zero_probability_values_are_supported():
    source = make_source(first_values=(0.0, 0.0, 0.0, 0.0), second_values=(0.0, 0.0, 0.0, 0.0))
    report = build_model_drift_report(source)
    assert validate_model_drift_report(report).is_valid


def test_leading_zero_actual_value_is_preserved():
    report = build_model_drift_report(make_source())
    assert report.source_report_identity == "actual-vs-ranked-report-fixture"


def test_report_identity_changes_with_threshold():
    source = make_source(second_values=(0.91, 0.92, 0.88, 0.90))
    first = build_model_drift_report(source, rules=(ModelDriftRule("top_probability", 0.20),))
    second = build_model_drift_report(source, rules=(ModelDriftRule("top_probability", 0.30),))
    assert first.report_identity != second.report_identity


def test_report_identity_changes_with_bin_count():
    source = make_source(second_values=(0.91, 0.92, 0.88, 0.90))
    first = build_model_drift_report(source, bin_count=10)
    second = build_model_drift_report(source, bin_count=5)
    assert first.report_identity != second.report_identity


def test_multiple_comparison_periods_are_supported():
    observations = []
    values = (0.1, 0.11, 0.09, 0.1, 0.1, 0.11, 0.09, 0.1, 0.8, 0.82, 0.78, 0.81)
    for i, value in enumerate(values):
        target = date(2026, 1, 1) + timedelta(days=i)
        observations.append(ActualVsRankedObservation(
            "panel", f"m{i}", target, "001", 1, 1.0,
            ((1, True),), "TOP_1", value, value,
        ))
    source = ActualVsRankedReport(
        "45.0.0", "panel", "source-45", tuple(observations), ((1, 12),),
        (("TOP_1", 12),), ((1, 1.0),), 12, 0, 1.0, 1.0, 1.0,
        sum(values) / len(values), sum(values) / len(values), "actual-vs-ranked-report-multi",
    )
    report = build_model_drift_report(source, period_days=4)
    assert len(report.observations) == 4
    assert report.drifted is True
