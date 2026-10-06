from datetime import date

import pytest

from analytics.alert_threshold import (
    ALERT_THRESHOLD_VERSION,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    AlertRule,
    AlertThresholdReport,
    build_alert_threshold_report,
    alert_threshold_observations,
    alert_threshold_summary,
    validate_alert_threshold_report,
)


def rules():
    return (
        AlertRule("perf", "mean_actual_rank", 2.0, SEVERITY_WARNING, "gte"),
        AlertRule("critical", "miss_rate", 0.5, SEVERITY_CRITICAL, "gte"),
        AlertRule("info", "mean_top_probability", 0.4, SEVERITY_INFO, "lte"),
    )


def report():
    return build_alert_threshold_report(
        "performance",
        "source-55",
        (
            ("mean_actual_rank", 2.5),
            ("miss_rate", 0.6),
            ("mean_top_probability", 0.7),
        ),
        rules(),
        evaluated_at=date(2026, 9, 30),
    )


def test_version():
    assert report().version == ALERT_THRESHOLD_VERSION


def test_all_thresholds_evaluated():
    result = report()
    assert len(result.observations) == 3


def test_active_alerts():
    result = report()
    assert result.active_alerts == ("perf", "critical")


def test_severity_buckets():
    result = report()
    assert result.critical_alerts == ("critical",)
    assert result.warning_alerts == ("perf",)


def test_info_active_is_not_warning_or_critical():
    result = build_alert_threshold_report(
        "x", "y", (("metric", 0.1),),
        (AlertRule("i", "metric", 0.5, SEVERITY_INFO, "lte"),)
    )
    assert result.active_alerts == ("i",)
    assert result.warning_alerts == ()
    assert result.critical_alerts == ()


@pytest.mark.parametrize(
    "operator,value,expected",
    [
        ("gte", 1.0, True),
        ("gte", 0.99, False),
        ("gt", 1.0, False),
        ("gt", 1.01, True),
        ("lte", 1.0, True),
        ("lte", 1.01, False),
        ("lt", 1.0, False),
        ("lt", 0.99, True),
        ("eq", 1.0, True),
        ("eq", 1.0000000001, False),
    ],
)
def test_operators(operator, value, expected):
    result = build_alert_threshold_report(
        "x", "y", (("m", value),),
        (AlertRule("a", "m", 1.0, SEVERITY_WARNING, operator),)
    )
    assert result.observations[0].active is expected


def test_disabled_rule_is_not_evaluated():
    result = build_alert_threshold_report(
        "x", "y", (("m", 10.0),),
        (AlertRule("a", "m", 1.0, SEVERITY_CRITICAL, "gte", False),)
    )
    assert result.observations == ()
    assert result.alert_count == 0


def test_missing_metric_for_enabled_rule_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("other", 1.0),),
            (AlertRule("a", "m", 1.0),)
        )


def test_duplicate_rule_ids_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "m", 1.0), AlertRule("a", "m", 2.0))
        )


@pytest.mark.parametrize("severity", ["LOW", "", "critical"])
def test_invalid_severity_rejected(severity):
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "m", 1.0, severity),)
        )


@pytest.mark.parametrize("operator", ["bad", "", "GTE"])
def test_invalid_operator_rejected(operator):
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "m", 1.0, SEVERITY_WARNING, operator),)
        )


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "m", threshold),)
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_value_rejected(value):
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", value),),
            (AlertRule("a", "m", 1.0),)
        )


def test_duplicate_metric_values_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0), ("m", 2.0)),
            (AlertRule("a", "m", 1.0),)
        )


def test_empty_rules_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report("x", "y", (("m", 1.0),), ())


def test_empty_values_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report("x", "y", (), rules())


def test_empty_source_type_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report("", "y", (("m", 1.0),), rules())


def test_empty_source_identity_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report("x", "", (("m", 1.0),), rules())


def test_blank_rule_id_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("", "m", 1.0),)
        )


def test_blank_metric_rejected():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "", 1.0),)
        )


def test_enabled_must_be_boolean():
    with pytest.raises(ValueError):
        build_alert_threshold_report(
            "x", "y", (("m", 1.0),),
            (AlertRule("a", "m", 1.0, enabled=1),)
        )


def test_summary_valid():
    result = report()
    summary = alert_threshold_summary(result)
    assert summary["status"] == "VALID"
    assert summary["alert_count"] == 2


def test_accessor_all():
    result = report()
    assert len(alert_threshold_observations(result)) == 3


def test_accessor_active_only():
    result = report()
    assert tuple(item.alert_id for item in alert_threshold_observations(result, active_only=True)) == ("perf", "critical")


def test_deterministic_identity():
    assert report().report_identity == report().report_identity


def test_identity_changes_with_value():
    first = report()
    second = build_alert_threshold_report(
        "performance", "source-55",
        (("mean_actual_rank", 3.0), ("miss_rate", 0.6), ("mean_top_probability", 0.7)),
        rules(), evaluated_at=date(2026, 9, 30)
    )
    assert first.report_identity != second.report_identity


