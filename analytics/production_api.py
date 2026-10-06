from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from flask import Flask, jsonify, request

from analytics.production_serving import (
    INFERENCE_ACCEPTED,
    InferenceRequest,
    ServingPlan,
    build_inference_request,
    serve_inference,
    validate_serving_plan,
)
from analytics.api_security import (
    AUTHENTICATED,
    AUTHORIZED,
    ApiCredentialStore,
    ApiSecurityPolicy,
    SecurityDecision,
    authorize,
    validate_security_policy,
)
from analytics.api_rate_limit import (
    API_RATE_LIMIT_VERSION,
    RATE_LIMITED,
    ApiRateLimitPolicy,
    ApiRateLimiter,
    rate_limit_headers,
    validate_rate_limit_policy,
)
from analytics.api_validation import (
    API_VALIDATION_VERSION,
    ApiValidationPolicy,
    validate_api_request,
    validate_api_validation_policy,
)

PRODUCTION_API_VERSION = "69.0.0"
API_READY = "READY"
API_NOT_READY = "NOT_READY"
API_HEALTHY = "HEALTHY"
API_UNHEALTHY = "UNHEALTHY"
API_ACCEPTED = "API_ACCEPTED"
API_REJECTED = "API_REJECTED"
API_BOUNDARY = "PRODUCTION_API_BOUNDARY"
SECURITY_REQUIRED = "SECURITY_REQUIRED"
SECURITY_DENIED = "SECURITY_DENIED"
RATE_LIMIT_REQUIRED = "RATE_LIMIT_REQUIRED"
RATE_LIMIT_DENIED = "RATE_LIMIT_DENIED"

@dataclass(frozen=True)
class ApiPolicy:
    require_ready_for_inference: bool = True
    require_json_body: bool = True
    require_feature_mapping: bool = True
    max_json_bytes: int = 1_048_576

@dataclass(frozen=True)
class ApiCheck:
    check_id: str
    status: str
    detail: str

@dataclass(frozen=True)
class ApiResult:
    status: str
    http_status: int
    payload: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        return self.status == API_ACCEPTED
def validate_api_policy(policy: ApiPolicy) -> None:
    if not isinstance(policy, ApiPolicy):
        raise TypeError("policy must be ApiPolicy")
    values = (
        policy.require_ready_for_inference,
        policy.require_json_body,
        policy.require_feature_mapping,
    )
    if not all(isinstance(value, bool) for value in values):
        raise ValueError("API policy boolean fields must be boolean")
    if (
        isinstance(policy.max_json_bytes, bool)
        or not isinstance(policy.max_json_bytes, int)
        or policy.max_json_bytes <= 0
    ):
        raise ValueError("max_json_bytes must be a positive integer")

