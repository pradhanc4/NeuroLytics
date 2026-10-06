from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from analytics.production_activation import (
    ProductionActivationReceipt, ACTIVATED, validate_activation_receipt,
)

PRODUCTION_SERVING_VERSION = "68.0.0"
VALID, INVALID = "VALID", "INVALID"
READY, BLOCKED = "READY", "BLOCKED"
INFERENCE_ACCEPTED, INFERENCE_REJECTED = "INFERENCE_ACCEPTED", "INFERENCE_REJECTED"
SERVING_BOUNDARY = "SERVING_BOUNDARY"

@dataclass(frozen=True)
class ServingPolicy:
    require_activated_receipt: bool = True
    require_feature_mapping: bool = True
    require_finite_numeric_features: bool = True
    require_deterministic_request: bool = True
    require_model_identity_binding: bool = True
    require_artifact_identity_binding: bool = True

@dataclass(frozen=True)
class ServingCheck:
    check_id: str
    status: str
    detail: str

@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    model_identity: str
    model_version: str
    artifact_identity: str
    features: tuple[tuple[str, float], ...]
    request_hash: str

@dataclass(frozen=True)
class ServingPlan:
    serving_id: str
    activation_id: str
    model_identity: str
    model_version: str
    artifact_identity: str
    policy: ServingPolicy
    checks: tuple[ServingCheck, ...]
    status: str
    serving_state: str
    plan_identity: str

@dataclass(frozen=True)
class InferenceResponse:
    request_id: str
    serving_id: str
    model_identity: str
    model_version: str
    artifact_identity: str
    prediction: Any
    request_hash: str
    response_identity: str
    status: str
    deterministic: bool = True

@dataclass(frozen=True)
class ServingResult:
    status: str
    issues: tuple[str, ...]
    response: InferenceResponse | None = None
    @property
    def is_valid(self) -> bool:
        return self.status == VALID
def _hash(payload: Any) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return "production-serving-" + hashlib.sha256(raw).hexdigest()

def _check(check_id: str, ok: bool, detail: str) -> ServingCheck:
    return ServingCheck(check_id, "PASS" if ok else "FAIL", detail)

def validate_serving_policy(policy: ServingPolicy) -> None:
    if not isinstance(policy, ServingPolicy):
        raise TypeError("policy must be ServingPolicy")
    values = (
        policy.require_activated_receipt,
        policy.require_feature_mapping,
        policy.require_finite_numeric_features,
        policy.require_deterministic_request,
        policy.require_model_identity_binding,
        policy.require_artifact_identity_binding,
    )
    if not all(isinstance(v, bool) for v in values):
        raise ValueError("serving policy fields must be boolean")

