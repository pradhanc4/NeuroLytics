from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from flask import Flask, jsonify, request, render_template, send_from_directory
from pathlib import Path
import threading
from jinja2 import FileSystemLoader

from analytics.api_rate_limit import (
    RATE_LIMITED,
    ApiRateLimitPolicy,
    ApiRateLimiter,
    rate_limit_headers,
    validate_rate_limit_policy,
)
from analytics.admin_dashboard import AdminDashboardService, admin_dashboard_contract, admin_dashboard_summary
from analytics.api_security import (
    AUTHORIZED,
    ApiCredentialStore,
    ApiSecurityPolicy,
    authorize,
    validate_security_policy,
)
from analytics.performance_monitoring_api import (
    PerformanceMonitoringApiService,
)
from analytics.production_api import (
    API_ACCEPTED,
    API_HEALTHY,
    API_READY,
    API_REJECTED,
    InferenceApiService,
)
from analytics.historical_dashboard import (
    HistoricalDashboardService,
    HISTORICAL_DASHBOARD_VERSION,
    HISTORICAL_DASHBOARD_BOUNDARY,
)
from analytics.analytics_dashboard import AnalyticsDashboardService
from analytics.drift_dashboard import (
    DriftMonitoringDashboardService,
    drift_dashboard_summary,
    drift_dashboard_overview,
    drift_dashboard_section,
    drift_dashboard_observations,
)
from analytics.performance_dashboard import (
    PerformanceOverTimeDashboardService,
    performance_dashboard_summary,
    performance_dashboard_periods,
    performance_dashboard_trends,
    performance_dashboard_hit_rates,
    performance_dashboard_metrics,
)
from analytics.top_k_dashboard import (
    TopKDashboardService,
    top_k_dashboard_summary,
    top_k_dashboard_metrics,
    top_k_dashboard_rows,
    top_k_dashboard_hit_rate,
    top_k_dashboard_rank_distribution,
    top_k_dashboard_coverage,
)
from analytics.ranking_dashboard import (
    RankingDashboardService,
    ranking_dashboard_summary,
    ranking_dashboard_panel,
    ranking_dashboard_jodi,
    ranking_dashboard_top_k,
    ranking_dashboard_actual_vs_ranked,
    ranking_dashboard_performance,
)
from analytics.live_ranking_reports import get_validation_ranking_reports
from analytics.model_health_dashboard import (
    ModelHealthDashboardService,
    model_health_dashboard_summary,
    model_health_dashboard_scorecard,
    model_health_dashboard_components,
    model_health_dashboard_thresholds,
    model_health_dashboard_lineage,
    model_health_dashboard_validation,
)
from analytics.model_dashboard import (
    ModelDashboardService,
    model_dashboard_summary,
    model_dashboard_identity,
    model_dashboard_health,
    model_dashboard_comparison,
    model_dashboard_champion_challenger,
    model_dashboard_selection,
    model_dashboard_lifecycle,
    model_dashboard_rollout,
)
from database.engine import SessionLocal
from database.models import Market
from database.services import HistoricalResultService
from analytics.manual_retraining import retrain_models, training_status
from analytics.sequential_prediction import train_sequential_models, load_status as sequential_training_status, predict_stage_2
from analytics.rowwise_training_audit import load_rowwise_training_audit, build_rowwise_training_audit
from analytics.production_hierarchical_prediction import predict_production_hierarchical
from analytics.reproducibility_audit import run_reproducibility_audit, reproducibility_summary
from analytics.data_integrity_audit import run_data_integrity_audit, data_integrity_summary
from analytics.temporal_safety_audit import run_temporal_safety_audit, temporal_safety_summary
from analytics.performance_scalability_audit import run_performance_scalability_audit, performance_scalability_summary
from analytics.failure_recovery import (
    run_failure_recovery_audit,
    failure_recovery_summary,
    recovery_status,
)
from analytics.security_audit import audit_security_contract, security_audit_summary
from analytics.production_readiness_audit import run_production_readiness_audit, production_readiness_summary
from analytics.production_release import run_production_release_audit, production_release_summary, release_gate
from analytics.system_orchestrator import NeuroLyticsSystem
from analytics.live_activity import live_activity
from database.models import PredictionFeedback, SequentialPredictionStage

from analytics.production_serving import (
    READY as SERVING_READY,
    validate_serving_plan,
)

PRODUCTION_SERVICE_VERSION = "76.0.0"
PRODUCTION_SERVICE_BOUNDARY = "PRODUCTION_SERVICE_INTEGRATION_BOUNDARY"

SERVICE_CREATED = "CREATED"
SERVICE_STARTING = "STARTING"
SERVICE_RUNNING = "RUNNING"
SERVICE_STOPPED = "STOPPED"
SERVICE_FAILED = "FAILED"

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class ProductionServicePolicy:
    require_inference_ready: bool = True
    require_monitoring_healthy: bool = True
    require_shared_security: bool = True
    require_shared_rate_limiter: bool = True

    def validate(self) -> None:
        for value in (
            self.require_inference_ready,
            self.require_monitoring_healthy,
            self.require_shared_security,
            self.require_shared_rate_limiter,
        ):
            if not isinstance(value, bool):
                raise ValueError("production service policy fields must be boolean")


@dataclass(frozen=True)
class ProductionDependency:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ProductionServiceResult:
    status: str
    http_status: int
    payload: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


