from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.model_health import (
    ModelHealthReport,
    model_health_summary,
    validate_model_health_report,
)

MODEL_HEALTH_DASHBOARD_VERSION = "85.0.0"
MODEL_HEALTH_DASHBOARD_BOUNDARY = "MODEL_HEALTH_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ModelHealthDashboardService:
    """Read-only dashboard projection of the authoritative Phase 57 scorecard."""

    health_report: ModelHealthReport | None = None

    def _state(self) -> dict[str, object]:
        report = self.health_report
        if report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        identity = getattr(report, "report_identity", "")
        return {
            "status": AVAILABLE if identity else INVALID,
            "report_identity": identity,
            "version": getattr(report, "version", None),
        }

    def summary(self) -> dict[str, object]:
        state = self._state()
        if self.health_report is None:
            return {
                "status": VALID,
                "version": MODEL_HEALTH_DASHBOARD_VERSION,
                "boundary": MODEL_HEALTH_DASHBOARD_BOUNDARY,
                "read_only": True,
                "health_report": state,
            }
        source = model_health_summary(self.health_report)
        return {
            "status": source["status"],
            "version": MODEL_HEALTH_DASHBOARD_VERSION,
            "boundary": MODEL_HEALTH_DASHBOARD_BOUNDARY,
            "read_only": True,
            "model_identity": source["model_identity"],
            "health_status": source["health_status"],
            "weighted_score": source["weighted_score"],
            "component_count": source["component_count"],
            "critical_component_count": len(source["critical_components"]),
            "degraded_component_count": len(source["degraded_components"]),
            "critical_components": source["critical_components"],
            "degraded_components": source["degraded_components"],
            "report_identity": source["report_identity"],
            "source_version": source["version"],
        }

    def scorecard(self) -> dict[str, object]:
        state = self._state()
        if self.health_report is None:
            return state
        score = self.health_report.score
        validation = validate_model_health_report(self.health_report)
        return {
            "status": validation.status,
            "model_identity": self.health_report.model_identity,
            "weighted_score": score.weighted_score,
            "health_status": score.status,
            "component_count": score.component_count,
            "critical_components": score.active_critical_components,
            "degraded_components": score.active_degraded_components,
            "healthy_min": self.health_report.healthy_min,
            "degraded_min": self.health_report.degraded_min,
            "report_identity": self.health_report.report_identity,
            "validation_issues": validation.issues,
        }

    def components(self) -> dict[str, object]:
        state = self._state()
        if self.health_report is None:
            return state
        return {
            "status": validate_model_health_report(self.health_report).status,
            "model_identity": self.health_report.model_identity,
            "component_count": len(self.health_report.components),
            "components": tuple(
                {
                    "name": item.name,
                    "score": item.score,
                    "status": item.status,
                    "weight": item.weight,
                    "source_identity": item.source_identity,
                }
                for item in self.health_report.components
            ),
            "report_identity": self.health_report.report_identity,
        }

    def thresholds(self) -> dict[str, object]:
        state = self._state()
        if self.health_report is None:
            return state
        return {
            "status": validate_model_health_report(self.health_report).status,
            "healthy_min": self.health_report.healthy_min,
            "degraded_min": self.health_report.degraded_min,
            "bands": (
                {"status": "HEALTHY", "minimum": self.health_report.healthy_min},
                {"status": "DEGRADED", "minimum": self.health_report.degraded_min},
                {"status": "CRITICAL", "minimum": 0.0},
            ),
            "report_identity": self.health_report.report_identity,
        }

    def lineage(self) -> dict[str, object]:
        state = self._state()
        if self.health_report is None:
            return state
        return {
            "status": validate_model_health_report(self.health_report).status,
            "model_identity": self.health_report.model_identity,
            "report_identity": self.health_report.report_identity,
            "source_identities": tuple(
                {"component": item.name, "source_identity": item.source_identity}
                for item in self.health_report.components
            ),
            "source_count": len(self.health_report.components),
        }

    def validation(self) -> dict[str, object]:
        if self.health_report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        result = validate_model_health_report(self.health_report)
        return {
            "status": result.status,
            "is_valid": result.is_valid,
            "issues": result.issues,
            "report_identity": self.health_report.report_identity,
        }

    def dashboard(self) -> dict[str, object]:
        return {
            "status": VALID,
            "summary": self.summary(),
            "scorecard": self.scorecard(),
            "components": self.components(),
            "thresholds": self.thresholds(),
            "lineage": self.lineage(),
            "validation": self.validation(),
        }


def model_health_dashboard_summary(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.summary()


def model_health_dashboard_scorecard(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.scorecard()


def model_health_dashboard_components(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.components()


def model_health_dashboard_thresholds(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.thresholds()


def model_health_dashboard_lineage(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.lineage()


def model_health_dashboard_validation(service: ModelHealthDashboardService) -> dict[str, object]:
    return service.validation()


def model_health_dashboard_contract() -> dict[str, object]:
    return {
        "version": MODEL_HEALTH_DASHBOARD_VERSION,
        "boundary": MODEL_HEALTH_DASHBOARD_BOUNDARY,
        "read_only": True,
        "routes": (
            "/v1/model-health/summary",
            "/v1/model-health/scorecard",
            "/v1/model-health/components",
            "/v1/model-health/thresholds",
            "/v1/model-health/lineage",
            "/v1/model-health/validation",
        ),
    }


__all__ = [
    "MODEL_HEALTH_DASHBOARD_VERSION",
    "MODEL_HEALTH_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "ModelHealthDashboardService",
    "model_health_dashboard_summary",
    "model_health_dashboard_scorecard",
    "model_health_dashboard_components",
    "model_health_dashboard_thresholds",
    "model_health_dashboard_lineage",
    "model_health_dashboard_validation",
    "model_health_dashboard_contract",
]