def validate_feature_mapping(features: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    if not isinstance(features, Mapping):
        raise TypeError("features must be a mapping")
    if not features:
        raise ValueError("features must not be empty")
    normalized = []
    for name, value in features.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("feature names must not be empty")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("feature values must be numeric")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError("feature values must be finite")
        normalized.append((name, number))
    return tuple(sorted(normalized))

def build_inference_request(
    request_id: str,
    model_identity: str,
    model_version: str,
    artifact_identity: str,
    features: Mapping[str, Any],
) -> InferenceRequest:
    values = (request_id, model_identity, model_version, artifact_identity)
    if not all(isinstance(v, str) and v.strip() for v in values):
        raise ValueError("request and model identities must not be empty")
    normalized = validate_feature_mapping(features)
    request_hash = _hash((request_id, model_identity, model_version, artifact_identity, normalized))
    return InferenceRequest(
        request_id, model_identity, model_version, artifact_identity,
        normalized, request_hash,
    )
def build_serving_plan(
    serving_id: str,
    activation_receipt: ProductionActivationReceipt,
    *,
    policy: ServingPolicy = ServingPolicy(),
) -> ServingPlan:
    if not isinstance(serving_id, str) or not serving_id.strip():
        raise ValueError("serving_id must not be empty")
    if not isinstance(activation_receipt, ProductionActivationReceipt):
        raise TypeError("activation_receipt must be ProductionActivationReceipt")
    validate_serving_policy(policy)

    receipt_validation = validate_activation_receipt(activation_receipt)
    if not receipt_validation.is_valid:
        raise ValueError("invalid activation receipt: " + ", ".join(receipt_validation.issues))

    checks = [
        _check(
            "ACTIVATION_STATUS",
            activation_receipt.activation_status == ACTIVATED,
            "activation receipt is ACTIVATED",
        ),
        _check(
            "MODEL_IDENTITY",
            bool(activation_receipt.model_identity.strip()),
            "activated model identity is present",
        ),
        _check(
            "MODEL_VERSION",
            bool(activation_receipt.model_version.strip()),
            "activated model version is present",
        ),
        _check(
            "ARTIFACT_IDENTITY",
            bool(activation_receipt.artifact_identity.strip()),
            "activated artifact identity is present",
        ),
        _check(
            "AUTHORIZATION_IDENTITY",
            bool(activation_receipt.authorization_id.strip()),
            "activation authorization is present",
        ),
        _check(
            "TRANSITION_LINEAGE",
            bool(activation_receipt.transition_source_identity.strip()),
            "activation transition lineage is present",
        ),
    ]
    failed = tuple(c.check_id for c in checks if c.status == "FAIL")
    status = BLOCKED if failed else READY
    plan_identity = _hash((
        PRODUCTION_SERVING_VERSION,
        serving_id,
        activation_receipt.activation_id,
        activation_receipt.model_identity,
        activation_receipt.model_version,
        activation_receipt.artifact_identity,
        policy,
        tuple(checks),
        status,
        READY if not failed else BLOCKED,
    ))
    return ServingPlan(
        serving_id,
        activation_receipt.activation_id,
        activation_receipt.model_identity,
        activation_receipt.model_version,
        activation_receipt.artifact_identity,
        policy,
        tuple(checks),
        status,
        READY if not failed else BLOCKED,
        plan_identity,
    )
def validate_serving_plan(plan: ServingPlan) -> ServingResult:
    if not isinstance(plan, ServingPlan):
        return ServingResult(INVALID, ("INVALID_PLAN_TYPE",))
    issues = []
    if not plan.serving_id.strip():
        issues.append("MISSING_SERVING_ID")
    if not plan.activation_id.strip():
        issues.append("MISSING_ACTIVATION_ID")
    if not plan.model_identity.strip():
        issues.append("MISSING_MODEL_IDENTITY")
    if not plan.model_version.strip():
        issues.append("MISSING_MODEL_VERSION")
    if not plan.artifact_identity.strip():
        issues.append("MISSING_ARTIFACT_IDENTITY")
    if plan.status not in (READY, BLOCKED):
        issues.append("INVALID_SERVING_STATUS")
    if plan.serving_state not in (READY, BLOCKED):
        issues.append("INVALID_SERVING_STATE")
    ids = tuple(c.check_id for c in plan.checks)
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_CHECK_IDS")
    failed = tuple(c.check_id for c in plan.checks if c.status == "FAIL")
    if plan.status == READY and failed:
        issues.append("READY_WITH_FAILED_CHECKS")
    if plan.status == BLOCKED and not failed:
        issues.append("BLOCKED_WITHOUT_FAILED_CHECKS")
    expected_identity = _hash((
        PRODUCTION_SERVING_VERSION,
        plan.serving_id,
        plan.activation_id,
        plan.model_identity,
        plan.model_version,
        plan.artifact_identity,
        plan.policy,
        plan.checks,
        plan.status,
        plan.serving_state,
    ))
    if plan.plan_identity != expected_identity:
        issues.append("INVALID_PLAN_IDENTITY")
    return ServingResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )

def serving_checks(plan: ServingPlan) -> tuple[ServingCheck, ...]:
    return plan.checks

def serving_failed_checks(plan: ServingPlan) -> tuple[str, ...]:
    return tuple(c.check_id for c in plan.checks if c.status == "FAIL")
