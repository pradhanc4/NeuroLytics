from dataclasses import replace
from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_monitoring import (
    DEFAULT_METRICS,
    INVALID,
    PERFORMANCE_MONITORING_VERSION,
    VALID,
    build_performance_monitoring_report,
    monitoring_baseline_value,
    monitoring_latest_value,
    monitoring_metric_names,
    performance_monitoring_summary,
    validate_performance_monitoring_report,
)
from analytics.performance_over_time import build_performance_over_time_report
from analytics.top_k_framework import TopKEvaluationReport, TopKEvaluationRow


def row(group, target_date, rank, source="panel"):
    return TopKEvaluationRow(
        source,
        group,
        target_date,
        "045" if source == "panel" else "05",
        rank,
        (
            (1, rank is not None and rank <= 1),
            (3, rank is not None and rank <= 3),
            (5, rank is not None and rank <= 5),
        ),
        1.0 / rank if rank else 0.0,
        0.2 + (rank or 0) * 0.02,
        0.5 + (rank or 0) * 0.02,
    )


def phase44_source(rows, source_type="panel"):
    return TopKEvaluationReport(
        "44.0.0",
        source_type,
        "top-k-evaluation-report-phase44-test",
        (1, 3, 5),
        tuple(rows),
        ((1, 0.5), (3, 0.75), (5, 1.0)),
        0.75,
        len(rows),
        sum(item.actual_rank is not None for item in rows),
        "top-k-evaluation-report-phase44-test",
    )


def phase46_report(rows, period_days=7):
    phase45 = build_actual_vs_ranked_report(phase44_source(rows))
    return build_performance_over_time_report(
        phase45,
        period_days=period_days,
    )


def monitoring(rows, period_days=7, metrics=None):
    return build_performance_monitoring_report(
        phase46_report(rows, period_days),
        metrics=metrics,
    )


def test_version():
    assert PERFORMANCE_MONITORING_VERSION == "47.0.0"


def test_default_metrics_are_defined():
    assert DEFAULT_METRICS == (
        "mean_actual_rank",
        "mean_reciprocal_rank",
        "miss_rate",
        "mean_top_probability",
        "mean_cumulative_probability",
    )


def test_builds_from_phase46_report():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), 3),
    ])
    assert report.source_type == "panel"
    assert report.period_count == 1
    assert report.observation_count == 2


def test_source_lineage_is_preserved():
    source = phase46_report([row("g1", date(2026, 9, 1), 1)])
    report = build_performance_monitoring_report(source)
    assert report.source_report_identity == source.report_identity


def test_default_metrics_are_monitored():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    assert report.monitored_metrics == DEFAULT_METRICS


def test_custom_metrics_are_supported():
    report = monitoring(
        [row("g1", date(2026, 9, 1), 1)],
        metrics=("miss_rate", "hit_at_3"),
    )
    assert report.monitored_metrics == ("miss_rate", "hit_at_3")


def test_duplicate_metrics_are_normalized():
    report = monitoring(
        [row("g1", date(2026, 9, 1), 1)],
        metrics=("miss_rate", "miss_rate", "hit_at_3"),
    )
    assert report.monitored_metrics == ("miss_rate", "hit_at_3")


def test_empty_metric_selection_rejected():
    with pytest.raises(ValueError, match="at least one"):
        monitoring([row("g1", date(2026, 9, 1), 1)], metrics=())


def test_unknown_metric_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        monitoring([row("g1", date(2026, 9, 1), 1)], metrics=("accuracy",))


def test_snapshot_count_matches_periods_times_metrics():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    assert len(report.snapshots) == report.period_count * len(report.monitored_metrics)


def test_snapshot_period_lineage():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    for snapshot in report.snapshots:
        assert snapshot.period_end == snapshot.period_start + timedelta(days=6)


def test_snapshot_observation_count_preserved():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), 2),
    ])
    assert {item.observation_count for item in report.snapshots} == {2}


def test_snapshot_actual_count_preserved():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), None),
    ])
    assert {item.actual_available_observations for item in report.snapshots} == {1}


def test_rank_metric_snapshot():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), 3),
    ])
    value = next(
        item.value for item in report.snapshots
        if item.metric == "mean_actual_rank"
    )
    assert value == pytest.approx(2.0)


def test_mrr_snapshot():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), 2),
    ])
    value = next(
        item.value for item in report.snapshots
        if item.metric == "mean_reciprocal_rank"
    )
    assert value == pytest.approx(0.75)


def test_miss_rate_snapshot():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 2), None),
    ])
    value = next(
        item.value for item in report.snapshots
        if item.metric == "miss_rate"
    )
    assert value == pytest.approx(0.5)


def test_hit_rate_snapshot():
    report = monitoring(
        [row("g1", date(2026, 9, 1), 3)],
        metrics=("hit_at_3",),
    )
    assert report.snapshots[0].value == pytest.approx(1.0)


def test_latest_period_is_last_period():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    assert report.latest_period_start == date(2026, 9, 8)


def test_baseline_is_first_period():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    assert dict(report.baseline_values)["mean_actual_rank"] == pytest.approx(1.0)


def test_latest_values_are_last_period_values():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    assert dict(report.latest_values)["mean_actual_rank"] == pytest.approx(3.0)


def test_latest_value_query():
    report = monitoring([row("g1", date(2026, 9, 1), 2)])
    assert monitoring_latest_value(report, "mean_actual_rank") == pytest.approx(2.0)


def test_baseline_value_query():
    report = monitoring([row("g1", date(2026, 9, 1), 2)])
    assert monitoring_baseline_value(report, "mean_actual_rank") == pytest.approx(2.0)


