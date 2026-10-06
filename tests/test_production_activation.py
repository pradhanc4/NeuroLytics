from datetime import date, timedelta
import pytest

from features.feature_artifact import FeatureArtifact
from features.feature_versioning import FeatureVersionIdentity
from analytics.retraining_decision import RetrainingEvidence, build_retraining_decision_report
from analytics.retraining_dataset import build_retraining_dataset_report
from analytics.automated_retraining import build_automated_retraining_report
from analytics.post_retraining_validation import build_post_retraining_validation_report
from analytics.model_version_lifecycle import build_model_version, CANDIDATE, ACTIVE
from analytics.model_rollout import build_model_rollout_plan, authorize_model_rollout
from analytics.activation_authorization_readiness import build_authorization_record
from analytics.production_activation import *

def dataset():
    identity = FeatureVersionIdentity("67-test", "x", "sha256", "x")
    artifacts = tuple(
        FeatureArtifact(
            date(2026, 1, 1) + timedelta(days=i), "67-test",
            ("f1", "f2"), {"f1": float(i), "f2": float(i % 3)},
            (), identity, "VALID", "CLEAN",
        ) for i in range(12)
    )
    decision = build_retraining_decision_report(
        "d67", "model67", "2026-09-30",
        (RetrainingEvidence(
            "performance_degradation", "miss_rate", .1, .3, .1,
            True, 1, "p", "p", "",
        ),),
    )
    return build_retraining_dataset_report(
        "ds67", decision, artifacts,
        {a.target_date: i % 2 for i, a in enumerate(artifacts)}, "data67",
    )

def validation_report():
    d = dataset()
    return build_post_retraining_validation_report(
        "v67", build_automated_retraining_report("r67", d), d,
    )

def lifecycle_model():
    r = validation_report()
    return build_model_version(
        r.model_identity, "64.0.0", CANDIDATE,
        "selection-67", r.artifact_identity,
    )

def rollout_plan():
    r, m = validation_report(), lifecycle_model()
    p = build_model_rollout_plan(
        "roll67", m, r, source_selection_identity="selection-67",
        authorization_id="auth67",
    )
    return authorize_model_rollout(p, "auth67")

def activation_plan(**kwargs):
    return build_production_activation_plan(
        "activation67", rollout_plan(), lifecycle_model(), **kwargs
    )
def test_01_version():
    assert PRODUCTION_ACTIVATION_VERSION == "67.0.0"

def test_02_policy_valid():
    validate_activation_policy(ActivationPolicy())

def test_03_plan_ready():
    assert activation_plan().status == READY_TO_EXECUTE

def test_04_plan_pending():
    assert activation_plan().activation_state == PENDING

def test_05_plan_valid():
    assert validate_production_activation_plan(activation_plan()).is_valid

def test_06_summary():
    assert activation_summary(activation_plan())["status"] == VALID

def test_07_checks_present():
    assert len(activation_checks(activation_plan())) >= 8

def test_08_failed_checks_empty():
    assert activation_failed_checks(activation_plan()) == ()

def test_09_execute():
    result = execute_production_activation(activation_plan(), lifecycle_model())
    assert result.status == VALID
    assert result.receipt.resulting_state == ACTIVE

def test_10_receipt_valid():
    result = execute_production_activation(activation_plan(), lifecycle_model())
    assert validate_activation_receipt(result.receipt).is_valid

def test_11_deterministic_receipt():
    a = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    b = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert a.receipt_identity == b.receipt_identity

def test_12_no_input_mutation():
    model = lifecycle_model()
    execute_production_activation(activation_plan(), model)
    assert model.state == CANDIDATE

def test_13_transition_lineage():
    result = execute_production_activation(activation_plan(), lifecycle_model())
    assert result.receipt.transition_source_identity.startswith("model-rollout-plan-")

def test_14_rollback_preview():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    preview = rollback_activation_preview(receipt)
    assert preview["rollback_to"] == CANDIDATE
    assert preview["rollback_executed"] is False

def test_15_invalid_policy_type():
    with pytest.raises(TypeError):
        validate_activation_policy(object())

def test_16_invalid_policy_boolean():
    with pytest.raises(ValueError):
        validate_activation_policy(ActivationPolicy(require_candidate_state="x"))

def test_17_empty_activation_id():
    with pytest.raises(ValueError):
        build_production_activation_plan("", rollout_plan(), lifecycle_model())

def test_18_invalid_rollout_type():
    with pytest.raises(TypeError):
        build_production_activation_plan("x", object(), lifecycle_model())

def test_19_invalid_model_type():
    with pytest.raises(TypeError):
        build_production_activation_plan("x", rollout_plan(), object())
def test_20_invalid_plan_validation():
    plan = activation_plan()
    bad = type(plan)(
        plan.activation_id, plan.rollout_id, plan.plan_identity,
        plan.model_identity, plan.model_version, plan.artifact_identity,
        plan.authorization_id, "BAD", plan.target_state, plan.policy,
        plan.checks, plan.status, plan.activation_state, plan.plan_identity_hash,
    )
    assert not validate_production_activation_plan(bad).is_valid