def test_source_identity_preserved():
    assert report().source_identity == "source-55"
    assert report().observations[0].source_identity == "source-55"


def test_evaluation_date_preserved():
    assert report().observations[0].evaluated_at == date(2026, 9, 30)


def test_threshold_is_inclusive():
    result = build_alert_threshold_report(
        "x", "y", (("m", 1.0),),
        (AlertRule("a", "m", 1.0, SEVERITY_WARNING, "gte"),)
    )
    assert result.active_alerts == ("a",)


def test_validation_passes():
    assert validate_alert_threshold_report(report()).is_valid


def test_validation_invalid_type():
    assert validate_alert_threshold_report(object()).issues == ("INVALID_REPORT_TYPE",)


def test_validation_bad_version():
    value = report()
    bad = AlertThresholdReport(
        "bad", value.source_type, value.source_identity, value.rules,
        value.observations, value.active_alerts, value.critical_alerts,
        value.warning_alerts, value.alert_count, value.report_identity
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_validation_bad_active_flag():
    value = report()
    item = value.observations[0]
    changed = item.__class__(
        item.alert_id, item.metric, item.observed_value, item.threshold,
        item.operator, item.severity, not item.active, item.evaluated_at,
        item.source_identity
    )
    bad = AlertThresholdReport(
        value.version, value.source_type, value.source_identity, value.rules,
        (changed,) + value.observations[1:], value.active_alerts,
        value.critical_alerts, value.warning_alerts, value.alert_count,
        value.report_identity
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_validation_bad_source_identity():
    value = report()
    item = value.observations[0]
    changed = item.__class__(
        item.alert_id, item.metric, item.observed_value, item.threshold,
        item.operator, item.severity, item.active, item.evaluated_at, "other"
    )
    bad = AlertThresholdReport(
        value.version, value.source_type, value.source_identity, value.rules,
        (changed,) + value.observations[1:], value.active_alerts,
        value.critical_alerts, value.warning_alerts, value.alert_count,
        value.report_identity
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_validation_bad_active_collection():
    value = report()
    bad = AlertThresholdReport(
        value.version, value.source_type, value.source_identity, value.rules,
        value.observations, (), value.critical_alerts, value.warning_alerts,
        value.alert_count, value.report_identity
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_validation_bad_count():
    value = report()
    bad = AlertThresholdReport(
        value.version, value.source_type, value.source_identity, value.rules,
        value.observations, value.active_alerts, value.critical_alerts,
        value.warning_alerts, 99, value.report_identity
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_validation_bad_identity():
    value = report()
    bad = AlertThresholdReport(
        value.version, value.source_type, value.source_identity, value.rules,
        value.observations, value.active_alerts, value.critical_alerts,
        value.warning_alerts, value.alert_count, "bad"
    )
    assert not validate_alert_threshold_report(bad).is_valid


def test_multi_source_types():
    result = build_alert_threshold_report(
        "concept_drift", "concept-55",
        (("conditional_rate_change", 0.2),),
        (AlertRule("concept", "conditional_rate_change", 0.1),)
    )
    assert result.active_alerts == ("concept",)


def test_clear_state():
    result = build_alert_threshold_report(
        "feature_drift", "feature-54",
        (("psi", 0.05),),
        (AlertRule("feature", "psi", 0.2, SEVERITY_WARNING, "gte"),)
    )
    assert result.alert_count == 0
    assert result.active_alerts == ()


def test_multiple_rules_same_metric_allowed():
    result = build_alert_threshold_report(
        "x", "y", (("m", 5.0),),
        (
            AlertRule("warning", "m", 3.0, SEVERITY_WARNING),
            AlertRule("critical", "m", 5.0, SEVERITY_CRITICAL),
        )
    )
    assert result.active_alerts == ("warning", "critical")


def test_disabled_rule_does_not_require_metric():
    result = build_alert_threshold_report(
        "x", "y", (("other", 1.0),),
        (AlertRule("disabled", "missing", 1.0, enabled=False),)
    )
    assert result.observations == ()


def test_report_identity_prefix():
    assert report().report_identity.startswith("alert-threshold-report-")


def test_no_action_boundary():
    result = report()
    assert result.alert_count == 2
    assert result.source_identity == "source-55"
    assert not hasattr(result, "retrain")
    assert not hasattr(result, "promote")


def test_rule_order_preserved():
    result = report()
    assert tuple(item.alert_id for item in result.observations) == ("perf", "critical", "info")


def test_disabled_rules_preserved_in_report():
    result = build_alert_threshold_report(
        "x", "y", (("m", 1.0),),
        (AlertRule("disabled", "m", 0.0, enabled=False),)
    )
    assert result.rules[0].enabled is False


def test_gte_boundary_precision():
    result = build_alert_threshold_report(
        "x", "y", (("m", 1.000000000001),),
        (AlertRule("a", "m", 1.0, operator="gte"),)
    )
    assert result.active_alerts == ("a",)
