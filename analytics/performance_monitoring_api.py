from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Mapping

from analytics.calibration_drift import (
    CalibrationDriftReport,
    calibration_drift_summary,
    validate_calibration_drift_report,
)
from analytics.concept_drift import ConceptDriftReport, concept_drift_summary, validate_concept_drift_report
from analytics.data_drift import DataDriftReport, data_drift_summary, validate_data_drift_report
from analytics.feature_drift import FeatureDriftReport, feature_drift_summary, validate_feature_drift_report
from analytics.model_drift import ModelDriftReport, model_drift_summary, validate_model_drift_report
from analytics.model_health import ModelHealthReport, model_health_summary, validate_model_health_report
from analytics.performance_degradation import (
    PerformanceDegradationReport,
    performance_degradation_summary,
    validate_performance_degradation_report,
)
from analytics.performance_monitoring import (
    PerformanceMonitoringReport,
    performance_monitoring_summary,
    validate_performance_monitoring_report,
)
from analytics.performance_over_time import (
    PerformanceOverTimeReport,
    performance_over_time_summary,
    validate_performance_over_time_report,
)
from analytics.prediction_distribution_monitoring import (
    PredictionDistributionMonitoringReport,
    prediction_distribution_monitoring_summary,
    validate_prediction_distribution_monitoring_report,
)
from analytics.ranking_drift import RankingDriftReport, ranking_drift_summary, validate_ranking_drift_report

PERFORMANCE_MONITORING_API_VERSION = "72.0.0"
VALID = "VALID"
INVALID = "INVALID"
MONITORING_AVAILABLE = "MONITORING_AVAILABLE"
MONITORING_UNAVAILABLE = "MONITORING_UNAVAILABLE"
MONITORING_BOUNDARY = "PERFORMANCE_MONITORING_API_BOUNDARY"

@dataclass(frozen=True)
class MonitoringReportEntry:
    name: str
    report: Any
    summary: Callable[[Any], Mapping[str, Any]]
    validate: Callable[[Any], Any]

@dataclass(frozen=True)
class MonitoringApiResult:
    status: str
    http_status: int
    payload: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

