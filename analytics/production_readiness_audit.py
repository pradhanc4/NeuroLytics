from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select

from database.engine import SessionLocal
from database.models import HistoricalResult, Market

PRODUCTION_READINESS_VERSION = "98.0.0"
PRODUCTION_READINESS_BOUNDARY = "PRODUCTION_READINESS_AUDIT"
VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"

REQUIRED_MODULES = (
    "analytics.production_service",
    "analytics.production_serving",
    "analytics.production_api",
    "analytics.performance_monitoring_api",
    "analytics.api_security",
    "analytics.api_rate_limit",
    "analytics.api_validation",
    "analytics.reproducibility_audit",
    "analytics.data_integrity_audit",
    "analytics.temporal_safety_audit",
    "analytics.performance_scalability_audit",
    "analytics.failure_recovery",
    "analytics.security_audit",
)

REQUIRED_ROUTES = (
    "/health", "/ready", "/v1/inference", "/v1/monitoring/summary",
    "/v1/model/summary", "/v1/model-health/summary",
    "/v1/ranking/summary", "/v1/top-k/summary",
    "/v1/performance/summary", "/v1/drift/summary",
    "/v1/admin/summary", "/v1/admin/reproducibility",
    "/v1/admin/data-integrity", "/v1/admin/temporal-safety",
    "/v1/admin/performance-scalability", "/v1/admin/failure-recovery",
    "/v1/admin/recovery-status", "/v1/admin/security-audit",
    "/v1/admin/production-readiness",
)

REQUIRED_FRONTEND_FILES = (
    "frontend/templates/index.html",
    "frontend/static/js/app.js",
    "frontend/static/css/app.css",
)

AUDIT_REPORTS = (
    "reproducibility_audit.json",
    "data_integrity_audit.json",
    "temporal_safety_audit.json",
    "performance_scalability_audit.json",
    "failure_recovery_audit.json",
    "security_audit.json",
)

@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str

@dataclass(frozen=True)
class ProductionReadinessReport:
    version: str
    status: str
    checks: tuple[ReadinessCheck, ...]
    report_identity: str

