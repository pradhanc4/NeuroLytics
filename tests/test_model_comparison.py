import math

import pytest

from analytics.model_health import CRITICAL, DEGRADED, HEALTHY, HealthComponent, build_model_health_report
from analytics.model_comparison import (
    MODEL_COMPARISON_VERSION,
    ModelComparisonReport,
    ModelHealthSnapshot,
    ModelMetricComparison,
    build_model_comparison_report,
    build_model_health_snapshot,
    model_comparison_metrics,
    model_comparison_snapshots,
    model_comparison_summary,
    validate_model_comparison_report,
)


def health(model, score, period_source):
    status = HEALTHY if score >= 0.8 else DEGRADED if score >= 0.5 else CRITICAL
    return build_model_health_report(
        model,
        (HealthComponent("overall", score, status, 1.0, period_source),),
    )


def snapshots():
    return (
        build_model_health_snapshot("P1", health("model-a", 0.70, "a-p1")),
        build_model_health_snapshot("P1", health("model-b", 0.90, "b-p1")),
        build_model_health_snapshot("P2", health("model-a", 0.85, "a-p2")),
        build_model_health_snapshot("P2", health("model-b", 0.90, "b-p2")),
        build_model_health_snapshot("P2", health("model-c", 0.60, "c-p2")),
    )


def report():
    return build_model_comparison_report("cmp-58", "P1", "P2", snapshots())


def test_version():
    assert report().version == MODEL_COMPARISON_VERSION


def test_common_models():
    assert report().common_models == ("model-a", "model-b")


def test_baseline_only_models():
    assert report().baseline_only_models == ()


def test_comparison_only_models():
    assert report().comparison_only_models == ("model-c",)


def test_improved_models():
    assert report().improved_models == ("model-a",)


def test_declined_models():
    assert report().declined_models == ()


def test_unchanged_models():
    assert report().unchanged_models == ("model-b",)


def test_metric_count():
    assert len(report().metric_comparisons) == 2


def test_model_a_change():
    item = model_comparison_metrics(report(), "model-a")[0]
    assert math.isclose(item.absolute_change, 0.15)
    assert math.isclose(item.relative_change, 0.15 / 0.70)


def test_model_b_change():
    item = model_comparison_metrics(report(), "model-b")[0]
    assert item.absolute_change == 0.0
    assert item.relative_change == 0.0


def test_snapshot_accessor():
    assert len(model_comparison_snapshots(report(), "P1")) == 2


def test_snapshot_accessor_all():
    assert len(model_comparison_snapshots(report())) == 5


def test_metric_accessor_all():
    assert len(model_comparison_metrics(report())) == 2


def test_summary():
    summary = model_comparison_summary(report())
    assert summary["status"] == "VALID"
    assert summary["comparisons"] == 2


def test_snapshot_source_lineage():
    assert snapshots()[0].source_report_identity


def test_snapshot_period():
    assert snapshots()[0].period_label == "P1"


def test_snapshot_model():
    assert snapshots()[0].model_identity == "model-a"


def test_snapshot_score():
    assert snapshots()[0].health_score == 0.70


def test_snapshot_status():
    assert snapshots()[0].health_status == DEGRADED


def test_snapshot_components():
    assert snapshots()[0].component_scores == (("overall", 0.70),)


def test_builder_rejects_blank_period():
    with pytest.raises(ValueError):
        build_model_health_snapshot("", health("m", 0.8, "x"))


def test_builder_rejects_wrong_report_type():
    with pytest.raises(TypeError):
        build_model_health_snapshot("P", object())


def test_report_rejects_blank_comparison_id():
    with pytest.raises(ValueError):
        build_model_comparison_report("", "P1", "P2", snapshots())


def test_report_rejects_identical_periods():
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P", "P", snapshots())


def test_report_rejects_empty_snapshots():
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", ())


def test_report_rejects_undeclared_period():
    values = snapshots() + (ModelHealthSnapshot("P3", "z", 0.5, DEGRADED, (), "z"),)
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", values)


def test_report_rejects_duplicate_model_period():
    values = snapshots() + (snapshots()[0],)
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", values)


