from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from analytics.model_rollout import (
    ModelRolloutPlan, READY, AUTHORIZED, validate_model_rollout_plan,
)
from analytics.model_version_lifecycle import (
    ModelVersion, CANDIDATE, ACTIVE, transition_model_version,
)
from analytics.activation_authorization_readiness import (
    AuthorizationRecord, validate_activation_plan_binding,
)

PRODUCTION_ACTIVATION_VERSION = "67.0.0"
VALID, INVALID = "VALID", "INVALID"
READY_TO_EXECUTE, BLOCKED = "READY_TO_EXECUTE", "BLOCKED"
PENDING, ACTIVATED, NOT_ACTIVATED = "PENDING", "ACTIVATED", "NOT_ACTIVATED"
EXECUTION_BOUNDARY = "EXECUTION_BOUNDARY"

@dataclass(frozen=True)
class ActivationPolicy:
    require_authorized_rollout: bool = True
    require_candidate_state: bool = True
    require_active_target: bool = True
    require_exact_plan_identity: bool = True
    require_transition_lineage: bool = True
    require_single_execution_identity: bool = True
@dataclass(frozen=True)
class ActivationCheck:
    check_id: str
    status: str
    detail: str

@dataclass(frozen=True)
class ProductionActivationPlan:
    activation_id: str
    rollout_id: str
    plan_identity: str
    model_identity: str
    model_version: str
    artifact_identity: str
    authorization_id: str
    current_state: str
    target_state: str
    policy: ActivationPolicy
    checks: tuple[ActivationCheck, ...]
    status: str
    activation_state: str
    plan_identity_hash: str
@dataclass(frozen=True)
class ProductionActivationReceipt:
    activation_id: str
    rollout_id: str
    plan_identity: str
    model_identity: str
    model_version: str
    artifact_identity: str
    authorization_id: str
    previous_state: str
    resulting_state: str
    transition_source_identity: str
    activation_status: str
    rollback_state: str
    receipt_identity: str

@dataclass(frozen=True)
class ProductionActivationResult:
    status: str
    issues: tuple[str, ...]
    receipt: ProductionActivationReceipt | None = None

    @property
    def is_valid(self) -> bool:
        return self.status == VALID
def _hash(payload) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return "production-activation-" + hashlib.sha256(raw).hexdigest()

def _check(check_id: str, ok: bool, detail: str) -> ActivationCheck:
    return ActivationCheck(check_id, "PASS" if ok else "FAIL", detail)

def validate_activation_policy(policy: ActivationPolicy) -> None:
    if not isinstance(policy, ActivationPolicy):
        raise TypeError("policy must be ActivationPolicy")
    values = (
        policy.require_authorized_rollout,
        policy.require_candidate_state,
        policy.require_active_target,
        policy.require_exact_plan_identity,
        policy.require_transition_lineage,
        policy.require_single_execution_identity,
    )
    if not all(isinstance(value, bool) for value in values):
        raise ValueError("activation policy fields must be boolean")