def _identity(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "production-readiness-" + hashlib.sha256(raw).hexdigest()

def _check(name: str, ok: bool, detail: str, *, warning: bool = False) -> ReadinessCheck:
    if ok:
        status = VALID
    else:
        status = WARNING if warning else INVALID
    return ReadinessCheck(name, status, detail)

def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

def _report_status(path: Path) -> str | None:
    payload = _load_json(path)
    status = payload.get("status") if payload else None
    return status if isinstance(status, str) else None

def _production_source(root: Path) -> str:
    path = root / "analytics" / "production_service.py"
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""

def _database_check() -> tuple[bool, str]:
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        tables = set(inspector.get_table_names())
        expected = {"markets", "historical_results", "sequential_prediction_stages", "prediction_feedback"}
        missing = sorted(expected - tables)
        if missing:
            return False, f"Required database tables are missing: {missing}"
        market_count = len(db.scalars(select(Market.id)).all())
        result_count = len(db.scalars(select(HistoricalResult.id)).all())
        return True, f"Database reachable; required tables present; markets={market_count}, historical_results={result_count}"
    except Exception as exc:
        return False, f"Database readiness check failed: {type(exc).__name__}"
    finally:
        db.close()

def _historical_data_available() -> bool:
    db = SessionLocal()
    try:
        return db.scalar(select(HistoricalResult.id).limit(1)) is not None
    except Exception:
        return False
    finally:
        db.close()

def run_production_readiness_audit(project_root: str | Path = ".") -> ProductionReadinessReport:
    root = Path(project_root)
    checks: list[ReadinessCheck] = []
    missing_modules: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            __import__(module_name)
        except Exception:
            missing_modules.append(module_name)
    checks.append(_check(
        "core_module_imports",
        not missing_modules,
        "All production-boundary modules import successfully."
        if not missing_modules else f"Modules failed to import: {missing_modules}",
    ))

    source = _production_source(root)
    missing_routes = [route for route in REQUIRED_ROUTES if route not in source]
    checks.append(_check(
        "production_route_inventory",
        not missing_routes,
        "Critical production and administrative routes are present."
        if not missing_routes else f"Missing routes: {missing_routes}",
    ))

    missing_frontend = [
        path for path in REQUIRED_FRONTEND_FILES
        if not (root / path).is_file()
    ]
    checks.append(_check(
        "frontend_release_assets",
        not missing_frontend,
        "Required frontend template, JavaScript, and CSS assets are present."
        if not missing_frontend else f"Missing frontend assets: {missing_frontend}",
    ))

    db_ok, db_detail = _database_check()
    checks.append(_check("database_readiness", db_ok, db_detail))

    report_dir = root / "reports"
    missing_reports = [name for name in AUDIT_REPORTS if not (report_dir / name).is_file()]
    checks.append(_check(
        "hardening_audit_artifacts",
        not missing_reports,
        "Phase 92–97 audit reports are present."
        if not missing_reports else f"Missing audit reports: {missing_reports}",
    ))

    report_statuses = {
        name: _report_status(report_dir / name)
        for name in AUDIT_REPORTS
        if (report_dir / name).is_file()
    }
    bad_reports = {
        name: status for name, status in report_statuses.items()
        if status != VALID
    }
    checks.append(_check(
        "hardening_audit_status",
        len(report_statuses) == len(AUDIT_REPORTS) and not bad_reports,
        "All Phase 92–97 persisted audit reports are VALID."
        if not bad_reports and len(report_statuses) == len(AUDIT_REPORTS)
        else f"Audit reports require review: {bad_reports}",
    ))

    models_dir = root / "models"
    artifacts = [
        path for path in models_dir.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    ] if models_dir.exists() else []
    checks.append(_check(
        "model_artifact_readiness",
        bool(artifacts),
        "At least one persisted model artifact is available."
        if artifacts else
        "No persisted model artifacts are currently present; release readiness is conditional until a validated artifact is available.",
        warning=True,
    ))

    checks.append(_check(
        "historical_data_readiness",
        _historical_data_available(),
        "Historical data is available for operational prediction workflows."
        if _historical_data_available()
        else "No historical result rows are currently present; operational prediction readiness is conditional.",
        warning=True,
    ))
    required_docs = (
        "docs/PHASE_97_SECURITY_AUDIT.md",
        "docs/PHASE_96_FAILURE_RECOVERY.md",
        "docs/PHASE_95_PERFORMANCE_SCALABILITY_TESTING.md",
        "docs/PHASE_94_LEAKAGE_TEMPORAL_SAFETY_AUDIT.md",
        "docs/PHASE_93_DATA_INTEGRITY_AUDIT.md",
        "docs/PHASE_92_REPRODUCIBILITY_AUDIT.md",
    )
    missing_docs = [path for path in required_docs if not (root / path).is_file()]
    checks.append(_check(
        "release_documentation",
        not missing_docs,
        "Release-hardening documentation for Phases 92–97 is present."
        if not missing_docs else f"Missing documentation: {missing_docs}",
    ))

    roadmap = root / "docs" / "ROADMAP_1_100.md"
    roadmap_text = roadmap.read_text(encoding="utf-8", errors="ignore") if roadmap.exists() else ""
    checks.append(_check(
        "roadmap_gate",
        "Phase 97 — Security Audit — COMPLETE" in roadmap_text,
        "Roadmap confirms Phase 97 completion before the Phase 98 audit.",
    ))

    checks.append(_check(
        "runtime_environment",
        sys.version_info >= (3, 10) and platform.system() == "Windows",
        f"Runtime={platform.system()} Python={platform.python_version()}",
    ))

    source_contracts = (
        "apply_security_headers",
        "authorize_request",
        "rate_limit",
        "INTERNAL_SERVER_ERROR_RECOVERABLE",
        "run_reproducibility_audit",
        "run_data_integrity_audit",
        "run_temporal_safety_audit",
        "run_performance_scalability_audit",
        "run_failure_recovery_audit",
        "audit_security_contract",
    )
    missing_contracts = [item for item in source_contracts if item not in source]
    checks.append(_check(
        "production_hardening_contract",
        not missing_contracts,
        "Production service contains the required security, recovery, and audit contracts."
        if not missing_contracts else f"Missing production contracts: {missing_contracts}",
    ))

    invalid_count = sum(c.status == INVALID for c in checks)
    warning_count = sum(c.status == WARNING for c in checks)
    status = INVALID if invalid_count else (WARNING if warning_count else VALID)
    identity = _identity({
        "version": PRODUCTION_READINESS_VERSION,
        "checks": [(c.name, c.status, c.detail) for c in checks],
    })
    return ProductionReadinessReport(
        PRODUCTION_READINESS_VERSION, status, tuple(checks), identity
    )

def production_readiness_summary(report: ProductionReadinessReport) -> dict[str, Any]:
    invalid = sum(c.status == INVALID for c in report.checks)
    warnings = sum(c.status == WARNING for c in report.checks)
    return {
        "status": report.status,
        "version": report.version,
        "boundary": PRODUCTION_READINESS_BOUNDARY,
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail}
            for c in report.checks
        ],
        "counts": {
            "total": len(report.checks),
            "valid": len(report.checks) - invalid - warnings,
            "warnings": warnings,
            "invalid": invalid,
        },
        "report_identity": report.report_identity,
    }

def write_production_readiness_report(
    report: ProductionReadinessReport,
    path: str | Path = "reports/production_readiness_audit.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(production_readiness_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination

__all__ = [
    "PRODUCTION_READINESS_VERSION", "PRODUCTION_READINESS_BOUNDARY",
    "VALID", "WARNING", "INVALID", "ReadinessCheck",
    "ProductionReadinessReport", "REQUIRED_ROUTES",
    "run_production_readiness_audit", "production_readiness_summary",
    "write_production_readiness_report",
]
