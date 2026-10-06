from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from typing import Any

from analytics.calibration_drift import (
    CalibrationDriftReport,
    calibration_drift_summary,
    validate_calibration_drift_report,
)
from analytics.concept_drift import (
    ConceptDriftReport,
    concept_drift_summary,
    validate_concept_drift_report,
)
from analytics.data_drift import (
    DataDriftReport,
    data_drift_summary,
    validate_data_drift_report,
)
from analytics.feature_drift import (
    FeatureDriftReport,
    feature_drift_summary,
    validate_feature_drift_report,
)
from analytics.model_drift import (
    ModelDriftReport,
    model_drift_summary,
    validate_model_drift_report,
)
from analytics.ranking_drift import (
    RankingDriftReport,
    ranking_drift_summary,
    validate_ranking_drift_report,
)

DRIFT_DASHBOARD_VERSION = "84.0.0"
DRIFT_DASHBOARD_BOUNDARY = "DRIFT_MONITORING_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"

_REPORTS = (
    "data",
    "model",
    "calibration",
    "ranking",
    "feature",
    "concept",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return tuple(_json_value(item) for item in value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class DriftMonitoringDashboardService:
    """Read-only dashboard projection of Phases 49, 50, 52-55 drift reports."""

    data_report: DataDriftReport | None = None
    model_report: ModelDriftReport | None = None
    calibration_report: CalibrationDriftReport | None = None
    ranking_report: RankingDriftReport | None = None
    feature_report: FeatureDriftReport | None = None
    concept_report: ConceptDriftReport | None = None
    max_observations: int = 500

    def _report_map(self) -> dict[str, object | None]:
        return {
            "data": self.data_report,
            "model": self.model_report,
            "calibration": self.calibration_report,
            "ranking": self.ranking_report,
            "feature": self.feature_report,
            "concept": self.concept_report,
        }

    def _state(self, name: str) -> dict[str, object]:
        report = self._report_map()[name]
        if report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        return {
            "status": AVAILABLE if getattr(report, "report_identity", "") else INVALID,
            "report_identity": getattr(report, "report_identity", ""),
            "version": getattr(report, "version", ""),
        }

    def _summary(self, name: str) -> dict[str, object]:
        report = self._report_map()[name]
        state = self._state(name)
        if report is None:
            return state
        summary_fn = {
            "data": data_drift_summary,
            "model": model_drift_summary,
            "calibration": calibration_drift_summary,
            "ranking": ranking_drift_summary,
            "feature": feature_drift_summary,
            "concept": concept_drift_summary,
        }[name]
        result = _json_value(summary_fn(report))
        result["dashboard_status"] = state["status"]
        return result

    def _validation(self, name: str) -> dict[str, object]:
        report = self._report_map()[name]
        if report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        validation_fn = {
            "data": validate_data_drift_report,
            "model": validate_model_drift_report,
            "calibration": validate_calibration_drift_report,
            "ranking": validate_ranking_drift_report,
            "feature": validate_feature_drift_report,
            "concept": validate_concept_drift_report,
        }[name]
        result = validation_fn(report)
        return {
            "status": result.status,
            "issues": tuple(result.issues),
            "is_valid": result.is_valid,
        }
    def observations(self, name: str) -> dict[str, object]:
        if name not in _REPORTS:
            raise ValueError("unknown drift report: " + name)
        report = self._report_map()[name]
        state = self._state(name)
        if report is None:
            return state

        values = getattr(report, "observations", ())
        limit = min(max(int(self.max_observations), 1), 2000)
        rows = tuple(_json_value(item) for item in values[:limit])
        validation = self._validation(name)
        return {
            "status": validation["status"],
            "report_identity": report.report_identity,
            "observation_count": len(values),
            "returned_observations": len(rows),
            "observations": rows,
        }

    def summary(self) -> dict[str, object]:
        sections = {name: self._summary(name) for name in _REPORTS}
        attached = sum(
            1 for name in _REPORTS if sections[name].get("dashboard_status") == AVAILABLE
            or sections[name].get("status") == AVAILABLE
        )
        drifted = tuple(
            name for name in _REPORTS
            if sections[name].get("drifted") is True
        )
        return {
            "status": VALID,
            "version": DRIFT_DASHBOARD_VERSION,
            "boundary": DRIFT_DASHBOARD_BOUNDARY,
            "read_only": True,
            "section_count": len(_REPORTS),
            "available_sections": attached,
            "drifted_sections": drifted,
            "drift_detected": bool(drifted),
            "sections": sections,
        }

    def overview(self) -> dict[str, object]:
        summary = self.summary()
        return {
            "status": summary["status"],
            "version": DRIFT_DASHBOARD_VERSION,
            "boundary": DRIFT_DASHBOARD_BOUNDARY,
            "read_only": True,
            "section_count": summary["section_count"],
            "available_sections": summary["available_sections"],
            "drifted_sections": summary["drifted_sections"],
            "drift_detected": summary["drift_detected"],
            "sections": {
                name: self._summary(name)
                for name in _REPORTS
            },
        }

    def section(self, name: str) -> dict[str, object]:
        if name not in _REPORTS:
            raise ValueError("unknown drift report: " + name)
        return {
            "summary": self._summary(name),
            "validation": self._validation(name),
            "observations": self.observations(name),
        }

    def dashboard(self) -> dict[str, object]:
        return {
            "status": VALID,
            "summary": self.summary(),
            "overview": self.overview(),
            "sections": {
                name: self.section(name)
                for name in _REPORTS
            },
        }


def drift_dashboard_summary(service: DriftMonitoringDashboardService) -> dict[str, object]:
    return service.summary()


def drift_dashboard_overview(service: DriftMonitoringDashboardService) -> dict[str, object]:
    return service.overview()


def drift_dashboard_section(
    service: DriftMonitoringDashboardService,
    name: str,
) -> dict[str, object]:
    return service.section(name)


def drift_dashboard_observations(
    service: DriftMonitoringDashboardService,
    name: str,
) -> dict[str, object]:
    return service.observations(name)


def drift_dashboard_contract() -> dict[str, object]:
    return {
        "version": DRIFT_DASHBOARD_VERSION,
        "boundary": DRIFT_DASHBOARD_BOUNDARY,
        "read_only": True,
        "sections": _REPORTS,
        "routes": (
            "/v1/drift/summary",
            "/v1/drift/overview",
            "/v1/drift/<name>",
            "/v1/drift/<name>/observations",
        ),
    }


__all__ = [
    "DRIFT_DASHBOARD_VERSION",
    "DRIFT_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "DriftMonitoringDashboardService",
    "drift_dashboard_summary",
    "drift_dashboard_overview",
    "drift_dashboard_section",
    "drift_dashboard_observations",
    "drift_dashboard_contract",
]