def build_production_activation_plan(
    activation_id: str,
    rollout_plan: ModelRolloutPlan,
    model_version: ModelVersion,
    *,
    policy: ActivationPolicy = ActivationPolicy(),
) -> ProductionActivationPlan:
    if not isinstance(activation_id, str) or not activation_id.strip():
        raise ValueError("activation_id must not be empty")
    if not isinstance(rollout_plan, ModelRolloutPlan):
        raise TypeError("rollout_plan must be ModelRolloutPlan")
    if not isinstance(model_version, ModelVersion):
        raise TypeError("model_version must be ModelVersion")
    validate_activation_policy(policy)
    rollout_validation = validate_model_rollout_plan(rollout_plan)
    if not rollout_validation.is_valid:
        raise ValueError(
            "invalid rollout plan: " + ", ".join(rollout_validation.issues)
        )

    checks = []
    checks.append(_check(
        "ROLLOUT_STATUS", rollout_plan.status == READY,
        "rollout plan is READY",
    ))
    checks.append(_check(
        "ROLLOUT_AUTHORIZATION",
        rollout_plan.activation_state == AUTHORIZED
        and bool(rollout_plan.authorization_id.strip()),
        "rollout plan has explicit authorization",
    ))
    checks.append(_check(
        "MODEL_IDENTITY",
        rollout_plan.model_identity == model_version.model_identity,
        "rollout and lifecycle model identities match",
    ))
    checks.append(_check(
        "MODEL_VERSION",
        rollout_plan.model_version == model_version.version
        and bool(model_version.version.strip()),
        "rollout and lifecycle model versions match",
    ))
    checks.append(_check(
        "ARTIFACT_IDENTITY",
        rollout_plan.artifact_identity == model_version.artifact_identity
        and bool(model_version.artifact_identity.strip()),
        "rollout and lifecycle artifact identities match",
    ))
    checks.append(_check(
        "CURRENT_STATE", model_version.state == CANDIDATE,
        "lifecycle model is currently CANDIDATE",
    ))
    checks.append(_check(
        "TARGET_STATE", rollout_plan.target_state == ACTIVE,
        "rollout target is ACTIVE",
    ))
    checks.append(_check(
        "PLAN_IDENTITY", bool(rollout_plan.plan_identity.strip()),
        "rollout plan identity is present",
    ))
    checks.append(_check(
        "TRANSITION_LINEAGE",
        bool(rollout_plan.source_selection_identity.strip()),
        "transition source lineage is present",
    ))
    if policy.require_exact_plan_identity:
        checks.append(_check(
            "EXECUTION_IDENTITY", bool(activation_id.strip()),
            "execution identity is present",
        ))

    failed = tuple(c.check_id for c in checks if c.status == "FAIL")
    status = BLOCKED if failed else READY_TO_EXECUTE
    state = PENDING
    identity = _hash((
        PRODUCTION_ACTIVATION_VERSION,
        activation_id,
        rollout_plan.rollout_id,
        rollout_plan.plan_identity,
        model_version.model_identity,
        model_version.version,
        model_version.artifact_identity,
        rollout_plan.authorization_id,
        model_version.state,
        rollout_plan.target_state,
        policy,
        tuple(checks),
        status,
        state,
    ))
    return ProductionActivationPlan(
        activation_id,
        rollout_plan.rollout_id,
        rollout_plan.plan_identity,
        model_version.model_identity,
        model_version.version,
        model_version.artifact_identity,
        rollout_plan.authorization_id,
        model_version.state,
        rollout_plan.target_state,
        policy,
        tuple(checks),
        status,
        state,
        identity,
    )

def execute_authorized_production_activation(
    activation_plan: ProductionActivationPlan,
    model_version: ModelVersion,
    authorization_record: AuthorizationRecord,
) -> ProductionActivationResult:
    if not isinstance(authorization_record, AuthorizationRecord):
        return ProductionActivationResult(INVALID, ("INVALID_AUTHORIZATION_RECORD_TYPE",))
    binding_status, binding_issues = validate_activation_plan_binding(
        authorization_record, activation_plan
    )
    if binding_status != VALID:
        return ProductionActivationResult(
            INVALID, tuple("AUTHORIZATION_" + issue for issue in binding_issues)
        )
    return execute_production_activation(activation_plan, model_version)