class NeuroLyticsProductionService:
    """Composition/lifecycle boundary for the existing production services.

    This class does not replace serving, inference API, monitoring API,
    authentication, or rate limiting. It coordinates their startup,
    readiness, health, and shared production contract.
    """

    def __init__(
        self,
        inference_service: InferenceApiService,
        monitoring_service: PerformanceMonitoringApiService,
        *,
        security_store: ApiCredentialStore | None = None,
        security_policy: ApiSecurityPolicy | None = None,
        rate_limit_policy: ApiRateLimitPolicy | None = None,
        rate_limiter: ApiRateLimiter | None = None,
        policy: ProductionServicePolicy = ProductionServicePolicy(),
    ) -> None:
        if not isinstance(inference_service, InferenceApiService):
            raise TypeError("inference_service must be InferenceApiService")
        if not isinstance(monitoring_service, PerformanceMonitoringApiService):
            raise TypeError("monitoring_service must be PerformanceMonitoringApiService")

        policy.validate()
        security = security_policy or ApiSecurityPolicy(enabled=False)
        limits = rate_limit_policy or ApiRateLimitPolicy(enabled=False)
        validate_security_policy(security)
        validate_rate_limit_policy(limits)

        if security_store is None:
            security_store = ApiCredentialStore()

        if not isinstance(security_store, ApiCredentialStore):
            raise TypeError("security_store must be ApiCredentialStore")

        if not isinstance(rate_limiter, ApiRateLimiter):
            rate_limiter = ApiRateLimiter(limits)
        elif rate_limiter.policy != limits:
            raise ValueError("rate_limiter policy does not match rate_limit_policy")

        self._inference = inference_service
        self._monitoring = monitoring_service
        self._security_store = security_store
        self._security_policy = security
        self._rate_limit_policy = limits
        self._rate_limiter = rate_limiter
        self._policy = policy
        self._state = SERVICE_CREATED
        self._startup_issues: tuple[str, ...] = ()

    @property
    def state(self) -> str:
        return self._state

    @property
    def inference_service(self) -> InferenceApiService:
        return self._inference

    @property
    def monitoring_service(self) -> PerformanceMonitoringApiService:
        return self._monitoring

    @property
    def security_store(self) -> ApiCredentialStore:
        return self._security_store

    @property
    def security_policy(self) -> ApiSecurityPolicy:
        return self._security_policy

    @property
    def rate_limit_policy(self) -> ApiRateLimitPolicy:
        return self._rate_limit_policy

    @property
    def rate_limiter(self) -> ApiRateLimiter:
        return self._rate_limiter

    @property
    def policy(self) -> ProductionServicePolicy:
        return self._policy

    @property
    def startup_issues(self) -> tuple[str, ...]:
        return self._startup_issues

    def dependencies(self) -> tuple[ProductionDependency, ...]:
        serving = validate_serving_plan(self._inference.serving_plan)
        monitoring = self._monitoring.health()

        return (
            ProductionDependency(
                "production_serving",
                "READY" if serving.is_valid and self._inference.serving_plan.serving_state == SERVING_READY else "NOT_READY",
                "Phase 68 serving plan validation",
            ),
            ProductionDependency(
                "inference_api",
                "READY" if self._inference.readiness().is_valid else "NOT_READY",
                "Phase 69 inference API readiness",
            ),
            ProductionDependency(
                "monitoring_api",
                "READY" if monitoring["status"] == "HEALTHY" else "DEGRADED",
                "Phase 72 monitoring API health",
            ),
            ProductionDependency(
                "security",
                "ENABLED" if self._security_policy.enabled else "DISABLED",
                "Phase 70/73 shared security policy",
            ),
            ProductionDependency(
                "rate_limiter",
                "ENABLED" if self._rate_limit_policy.enabled else "DISABLED",
                "Phase 71 shared rate limiter",
            ),
        )

    def _validate_startup(self) -> tuple[str, ...]:
        issues: list[str] = []
        serving = validate_serving_plan(self._inference.serving_plan)
        if not serving.is_valid:
            issues.extend("SERVING:" + issue for issue in serving.issues)

        if self._policy.require_inference_ready and not self._inference.readiness().is_valid:
            issues.append("INFERENCE_API_NOT_READY")

        monitoring_health = self._monitoring.health()
        if self._policy.require_monitoring_healthy and monitoring_health["status"] != "HEALTHY":
            issues.append("MONITORING_API_NOT_HEALTHY")

        if self._policy.require_shared_security and not isinstance(
            self._security_store, ApiCredentialStore
        ):
            issues.append("SECURITY_STORE_INVALID")

        if self._policy.require_shared_rate_limiter and not isinstance(
            self._rate_limiter, ApiRateLimiter
        ):
            issues.append("RATE_LIMITER_INVALID")

        return tuple(sorted(set(issues)))

    def startup(self) -> ProductionServiceResult:
        if self._state == SERVICE_RUNNING:
            return ProductionServiceResult(VALID, 200, self.health())

        self._state = SERVICE_STARTING
        issues = self._validate_startup()
        self._startup_issues = issues

        if issues:
            self._state = SERVICE_FAILED
            return ProductionServiceResult(
                INVALID,
                503,
                {
                    "service_version": PRODUCTION_SERVICE_VERSION,
                    "boundary": PRODUCTION_SERVICE_BOUNDARY,
                    "status": SERVICE_FAILED,
                    "error": {
                        "code": "PRODUCTION_SERVICE_STARTUP_FAILED",
                        "message": "Production service dependencies are not ready.",
                        "details": list(issues),
                    },
                },
            )

        self._state = SERVICE_RUNNING
        return ProductionServiceResult(VALID, 200, self.health())

    def shutdown(self) -> ProductionServiceResult:
        if self._state == SERVICE_STOPPED:
            return ProductionServiceResult(VALID, 200, self.health())
        self._state = SERVICE_STOPPED
        return ProductionServiceResult(VALID, 200, self.health())

    def health(self) -> dict[str, Any]:
        dependencies = self.dependencies()
        failed = tuple(
            dependency.name
            for dependency in dependencies
            if dependency.status in {"NOT_READY", "DEGRADED"}
        )
        return {
            "service_version": PRODUCTION_SERVICE_VERSION,
            "boundary": PRODUCTION_SERVICE_BOUNDARY,
            "status": "HEALTHY" if not failed else "DEGRADED",
            "service_state": self._state,
            "dependencies": tuple(
                {
                    "name": dependency.name,
                    "status": dependency.status,
                    "detail": dependency.detail,
                }
                for dependency in dependencies
            ),
            "failed_dependencies": failed,
            "serving_id": self._inference.serving_plan.serving_id,
            "model_identity": self._inference.serving_plan.model_identity,
            "model_version": self._inference.serving_plan.model_version,
            "artifact_identity": self._inference.serving_plan.artifact_identity,
        }

    def readiness(self) -> ProductionServiceResult:
        if self._state != SERVICE_RUNNING:
            return ProductionServiceResult(
                INVALID,
                503,
                {
                    "service_version": PRODUCTION_SERVICE_VERSION,
                    "boundary": PRODUCTION_SERVICE_BOUNDARY,
                    "status": SERVICE_FAILED,
                    "error": {
                        "code": "PRODUCTION_SERVICE_NOT_RUNNING",
                        "message": "Production service has not reached RUNNING state.",
                    },
                },
            )

        issues = self._validate_startup()
        if issues:
            self._startup_issues = issues
            self._state = SERVICE_FAILED
            return ProductionServiceResult(
                INVALID,
                503,
                {
                    "service_version": PRODUCTION_SERVICE_VERSION,
                    "boundary": PRODUCTION_SERVICE_BOUNDARY,
                    "status": SERVICE_FAILED,
                    "error": {
                        "code": "PRODUCTION_SERVICE_NOT_READY",
                        "message": "A production dependency is no longer ready.",
                        "details": list(issues),
                    },
                },
            )

        return ProductionServiceResult(
            VALID,
            200,
            {
                "service_version": PRODUCTION_SERVICE_VERSION,
                "boundary": PRODUCTION_SERVICE_BOUNDARY,
                "status": SERVICE_RUNNING,
                "readiness": "READY",
                "serving_id": self._inference.serving_plan.serving_id,
            },
        )

    def infer(self, payload: Mapping[str, Any]) -> ProductionServiceResult:
        readiness = self.readiness()
        if not readiness.is_valid:
            return readiness
        result = self._inference.infer(payload)
        return ProductionServiceResult(
            VALID if result.is_valid else INVALID,
            result.http_status,
            result.payload,
        )

    def monitoring(self, name: str) -> ProductionServiceResult:
        readiness = self.readiness()
        if not readiness.is_valid:
            return readiness
        result = self._monitoring.get(name)
        return ProductionServiceResult(
            VALID if result.is_valid else INVALID,
            result.http_status,
            result.payload,
        )


def _security_failure(decision) -> tuple[dict[str, Any], int]:
    status = 401 if decision.code in {"MISSING_CREDENTIAL", "INVALID_CREDENTIAL"} else 403
    return (
        {
            "service_version": PRODUCTION_SERVICE_VERSION,
            "boundary": PRODUCTION_SERVICE_BOUNDARY,
            "status": INVALID,
            "error": {
                "code": decision.code,
                "message": decision.message,
            },
        },
        status,
    )


