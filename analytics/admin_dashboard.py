"""Phase 87 — Admin / Configuration Dashboard.

Read-only administrative projection over the existing production-service
configuration. This module does not mutate credentials, rate limits, model
state, serving state, or runtime policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from analytics.api_rate_limit import rate_limit_summary
from analytics.api_security import security_summary
if TYPE_CHECKING:
    from analytics.production_service import NeuroLyticsProductionService

ADMIN_DASHBOARD_VERSION = "87.0.0"
ADMIN_DASHBOARD_BOUNDARY = "ADMIN_CONFIGURATION_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class AdminDashboardService:
    """Read-only administration/configuration projection."""

    production_service: NeuroLyticsProductionService

    def __post_init__(self) -> None:
        required = ("state", "security_policy", "security_store", "rate_limit_policy", "rate_limiter", "policy", "dependencies", "health", "inference_service")
        if not all(hasattr(self.production_service, name) for name in required):
            raise TypeError("production_service must expose the production service contract")

    @property
    def service(self) -> NeuroLyticsProductionService:
        return self.production_service

    def service_state(self) -> dict[str, Any]:
        return {
            "status": VALID,
            "service_state": self.service.state,
            "startup_issues": list(self.service.startup_issues),
            "service_version": self.service.health().get("service_version"),
            "boundary": self.service.health().get("boundary"),
        }

    def security(self) -> dict[str, Any]:
        summary = dict(security_summary(self.service.security_policy, self.service.security_store))
        return {
            "status": VALID,
            "summary": summary,
            "credential_metadata": [
                {
                    "credential_id": credential.credential_id,
                    "role": credential.role,
                    "scopes": list(credential.scopes),
                    "revoked": credential.revoked,
                    "raw_key_exposed": False,
                    "key_hash_exposed": False,
                }
                for credential in self.service.security_store.credentials()
            ],
        }

    def rate_limit(self) -> dict[str, Any]:
        return {
            "status": VALID,
            "summary": rate_limit_summary(
                self.service.rate_limit_policy,
                self.service.rate_limiter,
            ),
        }

    def production_policy(self) -> dict[str, Any]:
        policy = self.service.policy
        return {
            "status": VALID,
            "policy": {
                "require_inference_ready": policy.require_inference_ready,
                "require_monitoring_healthy": policy.require_monitoring_healthy,
                "require_shared_security": policy.require_shared_security,
                "require_shared_rate_limiter": policy.require_shared_rate_limiter,
            },
        }

    def serving(self) -> dict[str, Any]:
        plan = self.service.inference_service.serving_plan
        return {
            "status": VALID,
            "serving_state": plan.serving_state,
            "model_identity": getattr(plan, "model_identity", None),
            "model_version": getattr(plan, "model_version", None),
            "artifact_identity": getattr(plan, "artifact_identity", None),
        }

    def dependencies(self) -> dict[str, Any]:
        return {
            "status": VALID,
            "dependencies": [
                {
                    "name": dependency.name,
                    "status": dependency.status,
                    "description": dependency.detail,
                }
                for dependency in self.service.dependencies()
            ],
        }

    def scopes(self, configured_scopes: Mapping[str, str]) -> dict[str, Any]:
        if not isinstance(configured_scopes, Mapping):
            raise TypeError("configured_scopes must be a mapping")
        values = []
        for name, scope in sorted(configured_scopes.items()):
            if not isinstance(name, str) or not name:
                raise ValueError("scope names must be non-empty strings")
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError("scope values must be non-empty strings")
            values.append({"name": name, "scope": scope})
        return {"status": VALID, "scopes": values, "count": len(values)}

    def dashboard(self, configured_scopes: Mapping[str, str]) -> dict[str, Any]:
        return {
            "status": VALID,
            "version": ADMIN_DASHBOARD_VERSION,
            "boundary": ADMIN_DASHBOARD_BOUNDARY,
            "read_only": True,
            "service_state": self.service_state(),
            "security": self.security(),
            "rate_limit": self.rate_limit(),
            "production_policy": self.production_policy(),
            "serving": self.serving(),
            "dependencies": self.dependencies(),
            "scopes": self.scopes(configured_scopes),
        }


def admin_dashboard_summary() -> dict[str, Any]:
    return {
        "version": ADMIN_DASHBOARD_VERSION,
        "boundary": ADMIN_DASHBOARD_BOUNDARY,
        "read_only": True,
        "sections": (
            "service_state",
            "security",
            "rate_limit",
            "production_policy",
            "serving",
            "dependencies",
            "scopes",
        ),
    }


def admin_dashboard_contract() -> dict[str, Any]:
    return {
        "status": VALID,
        "version": ADMIN_DASHBOARD_VERSION,
        "boundary": ADMIN_DASHBOARD_BOUNDARY,
        "read_only": True,
        "mutation_routes": [],
        "secrets_exposed": False,
    }


__all__ = [
    "ADMIN_DASHBOARD_VERSION",
    "ADMIN_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "AdminDashboardService",
    "admin_dashboard_summary",
    "admin_dashboard_contract",
]