def test_metric_names_query():
    report = monitoring([row("g1", date(2026, 9, 1), 2)])
    assert monitoring_metric_names(report) == DEFAULT_METRICS


def test_unknown_latest_metric_query_rejected():
    report = monitoring([row("g1", date(2026, 9, 1), 2)])
    with pytest.raises(KeyError):
        monitoring_latest_value(report, "accuracy")


def test_unknown_baseline_metric_query_rejected():
    report = monitoring([row("g1", date(2026, 9, 1), 2)])
    with pytest.raises(KeyError):
        monitoring_baseline_value(report, "accuracy")


def test_report_is_valid():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    result = validate_performance_monitoring_report(report)
    assert result.status == VALID
    assert result.is_valid


def test_summary_is_valid():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    summary = performance_monitoring_summary(report)
    assert summary["status"] == VALID
    assert summary["periods"] == 1


def test_identity_is_deterministic():
    rows = [
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ]
    first = monitoring(rows)
    second = monitoring(rows)
    assert first.report_identity == second.report_identity


def test_panel_source_supported():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    assert report.source_type == "panel"


def test_jodi_source_supported():
    phase45 = build_actual_vs_ranked_report(
        phase44_source([row("g1", date(2026, 9, 1), 1, "jodi")], "jodi")
    )
    source = build_performance_over_time_report(phase45)
    report = build_performance_monitoring_report(source)
    assert report.source_type == "jodi"


def test_invalid_source_type():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    invalid = replace(report, source_type="other")
    result = validate_performance_monitoring_report(invalid)
    assert result.status == INVALID
    assert "INVALID_SOURCE_TYPE" in result.issues


def test_invalid_version():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    invalid = replace(report, version="0.0.0")
    result = validate_performance_monitoring_report(invalid)
    assert "INVALID_VERSION" in result.issues


def test_invalid_snapshot_count():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    invalid = replace(report, snapshots=report.snapshots[:-1])
    result = validate_performance_monitoring_report(invalid)
    assert "SNAPSHOT_COUNT_MISMATCH" in result.issues


def test_duplicate_metric_names_are_invalid_after_manual_corruption():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    invalid = replace(
        report,
        monitored_metrics=report.monitored_metrics + (report.monitored_metrics[0],),
    )
    result = validate_performance_monitoring_report(invalid)
    assert "DUPLICATE_MONITORED_METRICS" in result.issues


def test_invalid_report_type():
    result = validate_performance_monitoring_report(None)
    assert result.status == INVALID
    assert result.issues == ("INVALID_REPORT_TYPE",)


def test_invalid_source_report_rejected():
    source = phase46_report([row("g1", date(2026, 9, 1), 1)])
    invalid_source = replace(source, source_type="other")
    with pytest.raises(ValueError, match="invalid Phase 46"):
        build_performance_monitoring_report(invalid_source)


def test_custom_period_size_is_preserved():
    report = monitoring(
        [row("g1", date(2026, 9, 1), 1)],
        period_days=3,
    )
    assert report.source_period_days == 3
    assert report.snapshots[0].period_end == date(2026, 9, 3)


def test_zero_digit_lineage_value_is_untouched():
    source = phase46_report([row("g1", date(2026, 9, 1), 1)])
    report = build_performance_monitoring_report(source)
    assert report.source_report_identity == source.report_identity


def test_monitoring_does_not_create_alerts():
    report = monitoring([row("g1", date(2026, 9, 1), 10)])
    assert not hasattr(report, "alerts")


def test_monitoring_does_not_retrain_models():
    report = monitoring([row("g1", date(2026, 9, 1), 10)])
    assert not hasattr(report, "model_artifacts")


def test_summary_contains_baseline_and_latest():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    summary = performance_monitoring_summary(report)
    assert "baseline_values" in summary
    assert "latest_values" in summary


def test_summary_contains_source_identity():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    summary = performance_monitoring_summary(report)
    assert summary["source_report_identity"] == report.source_report_identity


def test_validation_detects_latest_value_mismatch():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    invalid = replace(report, latest_values=(("mean_actual_rank", 999.0),))
    result = validate_performance_monitoring_report(invalid)
    assert "LATEST_VALUE_MISMATCH" in result.issues


def test_validation_detects_baseline_value_mismatch():
    report = monitoring([
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 9), 3),
    ])
    invalid = replace(report, baseline_values=(("mean_actual_rank", 999.0),))
    result = validate_performance_monitoring_report(invalid)
    assert "BASELINE_VALUE_MISMATCH" in result.issues


def test_validation_detects_snapshot_metric_set_mismatch():
    report = monitoring([row("g1", date(2026, 9, 1), 1)])
    invalid = replace(report, snapshots=tuple(item for item in report.snapshots if item.metric != "miss_rate"))
    result = validate_performance_monitoring_report(invalid)
    assert "SNAPSHOT_COUNT_MISMATCH" in result.issues
    assert "SNAPSHOT_METRIC_SET_MISMATCH" in result.issues


def test_validation_accepts_custom_metric_baseline_and_latest():
    report = monitoring(
        [row("g1", date(2026, 9, 1), 1), row("g2", date(2026, 9, 9), 3)],
        metrics=("hit_at_3",),
    )
    result = validate_performance_monitoring_report(report)
    assert result.status == VALID
    assert dict(report.baseline_values)["hit_at_3"] == pytest.approx(1.0)
    assert dict(report.latest_values)["hit_at_3"] == pytest.approx(1.0)