def create_production_app(
    service: NeuroLyticsProductionService,
    *,
    inference_scope: str = "inference:read",
    monitoring_scope: str = "monitoring:read",
    historical_scope: str = "historical:read",
    analytics_scope: str = "analytics:read",
    ranking_scope: str = "ranking:read",
    top_k_scope: str = "top-k:read",
    performance_scope: str = "performance:read",
    drift_scope: str = "drift:read",
    model_health_scope: str = "model-health:read",
    admin_scope: str = "admin:read",
) -> Flask:
    if not isinstance(service, NeuroLyticsProductionService):
        raise TypeError("service must be NeuroLyticsProductionService")
    if not isinstance(inference_scope, str) or not inference_scope.strip():
        raise ValueError("inference_scope must be non-empty")
    if not isinstance(monitoring_scope, str) or not monitoring_scope.strip():
        raise ValueError("monitoring_scope must be non-empty")
    if not isinstance(historical_scope, str) or not historical_scope.strip():
        raise ValueError("historical_scope must be non-empty")
    if not isinstance(analytics_scope, str) or not analytics_scope.strip():
        raise ValueError("analytics_scope must be non-empty")
    if not isinstance(ranking_scope, str) or not ranking_scope.strip():
        raise ValueError("ranking_scope must be non-empty")
    if not isinstance(top_k_scope, str) or not top_k_scope.strip():
        raise ValueError("top_k_scope must be non-empty")
    if not isinstance(performance_scope, str) or not performance_scope.strip():
        raise ValueError("performance_scope must be non-empty")
    if not isinstance(drift_scope, str) or not drift_scope.strip():
        raise ValueError("drift_scope must be non-empty")
    if not isinstance(model_health_scope, str) or not model_health_scope.strip():
        raise ValueError("model_health_scope must be non-empty")
    if not isinstance(admin_scope, str) or not admin_scope.strip():
        raise ValueError("admin_scope must be non-empty")

    app = Flask(__name__)
    system = NeuroLyticsSystem()
    app.config["NEUROLYTICS_SYSTEM"] = system
    app.config["NEUROLYTICS_PRODUCTION_SERVICE_VERSION"] = PRODUCTION_SERVICE_VERSION
    app.config["NEUROLYTICS_PRODUCTION_SERVICE_BOUNDARY"] = PRODUCTION_SERVICE_BOUNDARY
    frontend_root = Path(__file__).resolve().parent.parent / "frontend"
    app.jinja_loader = FileSystemLoader(str(frontend_root / "templates"))
    app.config["NEUROLYTICS_FRONTEND_VERSION"] = "77.0.0"
    app.config["NEUROLYTICS_FRONTEND_BOUNDARY"] = "FRONTEND_FOUNDATION_BOUNDARY"

    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def frontend_index():
        return render_template("index.html")

    @app.get("/frontend/static/<path:filename>")
    def frontend_static(filename: str):
        return send_from_directory(frontend_root / "static", filename)

    @app.get("/frontend/config")
    def frontend_config():
        return jsonify({
            "version": "77.0.0",
            "boundary": "FRONTEND_FOUNDATION_BOUNDARY",
            "api_base": "",
            "routes": {
                "health": "/health",
                "readiness": "/ready",
                "inference": "/v1/inference",
                "monitoring_summary": "/v1/monitoring/summary",
                "monitoring_report": "/v1/monitoring/<name>",
                "model_summary": "/v1/model/summary",
                "model_identity": "/v1/model/identity",
                "model_health": "/v1/model/health",
                "model_comparison": "/v1/model/comparison",
                "model_champion_challenger": "/v1/model/champion-challenger",
                "model_selection": "/v1/model/selection",
                "model_lifecycle": "/v1/model/lifecycle",
                "model_rollout": "/v1/model/rollout",
                "ranking_summary": "/v1/ranking/summary",
                "ranking_panel": "/v1/ranking/panel",
                "ranking_jodi": "/v1/ranking/jodi",
                "ranking_top_k": "/v1/ranking/top-k",
                "ranking_actual_vs_ranked": "/v1/ranking/actual-vs-ranked",
                "ranking_performance": "/v1/ranking/performance",
                "top_k_summary": "/v1/top-k/summary",
                "top_k_metrics": "/v1/top-k/metrics",
                "top_k_rows": "/v1/top-k/rows",
                "top_k_hit_rate": "/v1/top-k/hit-rate",
                "top_k_rank_distribution": "/v1/top-k/rank-distribution",
                "top_k_coverage": "/v1/top-k/coverage",
                "performance_summary": "/v1/performance/summary",
                "performance_periods": "/v1/performance/periods",
                "performance_trends": "/v1/performance/trends",
                "performance_hit_rates": "/v1/performance/hit-rates",
                "performance_metrics": "/v1/performance/metrics",
                "drift_summary": "/v1/drift/summary",
                "drift_overview": "/v1/drift/overview",
                "drift_section": "/v1/drift/<name>",
                "drift_observations": "/v1/drift/<name>/observations",
                "model_health_summary": "/v1/model-health/summary",
                "model_health_scorecard": "/v1/model-health/scorecard",
                "model_health_components": "/v1/model-health/components",
                "model_health_thresholds": "/v1/model-health/thresholds",
                "model_health_lineage": "/v1/model-health/lineage",
                "model_health_validation": "/v1/model-health/validation",
                "admin_summary": "/v1/admin/summary",
                "admin_service": "/v1/admin/service",
                "admin_security": "/v1/admin/security",
                "admin_rate_limit": "/v1/admin/rate-limit",
                "admin_policy": "/v1/admin/policy",
                "admin_serving": "/v1/admin/serving",
                "admin_dependencies": "/v1/admin/dependencies",
                "admin_scopes": "/v1/admin/scopes",
                "admin_temporal_safety": "/v1/admin/temporal-safety",
                "admin_performance_scalability": "/v1/admin/performance-scalability",
                "admin_production_readiness": "/v1/admin/production-readiness",
                "admin_production_release": "/v1/admin/production-release",
            },
        })

    admin_service = AdminDashboardService(service)
    configured_scopes = {"inference": inference_scope, "monitoring": monitoring_scope, "historical": historical_scope, "analytics": analytics_scope, "ranking": ranking_scope, "top_k": top_k_scope, "performance": performance_scope, "drift": drift_scope, "model_health": model_health_scope, "admin": admin_scope}

    excel_run_lock = threading.Lock()
    excel_run_state: dict[str, Any] = {
        "status": "IDLE",
        "result": None,
        "error": None,
    }
    excel_import_lock = threading.Lock()
    excel_import_run_state: dict[str, Any] = {
        "status": "IDLE",
        "result": None,
        "error": None,
    }

    @app.get("/v1/live/status")
    def live_status():
        """Return the current live processing state and bounded event history."""
        return jsonify(live_activity.snapshot())

    @app.get("/v1/live/events")
    def live_events():
        """Return live events after an optional sequence number."""
        raw_sequence = request.args.get("since", "0")
        try:
            sequence = int(raw_sequence)
        except (TypeError, ValueError):
            return jsonify({"status": INVALID, "error": {"code": "LIVE_SEQUENCE_INVALID", "message": "since must be a non-negative integer."}}), 400
        try:
            return jsonify(live_activity.events_since(sequence))
        except ValueError as exc:
            return jsonify({"status": INVALID, "error": {"code": "LIVE_SEQUENCE_INVALID", "message": str(exc)}}), 400

    @app.get("/v1/historical/excel-sequential/status")
    def excel_sequential_status():
        """Return the in-process Excel sequential worker status."""
        return jsonify(excel_run_state), 200

    @app.get("/v1/historical/excel-import/status")
    def excel_import_status():
        """Return the Excel -> database-only importer status."""
        return jsonify(excel_import_run_state), 200

    @app.post("/v1/historical/excel-import/start")
    def excel_import_start():
        """Start Excel ingestion only; no prediction, ML, feedback, or retraining."""
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited

        with excel_import_lock:
            if excel_import_run_state["status"] == "RUNNING":
                return jsonify({
                    "status": "RUNNING",
                    "message": "Excel database import is already running.",
                }), 409, rate_limit_headers(limited)

            payload = request.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                return jsonify({
                    "status": INVALID,
                    "error": {"code": "INVALID_JSON", "message": "Request body must be a JSON object."},
                }), 400, rate_limit_headers(limited)

            from scripts.import_excel_database import (
                DEFAULT_CHECKPOINT,
                DEFAULT_EXCEL,
                DEFAULT_MARKET,
                DEFAULT_SHEET,
                import_excel,
            )

            excel_path = Path(payload.get("excel", DEFAULT_EXCEL))
            checkpoint_path = Path(payload.get("checkpoint", DEFAULT_CHECKPOINT))
            market_name = str(payload.get("market", DEFAULT_MARKET))
            sheet_name = str(payload.get("sheet", DEFAULT_SHEET))
            start_row = payload.get("start_row")
            limit = payload.get("limit")
            if start_row is not None:
                start_row = int(start_row)
            if limit is not None:
                limit = int(limit)

            excel_import_run_state.update({"status": "RUNNING", "result": None, "error": None})

            def importer_worker() -> None:
                try:
                    result = import_excel(
                        excel_path,
                        market_name=market_name,
                        checkpoint_path=checkpoint_path,
                        sheet_name=sheet_name,
                        start_row=start_row,
                        limit=limit,
                        dry_run=False,
                    )
                    excel_import_run_state.update({
                        "status": "COMPLETED",
                        "result": result,
                        "error": None,
                    })
                except Exception as exc:
                    excel_import_run_state.update({
                        "status": "FAILED",
                        "result": None,
                        "error": str(exc),
                    })
                    live_activity.emit(
                        "Excel database import failed",
                        status="FAILED",
                        source="EXCEL_DATABASE_IMPORT",
                        stage="DATABASE_IMPORT",
                        operation="Excel database import failed",
                        error=str(exc),
                    )

            threading.Thread(
                target=importer_worker,
                name="neurolytics-excel-database-import",
                daemon=True,
            ).start()
            return jsonify({
                "status": "STARTED",
                "message": "Excel database import started. ML and prediction are disabled for this operation.",
                "excel": str(excel_path),
                "checkpoint": str(checkpoint_path),
                "market": market_name,
                "limit": limit,
                "ml_executed": False,
            }), 202, rate_limit_headers(limited)

    @app.post("/v1/historical/excel-sequential/start")
    def excel_sequential_start():
        """Start the real Excel sequential processor inside the Flask process.

        Running the worker in-process is intentional: it shares the same
        thread-safe live_activity instance used by the website, so every
        prediction/evaluation/retraining event is visible immediately.
        """
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited

        with excel_run_lock:
            if excel_run_state["status"] == "RUNNING":
                return jsonify({
                    "status": "RUNNING",
                    "message": "Excel sequential processing is already running.",
                }), 409, rate_limit_headers(limited)

            payload = request.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                return jsonify({"status": INVALID, "error": {"code": "INVALID_JSON", "message": "Request body must be a JSON object."}}), 400, rate_limit_headers(limited)

            from scripts.process_excel_sequential import (
                DEFAULT_CHECKPOINT,
                DEFAULT_EXCEL,
                DEFAULT_MARKET,
                process_excel,
            )

            excel_path = Path(payload.get("excel", DEFAULT_EXCEL))
            checkpoint_path = Path(payload.get("checkpoint", DEFAULT_CHECKPOINT))
            market_name = str(payload.get("market", DEFAULT_MARKET))
            start_row = payload.get("start_row")
            limit = payload.get("limit")
            if start_row is not None:
                start_row = int(start_row)
            if limit is not None:
                limit = int(limit)

            excel_run_state.update({"status": "RUNNING", "result": None, "error": None})

            def worker() -> None:
                try:
                    result = process_excel(
                        excel_path,
                        market_name=market_name,
                        checkpoint_path=checkpoint_path,
                        start_row=start_row,
                        limit=limit,
                        dry_run=False,
                    )
                    excel_run_state.update({"status": "COMPLETED", "result": result, "error": None})
                except Exception as exc:
                    excel_run_state.update({"status": "FAILED", "result": None, "error": str(exc)})
                    live_activity.emit(
                        "Sequential Excel processing failed",
                        status="FAILED",
                        source="EXCEL_SEQUENTIAL",
                        operation="Sequential Excel processing failed",
                        error=str(exc),
                    )

            threading.Thread(target=worker, name="neurolytics-excel-sequential", daemon=True).start()
            return jsonify({
                "status": "STARTED",
                "message": "Real sequential Excel processing started in the Flask process.",
                "excel": str(excel_path),
                "checkpoint": str(checkpoint_path),
                "market": market_name,
                "limit": limit,
            }), 202, rate_limit_headers(limited)

    @app.get("/v1/admin/summary")
    def admin_summary():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify({**admin_dashboard_summary(), "dashboard": admin_service.dashboard(configured_scopes)})

    @app.get("/v1/admin/reproducibility")
    def admin_reproducibility():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            report = run_reproducibility_audit(db)
            payload = reproducibility_summary(report)
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/data-integrity")
    def admin_data_integrity():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            report = run_data_integrity_audit(db)
            payload = data_integrity_summary(report)
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/performance-scalability")
    def admin_performance_scalability():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            report = run_performance_scalability_audit(db)
            payload = performance_scalability_summary(report)
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/temporal-safety")
    def admin_temporal_safety():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            report = run_temporal_safety_audit(db)
            payload = temporal_safety_summary(report)
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/service")
    def admin_service_state():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.service_state())

    @app.get("/v1/admin/security")
    def admin_security():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.security())

    @app.get("/v1/admin/rate-limit")
    def admin_rate_limit():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.rate_limit())

    @app.get("/v1/admin/policy")
    def admin_policy():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.production_policy())

    @app.get("/v1/admin/serving")
    def admin_serving():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.serving())

    @app.get("/v1/admin/dependencies")
    def admin_dependencies():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.dependencies())

    @app.get("/v1/admin/failure-recovery")
    def admin_failure_recovery():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(failure_recovery_summary(run_failure_recovery_audit())), 200

    @app.get("/v1/admin/recovery-status")
    def admin_recovery_status():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(recovery_status()), 200

    @app.get("/v1/admin/scopes")
    def admin_scopes():
        failure, status = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(failure), status
        return jsonify(admin_service.scopes(configured_scopes))

    def authorize_request(required_scope: str):
        policy = service.security_policy
        if not policy.enabled:
            return None, None
        raw_key = request.headers.get(policy.credential_header, "")
        decision = authorize(service.security_store.verify(raw_key), required_scope)
        if decision.status != AUTHORIZED:
            payload, status = _security_failure(decision)
            return payload, status
        return decision, None

    def rate_limit(decision):
        if decision is not None and decision.context is not None:
            identity = "credential:" + decision.context.credential_id
        else:
            identity = "ip:" + (request.remote_addr or "unknown")
        limit = service.rate_limiter.check(identity)
        if not limit.allowed:
            payload = {
                "service_version": PRODUCTION_SERVICE_VERSION,
                "boundary": PRODUCTION_SERVICE_BOUNDARY,
                "status": INVALID,
                "error": {
                    "code": "RATE_LIMIT_DENIED",
                    "message": "API request rate limit exceeded.",
                    "details": {"code": RATE_LIMITED},
                },
            }
            return jsonify(payload), 429, rate_limit_headers(limit)
        return limit

    @app.get("/health")
    def health():
        return jsonify(service.health()), 200

    @app.get("/ready")
    def ready():
        decision, failure = authorize_request(inference_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        result = service.readiness()
        return jsonify(result.payload), result.http_status, rate_limit_headers(limited)

    @app.get("/v1/system/status")
    def system_status():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(system.status()), 200, rate_limit_headers(limited)

    @app.get("/v1/system/pipeline")
    def system_pipeline():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify({
            "system": system.status()["system"],
            "version": system.version,
            "boundary": system.boundary,
            "frames": system.pipeline_status(),
        }), 200, rate_limit_headers(limited)

    @app.get("/v1/system/database")
    def system_database():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(system.database_snapshot()), 200, rate_limit_headers(limited)

    @app.post("/v1/inference")
    def inference():
        decision, failure = authorize_request(inference_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        if not request.is_json:
            return jsonify({
                "service_version": PRODUCTION_SERVICE_VERSION,
                "boundary": PRODUCTION_SERVICE_BOUNDARY,
                "status": INVALID,
                "error": {
                    "code": "CONTENT_TYPE_REQUIRED",
                    "message": "application/json is required.",
                },
            }), 415, rate_limit_headers(limited)
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({
                "service_version": PRODUCTION_SERVICE_VERSION,
                "boundary": PRODUCTION_SERVICE_BOUNDARY,
                "status": INVALID,
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body must contain valid JSON.",
                },
            }), 400, rate_limit_headers(limited)
        result = service.infer(payload)
        return jsonify(result.payload), result.http_status, rate_limit_headers(limited)

    @app.get("/v1/monitoring/summary")
    def monitoring_summary():
        decision, failure = authorize_request(monitoring_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        payload = service.monitoring_service.summary()
        return jsonify(payload), 200, rate_limit_headers(limited)

    def analytics_payload(method_name: str, market_id: int | None):
        db = SessionLocal()
        try:
            return getattr(AnalyticsDashboardService(db), method_name)(market_id)
        finally:
            db.close()

    @app.get("/v1/analytics/summary")
    def analytics_summary():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(analytics_payload("summary", request.args.get("market_id", type=int))), 200, rate_limit_headers(limited)

    @app.get("/v1/analytics/distribution")
    def analytics_distribution():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(analytics_payload("distribution", request.args.get("market_id", type=int))), 200, rate_limit_headers(limited)

    @app.get("/v1/analytics/columns")
    def analytics_columns():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(analytics_payload("column_statistics", request.args.get("market_id", type=int))), 200, rate_limit_headers(limited)

    @app.get("/v1/analytics/trends")
    def analytics_trends():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(analytics_payload("trends", request.args.get("market_id", type=int))), 200, rate_limit_headers(limited)

    @app.get("/v1/analytics/insights")
    def analytics_insights():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(analytics_payload("insights", request.args.get("market_id", type=int))), 200, rate_limit_headers(limited)

    def model_dashboard_payload(method):
        dashboard = ModelDashboardService(service.inference_service.serving_plan)
        return method(dashboard)

    @app.get("/v1/model/summary")
    def model_summary():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/retrain/status")
    def model_retrain_status():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(training_status()), 200, rate_limit_headers(limited)

    @app.post("/v1/model/retrain")
    def model_retrain():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            result = retrain_models()
            code = 200 if result.get("status") == "COMPLETED" else 400
            return jsonify(result), code, rate_limit_headers(limited)
        except Exception as exc:
            return jsonify({
                "status": INVALID,
                "error": {
                    "code": "MODEL_RETRAIN_FAILED",
                    "message": str(exc),
                },
            }), 500, rate_limit_headers(limited)

    @app.get("/v1/model/sequential/status")
    def model_sequential_status():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        return jsonify(sequential_training_status()), 200, rate_limit_headers(limited)

    @app.get("/v1/model/training-audit")
    def model_training_audit():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            force = request.args.get("force", "false").lower() == "true"
            payload = build_rowwise_training_audit(force=force)
            return jsonify(payload), 200, rate_limit_headers(limited)
        except Exception as exc:
            return jsonify({"status": INVALID, "error": {"code": "TRAINING_AUDIT_FAILED", "message": str(exc)}}), 500, rate_limit_headers(limited)
    @app.post("/v1/model/sequential/retrain")
    def model_sequential_retrain():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            result = train_sequential_models()
            code = 200 if result.get("status") == "COMPLETED" else 400
            return jsonify(result), code, rate_limit_headers(limited)
        except Exception as exc:
            return jsonify({
                "status": INVALID,
                "error": {"code": "SEQUENTIAL_RETRAIN_FAILED", "message": str(exc)},
            }), 500, rate_limit_headers(limited)

    @app.post("/v1/model/sequential/predict")
    def model_sequential_predict():
        decision, failure = authorize_request(inference_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            payload = request.get_json(silent=True) or {}
            raw_market_id = payload.get("market_id")
            market_id = None if raw_market_id in (None, "") else int(raw_market_id)
            market_name = str(payload.get("market_name", "")).strip() or None
            result = predict_stage_2(
                str(payload.get("open", "")).strip(),
                str(payload.get("jodi_first", "")).strip(),
                top_k=int(payload.get("top_k", 10)),
                market_id=market_id,
                market_name=market_name,
            )
            return jsonify(result), 200, rate_limit_headers(limited)
        except (ValueError, TypeError) as exc:
            return jsonify({
                "status": INVALID,
                "error": {"code": "SEQUENTIAL_PREDICTION_INVALID", "message": str(exc)},
            }), 400, rate_limit_headers(limited)

    @app.post("/v1/model/sequential/hierarchical-predict")
    def model_sequential_hierarchical_predict():
        decision, failure = authorize_request(inference_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            payload = request.get_json(silent=True) or {}
            raw_market_id = payload.get("market_id")
            market_id = None if raw_market_id in (None, "") else int(raw_market_id)
            market_name = str(payload.get("market_name", "")).strip() or None
            target_date = __import__("datetime").date.fromisoformat(str(payload["date"]))
            result = predict_production_hierarchical(
                open_result=str(payload.get("open", "")).strip(),
                target_date=target_date,
                market_id=market_id,
                market_name=market_name,
                top_k=int(payload.get("top_k", 10)),
            )
            return jsonify({
                "status": result.status,
                "version": result.version,
                "qualification": result.qualification,
                "target_date": result.target_date.isoformat(),
                "open": result.open_result,
                "selected_jodi": result.selected_jodi,
                "selected": __import__("dataclasses").asdict(result.selected) if result.selected else None,
                "candidates": [__import__("dataclasses").asdict(item) for item in result.candidates],
                "jodi_candidates": list(result.jodi_candidates),
                "operational_top_k": list(result.operational_top_k),
                "temporal_safe": result.temporal_safe,
                "family_constraints_enforced": result.family_constraints_enforced,
                "issues": list(result.issues),
                "integration_identity": result.integration_identity,
            }), 200, rate_limit_headers(limited)
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify({
                "status": INVALID,
                "error": {"code": "HIERARCHICAL_PREDICTION_INVALID", "message": str(exc)},
            }), 400, rate_limit_headers(limited)

    @app.post("/v1/model/feedback")
    def model_feedback():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            payload = request.get_json(silent=True) or {}
            stage = str(payload.get("stage", "")).strip()
            predicted = str(payload.get("predicted_value", "")).strip()
            actual = str(payload.get("actual_value", "")).strip() or None
            raw_correct = payload.get("is_correct")
            if isinstance(raw_correct, bool):
                is_correct = raw_correct
            elif str(raw_correct).strip().lower() in {"true", "1", "yes"}:
                is_correct = True
            elif str(raw_correct).strip().lower() in {"false", "0", "no"}:
                is_correct = False
            else:
                raise ValueError("is_correct must be a boolean.")
            if stage not in {"STAGE_1", "STAGE_2"}:
                raise ValueError("stage must be STAGE_1 or STAGE_2.")
            if not predicted:
                raise ValueError("predicted_value is required.")
            db = SessionLocal()
            try:
                market_id = payload.get("market_id")
                feedback = PredictionFeedback(
                    market_id=int(market_id) if market_id is not None else None,
                    result_date=__import__("datetime").date.fromisoformat(str(payload["date"])) if payload.get("date") else None,
                    stage=stage,
                    predicted_value=predicted,
                    actual_value=actual,
                    is_correct=is_correct,
                    model_identity=str(payload.get("model_identity", "")).strip() or None,
                    notes=str(payload.get("notes", "")).strip() or None,
                )
                db.add(feedback)
                db.commit()
            finally:
                db.close()
            live_activity.emit(
                "Prediction evaluated",
                status="RUNNING",
                stage=stage,
                operation="Comparing prediction with actual",
                prediction=predicted,
                actual=actual,
                result="CORRECT" if is_correct else "INCORRECT",
                total_predictions=live_activity.snapshot()["state"]["total_predictions"] + 1,
                correct_predictions=live_activity.snapshot()["state"]["correct_predictions"] + (1 if is_correct else 0),
                incorrect_predictions=live_activity.snapshot()["state"]["incorrect_predictions"] + (0 if is_correct else 1),
            )
            retraining = None
            if not is_correct:
                live_activity.emit(
                    "Prediction incorrect; retraining started",
                    stage=stage,
                    operation="Retraining sequential model",
                )
                retraining = train_sequential_models()
                live_activity.emit(
                    "Sequential model retraining completed",
                    stage=stage,
                    operation="Returning to next entry",
                    retraining_events=live_activity.snapshot()["state"]["retraining_events"] + 1,
                )
            live_activity.emit(
                "Entry evaluation completed",
                status="READY",
                stage=stage,
                operation="Ready for next entry",
                processed_entries=live_activity.snapshot()["state"]["processed_entries"] + 1,
            )
            return jsonify({
                "status": VALID,
                "message": "Prediction feedback recorded.",
                "retraining": retraining,
            }), 200, rate_limit_headers(limited)
        except (ValueError, TypeError) as exc:
            return jsonify({
                "status": INVALID,
                "error": {"code": "PREDICTION_FEEDBACK_INVALID", "message": str(exc)},
            }), 400, rate_limit_headers(limited)

    @app.get("/v1/model/identity")
    def model_identity():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_identity)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/health")
    def model_health():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_health)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/comparison")
    def model_comparison():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_comparison)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/champion-challenger")
    def model_champion_challenger():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_champion_challenger)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/selection")
    def model_selection():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_selection)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/lifecycle")
    def model_lifecycle():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_lifecycle)), 200, rate_limit_headers(limited)

    @app.get("/v1/model/rollout")
    def model_rollout():
        decision, failure = authorize_request(analytics_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_dashboard_payload(model_dashboard_rollout)), 200, rate_limit_headers(limited)

    def ranking_dashboard_payload(method):
        reports = get_validation_ranking_reports()
        if not reports:
            return method(RankingDashboardService())
        service = RankingDashboardService(
            panel_report=reports["panel"],
            jodi_report=reports["jodi"],
            top_k_report=reports["top_k"],
            actual_vs_ranked_report=reports["actual_vs_ranked"],
            performance_report=reports["performance"],
        )
        return method(service)

    @app.get("/v1/ranking/summary")
    def ranking_summary():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/ranking/panel")
    def ranking_panel():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_panel)), 200, rate_limit_headers(limited)

    @app.get("/v1/ranking/jodi")
    def ranking_jodi():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_jodi)), 200, rate_limit_headers(limited)

    @app.get("/v1/ranking/top-k")
    def ranking_top_k():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_top_k)), 200, rate_limit_headers(limited)

    @app.get("/v1/ranking/actual-vs-ranked")
    def ranking_actual_vs_ranked():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_actual_vs_ranked)), 200, rate_limit_headers(limited)

    @app.get("/v1/ranking/performance")
    def ranking_performance():
        decision, failure = authorize_request(ranking_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(ranking_dashboard_payload(ranking_dashboard_performance)), 200, rate_limit_headers(limited)

    def top_k_dashboard_payload(method):
        return method(TopKDashboardService())

    @app.get("/v1/top-k/summary")
    def top_k_summary_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/top-k/metrics")
    def top_k_metrics_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_metrics)), 200, rate_limit_headers(limited)

    @app.get("/v1/top-k/rows")
    def top_k_rows_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_rows)), 200, rate_limit_headers(limited)

    @app.get("/v1/top-k/hit-rate")
    def top_k_hit_rate_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_hit_rate)), 200, rate_limit_headers(limited)

    @app.get("/v1/top-k/rank-distribution")
    def top_k_rank_distribution_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_rank_distribution)), 200, rate_limit_headers(limited)

    @app.get("/v1/top-k/coverage")
    def top_k_coverage_route():
        decision, failure = authorize_request(top_k_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(top_k_dashboard_payload(top_k_dashboard_coverage)), 200, rate_limit_headers(limited)

    def performance_dashboard_payload(method):
        return method(PerformanceOverTimeDashboardService())

    @app.get("/v1/performance/summary")
    def performance_summary():
        decision, failure = authorize_request(performance_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(performance_dashboard_payload(performance_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/performance/periods")
    def performance_periods():
        decision, failure = authorize_request(performance_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(performance_dashboard_payload(performance_dashboard_periods)), 200, rate_limit_headers(limited)

    @app.get("/v1/performance/trends")
    def performance_trends():
        decision, failure = authorize_request(performance_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(performance_dashboard_payload(performance_dashboard_trends)), 200, rate_limit_headers(limited)

    @app.get("/v1/performance/hit-rates")
    def performance_hit_rates():
        decision, failure = authorize_request(performance_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(performance_dashboard_payload(performance_dashboard_hit_rates)), 200, rate_limit_headers(limited)

    @app.get("/v1/performance/metrics")
    def performance_metrics():
        decision, failure = authorize_request(performance_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(performance_dashboard_payload(performance_dashboard_metrics)), 200, rate_limit_headers(limited)

    def drift_dashboard_payload(method, name=None):
        dashboard = DriftMonitoringDashboardService()
        return method(dashboard) if name is None else method(dashboard, name)

    def model_health_dashboard_payload(method):
        dashboard = ModelHealthDashboardService()
        return method(dashboard)

    @app.get("/v1/model-health/summary")
    def model_health_dashboard_summary_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/model-health/scorecard")
    def model_health_dashboard_scorecard_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_scorecard)), 200, rate_limit_headers(limited)

    @app.get("/v1/model-health/components")
    def model_health_dashboard_components_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_components)), 200, rate_limit_headers(limited)

    @app.get("/v1/model-health/thresholds")
    def model_health_dashboard_thresholds_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_thresholds)), 200, rate_limit_headers(limited)

    @app.get("/v1/model-health/lineage")
    def model_health_dashboard_lineage_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_lineage)), 200, rate_limit_headers(limited)

    @app.get("/v1/model-health/validation")
    def model_health_dashboard_validation_route():
        decision, failure = authorize_request(model_health_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(model_health_dashboard_payload(model_health_dashboard_validation)), 200, rate_limit_headers(limited)


    @app.get("/v1/drift/summary")
    def drift_summary():
        decision, failure = authorize_request(drift_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(drift_dashboard_payload(drift_dashboard_summary)), 200, rate_limit_headers(limited)

    @app.get("/v1/drift/overview")
    def drift_overview():
        decision, failure = authorize_request(drift_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        return jsonify(drift_dashboard_payload(drift_dashboard_overview)), 200, rate_limit_headers(limited)

    @app.get("/v1/drift/<name>")
    def drift_section(name: str):
        decision, failure = authorize_request(drift_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        try:
            return jsonify(drift_dashboard_payload(drift_dashboard_section, name)), 200, rate_limit_headers(limited)
        except ValueError as exc:
            return jsonify({"status": INVALID, "error": {"code": "DRIFT_SECTION_INVALID", "message": str(exc)}}), 400, rate_limit_headers(limited)

    @app.get("/v1/drift/<name>/observations")
    def drift_observations(name: str):
        decision, failure = authorize_request(drift_scope)
        if failure is not None: return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple): return limited
        try:
            return jsonify(drift_dashboard_payload(drift_dashboard_observations, name)), 200, rate_limit_headers(limited)
        except ValueError as exc:
            return jsonify({"status": INVALID, "error": {"code": "DRIFT_SECTION_INVALID", "message": str(exc)}}), 400, rate_limit_headers(limited)

    @app.get("/v1/historical/summary")
    def historical_summary():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            payload = HistoricalDashboardService(db).summary()
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/historical/markets")
    def historical_markets():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            markets = db.query(Market).order_by(Market.name).all()
            payload = {
                "status": VALID,
                "markets": [
                    {"id": market.id, "name": market.name, "active": market.is_active}
                    for market in markets
                ],
            }
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.post("/v1/historical/records")
    def historical_record_create():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            if not request.is_json:
                raise ValueError("application/json is required.")
            payload = request.get_json(silent=True) or {}
            result_date_raw = str(payload.get("date", "")).strip()
            market_name = str(payload.get("market_name", "")).strip()
            raw_data = str(payload.get("data", "")).strip()
            if not result_date_raw:
                raise ValueError("date is required.")
            if not market_name:
                raise ValueError("market_name is required.")
            if not raw_data:
                raise ValueError("data is required.")
            from datetime import date
            result_date = date.fromisoformat(result_date_raw)
            parts = raw_data.split()
            if len(parts) != 3:
                raise ValueError("data must contain Open Jodi Close, for example: 123 45 678.")
            open_result, jodi_result, close_result = parts
            db = SessionLocal()
            try:
                service_db = HistoricalResultService(db)
                market = service_db.get_market(market_name)
                if market is None:
                    market = service_db.create_market(market_name)
                result = service_db.create_historical_result(
                    market,
                    result_date,
                    open_result,
                    jodi_result,
                    close_result,
                )
                saved = {
                    "id": result.id,
                    "date": result.result_date.isoformat(),
                    "market_id": result.market_id,
                    "market_name": market.name,
                    "open": result.open_result,
                    "jodi": result.jodi_result,
                    "close": result.close_result,
                    "columns": [
                        result.col1, result.col2, result.col3, result.col4,
                        result.col5, result.col6, result.col7, result.col8,
                    ],
                }
            finally:
                db.close()
            return jsonify({"status": VALID, "message": "Historical data saved.", "record": saved}), 201, rate_limit_headers(limited)
        except (ValueError, TypeError) as exc:
            return jsonify({
                "status": INVALID,
                "error": {"code": "HISTORICAL_CREATE_INVALID", "message": str(exc)},
            }), 400, rate_limit_headers(limited)

    @app.post("/v1/historical/stage1")
    def historical_stage1():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            payload = request.get_json(silent=True) or {}
            from datetime import date
            result_date = date.fromisoformat(str(payload.get("date", "")).strip())
            market_name = str(payload.get("market_name", "")).strip()
            open_result = str(payload.get("open", "")).strip()
            jodi_first = str(payload.get("jodi_first", "")).strip()
            if not market_name:
                raise ValueError("market_name is required.")
            if len(open_result) != 3 or not open_result.isdigit():
                raise ValueError("Open must contain exactly 3 digits.")
            if len(jodi_first) != 1 or not jodi_first.isdigit():
                raise ValueError("Jodi first digit must contain exactly 1 digit.")
            live_activity.emit(
                "Stage 1 data received",
                status="RUNNING",
                source="WEBSITE",
                current_date=result_date.isoformat(),
                stage="STAGE_1",
                operation="Saving Stage 1",
                actual=None,
                result=None,
            )
            workflow = system.save_stage1(result_date, market_name, open_result, jodi_first)
            live_activity.emit(
                "Stage 1 stored in database",
                current_date=result_date.isoformat(),
                stage="STAGE_1",
                operation="Generating Stage 2 prediction",
            )
            try:
                prediction = predict_stage_2(open_result, jodi_first)
            except ValueError as exc:
                prediction = {"status": "NOT_READY", "message": str(exc)}
            live_activity.emit(
                "Stage 2 prediction generated",
                current_date=result_date.isoformat(),
                stage="STAGE_2",
                operation="Waiting for actual result",
                prediction=prediction,
            )
            return jsonify({
                "status": VALID,
                "message": "Stage 1 saved. Open + Jodi first digit are ready for Stage 2 prediction.",
                "stage": {
                    "id": workflow.payload["stage_id"],
                    "date": workflow.payload["date"],
                    "market_id": workflow.payload["market_id"],
                    "market_name": workflow.payload["market_name"],
                    "open": workflow.payload["open"],
                    "jodi_first": workflow.payload["jodi_first"],
                },
                "prediction": prediction,
            }), 201, rate_limit_headers(limited)
        except (ValueError, TypeError) as exc:
            return jsonify({"status": INVALID, "error": {"code": "STAGE1_INVALID", "message": str(exc)}}), 400, rate_limit_headers(limited)

    @app.post("/v1/historical/stage2")
    def historical_stage2():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            payload = request.get_json(silent=True) or {}
            from datetime import date
            raw_stage_id = payload.get("stage_id")
            stage_id = int(raw_stage_id) if raw_stage_id not in (None, "") else None
            result_date = date.fromisoformat(str(payload.get("date", "")).strip()) if payload.get("date") else None
            market_name = str(payload.get("market_name", "")).strip()
            jodi_second = str(payload.get("jodi_second", "")).strip()
            close_result = str(payload.get("close", "")).strip()
            if len(jodi_second) != 1 or not jodi_second.isdigit():
                raise ValueError("Jodi second digit must contain exactly 1 digit.")
            if len(close_result) != 3 or not close_result.isdigit():
                raise ValueError("Close must contain exactly 3 digits.")
            if stage_id is None:
                if result_date is None or not market_name:
                    raise ValueError("date and market_name are required when stage_id is not provided.")
                db = SessionLocal()
                try:
                    market = db.query(Market).filter(Market.name == market_name).one_or_none()
                    if market is None:
                        raise ValueError("Market was not found.")
                    stage = db.query(SequentialPredictionStage).filter(
                        SequentialPredictionStage.market_id == market.id,
                        SequentialPredictionStage.result_date == result_date,
                    ).one_or_none()
                    if stage is None:
                        raise ValueError("Stage 1 must be saved before Stage 2.")
                    stage_id = stage.id
                finally:
                    db.close()

            live_activity.emit(
                "Stage 2 actual result received",
                status="RUNNING",
                source="WEBSITE",
                stage="STAGE_2",
                operation="Saving actual result",
                actual=f"{jodi_second} {close_result}",
            )
            workflow = system.complete_stage2(stage_id, jodi_second, close_result)
            saved = {
                "id": workflow.payload["record_id"],
                "stage_id": workflow.payload["stage_id"],
                "date": workflow.payload["date"],
                "market_id": workflow.payload["market_id"],
                "market_name": workflow.payload["market_name"],
                "open": workflow.payload["open"],
                "jodi": workflow.payload["jodi"],
                "close": workflow.payload["close"],
                "columns": workflow.payload["columns"],
            }
            return jsonify({"status": VALID, "message": "Stage 2 saved and complete historical result created.", "record": saved}), 201, rate_limit_headers(limited)
        except (ValueError, TypeError) as exc:
            return jsonify({"status": INVALID, "error": {"code": "STAGE2_INVALID", "message": str(exc)}}), 400, rate_limit_headers(limited)

    @app.get("/v1/historical/stages")
    def historical_stages():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            rows = db.query(SequentialPredictionStage).filter(
                SequentialPredictionStage.status == "STAGE_1"
            ).order_by(
                SequentialPredictionStage.result_date.desc()
            ).limit(1000).all()
            market_ids = {row.market_id for row in rows}
            markets = {market.id: market.name for market in db.query(Market).filter(Market.id.in_(market_ids)).all()}
            payload = [{
                "id": row.id,
                "date": row.result_date.isoformat(),
                "market_id": row.market_id,
                "market_name": markets.get(row.market_id, ""),
                "open": row.open_result,
                "jodi_first": row.jodi_first_digit,
                "status": row.status,
            } for row in rows]
        finally:
            db.close()
        return jsonify({"status": VALID, "count": len(payload), "stages": payload}), 200, rate_limit_headers(limited)

    @app.get("/v1/historical/records")
    def historical_records():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        try:
            market_id = request.args.get("market_id", type=int)
            from datetime import date
            start = date.fromisoformat(request.args["start_date"]) if request.args.get("start_date") else None
            end = date.fromisoformat(request.args["end_date"]) if request.args.get("end_date") else None
            limit = request.args.get("limit", default=100, type=int)
            db = SessionLocal()
            try:
                payload = HistoricalDashboardService(db).records(market_id=market_id, start_date=start, end_date=end, limit=limit)
            finally:
                db.close()
            return jsonify(payload), 200, rate_limit_headers(limited)
        except ValueError as exc:
            return jsonify({"status": INVALID, "error": {"code": "HISTORICAL_QUERY_INVALID", "message": str(exc)}}), 400, rate_limit_headers(limited)

    @app.get("/v1/historical/frequency")
    def historical_frequency():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            payload = HistoricalDashboardService(db).frequency(request.args.get("market_id", type=int))
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/historical/daily")
    def historical_daily():
        decision, failure = authorize_request(historical_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        db = SessionLocal()
        try:
            payload = HistoricalDashboardService(db).daily_series(request.args.get("market_id", type=int))
        finally:
            db.close()
        return jsonify(payload), 200, rate_limit_headers(limited)

    @app.get("/v1/monitoring/<name>")
    def monitoring_report(name: str):
        decision, failure = authorize_request(monitoring_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        result = service.monitoring(name)
        return jsonify(result.payload), result.http_status, rate_limit_headers(limited)

    @app.get("/v1/admin/security-audit")
    def admin_security_audit():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        report = audit_security_contract(Path(__file__).resolve().parent.parent)
        return jsonify(security_audit_summary(report)), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/production-readiness")
    def admin_production_readiness():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        report = run_production_readiness_audit(Path(__file__).resolve().parent.parent)
        return jsonify(production_readiness_summary(report)), 200, rate_limit_headers(limited)

    @app.get("/v1/admin/production-release")
    def admin_production_release():
        decision, failure = authorize_request(admin_scope)
        if failure is not None:
            return jsonify(decision), failure
        limited = rate_limit(decision)
        if isinstance(limited, tuple):
            return limited
        report = run_production_release_audit()
        return jsonify({
            "release": production_release_summary(report),
            "gate": release_gate(report),
        }), 200, rate_limit_headers(limited)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({
            "service_version": PRODUCTION_SERVICE_VERSION,
            "boundary": PRODUCTION_SERVICE_BOUNDARY,
            "status": INVALID,
            "error": {
                "code": "NOT_FOUND",
                "message": "Production service route was not found.",
            },
        }), 404

    @app.errorhandler(500)
    def internal_server_error(_):
        return jsonify({
            "service_version": PRODUCTION_SERVICE_VERSION,
            "boundary": PRODUCTION_SERVICE_BOUNDARY,
            "status": INVALID,
            "error": {
                "code": "INTERNAL_SERVER_ERROR_RECOVERABLE",
                "message": "The operation failed safely. No partial result was returned.",
                "recovery": {
                    "action": "SAFE_ABORT",
                    "data_fabrication": False,
                    "automatic_model_replacement": False,
                },
            },
        }), 500

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({
            "service_version": PRODUCTION_SERVICE_VERSION,
            "boundary": PRODUCTION_SERVICE_BOUNDARY,
            "status": INVALID,
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "HTTP method is not allowed for this route.",
            },
        }), 405

    return app


def production_service_summary(service: NeuroLyticsProductionService) -> dict[str, Any]:
    if not isinstance(service, NeuroLyticsProductionService):
        raise TypeError("service must be NeuroLyticsProductionService")
    health = service.health()
    return {
        "service_version": PRODUCTION_SERVICE_VERSION,
        "boundary": PRODUCTION_SERVICE_BOUNDARY,
        "service_state": service.state,
        "health_status": health["status"],
        "failed_dependencies": health["failed_dependencies"],
        "serving_id": service.inference_service.serving_plan.serving_id,
        "model_identity": service.inference_service.serving_plan.model_identity,
        "model_version": service.inference_service.serving_plan.model_version,
        "artifact_identity": service.inference_service.serving_plan.artifact_identity,
        "routes": (
            "/health",
            "/ready",
            "/v1/inference",
            "/v1/monitoring/summary",
            "/v1/monitoring/<name>",
        ),
    }


__all__ = [
    "PRODUCTION_SERVICE_VERSION",
    "PRODUCTION_SERVICE_BOUNDARY",
    "SERVICE_CREATED",
    "SERVICE_STARTING",
    "SERVICE_RUNNING",
    "SERVICE_STOPPED",
    "SERVICE_FAILED",
    "VALID",
    "INVALID",
    "ProductionServicePolicy",
    "ProductionDependency",
    "ProductionServiceResult",
    "NeuroLyticsProductionService",
    "create_production_app",
    "production_service_summary",
    "run_failure_recovery_audit",
]