def test_report_rejects_missing_baseline():
    values = tuple(item for item in snapshots() if item.period_label != "P1")
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", values)


def test_report_rejects_missing_comparison():
    values = tuple(item for item in snapshots() if item.period_label != "P2")
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", values)


def test_report_rejects_unsupported_metric():
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", snapshots(), metrics=("unknown",))


def test_report_rejects_duplicate_metrics():
    with pytest.raises(ValueError):
        build_model_comparison_report("x", "P1", "P2", snapshots(), metrics=("health_score", "health_score"))


def test_report_identity_prefix():
    assert report().report_identity.startswith("model-comparison-report-")


def test_deterministic_identity():
    assert report().report_identity == build_model_comparison_report("cmp-58", "P1", "P2", snapshots()).report_identity


def test_identity_changes_with_comparison_id():
    assert report().report_identity != build_model_comparison_report("other", "P1", "P2", snapshots()).report_identity


def test_identity_changes_with_snapshot():
    changed = (
        build_model_health_snapshot("P1", health("model-a", 0.71, "a-p1")),
        *snapshots()[1:],
    )
    assert report().report_identity != build_model_comparison_report("cmp-58", "P1", "P2", changed).report_identity


def test_identity_changes_with_period():
    values = (
        ModelHealthSnapshot("BASE", "model-a", 0.70, DEGRADED, (("overall", 0.70),), "a"),
        ModelHealthSnapshot("P2", "model-a", 0.85, HEALTHY, (("overall", 0.85),), "b"),
    )
    assert report().report_identity != build_model_comparison_report("cmp-58", "BASE", "P2", values).report_identity


def test_relative_change_zero_baseline():
    values = (
        ModelHealthSnapshot("P1", "m", 0.0, CRITICAL, (), "b"),
        ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
    )
    result = build_model_comparison_report("z", "P1", "P2", values)
    assert result.metric_comparisons[0].relative_change is None


def test_negative_change():
    values = (
        build_model_health_snapshot("P1", health("m", 0.8, "b")),
        build_model_health_snapshot("P2", health("m", 0.6, "c")),
    )
    result = build_model_comparison_report("z", "P1", "P2", values)
    assert result.declined_models == ("m",)


def test_unchanged_epsilon():
    values = (
        ModelHealthSnapshot("P1", "m", 0.8, HEALTHY, (), "b"),
        ModelHealthSnapshot("P2", "m", 0.8 + 1e-13, HEALTHY, (), "c"),
    )
    result = build_model_comparison_report("z", "P1", "P2", values)
    assert result.unchanged_models == ("m",)


def test_zero_baseline_absolute_change():
    values = (
        ModelHealthSnapshot("P1", "m", 0.0, CRITICAL, (), "b"),
        ModelHealthSnapshot("P2", "m", 0.2, CRITICAL, (), "c"),
    )
    result = build_model_comparison_report("z", "P1", "P2", values)
    assert result.metric_comparisons[0].absolute_change == 0.2


def test_invalid_snapshot_score():
    with pytest.raises(ValueError):
        build_model_comparison_report(
            "x",
            "P1",
            "P2",
            (
                ModelHealthSnapshot("P1", "m", 1.1, HEALTHY, (), "b"),
                ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
            ),
        )


def test_invalid_snapshot_status():
    with pytest.raises(ValueError):
        build_model_comparison_report(
            "x",
            "P1",
            "P2",
            (
                ModelHealthSnapshot("P1", "m", 0.9, "INVALID", (), "b"),
                ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
            ),
        )


def test_invalid_snapshot_source():
    with pytest.raises(ValueError):
        build_model_comparison_report(
            "x",
            "P1",
            "P2",
            (
                ModelHealthSnapshot("P1", "m", 0.9, HEALTHY, (), ""),
                ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
            ),
        )


def test_duplicate_component_snapshot_names():
    with pytest.raises(ValueError):
        build_model_comparison_report(
            "x",
            "P1",
            "P2",
            (
                ModelHealthSnapshot("P1", "m", 0.9, HEALTHY, (("x", 0.9), ("x", 0.8)), "b"),
                ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
            ),
        )


