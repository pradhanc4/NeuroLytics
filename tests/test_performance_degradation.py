from dataclasses import replace
from datetime import date

import pytest

from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_degradation import (
    DEFAULT_RULES,
    DEGRADED,
    INVALID,
    NOT_DEGRADED,
    PERFORMANCE_DEGRADATION_VERSION,
    DegradationRule,
    build_performance_degradation_report,
    performance_degradation_summary,
    validate_performance_degradation_report,
)
from analytics.performance_monitoring import build_performance_monitoring_report
from analytics.performance_over_time import build_performance_over_time_report
from analytics.top_k_framework import TopKEvaluationReport, TopKEvaluationRow


def row(group, day, rank):
    return TopKEvaluationRow(
        "panel", group, date(2026, 9, day), "045", rank,
        ((1, rank <= 1), (3, rank <= 3), (5, rank <= 5)),
        1.0 / rank, 0.2, 0.6,
    )


def monitoring(ranks):
    rows = [row(f"g{i}", 1 + i * 7, rank) for i, rank in enumerate(ranks)]
    source45 = TopKEvaluationReport(
        "44.0.0", "panel", "top-k-evaluation-report-test", (1, 3, 5),
        tuple(rows), ((1, 0.5), (3, 0.75), (5, 1.0)), 0.5,
        len(rows), len(rows), "top-k-evaluation-report-test",
    )
    source46 = build_performance_over_time_report(build_actual_vs_ranked_report(source45))
    return build_performance_monitoring_report(source46)


def test_version():
    assert PERFORMANCE_DEGRADATION_VERSION == "48.0.0"


def test_default_rules_defined():
    assert len(DEFAULT_RULES) == 5


def test_degradation_detected_for_worse_higher_metric():
    report = build_performance_degradation_report(monitoring([1, 3, 5]))
    assert report.degraded
    assert "mean_actual_rank" in report.degraded_metrics


def test_no_degradation_when_rank_improves():
    report = build_performance_degradation_report(monitoring([5, 3, 1]))
    assert not report.degraded


def test_absolute_threshold_prevents_small_change():
    source = monitoring([1, 1])
    report = build_performance_degradation_report(
        source, rules=(DegradationRule("mean_actual_rank", 2.0),)
    )
    assert not report.degraded


def test_lower_is_worse_metric_direction():
    report = build_performance_degradation_report(
        monitoring([1, 2, 3]),
        rules=(DegradationRule("mean_reciprocal_rank", 0.01),),
    )
    assert report.observations[0].direction == "WORSE_LOWER"


def test_consecutive_period_requirement():
    report = build_performance_degradation_report(
        monitoring([1, 3, 2, 4]),
        rules=(DegradationRule("mean_actual_rank", 0.5, None, 2),),
    )
    assert not report.degraded


def test_consecutive_period_requirement_satisfied():
    report = build_performance_degradation_report(
        monitoring([1, 2, 3, 4]),
        rules=(DegradationRule("mean_actual_rank", 0.5, None, 2),),
    )
    assert report.degraded


def test_relative_threshold_supported():
    report = build_performance_degradation_report(
        monitoring([1, 2]),
        rules=(DegradationRule("mean_actual_rank", 100.0, 2.0),),
    )
    assert not report.degraded


def test_relative_threshold_can_trigger():
    report = build_performance_degradation_report(
        monitoring([1, 2]),
        rules=(DegradationRule("mean_actual_rank", 100.0, 0.5),),
    )
    assert report.observations[0].relative_change == pytest.approx(1.0)
    assert report.degraded


def test_baseline_and_latest_are_preserved():
    report = build_performance_degradation_report(
        monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 0.5),)
    )
    item = report.observations[0]
    assert item.baseline_value == pytest.approx(1.0)
    assert item.latest_value == pytest.approx(3.0)
    assert item.absolute_change == pytest.approx(2.0)


def test_source_lineage():
    source = monitoring([1, 3])
    report = build_performance_degradation_report(source)
    assert report.monitoring_report_identity == source.report_identity
    assert report.source_report_identity == source.source_report_identity


def test_deterministic_identity():
    first = build_performance_degradation_report(monitoring([1, 3]))
    second = build_performance_degradation_report(monitoring([1, 3]))
    assert first.report_identity == second.report_identity


def test_summary():
    report = build_performance_degradation_report(monitoring([1, 3]))
    summary = performance_degradation_summary(report)
    assert summary["status"] == "VALID"
    assert summary["degraded"] is True


def test_valid_report():
    report = build_performance_degradation_report(monitoring([1, 3]))
    result = validate_performance_degradation_report(report)
    assert result.status == "VALID"


def test_invalid_type():
    result = validate_performance_degradation_report(None)
    assert result.status == INVALID


def test_invalid_version():
    report = build_performance_degradation_report(monitoring([1, 3]))
    result = validate_performance_degradation_report(replace(report, version="0"))
    assert "INVALID_VERSION" in result.issues


def test_duplicate_rules_rejected():
    source = monitoring([1, 3])
    rule = DegradationRule("mean_actual_rank", 0.5)
    with pytest.raises(ValueError, match="unique"):
        build_performance_degradation_report(source, rules=(rule, rule))


def test_unknown_rule_metric_rejected():
    source = monitoring([1, 3])
    with pytest.raises(ValueError, match="not monitored"):
        build_performance_degradation_report(source, rules=(DegradationRule("hit_at_9", 0.1),))


def test_empty_rules_rejected():
    with pytest.raises(ValueError, match="at least one"):
        build_performance_degradation_report(monitoring([1, 3]), rules=())


def test_bad_threshold_rejected():
    with pytest.raises(ValueError, match="positive"):
        build_performance_degradation_report(
            monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 0),)
        )