def test_21_blocked_without_authorization():
    report, model = validation_report(), lifecycle_model()
    blocked_rollout = build_model_rollout_plan(
        "roll67-blocked", model, report,
        source_selection_identity="selection-67", authorization_id="",
    )
    plan = build_production_activation_plan("blocked", blocked_rollout, model)
    assert plan.status == BLOCKED

def test_22_execute_blocked_returns_invalid():
    report, model = validation_report(), lifecycle_model()
    blocked_rollout = build_model_rollout_plan(
        "roll67-blocked2", model, report,
        source_selection_identity="selection-67", authorization_id="",
    )
    plan = build_production_activation_plan("blocked2", blocked_rollout, model)
    assert execute_production_activation(plan, model).status == INVALID

def test_23_changed_state_rejected():
    model, plan = lifecycle_model(), activation_plan()
    changed = build_model_version(
        model.model_identity, model.version, ACTIVE,
        model.source_selection_identity, model.artifact_identity,
    )
    assert execute_production_activation(plan, changed).status == INVALID

def test_24_identity_mismatch_rejected():
    model, plan = lifecycle_model(), activation_plan()
    changed = build_model_version(
        "different-model", model.version, CANDIDATE,
        model.source_selection_identity, model.artifact_identity,
    )
    assert execute_production_activation(plan, changed).status == INVALID

def test_25_artifact_mismatch_rejected():
    model, plan = lifecycle_model(), activation_plan()
    changed = build_model_version(
        model.model_identity, model.version, CANDIDATE,
        model.source_selection_identity, "different-artifact",
    )
    assert execute_production_activation(plan, changed).status == INVALID

def test_26_receipt_identity_prefix():
    receipt = execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt
    assert receipt.receipt_identity.startswith("production-activation-")

def test_27_receipt_accessor():
    receipt = execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt
    assert activation_receipt_identity(receipt) == receipt.receipt_identity

def test_28_invalid_receipt_type():
    with pytest.raises(ValueError):
        activation_receipt_identity(object())

def test_29_invalid_receipt_state():
    receipt = execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt
    bad = type(receipt)(
        receipt.activation_id, receipt.rollout_id, receipt.plan_identity,
        receipt.model_identity, receipt.model_version, receipt.artifact_identity,
        receipt.authorization_id, ACTIVE, ACTIVE,
        receipt.transition_source_identity, receipt.activation_status,
        receipt.rollback_state, receipt.receipt_identity,
    )
    assert not validate_activation_receipt(bad).is_valid
def test_30_receipt_identity_detects_tampering():
    receipt = execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt
    tampered = type(receipt)(
        receipt.activation_id, receipt.rollout_id, receipt.plan_identity,
        receipt.model_identity, receipt.model_version, "tampered-artifact",
        receipt.authorization_id, receipt.previous_state, receipt.resulting_state,
        receipt.transition_source_identity, receipt.activation_status,
        receipt.rollback_state, receipt.receipt_identity,
    )
    assert not validate_activation_receipt(tampered).is_valid

def test_30_invalid_receipt_identity():
    receipt = execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt
    bad = type(receipt)(
        receipt.activation_id, receipt.rollout_id, receipt.plan_identity,
        receipt.model_identity, receipt.model_version, receipt.artifact_identity,
        receipt.authorization_id, receipt.previous_state, receipt.resulting_state,
        receipt.transition_source_identity, receipt.activation_status,
        receipt.rollback_state, "bad",
    )
    assert not validate_activation_receipt(bad).is_valid

def test_31_invalid_rollback_preview():
    with pytest.raises(ValueError):
        rollback_activation_preview(object())

def test_32_execution_plan_identity_stable():
    assert activation_plan().plan_identity_hash == activation_plan().plan_identity_hash

def test_32_plan_identity_hash_detects_tampering():
    plan = activation_plan()
    tampered = type(plan)(
        plan.activation_id, plan.rollout_id, plan.plan_identity,
        plan.model_identity, plan.model_version, "tampered-artifact",
        plan.authorization_id, plan.current_state, plan.target_state,
        plan.policy, plan.checks, plan.status, plan.activation_state,
        plan.plan_identity_hash,
    )
    result = validate_production_activation_plan(tampered)
    assert result.status == INVALID
    assert "INVALID_PLAN_IDENTITY_HASH" in result.issues

def test_33_model_identity_bound():
    assert activation_plan().model_identity == lifecycle_model().model_identity

def test_34_model_version_bound():
    assert activation_plan().model_version == lifecycle_model().version

def test_35_artifact_bound():
    assert activation_plan().artifact_identity == lifecycle_model().artifact_identity

def test_36_authorization_bound():
    assert activation_plan().authorization_id == "auth67"

def test_37_rollout_bound():
    assert activation_plan().rollout_id == "roll67"

def test_38_target_active():
    assert activation_plan().target_state == ACTIVE

def test_39_current_candidate():
    assert activation_plan().current_state == CANDIDATE

def test_40_activation_id():
    assert activation_plan().activation_id == "activation67"
def test_41_plan_hash_prefix():
    assert activation_plan().plan_identity_hash.startswith("production-activation-")