def _error_payload(code: str, message: str, *, details: Any = None) -> dict[str, Any]:
    payload = {
        "api_version": PRODUCTION_API_VERSION,
        "status": API_REJECTED,
        "error": {"code": code, "message": message},
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload

def _success_payload(response: Any) -> dict[str, Any]:
    return {
        "api_version": PRODUCTION_API_VERSION,
        "status": API_ACCEPTED,
        "inference_status": response.status,
        "request_id": response.request_id,
        "serving_id": response.serving_id,
        "model_identity": response.model_identity,
        "model_version": response.model_version,
        "artifact_identity": response.artifact_identity,
        "prediction": response.prediction,
        "request_hash": response.request_hash,
        "response_identity": response.response_identity,
        "deterministic": response.deterministic,
    }

class InferenceApiService:
    def __init__(
        self,
        serving_plan: ServingPlan,
        predictor: Callable[[Mapping[str, float]], Any],
        *,
        policy: ApiPolicy = ApiPolicy(),
    ) -> None:
        validate_api_policy(policy)
        if not isinstance(serving_plan, ServingPlan):
            raise TypeError("serving_plan must be ServingPlan")
        if not callable(predictor):
            raise TypeError("predictor must be callable")
        self._serving_plan = serving_plan
        self._predictor = predictor
        self._policy = policy

    @property
    def serving_plan(self) -> ServingPlan:
        return self._serving_plan

    @property
    def policy(self) -> ApiPolicy:
        return self._policy
    def health(self) -> dict[str, Any]:
        return {
            "api_version": PRODUCTION_API_VERSION,
            "status": API_HEALTHY,
            "boundary": API_BOUNDARY,
            "service": "neurolytics-inference",
        }

    def readiness(self) -> ApiResult:
        validation = validate_serving_plan(self._serving_plan)
        if not validation.is_valid:
            return ApiResult(
                API_REJECTED,
                503,
                _error_payload(
                    "SERVING_PLAN_NOT_READY",
                    "The Phase 68 serving plan is not valid.",
                    details=list(validation.issues),
                ),
            )
        return ApiResult(
            API_ACCEPTED,
            200,
            {
                "api_version": PRODUCTION_API_VERSION,
                "status": API_READY,
                "boundary": API_BOUNDARY,
                "serving_id": self._serving_plan.serving_id,
                "model_identity": self._serving_plan.model_identity,
                "model_version": self._serving_plan.model_version,
                "artifact_identity": self._serving_plan.artifact_identity,
            },
        )

    def infer(self, payload: Any) -> ApiResult:
        if not isinstance(payload, dict):
            return ApiResult(
                API_REJECTED, 400,
                _error_payload("INVALID_JSON_BODY", "JSON body must be an object."),
            )
        required = (
            "request_id",
            "model_identity",
            "model_version",
            "artifact_identity",
            "features",
        )
        missing = [key for key in required if key not in payload]
        if missing:
            return ApiResult(
                API_REJECTED, 400,
                _error_payload("MISSING_FIELDS", "Required inference fields are missing.", details=missing),
            )
        try:
            inference_request = build_inference_request(
                payload["request_id"],
                payload["model_identity"],
                payload["model_version"],
                payload["artifact_identity"],
                payload["features"],
            )
        except (TypeError, ValueError) as exc:
            return ApiResult(
                API_REJECTED, 400,
                _error_payload("INVALID_INFERENCE_REQUEST", str(exc)),
            )
        if self._policy.require_ready_for_inference:
            readiness = self.readiness()
            if not readiness.is_valid:
                return readiness
        result = serve_inference(
            self._serving_plan,
            inference_request,
            self._predictor,
        )
        if not result.is_valid or result.response is None:
            return ApiResult(
                API_REJECTED,
                422,
                _error_payload(
                    "INFERENCE_REJECTED",
                    "The Phase 68 serving boundary rejected the request.",
                    details=list(result.issues),
                ),
            )
        return ApiResult(API_ACCEPTED, 200, _success_payload(result.response))

def _security_error(decision: SecurityDecision) -> tuple[dict[str, Any], int]:
    if decision.code == "MISSING_CREDENTIAL":
        status = 401
    elif decision.code == "INVALID_CREDENTIAL":
        status = 401
    else:
        status = 403
    return (
        _error_payload(
            SECURITY_DENIED,
            decision.message,
            details={"code": decision.code},
        ),
        status,
    )

def authorize_http_request(
    store: ApiCredentialStore,
    policy: ApiSecurityPolicy,
    required_scope: str,
) -> SecurityDecision:
    validate_security_policy(policy)
    if not policy.enabled:
        return SecurityDecision(AUTHORIZED, AUTHORIZED, "API security is disabled by policy.")
    raw_key = request.headers.get(policy.credential_header)
    decision = store.verify(raw_key or "")
    return authorize(decision, required_scope)

def create_inference_app(
    service: InferenceApiService,
    *,
    security_store: ApiCredentialStore | None = None,
    security_policy: ApiSecurityPolicy | None = None,
    rate_limit_policy: ApiRateLimitPolicy | None = None,
    rate_limiter: ApiRateLimiter | None = None,
    validation_policy: ApiValidationPolicy | None = None,
) -> Flask:
    if not isinstance(service, InferenceApiService):
        raise TypeError("service must be InferenceApiService")
    policy = security_policy or ApiSecurityPolicy(enabled=False)
    validate_security_policy(policy)
    store = security_store or ApiCredentialStore()
    limit_policy = rate_limit_policy or ApiRateLimitPolicy(enabled=False)
    validate_rate_limit_policy(limit_policy)
    limiter = rate_limiter or ApiRateLimiter(limit_policy)
    if limiter.policy != limit_policy:
        raise ValueError("rate_limiter policy does not match rate_limit_policy")
    validation = validation_policy or ApiValidationPolicy(
        max_json_bytes=service.policy.max_json_bytes,
    )
    validate_api_validation_policy(validation)

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = service.policy.max_json_bytes
    app.config["NEUROLYTICS_API_VERSION"] = PRODUCTION_API_VERSION
    app.config["NEUROLYTICS_SECURITY_VERSION"] = "70.0.0"
    app.config["NEUROLYTICS_RATE_LIMIT_VERSION"] = API_RATE_LIMIT_VERSION
    app.config["NEUROLYTICS_VALIDATION_VERSION"] = API_VALIDATION_VERSION

    @app.get("/health")
    def health() -> Any:
        return jsonify(service.health()), 200

    @app.get("/ready")
    def ready() -> Any:
        decision = authorize_http_request(store, policy, policy.required_ready_scope)
        if decision.status != AUTHORIZED:
            failure_identity = "ip:" + (request.remote_addr or "unknown")
            failure_limit = limiter.check(failure_identity)
            if not failure_limit.allowed:
                payload = _error_payload(
                    RATE_LIMIT_DENIED,
                    "API request rate limit exceeded.",
                    details={"code": RATE_LIMITED, "identity": "ip"},
                )
                return jsonify(payload), 429, rate_limit_headers(failure_limit)
            payload, status = _security_error(decision)
            return jsonify(payload), status
        identity = (
            "credential:" + decision.context.credential_id
            if decision.context is not None
            else "ip:" + (request.remote_addr or "unknown")
        )
        limit_decision = limiter.check(identity)
        if not limit_decision.allowed:
            payload = _error_payload(
                RATE_LIMIT_DENIED,
                "API request rate limit exceeded.",
                details={"code": RATE_LIMITED, "identity": identity.split(":", 1)[0]},
            )
            return jsonify(payload), 429, rate_limit_headers(limit_decision)
        result = service.readiness()
        return jsonify(result.payload), result.http_status, rate_limit_headers(limit_decision)

    @app.post("/v1/inference")
    def inference() -> Any:
        decision = authorize_http_request(store, policy, policy.required_inference_scope)
        if decision.status != AUTHORIZED:
            failure_identity = "ip:" + (request.remote_addr or "unknown")
            failure_limit = limiter.check(failure_identity)
            if not failure_limit.allowed:
                payload = _error_payload(
                    RATE_LIMIT_DENIED,
                    "API request rate limit exceeded.",
                    details={"code": RATE_LIMITED, "identity": "ip"},
                )
                return jsonify(payload), 429, rate_limit_headers(failure_limit)
            payload, status = _security_error(decision)
            return jsonify(payload), status
        identity = (
            "credential:" + decision.context.credential_id
            if decision.context is not None
            else "ip:" + (request.remote_addr or "unknown")
        )
        limit_decision = limiter.check(identity)
        if not limit_decision.allowed:
            payload = _error_payload(
                RATE_LIMIT_DENIED,
                "API request rate limit exceeded.",
                details={"code": RATE_LIMITED, "identity": identity.split(":", 1)[0]},
            )
            return jsonify(payload), 429, rate_limit_headers(limit_decision)
        payload = request.get_json(silent=True) if request.is_json else None
        validation_result = validate_api_request(
            method=request.method,
            content_type=request.content_type,
            content_length=request.content_length,
            payload=payload,
            policy=validation,
        )
        if not validation_result.is_valid:
            return jsonify(_error_payload(
                validation_result.code or "API_VALIDATION_FAILED",
                validation_result.message,
                details=validation_result.details,
            )), validation_result.http_status
        result = service.infer(payload)
        return jsonify(result.payload), result.http_status, rate_limit_headers(limit_decision)

    @app.errorhandler(404)
    def not_found(_: Any) -> Any:
        return jsonify(_error_payload("NOT_FOUND", "API route was not found.")), 404

    @app.errorhandler(405)
    def method_not_allowed(_: Any) -> Any:
        return jsonify(_error_payload(
            "METHOD_NOT_ALLOWED",
            "HTTP method is not allowed for this route.",
        )), 405

    @app.errorhandler(413)
    def too_large(_: Any) -> Any:
        return jsonify(_error_payload(
            "PAYLOAD_TOO_LARGE",
            "Request body exceeds the configured API limit.",
        )), 413

    return app

def create_secure_inference_app(
    service: InferenceApiService,
    security_store: ApiCredentialStore,
    *,
    security_policy: ApiSecurityPolicy | None = None,
    rate_limit_policy: ApiRateLimitPolicy | None = None,
    rate_limiter: ApiRateLimiter | None = None,
) -> Flask:
    policy = security_policy or ApiSecurityPolicy(enabled=True)
    if not policy.enabled:
        raise ValueError("create_secure_inference_app requires enabled security policy")
    limit_policy = rate_limit_policy or ApiRateLimitPolicy(enabled=True)
    return create_inference_app(
        service,
        security_store=security_store,
        security_policy=policy,
        rate_limit_policy=limit_policy,
        rate_limiter=rate_limiter,
    )
def api_summary(service: InferenceApiService) -> dict[str, Any]:
    readiness = service.readiness()
    return {
        "api_version": PRODUCTION_API_VERSION,
        "boundary": API_BOUNDARY,
        "health": service.health(),
        "readiness_status": readiness.status,
        "readiness_http_status": readiness.http_status,
        "serving_id": service.serving_plan.serving_id,
        "model_identity": service.serving_plan.model_identity,
        "model_version": service.serving_plan.model_version,
        "artifact_identity": service.serving_plan.artifact_identity,
        "routes": (
            "/health",
            "/ready",
            "/v1/inference",
        ),
    }

def api_checks(service: InferenceApiService) -> tuple[ApiCheck, ...]:
    validation = validate_serving_plan(service.serving_plan)
    return (
        ApiCheck(
            "SERVING_PLAN",
            "PASS" if validation.is_valid else "FAIL",
            "Phase 68 serving plan validation",
        ),
        ApiCheck(
            "PREDICTOR",
            "PASS" if callable(service._predictor) else "FAIL",
            "predictor callable contract",
        ),
        ApiCheck(
            "API_POLICY",
            "PASS",
            "API policy validated during service construction",
        ),
    )

def api_failed_checks(service: InferenceApiService) -> tuple[str, ...]:
    return tuple(
        check.check_id for check in api_checks(service)
        if check.status == "FAIL"
    )

__all__ = [
    "PRODUCTION_API_VERSION",
    "API_READY",
    "API_NOT_READY",
    "API_HEALTHY",
    "API_UNHEALTHY",
    "API_ACCEPTED",
    "API_REJECTED",
    "API_BOUNDARY",
    "SECURITY_REQUIRED",
    "SECURITY_DENIED",
    "ApiPolicy",
    "ApiCheck",
    "ApiResult",
    "InferenceApiService",
    "validate_api_policy",
    "authorize_http_request",
    "create_inference_app",
    "create_secure_inference_app",
    "api_summary",
    "api_checks",
    "api_failed_checks",
]