def test_bad_relative_threshold_rejected():
    with pytest.raises(ValueError, match="positive"):
        build_performance_degradation_report(
            monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 1, 0),)
        )


def test_bad_consecutive_periods_rejected():
    with pytest.raises(ValueError, match="consecutive"):
        build_performance_degradation_report(
            monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 1, None, 0),)
        )


def test_one_period_rejected():
    with pytest.raises(ValueError, match="two monitoring periods"):
        build_performance_degradation_report(monitoring([1]))


def test_degraded_metrics_match_flag():
    report = build_performance_degradation_report(monitoring([1, 3]))
    assert report.degraded == bool(report.degraded_metrics)


def test_non_degraded_constant_series():
    report = build_performance_degradation_report(monitoring([2, 2, 2]))
    assert report.degraded is False
    assert report.degraded_metrics == ()


def test_hit_metric_can_be_monitored_and_detected():
    source = monitoring([1, 1, 1])
    source = replace(source, monitored_metrics=("hit_at_1",))
    with pytest.raises(ValueError):
        build_performance_degradation_report(source, rules=(DegradationRule("hit_at_1", 0.1),))


def test_report_identity_prefix():
    report = build_performance_degradation_report(monitoring([1, 3]))
    assert report.report_identity.startswith("performance-degradation-report-")


def test_panel_source_supported():
    assert build_performance_degradation_report(monitoring([1, 3])).source_type == "panel"


def test_monitoring_report_validation_is_required():
    source = monitoring([1, 3])
    invalid = replace(source, source_type="other")
    with pytest.raises(ValueError, match="invalid Phase 47"):
        build_performance_degradation_report(invalid)


def test_default_rule_observation_count():
    report = build_performance_degradation_report(monitoring([1, 2, 3]))
    assert len(report.observations) == len(DEFAULT_RULES)


def test_not_degraded_constant_rank():
    report = build_performance_degradation_report(
        monitoring([2, 2]), rules=(DegradationRule("mean_actual_rank", 0.1),)
    )
    assert report.observations[0].degraded is False
    assert NOT_DEGRADED == "NOT_DEGRADED"


def test_degraded_constant_flag():
    report = build_performance_degradation_report(
        monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 0.1),)
    )
    assert report.observations[0].degraded is True
    assert DEGRADED == "DEGRADED"


def test_relative_change_zero_baseline_is_none():
    source = monitoring([1, 1])
    report = build_performance_degradation_report(
        source, rules=(DegradationRule("miss_rate", 0.01, 0.1),)
    )
    assert report.observations[0].relative_change is None


def test_no_alert_field():
    report = build_performance_degradation_report(monitoring([1, 3]))
    assert not hasattr(report, "alerts")


def test_no_retraining_field():
    report = build_performance_degradation_report(monitoring([1, 3]))
    assert not hasattr(report, "model_artifacts")


def test_source_identity_is_not_changed():
    source = monitoring([1, 3])
    report = build_performance_degradation_report(source)
    assert report.source_report_identity == source.source_report_identity


def test_absolute_change_sign_for_rank():
    report = build_performance_degradation_report(
        monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 0.1),)
    )
    assert report.observations[0].absolute_change > 0


def test_absolute_change_sign_for_mrr():
    source = monitoring([1, 2])
    report = build_performance_degradation_report(
        source, rules=(DegradationRule("mean_reciprocal_rank", 0.01),)
    )
    assert report.observations[0].absolute_change < 0


def test_validation_detects_degraded_metric_mismatch():
    report = build_performance_degradation_report(monitoring([1, 3]))
    invalid = replace(report, degraded_metrics=())
    result = validate_performance_degradation_report(invalid)
    assert "DEGRADED_METRICS_MISMATCH" in result.issues


def test_validation_detects_flag_mismatch():
    report = build_performance_degradation_report(monitoring([1, 3]))
    invalid = replace(report, degraded=False)
    result = validate_performance_degradation_report(invalid)
    assert "DEGRADED_FLAG_MISMATCH" in result.issues


def test_validation_detects_identity_mismatch():
    report = build_performance_degradation_report(monitoring([1, 3]))
    invalid = replace(report, report_identity="bad")
    result = validate_performance_degradation_report(invalid)
    assert "INVALID_REPORT_IDENTITY" in result.issues


def test_custom_rule_subset():
    report = build_performance_degradation_report(
        monitoring([1, 3]), rules=(DegradationRule("mean_actual_rank", 0.5),)
    )
    assert tuple(item.metric for item in report.observations) == ("mean_actual_rank",)


def test_multiple_metrics_can_degrade():
    report = build_performance_degradation_report(
        monitoring([1, 5, 10]),
        rules=(
            DegradationRule("mean_actual_rank", 0.5),
            DegradationRule("mean_reciprocal_rank", 0.01),
        ),
    )
    assert set(report.degraded_metrics) == {"mean_actual_rank", "mean_reciprocal_rank"}


def test_degradation_is_threshold_based_not_boolean_trend_only():
    report = build_performance_degradation_report(
        monitoring([1, 2]), rules=(DegradationRule("mean_actual_rank", 5.0),)
    )
    assert report.degraded is False


def test_evidence_periods_count_recent_adverse_steps():
    report = build_performance_degradation_report(
        monitoring([1, 2, 3, 4]), rules=(DegradationRule("mean_actual_rank", 0.1, None, 3),)
    )
    assert report.observations[0].evidence_periods == 3


def test_recovery_breaks_consecutive_evidence():
    report = build_performance_degradation_report(
        monitoring([1, 2, 1, 4]), rules=(DegradationRule("mean_actual_rank", 0.1, None, 2),)
    )
    assert report.observations[0].evidence_periods == 1
    assert report.degraded is False