def test_invalid_component_snapshot_score():
    with pytest.raises(ValueError):
        build_model_comparison_report(
            "x",
            "P1",
            "P2",
            (
                ModelHealthSnapshot("P1", "m", 0.9, HEALTHY, (("x", 1.2),), "b"),
                ModelHealthSnapshot("P2", "m", 0.5, DEGRADED, (), "c"),
            ),
        )


def test_validation_passes():
    assert validate_model_comparison_report(report()).is_valid


def test_validation_invalid_type():
    assert validate_model_comparison_report(object()).issues == ("INVALID_REPORT_TYPE",)


def test_validation_bad_version():
    value = report()
    bad = ModelComparisonReport(
        "bad",
        value.comparison_id,
        value.baseline_period,
        value.comparison_period,
        value.snapshots,
        value.metric_comparisons,
        value.improved_models,
        value.declined_models,
        value.unchanged_models,
        value.common_models,
        value.baseline_only_models,
        value.comparison_only_models,
        value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_common_models():
    value = report()
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, value.improved_models, value.declined_models,
        value.unchanged_models, ("wrong",), value.baseline_only_models, value.comparison_only_models,
        value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_comparison_change():
    value = report()
    item = value.metric_comparisons[0]
    changed = ModelMetricComparison(item.metric, item.model_identity, item.baseline_value, item.comparison_value, 0.99, item.relative_change)
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, (changed,) + value.metric_comparisons[1:], value.improved_models,
        value.declined_models, value.unchanged_models, value.common_models,
        value.baseline_only_models, value.comparison_only_models, value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_relative_change():
    value = report()
    item = value.metric_comparisons[0]
    changed = ModelMetricComparison(item.metric, item.model_identity, item.baseline_value, item.comparison_value, item.absolute_change, 99.0)
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, (changed,) + value.metric_comparisons[1:], value.improved_models,
        value.declined_models, value.unchanged_models, value.common_models,
        value.baseline_only_models, value.comparison_only_models, value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_improved_collection():
    value = report()
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, ("model-b",), value.declined_models,
        value.unchanged_models, value.common_models, value.baseline_only_models,
        value.comparison_only_models, value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_declined_collection():
    value = report()
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, value.improved_models, ("model-a",),
        value.unchanged_models, value.common_models, value.baseline_only_models,
        value.comparison_only_models, value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_unchanged_collection():
    value = report()
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, value.improved_models, value.declined_models,
        ("model-a",), value.common_models, value.baseline_only_models, value.comparison_only_models,
        value.report_identity,
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_validation_bad_identity():
    value = report()
    bad = ModelComparisonReport(
        value.version, value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, value.improved_models, value.declined_models,
        value.unchanged_models, value.common_models, value.baseline_only_models,
        value.comparison_only_models, "bad",
    )
    assert not validate_model_comparison_report(bad).is_valid


def test_no_promotion_boundary():
    value = report()
    assert not hasattr(value, "promote")
    assert not hasattr(value, "champion")
    assert not hasattr(value, "rollback")


def test_all_models_are_accounted_for():
    value = report()
    assert set(value.common_models) | set(value.baseline_only_models) | set(value.comparison_only_models) == {"model-a", "model-b", "model-c"}


def test_model_comparison_report_is_frozen():
    assert report().__dataclass_params__.frozen


def test_snapshot_is_frozen():
    assert snapshots()[0].__dataclass_params__.frozen


def test_metric_comparison_is_frozen():
    assert report().metric_comparisons[0].__dataclass_params__.frozen


def test_summary_identity():
    assert model_comparison_summary(report())["report_identity"] == report().report_identity


def test_metric_filter_unknown_model():
    assert model_comparison_metrics(report(), "missing") == ()


def test_snapshot_filter_unknown_period():
    assert model_comparison_snapshots(report(), "missing") == ()


def test_status_lineage_preserved():
    assert snapshots()[1].health_status == HEALTHY


def test_critical_status_supported():
    value = health("m", 0.2, "b")
    assert build_model_health_snapshot("P", value).health_status == CRITICAL