def execute_production_activation(
    activation_plan: ProductionActivationPlan,
    model_version: ModelVersion,
) -> ProductionActivationResult:
    validation = validate_production_activation_plan(activation_plan)
    if not validation.is_valid:
        return ProductionActivationResult(INVALID, validation.issues)
    if not isinstance(model_version, ModelVersion):
        return ProductionActivationResult(
            INVALID, ("INVALID_MODEL_VERSION_TYPE",)
        )
    if activation_plan.status != READY_TO_EXECUTE:
        return ProductionActivationResult(INVALID, ("ACTIVATION_PLAN_NOT_READY",))
    if activation_plan.current_state != CANDIDATE:
        return ProductionActivationResult(INVALID, ("CURRENT_MODEL_NOT_CANDIDATE",))
    if model_version.state != CANDIDATE:
        return ProductionActivationResult(
            INVALID, ("MODEL_STATE_CHANGED_SINCE_PREPARATION",)
        )
    if model_version.model_identity != activation_plan.model_identity:
        return ProductionActivationResult(
            INVALID, ("MODEL_IDENTITY_CHANGED_SINCE_PREPARATION",)
        )
    if model_version.version != activation_plan.model_version:
        return ProductionActivationResult(
            INVALID, ("MODEL_VERSION_CHANGED_SINCE_PREPARATION",)
        )
    if model_version.artifact_identity != activation_plan.artifact_identity:
        return ProductionActivationResult(
            INVALID, ("ARTIFACT_CHANGED_SINCE_PREPARATION",)
        )

    transition = transition_model_version(
        model_version,
        ACTIVE,
        "Phase 67 production activation executor",
        activation_plan.plan_identity,
    )
    receipt_payload = (
        PRODUCTION_ACTIVATION_VERSION,
        activation_plan.activation_id,
        activation_plan.rollout_id,
        activation_plan.plan_identity,
        activation_plan.model_identity,
        activation_plan.model_version,
        activation_plan.artifact_identity,
        activation_plan.authorization_id,
        CANDIDATE,
        ACTIVE,
        transition.source_identity,
        ACTIVATED,
        CANDIDATE,
    )
    receipt = ProductionActivationReceipt(
        activation_plan.activation_id,
        activation_plan.rollout_id,
        activation_plan.plan_identity,
        activation_plan.model_identity,
        activation_plan.model_version,
        activation_plan.artifact_identity,
        activation_plan.authorization_id,
        CANDIDATE,
        ACTIVE,
        transition.source_identity,
        ACTIVATED,
        CANDIDATE,
        _hash(receipt_payload),
    )
    return ProductionActivationResult(VALID, (), receipt)

def validate_production_activation_plan(
    plan: ProductionActivationPlan,
) -> ProductionActivationResult:
    if not isinstance(plan, ProductionActivationPlan):
        return ProductionActivationResult(INVALID, ("INVALID_PLAN_TYPE",))
    issues = []
    if plan.activation_id.strip() == "":
        issues.append("MISSING_ACTIVATION_ID")
    if plan.rollout_id.strip() == "":
        issues.append("MISSING_ROLLOUT_ID")
    if plan.plan_identity.strip() == "":
        issues.append("MISSING_ROLLOUT_PLAN_IDENTITY")
    if plan.model_identity.strip() == "":
        issues.append("MISSING_MODEL_IDENTITY")
    if plan.model_version.strip() == "":
        issues.append("MISSING_MODEL_VERSION")
    if plan.artifact_identity.strip() == "":
        issues.append("MISSING_ARTIFACT_IDENTITY")
    if plan.authorization_id.strip() == "":
        issues.append("MISSING_AUTHORIZATION_ID")
    if plan.current_state != CANDIDATE:
        issues.append("INVALID_CURRENT_STATE")
    if plan.target_state != ACTIVE:
        issues.append("INVALID_TARGET_STATE")
    if plan.status not in (READY_TO_EXECUTE, BLOCKED):
        issues.append("INVALID_ACTIVATION_STATUS")
    if plan.activation_state != PENDING:
        issues.append("INVALID_ACTIVATION_STATE")
    ids = tuple(check.check_id for check in plan.checks)
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_CHECK_IDS")
    expected_failed = tuple(
        check.check_id for check in plan.checks if check.status == "FAIL"
    )
    if plan.status == READY_TO_EXECUTE and expected_failed:
        issues.append("READY_WITH_FAILED_CHECKS")
    if plan.status == BLOCKED and not expected_failed:
        issues.append("BLOCKED_WITHOUT_FAILED_CHECKS")
    expected_identity = _hash((
        PRODUCTION_ACTIVATION_VERSION,
        plan.activation_id,
        plan.rollout_id,
        plan.plan_identity,
        plan.model_identity,
        plan.model_version,
        plan.artifact_identity,
        plan.authorization_id,
        plan.current_state,
        plan.target_state,
        plan.policy,
        plan.checks,
        plan.status,
        plan.activation_state,
    ))
    if plan.plan_identity_hash != expected_identity:
        issues.append("INVALID_PLAN_IDENTITY_HASH")
    return ProductionActivationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )

def activation_checks(plan: ProductionActivationPlan):
    return plan.checks
