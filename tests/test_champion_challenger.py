import math

import pytest

from analytics.champion_challenger import (
    ACTIVE,
    CHALLENGER,
    CHAMPION,
    CHAMPION_CHALLENGER_VERSION,
    INACTIVE,
    ModelRoleAssignment,
    ChampionChallengerReport,
    build_champion_challenger_report,
    champion_challenger_evidence,
    champion_challenger_models,
    champion_challenger_summary,
    validate_champion_challenger_report,
)
from analytics.model_comparison import ModelComparisonReport
from analytics.model_health import CRITICAL, DEGRADED, HEALTHY, HealthComponent, build_model_health_report
from analytics.model_comparison import build_model_comparison_report, build_model_health_snapshot


def health(model, score, source):
    status = HEALTHY if score >= 0.8 else DEGRADED if score >= 0.5 else CRITICAL
    return build_model_health_report(model, (HealthComponent("overall", score, status, 1.0, source),))


def comparison():
    snapshots = (
        build_model_health_snapshot("P1", health("model-a", 0.70, "a1")),
        build_model_health_snapshot("P1", health("model-b", 0.90, "b1")),
        build_model_health_snapshot("P1", health("model-c", 0.60, "c1")),
        build_model_health_snapshot("P2", health("model-a", 0.85, "a2")),
        build_model_health_snapshot("P2", health("model-b", 0.80, "b2")),
        build_model_health_snapshot("P2", health("model-c", 0.70, "c2")),
    )
    return build_model_comparison_report("cmp-58", "P1", "P2", snapshots)


def champion():
    return ModelRoleAssignment("model-a", CHAMPION, ACTIVE, "current production", "assignment-1")


def challengers():
    return (
        ModelRoleAssignment("model-b", CHALLENGER, ACTIVE, "candidate", "assignment-1"),
        ModelRoleAssignment("model-c", CHALLENGER, ACTIVE, "candidate", "assignment-1"),
    )


def report():
    return build_champion_challenger_report("framework-59", comparison(), champion(), challengers())


def test_version():
    assert report().version == CHAMPION_CHALLENGER_VERSION


def test_champion():
    assert report().champion.model_identity == "model-a"


def test_challengers():
    assert tuple(x.model_identity for x in report().challengers) == ("model-b", "model-c")


def test_evidence_count():
    assert len(report().evidence) == 2


def test_evidence_champion_identity():
    assert all(x.champion_identity == "model-a" for x in report().evidence)


def test_model_b_evidence():
    item = champion_challenger_evidence(report(), "model-b")[0]
    assert math.isclose(item.health_score, 0.80)
    assert math.isclose(item.champion_health_score, 0.85)
    assert math.isclose(item.absolute_change_vs_champion, -0.05)


def test_model_c_evidence():
    item = champion_challenger_evidence(report(), "model-c")[0]
    assert math.isclose(item.absolute_change_vs_champion, -0.15)


def test_relative_evidence():
    item = champion_challenger_evidence(report(), "model-b")[0]
    assert math.isclose(item.relative_change_vs_champion, -0.05 / 0.85)


def test_model_accessor():
    assert champion_challenger_models(report()) == ("model-a", "model-b", "model-c")


def test_evidence_accessor_all():
    assert len(champion_challenger_evidence(report())) == 2


def test_summary():
    summary = champion_challenger_summary(report())
    assert summary["status"] == "VALID"
    assert summary["champion"] == "model-a"
    assert summary["challengers"] == ("model-b", "model-c")


def test_periods():
    assert report().baseline_period == "P1"
    assert report().comparison_period == "P2"


def test_source_identity():
    assert report().comparison_source_identity == comparison().report_identity


def test_eligible_models():
    assert report().eligible_models == ("model-a", "model-b", "model-c")


def test_inactive_models():
    assert report().inactive_models == ()


def test_assignment_fields():
    assert champion().assignment_reason == "current production"
    assert champion().source_identity == "assignment-1"


def test_roles():
    assert champion().role == CHAMPION
    assert challengers()[0].role == CHALLENGER


def test_states():
    assert champion().state == ACTIVE
    assert challengers()[0].state == ACTIVE


def test_blank_framework_rejected():
    with pytest.raises(ValueError):
        build_champion_challenger_report("", comparison(), champion(), challengers())


def test_wrong_comparison_type_rejected():
    with pytest.raises(TypeError):
        build_champion_challenger_report("x", object(), champion(), challengers())


