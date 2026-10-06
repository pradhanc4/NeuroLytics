from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

API_VALIDATION_VERSION = "74.0.0"
API_VALIDATION_BOUNDARY = "API_VALIDATION_ERROR_HANDLING_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"

@dataclass(frozen=True)
class ApiValidationPolicy:
    allowed_methods: tuple[str, ...] = ("POST",)
    required_content_type: str = "application/json"
    require_object_body: bool = True
    max_json_bytes: int = 1_048_576

@dataclass(frozen=True)
class ApiValidationResult:
    status: str
    http_status: int
    code: str | None
    message: str
    details: Any = None

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

def validate_api_validation_policy(policy: ApiValidationPolicy) -> None:
    if not isinstance(policy, ApiValidationPolicy):
        raise TypeError("policy must be ApiValidationPolicy")
    if not policy.allowed_methods:
        raise ValueError("allowed_methods must not be empty")
    methods = tuple(dict.fromkeys(policy.allowed_methods))
    if any(not isinstance(method, str) or not method for method in methods):
        raise ValueError("allowed_methods must contain non-empty strings")
    if not isinstance(policy.required_content_type, str) or not policy.required_content_type:
        raise ValueError("required_content_type must be a non-empty string")
    if not isinstance(policy.require_object_body, bool):
        raise ValueError("require_object_body must be boolean")
    if (
        isinstance(policy.max_json_bytes, bool)
        or not isinstance(policy.max_json_bytes, int)
        or policy.max_json_bytes <= 0
    ):
        raise ValueError("max_json_bytes must be a positive integer")

def validate_api_request(
    *,
    method: str,
    content_type: str | None,
    content_length: int | None,
    payload: Any,
    policy: ApiValidationPolicy = ApiValidationPolicy(),
) -> ApiValidationResult:
    validate_api_validation_policy(policy)
    if method not in policy.allowed_methods:
        return ApiValidationResult(
            INVALID, 405, "METHOD_NOT_ALLOWED",
            "HTTP method is not allowed for this route.",
        )
    if content_length is not None and content_length > policy.max_json_bytes:
        return ApiValidationResult(
            INVALID, 413, "PAYLOAD_TOO_LARGE",
            "Request body exceeds the configured API limit.",
        )
    if content_type is None or not content_type.startswith(policy.required_content_type):
        return ApiValidationResult(
            INVALID, 415, "CONTENT_TYPE_REQUIRED",
            "Content-Type must be application/json.",
        )
    if payload is None:
        return ApiValidationResult(
            INVALID, 400, "INVALID_JSON",
            "Request body is not valid JSON.",
        )
    if policy.require_object_body and not isinstance(payload, dict):
        return ApiValidationResult(
            INVALID, 400, "INVALID_JSON_BODY",
            "JSON body must be an object.",
        )
    return ApiValidationResult(VALID, 200, None, "Request is valid.")

def validation_summary(policy: ApiValidationPolicy = ApiValidationPolicy()) -> Mapping[str, Any]:
    validate_api_validation_policy(policy)
    return {
        "version": API_VALIDATION_VERSION,
        "boundary": API_VALIDATION_BOUNDARY,
        "allowed_methods": policy.allowed_methods,
        "required_content_type": policy.required_content_type,
        "require_object_body": policy.require_object_body,
        "max_json_bytes": policy.max_json_bytes,
    }

__all__ = [
    "API_VALIDATION_VERSION",
    "API_VALIDATION_BOUNDARY",
    "VALID",
    "INVALID",
    "ApiValidationPolicy",
    "ApiValidationResult",
    "validate_api_validation_policy",
    "validate_api_request",
    "validation_summary",
]
