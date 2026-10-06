from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.production_serving import (
    ServingPlan,
    validate_serving_plan,
    serving_checks,
)

MODEL_DASHBOARD_VERSION = "80.0.0"
MODEL_DASHBOARD_BOUNDARY = "MODEL_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ModelDashboardService:
    """Read-only projection of existing model lifecycle and serving contracts.

    Phase 80 does not create a second model registry. It exposes the current
    serving lineage and accepts optional existing lifecycle reports when a
    caller has them available.
    """

    serving_plan: ServingPlan
    health_report: Any | None = None
    comparison_report: Any | None = None
    champion_challenger_report: Any | None = None
    selection_report: Any | None = None
    lifecycle_report: Any | None = None
    rollout_plan: Any | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.serving_plan, ServingPlan):
            raise TypeError("serving_plan must be a ServingPlan")

    def serving(self) -> dict[str, object]:
        validation = validate_serving_plan(self.serving_plan)
        checks = serving_checks(self.serving_plan)
        return {
            "status": validation.status,
            "serving_id": self.serving_plan.serving_id,
            "activation_id": self.serving_plan.activation_id,
            "model_identity": self.serving_plan.model_identity,
            "model_version": self.serving_plan.model_version,
            "artifact_identity": self.serving_plan.artifact_identity,
            "serving_status": self.serving_plan.status,
            "serving_state": self.serving_plan.serving_state,
            "failed_checks": tuple(c.check_id for c in checks if c.status == "FAIL"),
            "checks": tuple(
                {"check_id": c.check_id, "status": c.status, "detail": c.detail}
                for c in checks
            ),
            "plan_identity": self.serving_plan.plan_identity,
        }

    @staticmethod
    def _report_state(report: Any | None, identity_field: str = "report_identity") -> dict[str, object]:
        if report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        identity = getattr(report, identity_field, "")
        return {
            "status": AVAILABLE if identity else INVALID,
            "identity": identity,
            "version": getattr(report, "version", None),
        }

    def identity(self) -> dict[str, object]:
        return {
            "status": VALID,
            "model_identity": self.serving_plan.model_identity,
            "model_version": self.serving_plan.model_version,
            "artifact_identity": self.serving_plan.artifact_identity,
            "serving_id": self.serving_plan.serving_id,
            "activation_id": self.serving_plan.activation_id,
            "source": "production_serving",
        }

    def health(self) -> dict[str, object]:
        state = self._report_state(self.health_report)
        if self.health_report is None:
            return state
        score = getattr(self.health_report, "score", None)
        return {
            **state,
            "model_identity": getattr(self.health_report, "model_identity", None),
            "weighted_score": getattr(score, "weighted_score", None),
            "health_status": getattr(score, "status", None),
            "component_count": getattr(score, "component_count", None),
            "critical_components": getattr(score, "active_critical_components", ()),
            "degraded_components": getattr(score, "active_degraded_components", ()),
            "components": tuple(
                {
                    "name": item.name,
                    "score": item.score,
                    "status": item.status,
                    "weight": item.weight,
                    "source_identity": item.source_identity,
                }
                for item in getattr(self.health_report, "components", ())
            ),
        }

    def comparison(self) -> dict[str, object]:
        state = self._report_state(self.comparison_report)
        if self.comparison_report is None:
            return state
        return {
            **state,
            "baseline_period": self.comparison_report.baseline_period,
            "comparison_period": self.comparison_report.comparison_period,
            "common_models": self.comparison_report.common_models,
            "improved_models": self.comparison_report.improved_models,
            "declined_models": self.comparison_report.declined_models,
            "unchanged_models": self.comparison_report.unchanged_models,
            "comparisons": tuple(
                {
                    "model_identity": item.model_identity,
                    "baseline_value": item.baseline_value,
                    "comparison_value": item.comparison_value,
                    "absolute_change": item.absolute_change,
                    "relative_change": item.relative_change,
                }
                for item in self.comparison_report.metric_comparisons
            ),
        }
    def champion_challenger(self) -> dict[str, object]:
        state = self._report_state(self.champion_challenger_report)
        if self.champion_challenger_report is None:
            return state
        report = self.champion_challenger_report
        return {
            **state,
            "framework_id": report.framework_id,
            "baseline_period": report.baseline_period,
            "comparison_period": report.comparison_period,
            "champion": {
                "model_identity": report.champion.model_identity,
                "role": report.champion.role,
                "state": report.champion.state,
            },
            "challengers": tuple(
                {
                    "model_identity": item.model_identity,
                    "role": item.role,
                    "state": item.state,
                }
                for item in report.challengers
            ),
            "evidence": tuple(
                {
                    "model_identity": item.model_identity,
                    "champion_identity": item.champion_identity,
                    "health_score": item.health_score,
                    "champion_health_score": item.champion_health_score,
                    "absolute_change_vs_champion": item.absolute_change_vs_champion,
                    "relative_change_vs_champion": item.relative_change_vs_champion,
                }
                for item in report.evidence
            ),
        }

    def selection(self) -> dict[str, object]:
        state = self._report_state(self.selection_report)
        if self.selection_report is None:
            return state
        report = self.selection_report
        return {
            **state,
            "selection_id": report.selection_id,
            "champion_identity": report.champion_identity,
            "selected_model": report.selected_model,
            "promoted_models": report.promoted_models,
            "held_models": report.held_models,
            "ineligible_models": report.ineligible_models,
            "decisions": tuple(
                {
                    "model_identity": item.model_identity,
                    "health_score": item.health_score,
                    "health_status": item.health_status,
                    "eligibility": item.eligibility,
                    "action": item.action,
                    "reasons": item.reasons,
                }
                for item in report.decisions
            ),
        }

    def lifecycle(self) -> dict[str, object]:
        state = self._report_state(self.lifecycle_report)
        if self.lifecycle_report is None:
            return state
        report = self.lifecycle_report
        return {
            **state,
            "lifecycle_id": report.lifecycle_id,
            "active_versions": report.active_versions,
            "candidate_versions": report.candidate_versions,
            "deprecated_versions": report.deprecated_versions,
            "retired_versions": report.retired_versions,
            "rejected_versions": report.rejected_versions,
            "versions": tuple(
                {
                    "model_identity": item.model_identity,
                    "version": item.version,
                    "state": item.state,
                    "artifact_identity": item.artifact_identity,
                    "parent_version": item.parent_version,
                }
                for item in report.versions
            ),
            "transitions": tuple(
                {
                    "model_identity": item.model_identity,
                    "version": item.version,
                    "from_state": item.from_state,
                    "to_state": item.to_state,
                    "reason": item.reason,
                }
                for item in report.transitions
            ),
        }

    def rollout(self) -> dict[str, object]:
        state = self._report_state(self.rollout_plan, "plan_identity")
        if self.rollout_plan is None:
            return state
        plan = self.rollout_plan
        return {
            **state,
            "rollout_id": plan.rollout_id,
            "model_identity": plan.model_identity,
            "model_version": plan.model_version,
            "artifact_identity": plan.artifact_identity,
            "current_state": plan.current_state,
            "target_state": plan.target_state,
            "rollout_status": plan.status,
            "activation_state": plan.activation_state,
            "authorization_id": plan.authorization_id,
            "failed_checks": plan.failed_checks,
        }

    def summary(self) -> dict[str, object]:
        serving = self.serving()
        sections = {
            "identity": AVAILABLE,
            "serving": AVAILABLE if serving["status"] == VALID else INVALID,
            "health": self.health()["status"],
            "comparison": self.comparison()["status"],
            "champion_challenger": self.champion_challenger()["status"],
            "selection": self.selection()["status"],
            "lifecycle": self.lifecycle()["status"],
            "rollout": self.rollout()["status"],
        }
        return {
            "status": VALID if serving["status"] == VALID else INVALID,
            "version": MODEL_DASHBOARD_VERSION,
            "boundary": MODEL_DASHBOARD_BOUNDARY,
            "read_only": True,
            "model_identity": self.serving_plan.model_identity,
            "model_version": self.serving_plan.model_version,
            "artifact_identity": self.serving_plan.artifact_identity,
            "serving_id": self.serving_plan.serving_id,
            "serving_state": self.serving_plan.serving_state,
            "failed_checks": serving["failed_checks"],
            "checks": serving["checks"],
            "sections": sections,
        }