def test_invalid_comparison_rejected():
    value = comparison()
    bad = ModelComparisonReport(
        "bad", value.comparison_id, value.baseline_period, value.comparison_period,
        value.snapshots, value.metric_comparisons, value.improved_models,
        value.declined_models, value.unchanged_models, value.common_models,
        value.baseline_only_models, value.comparison_only_models, value.report_identity,
    )
    with pytest.raises(ValueError):
        build_champion_challenger_report("x", bad, champion(), challengers())


def test_champion_must_be_champion_role():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", CHALLENGER), challengers()
        )


def test_champion_must_be_active():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", CHAMPION, INACTIVE), challengers()
        )


def test_challenger_must_be_present():
    with pytest.raises(ValueError):
        build_champion_challenger_report("x", comparison(), champion(), ())


def test_challenger_role_required():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), champion(), (ModelRoleAssignment("model-b", CHAMPION),)
        )


def test_challenger_active_required():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), champion(), (ModelRoleAssignment("model-b", CHALLENGER, INACTIVE),)
        )


def test_unique_role_identities():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), champion(), (ModelRoleAssignment("model-a", CHALLENGER),)
        )


def test_champion_must_be_common():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("missing", CHAMPION), challengers()
        )


def test_challenger_must_be_common():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), champion(), challengers() + (ModelRoleAssignment("missing", CHALLENGER),)
        )


def test_blank_champion_identity():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("", CHAMPION), challengers()
        )


def test_blank_challenger_identity():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), champion(), challengers() + (ModelRoleAssignment("", CHALLENGER),)
        )


def test_invalid_role():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", "INVALID"), challengers()
        )


def test_invalid_state():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", CHAMPION, "INVALID"), challengers()
        )


def test_assignment_reason_type():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", CHAMPION, ACTIVE, None), challengers()
        )


def test_source_identity_type():
    with pytest.raises(ValueError):
        build_champion_challenger_report(
            "x", comparison(), ModelRoleAssignment("model-a", CHAMPION, ACTIVE, "", None), challengers()
        )


def test_zero_champion_relative_change():
    snapshots = (
        build_model_health_snapshot("P1", health("model-a", 0.0, "a1")),
        build_model_health_snapshot("P1", health("model-b", 0.5, "b1")),
        build_model_health_snapshot("P2", health("model-a", 0.0, "a2")),
        build_model_health_snapshot("P2", health("model-b", 0.5, "b2")),
    )
    cmp = build_model_comparison_report("z", "P1", "P2", snapshots)
    value = build_champion_challenger_report(
        "z", cmp, ModelRoleAssignment("model-a", CHAMPION), (ModelRoleAssignment("model-b", CHALLENGER),)
    )
    assert value.evidence[0].relative_change_vs_champion is None


def test_deterministic_identity():
    assert report().report_identity == report().report_identity


def test_identity_changes_with_framework():
    assert report().report_identity != build_champion_challenger_report(
        "other", comparison(), champion(), challengers()
    ).report_identity


def test_identity_changes_with_roles():
    changed = build_champion_challenger_report(
        "framework-59", comparison(), champion(),
        (ModelRoleAssignment("model-c", CHALLENGER, ACTIVE, "candidate", "assignment-1"),),
    )
    assert report().report_identity != changed.report_identity


def test_identity_prefix():
    assert report().report_identity.startswith("champion-challenger-report-")


def test_validation_passes():
    assert validate_champion_challenger_report(report()).is_valid


def test_validation_invalid_type():
    assert validate_champion_challenger_report(object()).issues == ("INVALID_REPORT_TYPE",)


