import math

import pytest

from analytics.model_health import (
    CRITICAL,
    DEGRADED,
    HEALTHY,
    VALID,
    MODEL_HEALTH_VERSION,
    HealthComponent,
    ModelHealthReport,
    build_model_health_report,
    model_health_component,
    model_health_component_names,
    model_health_summary,
    validate_model_health_report,
)


def components():
    return (
        HealthComponent("performance", 0.90, HEALTHY, 2.0, "perf-47"),
        HealthComponent("drift", 0.70, DEGRADED, 1.0, "drift-49"),
        HealthComponent("concept", 0.95, HEALTHY, 1.0, "concept-55"),
    )


def report():
    return build_model_health_report("model-v57", components())


def test_version():
    assert report().version == MODEL_HEALTH_VERSION


def test_weighted_score():
    assert math.isclose(report().score.weighted_score, 0.8625)


def test_overall_status():
    assert report().score.status == HEALTHY


def test_component_count():
    assert report().score.component_count == 3


def test_degraded_components():
    assert report().score.active_degraded_components == ("drift",)


def test_critical_components():
    assert report().score.active_critical_components == ()


def test_component_names():
    assert model_health_component_names(report()) == ("performance", "drift", "concept")


def test_component_lookup():
    assert model_health_component(report(), "drift").source_identity == "drift-49"


def test_missing_component_lookup():
    with pytest.raises(KeyError):
        model_health_component(report(), "missing")


def test_summary():
    summary = model_health_summary(report())
    assert summary["status"] == "VALID"
    assert summary["health_status"] == HEALTHY
    assert summary["component_count"] == 3


@pytest.mark.parametrize(
    "score,status",
    [
        (0.80, HEALTHY),
        (0.79, DEGRADED),
        (0.50, DEGRADED),
        (0.49, CRITICAL),
        (1.0, HEALTHY),
        (0.0, CRITICAL),
    ],
)
def test_status_boundaries(score, status):
    component = HealthComponent("x", score, status)
    assert build_model_health_report("m", (component,)).score.status == status


def test_custom_thresholds():
    result = build_model_health_report(
        "m",
        (HealthComponent("x", 0.70, DEGRADED),),
        healthy_min=0.90,
        degraded_min=0.60,
    )
    assert result.score.status == DEGRADED


def test_custom_threshold_critical():
    result = build_model_health_report(
        "m",
        (HealthComponent("x", 0.59, CRITICAL),),
        healthy_min=0.90,
        degraded_min=0.60,
    )
    assert result.score.status == CRITICAL


def test_weighting_changes_score():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("strong", 1.0, HEALTHY, 9.0),
            HealthComponent("weak", 0.0, CRITICAL, 1.0),
        ),
    )
    assert math.isclose(result.score.weighted_score, 0.9)
    assert result.score.status == HEALTHY


def test_equal_weights():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("a", 1.0, HEALTHY),
            HealthComponent("b", 0.0, CRITICAL),
        ),
    )
    assert math.isclose(result.score.weighted_score, 0.5)
    assert result.score.status == DEGRADED


def test_source_identity_preserved():
    assert report().components[0].source_identity == "perf-47"


def test_model_identity_preserved():
    assert report().model_identity == "model-v57"


def test_deterministic_identity():
    assert report().report_identity == report().report_identity


def test_identity_changes_with_score():
    first = report()
    second = build_model_health_report(
        "model-v57",
        (
            HealthComponent("performance", 0.80, HEALTHY, 2.0, "perf-47"),
            HealthComponent("drift", 0.70, DEGRADED, 1.0, "drift-49"),
            HealthComponent("concept", 0.95, HEALTHY, 1.0, "concept-55"),
        ),
    )
    assert first.report_identity != second.report_identity


def test_identity_prefix():
    assert report().report_identity.startswith("model-health-report-")


def test_empty_components_rejected():
    with pytest.raises(ValueError):
        build_model_health_report("m", ())


def test_blank_model_identity_rejected():
    with pytest.raises(ValueError):
        build_model_health_report("", components())


