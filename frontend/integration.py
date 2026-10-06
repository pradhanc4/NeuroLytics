"""Phase 88 — Full Frontend Integration contract.

Central registry for the already implemented frontend views and API boundaries.
It does not add a second API or mutate production state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

FRONTEND_INTEGRATION_VERSION = "88.0.0"
FRONTEND_INTEGRATION_BOUNDARY = "FULL_FRONTEND_INTEGRATION_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"

@dataclass(frozen=True)
class FrontendRoute:
    key: str
    title: str
    path: str
    read_only: bool = True

ROUTES = (
    FrontendRoute("overview", "Analytics Overview", "/"),
    FrontendRoute("analytics", "Analytics Dashboard", "/v1/analytics/summary"),
    FrontendRoute("historical", "Historical Data", "/v1/historical/summary"),
    FrontendRoute("ranking", "Ranking Dashboard", "/v1/ranking/summary"),
    FrontendRoute("top-k", "Top-K Dashboard", "/v1/top-k/summary"),
    FrontendRoute("performance", "Performance Dashboard", "/v1/performance/summary"),
    FrontendRoute("drift", "Drift / Monitoring", "/v1/drift/summary"),
    FrontendRoute("model-health", "Model Health Dashboard", "/v1/model-health/summary"),
    FrontendRoute("prediction", "Prediction", "/v1/inference", False),
    FrontendRoute("admin", "Admin / Configuration", "/v1/admin/summary"),
    FrontendRoute("monitoring", "Monitoring", "/v1/monitoring/summary"),
    FrontendRoute("models", "Model Status", "/v1/model/summary"),
)

def integration_summary() -> dict[str, object]:
    return {
        "version": FRONTEND_INTEGRATION_VERSION,
        "boundary": FRONTEND_INTEGRATION_BOUNDARY,
        "route_count": len(ROUTES),
        "routes": tuple(route.key for route in ROUTES),
        "read_only_views": tuple(route.key for route in ROUTES if route.read_only),
        "mutation_views": ("prediction",),
    }

def validate_integration(routes: Mapping[str, str] | None = None) -> tuple[str, ...]:
    expected = {route.key: route.title for route in ROUTES}
    if routes is None:
        return ()
    issues: list[str] = []
    for key, title in expected.items():
        if routes.get(key) != title:
            issues.append(f"MISSING_OR_INVALID_ROUTE:{key}")
    return tuple(issues)

__all__ = [
    "FRONTEND_INTEGRATION_VERSION",
    "FRONTEND_INTEGRATION_BOUNDARY",
    "FrontendRoute",
    "ROUTES",
    "integration_summary",
    "validate_integration",
]