def test_validation_bad_version():
    value = report()
    bad = ChampionChallengerReport(
        "bad", value.framework_id, value.comparison_source_identity, value.baseline_period,
        value.comparison_period, value.champion, value.challengers, value.evidence,
        value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_bad_framework():
    value = report()
    bad = ChampionChallengerReport(
        value.version, "", value.comparison_source_identity, value.baseline_period,
        value.comparison_period, value.champion, value.challengers, value.evidence,
        value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_bad_champion_role():
    value = report()
    bad_champion = ModelRoleAssignment("model-a", CHALLENGER)
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, bad_champion, value.challengers,
        value.evidence, value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_inactive_champion():
    value = report()
    bad_champion = ModelRoleAssignment("model-a", CHAMPION, INACTIVE)
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, bad_champion, value.challengers,
        value.evidence, value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_no_challengers():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, (),
        value.evidence, value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_duplicate_models():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion,
        (ModelRoleAssignment("model-a", CHALLENGER),), value.evidence,
        value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_evidence_champion():
    value = report()
    item = value.evidence[0]
    changed = item.__class__(
        item.model_identity, "other", item.health_score, item.champion_health_score,
        item.absolute_change_vs_champion, item.relative_change_vs_champion, item.comparison_source_identity,
    )
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        (changed,) + value.evidence[1:], value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_evidence_change():
    value = report()
    item = value.evidence[0]
    changed = item.__class__(
        item.model_identity, item.champion_identity, item.health_score, item.champion_health_score,
        99.0, item.relative_change_vs_champion, item.comparison_source_identity,
    )
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        (changed,) + value.evidence[1:], value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_evidence_relative():
    value = report()
    item = value.evidence[0]
    changed = item.__class__(
        item.model_identity, item.champion_identity, item.health_score, item.champion_health_score,
        item.absolute_change_vs_champion, 99.0, item.comparison_source_identity,
    )
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        (changed,) + value.evidence[1:], value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_evidence_source():
    value = report()
    item = value.evidence[0]
    changed = item.__class__(
        item.model_identity, item.champion_identity, item.health_score, item.champion_health_score,
        item.absolute_change_vs_champion, item.relative_change_vs_champion, "",
    )
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        (changed,) + value.evidence[1:], value.eligible_models, value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_eligible_models():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        value.evidence, ("model-a",), value.inactive_models, value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_inactive_overlap():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        value.evidence, value.eligible_models, ("model-a",), value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_duplicate_inactive():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        value.evidence, value.eligible_models, ("x", "x"), value.report_identity,
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_validation_identity_prefix():
    value = report()
    bad = ChampionChallengerReport(
        value.version, value.framework_id, value.comparison_source_identity,
        value.baseline_period, value.comparison_period, value.champion, value.challengers,
        value.evidence, value.eligible_models, value.inactive_models, "bad",
    )
    assert not validate_champion_challenger_report(bad).is_valid


def test_frozen_report():
    assert report().__dataclass_params__.frozen


def test_frozen_assignment():
    assert champion().__dataclass_params__.frozen


def test_frozen_evidence():
    assert report().evidence[0].__dataclass_params__.frozen


def test_no_promotion():
    value = report()
    assert not hasattr(value, "promote")
    assert not hasattr(value, "execute_promotion")
    assert not hasattr(value, "rollback")


def test_no_selection_score():
    value = report()
    assert not hasattr(value, "winner")
    assert not hasattr(value, "selection_score")


def test_assignment_reason_optional():
    value = build_champion_challenger_report(
        "x", comparison(), ModelRoleAssignment("model-a", CHAMPION),
        (ModelRoleAssignment("model-b", CHALLENGER),),
    )
    assert value.champion.assignment_reason == ""


def test_source_optional():
    value = build_champion_challenger_report(
        "x", comparison(), ModelRoleAssignment("model-a", CHAMPION),
        (ModelRoleAssignment("model-b", CHALLENGER),),
    )
    assert value.champion.source_identity == ""


def test_summary_identity():
    assert champion_challenger_summary(report())["report_identity"] == report().report_identity


def test_unknown_evidence_model():
    assert champion_challenger_evidence(report(), "missing") == ()


def test_all_challengers_have_evidence():
    assert {x.model_identity for x in report().evidence} == {x.model_identity for x in report().challengers}


def test_evidence_source_matches():
    assert all(x.comparison_source_identity == report().comparison_source_identity for x in report().evidence)


def test_champion_not_in_challengers():
    assert report().champion.model_identity not in {x.model_identity for x in report().challengers}


def test_common_period_lineage():
    assert report().baseline_period == comparison().baseline_period
    assert report().comparison_period == comparison().comparison_period


def test_critical_health_supported():
    snapshots = (
        build_model_health_snapshot("P1", health("a", 0.2, "a1")),
        build_model_health_snapshot("P1", health("b", 0.3, "b1")),
        build_model_health_snapshot("P2", health("a", 0.2, "a2")),
        build_model_health_snapshot("P2", health("b", 0.3, "b2")),
    )
    cmp = build_model_comparison_report("x", "P1", "P2", snapshots)
    value = build_champion_challenger_report(
        "x", cmp, ModelRoleAssignment("a", CHAMPION),
        (ModelRoleAssignment("b", CHALLENGER),),
    )
    assert value.evidence[0].health_score == 0.3
