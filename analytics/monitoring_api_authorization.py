from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy, SecurityDecision, authorize, validate_security_policy
from analytics.performance_monitoring_api import PerformanceMonitoringApiService

MONITORING_AUTHORIZATION_VERSION = "73.0.0"
MONITORING_AUTHORIZATION_BOUNDARY = "MONITORING_API_AUTHORIZATION_BOUNDARY"

@dataclass(frozen=True)
class MonitoringAuthorizationPolicy:
    security_policy: ApiSecurityPolicy = ApiSecurityPolicy()
    required_scope: str = "monitoring:read"
    public_health: bool = True


def validate_monitoring_authorization_policy(policy: MonitoringAuthorizationPolicy) -> None:
    if not isinstance(policy, MonitoringAuthorizationPolicy):
        raise TypeError("policy must be MonitoringAuthorizationPolicy")
    validate_security_policy(policy.security_policy)
    if not isinstance(policy.required_scope, str) or not policy.required_scope:
        raise ValueError("required_scope must be non-empty")
    if not isinstance(policy.public_health, bool):
        raise ValueError("public_health must be boolean")


def authorize_monitoring_request(store: ApiCredentialStore, policy: MonitoringAuthorizationPolicy, raw_key: str) -> SecurityDecision:
    validate_monitoring_authorization_policy(policy)
    if not policy.security_policy.enabled:
        return SecurityDecision("AUTHORIZED", "AUTHORIZED", "Monitoring authorization is disabled by policy.")
    return authorize(store.verify(raw_key or ""), policy.required_scope)


def monitoring_authorization_summary(policy: MonitoringAuthorizationPolicy, store: ApiCredentialStore) -> dict[str, Any]:
    validate_monitoring_authorization_policy(policy)
    return {
        "authorization_version": MONITORING_AUTHORIZATION_VERSION,
        "boundary": MONITORING_AUTHORIZATION_BOUNDARY,
        "enabled": policy.security_policy.enabled,
        "required_scope": policy.required_scope,
        "credential_header": policy.security_policy.credential_header,
        "credential_count": len(store.credentials()),
        "credential_ids": tuple(c.credential_id for c in store.credentials()),
        "raw_keys_exposed": False,
    }


def create_authorized_monitoring_app(service: PerformanceMonitoringApiService, store: ApiCredentialStore, policy: MonitoringAuthorizationPolicy = MonitoringAuthorizationPolicy()):
    if not isinstance(service, PerformanceMonitoringApiService):
        raise TypeError("service must be PerformanceMonitoringApiService")
    if not isinstance(store, ApiCredentialStore):
        raise TypeError("store must be ApiCredentialStore")
    validate_monitoring_authorization_policy(policy)
    from analytics.performance_monitoring_api import create_monitoring_app
    return create_monitoring_app(service, security_store=store, security_policy=policy.security_policy, required_scope=policy.required_scope)


__all__ = [
    "MONITORING_AUTHORIZATION_VERSION",
    "MONITORING_AUTHORIZATION_BOUNDARY",
    "MonitoringAuthorizationPolicy",
    "validate_monitoring_authorization_policy",
    "authorize_monitoring_request",
    "monitoring_authorization_summary",
    "create_authorized_monitoring_app",
]