def activation_failed_checks(plan: ProductionActivationPlan):
    return tuple(check.check_id for check in plan.checks if check.status == "FAIL")

def activation_summary(plan: ProductionActivationPlan) -> dict:
    validation = validate_production_activation_plan(plan)
    return {
        "status": validation.status,
        "version": PRODUCTION_ACTIVATION_VERSION,
        "activation_id": plan.activation_id,
        "rollout_id": plan.rollout_id,
        "plan_identity": plan.plan_identity,
        "model_identity": plan.model_identity,
        "model_version": plan.model_version,
        "artifact_identity": plan.artifact_identity,
        "authorization_id": plan.authorization_id,
        "current_state": plan.current_state,
        "target_state": plan.target_state,
        "activation_status": plan.status,
        "activation_state": plan.activation_state,
        "failed_checks": activation_failed_checks(plan),
        "plan_identity_hash": plan.plan_identity_hash,
    }

def validate_activation_receipt(
    receipt: ProductionActivationReceipt,
) -> ProductionActivationResult:
    if not isinstance(receipt, ProductionActivationReceipt):
        return ProductionActivationResult(INVALID, ("INVALID_RECEIPT_TYPE",))
    issues = []
    if not receipt.activation_id.strip():
        issues.append("MISSING_ACTIVATION_ID")
    if not receipt.rollout_id.strip():
        issues.append("MISSING_ROLLOUT_ID")
    if not receipt.plan_identity.strip():
        issues.append("MISSING_PLAN_IDENTITY")
    if receipt.previous_state != CANDIDATE:
        issues.append("INVALID_PREVIOUS_STATE")
    if receipt.resulting_state != ACTIVE:
        issues.append("INVALID_RESULTING_STATE")
    if receipt.activation_status != ACTIVATED:
        issues.append("INVALID_ACTIVATION_STATUS")
    if receipt.rollback_state != CANDIDATE:
        issues.append("INVALID_ROLLBACK_STATE")
    if not receipt.transition_source_identity.strip():
        issues.append("MISSING_TRANSITION_SOURCE")
    expected_identity = _hash((
        PRODUCTION_ACTIVATION_VERSION,
        receipt.activation_id,
        receipt.rollout_id,
        receipt.plan_identity,
        receipt.model_identity,
        receipt.model_version,
        receipt.artifact_identity,
        receipt.authorization_id,
        receipt.previous_state,
        receipt.resulting_state,
        receipt.transition_source_identity,
        receipt.activation_status,
        receipt.rollback_state,
    ))
    if receipt.receipt_identity != expected_identity:
        issues.append("INVALID_RECEIPT_IDENTITY")
    return ProductionActivationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
        receipt if not issues else None,
    )

def activation_receipt_identity(receipt: ProductionActivationReceipt) -> str:
    validation = validate_activation_receipt(receipt)
    if not validation.is_valid:
        raise ValueError("invalid activation receipt")
    return receipt.receipt_identity

def rollback_activation_preview(receipt: ProductionActivationReceipt) -> dict:
    validation = validate_activation_receipt(receipt)
    if not validation.is_valid:
        raise ValueError("invalid activation receipt")
    return {
        "activation_id": receipt.activation_id,
        "model_identity": receipt.model_identity,
        "model_version": receipt.model_version,
        "from_state": receipt.resulting_state,
        "rollback_to": receipt.rollback_state,
        "rollback_executed": False,
        "boundary": EXECUTION_BOUNDARY,
    }
__all__ = [
    "PRODUCTION_ACTIVATION_VERSION", "VALID", "INVALID",
    "READY_TO_EXECUTE", "BLOCKED", "PENDING", "ACTIVATED",
    "NOT_ACTIVATED", "EXECUTION_BOUNDARY", "ActivationPolicy",
    "ActivationCheck", "ProductionActivationPlan",
    "ProductionActivationReceipt", "ProductionActivationResult",
    "validate_activation_policy", "build_production_activation_plan",
    "execute_authorized_production_activation", "execute_production_activation",
    "validate_production_activation_plan",
    "activation_checks", "activation_failed_checks", "activation_summary",
    "validate_activation_receipt", "activation_receipt_identity",
    "rollback_activation_preview",
]