def model_dashboard_summary(service: ModelDashboardService) -> dict[str, object]:
    return service.summary()


def model_dashboard_identity(service: ModelDashboardService) -> dict[str, object]:
    return service.identity()


def model_dashboard_health(service: ModelDashboardService) -> dict[str, object]:
    return service.health()


def model_dashboard_comparison(service: ModelDashboardService) -> dict[str, object]:
    return service.comparison()


def model_dashboard_champion_challenger(service: ModelDashboardService) -> dict[str, object]:
    return service.champion_challenger()


def model_dashboard_selection(service: ModelDashboardService) -> dict[str, object]:
    return service.selection()


def model_dashboard_lifecycle(service: ModelDashboardService) -> dict[str, object]:
    return service.lifecycle()


def model_dashboard_rollout(service: ModelDashboardService) -> dict[str, object]:
    return service.rollout()


def model_dashboard_contract() -> dict[str, object]:
    return {
        "version": MODEL_DASHBOARD_VERSION,
        "boundary": MODEL_DASHBOARD_BOUNDARY,
        "read_only": True,
        "routes": (
            "/v1/model/summary",
            "/v1/model/identity",
            "/v1/model/health",
            "/v1/model/comparison",
            "/v1/model/champion-challenger",
            "/v1/model/selection",
            "/v1/model/lifecycle",
            "/v1/model/rollout",
        ),
    }


__all__ = [
    "MODEL_DASHBOARD_VERSION",
    "MODEL_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "ModelDashboardService",
    "model_dashboard_summary",
    "model_dashboard_identity",
    "model_dashboard_health",
    "model_dashboard_comparison",
    "model_dashboard_champion_challenger",
    "model_dashboard_selection",
    "model_dashboard_lifecycle",
    "model_dashboard_rollout",
    "model_dashboard_contract",
]