_REPORT_SPECS = {
    "performance": (PerformanceMonitoringReport, performance_monitoring_summary, validate_performance_monitoring_report),
    "performance_over_time": (PerformanceOverTimeReport, performance_over_time_summary, validate_performance_over_time_report),
    "performance_degradation": (PerformanceDegradationReport, performance_degradation_summary, validate_performance_degradation_report),
    "model_health": (ModelHealthReport, model_health_summary, validate_model_health_report),
    "model_drift": (ModelDriftReport, model_drift_summary, validate_model_drift_report),
    "data_drift": (DataDriftReport, data_drift_summary, validate_data_drift_report),
    "feature_drift": (FeatureDriftReport, feature_drift_summary, validate_feature_drift_report),
    "calibration_drift": (CalibrationDriftReport, calibration_drift_summary, validate_calibration_drift_report),
    "ranking_drift": (RankingDriftReport, ranking_drift_summary, validate_ranking_drift_report),
    "concept_drift": (ConceptDriftReport, concept_drift_summary, validate_concept_drift_report),
    "prediction_distribution": (PredictionDistributionMonitoringReport, prediction_distribution_monitoring_summary, validate_prediction_distribution_monitoring_report),
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return [_json_safe(v) for v in sorted(value, key=str)]
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return value


def _entry(name: str, report: Any) -> MonitoringReportEntry:
    if name not in _REPORT_SPECS:
        raise ValueError(f"unsupported monitoring report: {name}")
    report_type, summary, validate = _REPORT_SPECS[name]
    if not isinstance(report, report_type):
        raise TypeError(f"{name} must be {report_type.__name__}")
    return MonitoringReportEntry(name, report, summary, validate)


class PerformanceMonitoringApiService:
    def __init__(self, reports: Mapping[str, Any] | None = None) -> None:
        values = reports or {}
        normalized: dict[str, MonitoringReportEntry] = {}
        for name, report in values.items():
            normalized[name] = _entry(name, report)
        self._reports = dict(sorted(normalized.items()))

    @property
    def reports(self) -> tuple[str, ...]:
        return tuple(self._reports)

    def available(self, name: str) -> bool:
        return name in self._reports

    def summary(self) -> dict[str, Any]:
        return {
            "api_version": PERFORMANCE_MONITORING_API_VERSION,
            "boundary": MONITORING_BOUNDARY,
            "status": MONITORING_AVAILABLE if self._reports else MONITORING_UNAVAILABLE,
            "report_types": self.reports,
            "report_count": len(self._reports),
        }

    def get(self, name: str) -> MonitoringApiResult:
        entry = self._reports.get(name)
        if entry is None:
            return MonitoringApiResult(
                INVALID, 404,
                {"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": INVALID,
                 "error": {"code": "MONITORING_REPORT_NOT_FOUND", "message": "Monitoring report is not configured."}},
            )
        validation = entry.validate(entry.report)
        if not validation.is_valid:
            return MonitoringApiResult(
                INVALID, 503,
                {"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": INVALID,
                 "error": {"code": "MONITORING_REPORT_INVALID", "message": "Configured monitoring report failed validation.", "details": list(validation.issues)}},
            )
        payload = dict(entry.summary(entry.report))
        payload.update({"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": VALID,
                        "boundary": MONITORING_BOUNDARY, "report_type": name})
        return MonitoringApiResult(VALID, 200, _json_safe(payload))

    def all_reports(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in self.reports:
            item = self.get(name)
            if item.is_valid:
                result[name] = item.payload
        return result

    def health(self) -> dict[str, Any]:
        invalid = []
        for name, entry in self._reports.items():
            validation = entry.validate(entry.report)
            if not validation.is_valid:
                invalid.append(name)
        return {
            "api_version": PERFORMANCE_MONITORING_API_VERSION,
            "boundary": MONITORING_BOUNDARY,
            "status": "HEALTHY" if not invalid else "DEGRADED",
            "configured_report_count": len(self._reports),
            "valid_report_count": len(self._reports) - len(invalid),
            "invalid_reports": tuple(invalid),
        }


def create_monitoring_app(service: PerformanceMonitoringApiService, *, security_store=None, security_policy=None, required_scope="monitoring:read"):
    from flask import Flask, jsonify, request
    from analytics.api_security import AUTHORIZED, ApiCredentialStore, ApiSecurityPolicy, authorize

    if not isinstance(service, PerformanceMonitoringApiService):
        raise TypeError("service must be PerformanceMonitoringApiService")
    app = Flask(__name__)
    app.config["NEUROLYTICS_MONITORING_API_VERSION"] = PERFORMANCE_MONITORING_API_VERSION
    if security_store is not None and not isinstance(security_store, ApiCredentialStore):
        raise TypeError("security_store must be ApiCredentialStore")
    if security_policy is None:
        security_policy = ApiSecurityPolicy(enabled=False)
    if not isinstance(security_policy, ApiSecurityPolicy):
        raise TypeError("security_policy must be ApiSecurityPolicy")
    if not isinstance(required_scope, str) or not required_scope:
        raise ValueError("required_scope must be non-empty")

    @app.before_request
    def enforce_monitoring_authorization():
        if not security_policy.enabled or request.path == "/health":
            return None
        if not request.path.startswith("/v1/monitoring"):
            return None
        if security_store is None:
            return jsonify({"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": INVALID, "boundary": MONITORING_BOUNDARY, "error": {"code": "SECURITY_STORE_REQUIRED", "message": "Monitoring API security is enabled but no credential store was configured."}}), 503
        raw_key = request.headers.get(security_policy.credential_header, "")
        decision = authorize(security_store.verify(raw_key), required_scope)
        if decision.status == AUTHORIZED:
            return None
        status_code = 401 if decision.code in {"MISSING_CREDENTIAL", "INVALID_CREDENTIAL"} else 403
        return jsonify({"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": INVALID, "boundary": MONITORING_BOUNDARY, "error": {"code": decision.code, "message": decision.message}}), status_code

    @app.get("/health")
    def health():
        return jsonify(service.health()), 200

    @app.get("/v1/monitoring/summary")
    def summary():
        return jsonify(service.summary()), 200

    @app.get("/v1/monitoring")
    def all_monitoring():
        return jsonify(_json_safe({"api_version": PERFORMANCE_MONITORING_API_VERSION,
                                   "status": VALID, "boundary": MONITORING_BOUNDARY,
                                   "reports": service.all_reports()})), 200

    @app.get("/v1/monitoring/<name>")
    def monitoring_report(name: str):
        result = service.get(name)
        return jsonify(result.payload), result.http_status

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"api_version": PERFORMANCE_MONITORING_API_VERSION, "status": INVALID,
                        "error": {"code": "NOT_FOUND", "message": "Monitoring API route was not found."}}), 404

    return app


def monitoring_api_summary(service: PerformanceMonitoringApiService) -> dict[str, Any]:
    if not isinstance(service, PerformanceMonitoringApiService):
        raise TypeError("service must be PerformanceMonitoringApiService")
    return service.summary()


__all__ = [
    "PERFORMANCE_MONITORING_API_VERSION", "VALID", "INVALID",
    "MONITORING_AVAILABLE", "MONITORING_UNAVAILABLE", "MONITORING_BOUNDARY",
    "MonitoringReportEntry", "MonitoringApiResult", "PerformanceMonitoringApiService",
    "create_monitoring_app", "monitoring_api_summary",
]