def test_42_receipt_previous_candidate():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.previous_state == CANDIDATE

def test_43_receipt_active():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.resulting_state == ACTIVE

def test_44_receipt_activated():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.activation_status == ACTIVATED

def test_45_receipt_rollback_candidate():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.rollback_state == CANDIDATE

def test_46_receipt_source():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.transition_source_identity == activation_plan().plan_identity

def test_47_summary_version():
    assert activation_summary(activation_plan())["version"] == "67.0.0"

def test_48_summary_rollout():
    assert activation_summary(activation_plan())["rollout_id"] == "roll67"

def test_49_summary_model():
    assert activation_summary(activation_plan())["model_identity"] == lifecycle_model().model_identity

def test_50_summary_state():
    assert activation_summary(activation_plan())["activation_state"] == PENDING

def test_51_summary_failures():
    assert activation_summary(activation_plan())["failed_checks"] == ()

def test_52_checks_all_pass():
    assert all(c.status == "PASS" for c in activation_checks(activation_plan()))

def test_53_receipt_validation_status():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert validate_activation_receipt(receipt).status == VALID

def test_54_receipt_accessor_repeatable():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert activation_receipt_identity(receipt) == activation_receipt_identity(receipt)

def test_55_rollback_boundary():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert rollback_activation_preview(receipt)["boundary"] == EXECUTION_BOUNDARY

def test_56_no_rollback_execution():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert rollback_activation_preview(receipt)["rollback_executed"] is False
def test_57_result_has_receipt():
    assert execute_production_activation(
        activation_plan(), lifecycle_model()
    ).receipt is not None

def test_58_result_valid():
    assert execute_production_activation(
        activation_plan(), lifecycle_model()
    ).is_valid

def test_59_result_issues_empty():
    assert execute_production_activation(
        activation_plan(), lifecycle_model()
    ).issues == ()

def test_60_plan_status_constant():
    assert activation_plan().status == READY_TO_EXECUTE

def test_61_plan_state_constant():
    assert activation_plan().activation_state == PENDING

def test_62_policy_defaults():
    p = ActivationPolicy()
    assert p.require_authorized_rollout is True
    assert p.require_candidate_state is True
    assert p.require_active_target is True

def test_63_policy_identity():
    assert activation_plan().policy == ActivationPolicy()

def test_64_receipt_rollout_identity():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.rollout_id == "roll67"

def test_65_receipt_model_version():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.model_version == lifecycle_model().version

def test_66_receipt_artifact_identity():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.artifact_identity == lifecycle_model().artifact_identity

def test_67_receipt_authorization():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.authorization_id == "auth67"

def test_68_receipt_plan_identity():
    receipt = execute_production_activation(activation_plan(), lifecycle_model()).receipt
    assert receipt.plan_identity == activation_plan().plan_identity

def test_69_invalid_receipt_identity_accessor():
    with pytest.raises(ValueError):
        activation_receipt_identity(object())

def test_70_invalid_plan_type():
    assert not validate_production_activation_plan(object()).is_valid

def test_71_authorized_execution_requires_record():
    plan = activation_plan()
    result = execute_authorized_production_activation(plan, lifecycle_model(), object())
    assert result.status == INVALID
    assert "INVALID_AUTHORIZATION_RECORD_TYPE" in result.issues

def test_72_pending_record_blocks_execution():
    plan = activation_plan()
    record = build_authorization_record(
        "auth67", "eng", "release", "production",
        plan.model_identity, plan.model_version,
        plan.artifact_identity, plan.rollout_id,
    )
    result = execute_authorized_production_activation(plan, lifecycle_model(), record)
    assert result.status == INVALID
    assert "AUTHORIZATION_EXPLICIT_AUTHORIZATION_PENDING" in result.issues

def test_73_authorized_record_binds_execution():
    plan = activation_plan()
    record = build_authorization_record(
        "auth67", "eng", "release", "production",
        plan.model_identity, plan.model_version,
        plan.artifact_identity, plan.rollout_id,
    )
    record = type(record)(
        record.authorization_id, record.authorized_by, record.purpose,
        record.scope, record.artifact_identity, record.model_identity,
        record.model_version, record.rollout_id, "AUTHORIZED",
        record.record_identity,
    )
    result = execute_authorized_production_activation(plan, lifecycle_model(), record)
    assert result.status == VALID
    assert result.receipt is not None

def test_74_authorized_record_mismatch_blocks_execution():
    plan = activation_plan()
    record = build_authorization_record(
        "wrong-auth", "eng", "release", "production",
        plan.model_identity, plan.model_version,
        plan.artifact_identity, plan.rollout_id,
    )
    record = type(record)(
        record.authorization_id, record.authorized_by, record.purpose,
        record.scope, record.artifact_identity, record.model_identity,
        record.model_version, record.rollout_id, "AUTHORIZED",
        record.record_identity,
    )
    result = execute_authorized_production_activation(plan, lifecycle_model(), record)
    assert result.status == INVALID
    assert any(issue.startswith("AUTHORIZATION_") for issue in result.issues)