def test_blank_component_name_rejected():
    with pytest.raises(ValueError):
        build_model_health_report("m", (HealthComponent("", 1.0, HEALTHY),))


@pytest.mark.parametrize("score", [-0.01, 1.01, float("nan"), float("inf"), -float("inf")])
def test_invalid_score_rejected(score):
    with pytest.raises(ValueError):
        build_model_health_report("m", (HealthComponent("x", score, HEALTHY),))


@pytest.mark.parametrize("weight", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_weight_rejected(weight):
    with pytest.raises(ValueError):
        build_model_health_report("m", (HealthComponent("x", 1.0, HEALTHY, weight),))


@pytest.mark.parametrize("status", ["", "WARNING", "INVALID"])
def test_invalid_component_status_rejected(status):
    with pytest.raises(ValueError):
        build_model_health_report("m", (HealthComponent("x", 1.0, status),))


def test_duplicate_component_names_rejected():
    with pytest.raises(ValueError):
        build_model_health_report(
            "m",
            (
                HealthComponent("x", 1.0, HEALTHY),
                HealthComponent("x", 0.9, HEALTHY),
            ),
        )


@pytest.mark.parametrize(
    "healthy_min,degraded_min",
    [
        (0.0, 0.0),
        (1.1, 0.5),
        (float("nan"), 0.5),
        (0.8, 0.8),
        (0.8, 0.9),
        (0.8, -0.1),
    ],
)
def test_invalid_threshold_configuration_rejected(healthy_min, degraded_min):
    with pytest.raises(ValueError):
        build_model_health_report(
            "m",
            (HealthComponent("x", 0.8, HEALTHY),),
            healthy_min=healthy_min,
            degraded_min=degraded_min,
        )


def test_component_status_must_match_score():
    with pytest.raises(ValueError):
        build_model_health_report("m", (HealthComponent("x", 0.9, DEGRADED),))


def test_component_status_mismatch_detected_by_validation():
    value = report()
    item = value.components[0]
    changed = HealthComponent(item.name, item.score, DEGRADED, item.weight, item.source_identity)
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        (changed,) + value.components[1:],
        value.healthy_min,
        value.degraded_min,
        value.score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_passes():
    assert validate_model_health_report(report()).is_valid


def test_validation_invalid_type():
    assert validate_model_health_report(object()).issues == ("INVALID_REPORT_TYPE",)


def test_validation_bad_version():
    value = report()
    bad = ModelHealthReport(
        "bad",
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        value.score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_model_identity():
    value = report()
    bad = ModelHealthReport(
        value.version,
        "",
        value.components,
        value.healthy_min,
        value.degraded_min,
        value.score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_weighted_score():
    value = report()
    changed_score = value.score.__class__(
        0.1,
        value.score.status,
        value.score.component_count,
        value.score.active_critical_components,
        value.score.active_degraded_components,
    )
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        changed_score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_health_status():
    value = report()
    changed_score = value.score.__class__(
        value.score.weighted_score,
        CRITICAL,
        value.score.component_count,
        value.score.active_critical_components,
        value.score.active_degraded_components,
    )
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        changed_score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_component_count():
    value = report()
    changed_score = value.score.__class__(
        value.score.weighted_score,
        value.score.status,
        99,
        value.score.active_critical_components,
        value.score.active_degraded_components,
    )
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        changed_score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_critical_collection():
    value = report()
    changed_score = value.score.__class__(
        value.score.weighted_score,
        value.score.status,
        value.score.component_count,
        ("performance",),
        value.score.active_degraded_components,
    )
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        changed_score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_degraded_collection():
    value = report()
    changed_score = value.score.__class__(
        value.score.weighted_score,
        value.score.status,
        value.score.component_count,
        value.score.active_critical_components,
        ("performance",),
    )
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        changed_score,
        value.report_identity,
    )
    assert not validate_model_health_report(bad).is_valid


def test_validation_bad_identity():
    value = report()
    bad = ModelHealthReport(
        value.version,
        value.model_identity,
        value.components,
        value.healthy_min,
        value.degraded_min,
        value.score,
        "bad",
    )
    assert not validate_model_health_report(bad).is_valid


def test_critical_status_from_all_critical():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("a", 0.1, CRITICAL),
            HealthComponent("b", 0.2, CRITICAL),
        ),
    )
    assert result.score.status == CRITICAL
    assert result.score.active_critical_components == ("a", "b")