def serve_inference(
    serving_plan: ServingPlan,
    request: InferenceRequest,
    predictor: Callable[[Mapping[str, float]], Any],
) -> ServingResult:
    plan_validation = validate_serving_plan(serving_plan)
    if not plan_validation.is_valid:
        return ServingResult(INVALID, plan_validation.issues)
    if serving_plan.status != READY:
        return ServingResult(INVALID, ("SERVING_PLAN_NOT_READY",))
    if not isinstance(request, InferenceRequest):
        return ServingResult(INVALID, ("INVALID_REQUEST_TYPE",))
    if not callable(predictor):
        return ServingResult(INVALID, ("INVALID_PREDICTOR",))
    if request.model_identity != serving_plan.model_identity:
        return ServingResult(INVALID, ("MODEL_IDENTITY_MISMATCH",))
    if request.model_version != serving_plan.model_version:
        return ServingResult(INVALID, ("MODEL_VERSION_MISMATCH",))
    if request.artifact_identity != serving_plan.artifact_identity:
        return ServingResult(INVALID, ("ARTIFACT_IDENTITY_MISMATCH",))
    expected_hash = _hash((
        request.request_id, request.model_identity, request.model_version,
        request.artifact_identity, request.features,
    ))
    if request.request_hash != expected_hash:
        return ServingResult(INVALID, ("REQUEST_HASH_MISMATCH",))

    feature_mapping = dict(request.features)
    try:
        prediction = predictor(feature_mapping)
    except Exception as exc:
        return ServingResult(INVALID, ("PREDICTOR_ERROR:" + type(exc).__name__,))

    response_identity = _hash((
        PRODUCTION_SERVING_VERSION,
        request.request_id,
        serving_plan.serving_id,
        serving_plan.model_identity,
        serving_plan.model_version,
        serving_plan.artifact_identity,
        prediction,
        request.request_hash,
        INFERENCE_ACCEPTED,
    ))
    response = InferenceResponse(
        request.request_id,
        serving_plan.serving_id,
        serving_plan.model_identity,
        serving_plan.model_version,
        serving_plan.artifact_identity,
        prediction,
        request.request_hash,
        response_identity,
        INFERENCE_ACCEPTED,
        True,
    )
    return ServingResult(VALID, (), response)

def serving_summary(plan: ServingPlan) -> dict:
    validation = validate_serving_plan(plan)
    return {
        "status": validation.status,
        "version": PRODUCTION_SERVING_VERSION,
        "serving_id": plan.serving_id,
        "activation_id": plan.activation_id,
        "model_identity": plan.model_identity,
        "model_version": plan.model_version,
        "artifact_identity": plan.artifact_identity,
        "serving_status": plan.status,
        "serving_state": plan.serving_state,
        "failed_checks": serving_failed_checks(plan),
        "plan_identity": plan.plan_identity,
    }
def validate_inference_response(
    response: InferenceResponse,
) -> ServingResult:
    if not isinstance(response, InferenceResponse):
        return ServingResult(INVALID, ("INVALID_RESPONSE_TYPE",))
    issues = []
    if not response.request_id.strip():
        issues.append("MISSING_REQUEST_ID")
    if not response.serving_id.strip():
        issues.append("MISSING_SERVING_ID")
    if not response.model_identity.strip():
        issues.append("MISSING_MODEL_IDENTITY")
    if not response.model_version.strip():
        issues.append("MISSING_MODEL_VERSION")
    if not response.artifact_identity.strip():
        issues.append("MISSING_ARTIFACT_IDENTITY")
    if not response.request_hash.startswith("production-serving-"):
        issues.append("INVALID_REQUEST_HASH")
    expected_identity = _hash((
        PRODUCTION_SERVING_VERSION,
        response.request_id,
        response.serving_id,
        response.model_identity,
        response.model_version,
        response.artifact_identity,
        response.prediction,
        response.request_hash,
        response.status,
    ))
    if response.response_identity != expected_identity:
        issues.append("INVALID_RESPONSE_IDENTITY")
    if response.status != INFERENCE_ACCEPTED:
        issues.append("INVALID_RESPONSE_STATUS")
    if response.deterministic is not True:
        issues.append("NON_DETERMINISTIC_RESPONSE")
    return ServingResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
        response if not issues else None,
    )

def inference_response_identity(response: InferenceResponse) -> str:
    validation = validate_inference_response(response)
    if not validation.is_valid:
        raise ValueError("invalid inference response")
    return response.response_identity

def predict_with_mapping(
    serving_plan: ServingPlan,
    request: InferenceRequest,
    predictor: Callable[[Mapping[str, float]], Any],
) -> Any:
    result = serve_inference(serving_plan, request, predictor)
    if not result.is_valid or result.response is None:
        raise ValueError("inference rejected: " + ", ".join(result.issues))
    return result.response.prediction

__all__ = [
    "PRODUCTION_SERVING_VERSION", "VALID", "INVALID", "READY", "BLOCKED",
    "INFERENCE_ACCEPTED", "INFERENCE_REJECTED", "SERVING_BOUNDARY",
    "ServingPolicy", "ServingCheck", "InferenceRequest", "ServingPlan",
    "InferenceResponse", "ServingResult", "validate_serving_policy",
    "validate_feature_mapping", "build_inference_request",
    "build_serving_plan", "validate_serving_plan", "serving_checks",
    "serving_failed_checks", "serve_inference", "serving_summary",
    "validate_inference_response", "inference_response_identity",
    "predict_with_mapping",
]