def test_mixed_critical_and_healthy():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("a", 0.0, CRITICAL),
            HealthComponent("b", 1.0, HEALTHY),
        ),
    )
    assert result.score.status == DEGRADED


def test_all_healthy():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("a", 0.9, HEALTHY),
            HealthComponent("b", 1.0, HEALTHY),
        ),
    )
    assert result.score.status == HEALTHY


def test_no_automatic_action_boundary():
    result = report()
    assert not hasattr(result, "retrain")
    assert not hasattr(result, "promote")
    assert not hasattr(result, "rollback")


def test_component_order_preserved():
    assert tuple(item.name for item in report().components) == ("performance", "drift", "concept")


def test_zero_score_is_valid():
    result = build_model_health_report("m", (HealthComponent("x", 0.0, CRITICAL),))
    assert result.score.weighted_score == 0.0


def test_one_score_is_valid():
    result = build_model_health_report("m", (HealthComponent("x", 1.0, HEALTHY),))
    assert result.score.weighted_score == 1.0


def test_weighted_score_stays_in_bounds():
    result = report()
    assert 0.0 <= result.score.weighted_score <= 1.0


def test_custom_healthy_boundary_inclusive():
    result = build_model_health_report(
        "m",
        (HealthComponent("x", 0.85, HEALTHY),),
        healthy_min=0.85,
        degraded_min=0.50,
    )
    assert result.score.status == HEALTHY


def test_custom_degraded_boundary_inclusive():
    result = build_model_health_report(
        "m",
        (HealthComponent("x", 0.55, DEGRADED),),
        healthy_min=0.85,
        degraded_min=0.55,
    )
    assert result.score.status == DEGRADED


def test_source_identity_can_be_empty():
    result = build_model_health_report("m", (HealthComponent("x", 1.0, HEALTHY),))
    assert result.components[0].source_identity == ""


def test_report_is_frozen():
    assert report().__dataclass_params__.frozen


def test_health_score_is_frozen():
    assert report().score.__dataclass_params__.frozen


def test_summary_identity():
    assert model_health_summary(report())["report_identity"] == report().report_identity


def test_component_accessor_returns_exact_object():
    result = report()
    assert model_health_component(result, "performance") is result.components[0]


def test_identity_includes_model_identity():
    assert report().report_identity != build_model_health_report("other", components()).report_identity


def test_identity_includes_weights():
    changed = (
        HealthComponent("performance", 0.90, HEALTHY, 1.0, "perf-47"),
        HealthComponent("drift", 0.70, DEGRADED, 1.0, "drift-49"),
        HealthComponent("concept", 0.95, HEALTHY, 1.0, "concept-55"),
    )
    assert report().report_identity != build_model_health_report("model-v57", changed).report_identity


def test_identity_includes_source_lineage():
    changed = (
        HealthComponent("performance", 0.90, HEALTHY, 2.0, "other"),
        HealthComponent("drift", 0.70, DEGRADED, 1.0, "drift-49"),
        HealthComponent("concept", 0.95, HEALTHY, 1.0, "concept-55"),
    )
    assert report().report_identity != build_model_health_report("model-v57", changed).report_identity


def test_multiple_critical_and_degraded_components():
    result = build_model_health_report(
        "m",
        (
            HealthComponent("a", 0.2, CRITICAL),
            HealthComponent("b", 0.4, CRITICAL),
            HealthComponent("c", 0.6, DEGRADED),
            HealthComponent("d", 0.7, DEGRADED),
        ),
    )
    assert result.score.active_critical_components == ("a", "b")
    assert result.score.active_degraded_components == ("c", "d")


def test_report_validation_status_is_string():
    assert validate_model_health_report(report()).status == VALID


def test_summary_contains_thresholds_indirectly_via_report():
    result = report()
    assert result.healthy_min == 0.80
    assert result.degraded_min == 0.50
