from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analytics.production_readiness_audit import (
    INVALID,
    VALID,
    WARNING,
    production_readiness_summary,
    run_production_readiness_audit,
)

FINAL_SYSTEM_INTEGRATION_VERSION = "99.0.0"
FINAL_SYSTEM_INTEGRATION_BOUNDARY = "FINAL_SYSTEM_INTEGRATION"

REQUIRED_FILES = (
    "analytics/production_service.py",
    "analytics/production_readiness_audit.py",
    "frontend/templates/index.html",
    "frontend/static/js/app.js",
    "frontend/static/css/app.css",
)

REQUIRED_ROUTES = (
    "/health",
    "/ready",
    "/v1/inference",
    "/v1/historical/records",
    "/v1/historical/stage1",
    "/v1/historical/stage2",
    "/v1/model/summary",
    "/v1/model-health/summary",
    "/v1/ranking/summary",
    "/v1/ranking/top-k",
    "/v1/performance/summary",
    "/v1/drift/summary",
    "/v1/admin/security-audit",
    "/v1/admin/production-readiness",
)

@dataclass(frozen=True)
class IntegrationCheck:
    name: str
    status: str
    detail: str

@dataclass(frozen=True)
class FinalSystemIntegrationReport:
    version: str
    status: str
    checks: tuple[IntegrationCheck, ...]
    report_identity: str

def _identity(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "final-system-integration-" + hashlib.sha256(raw).hexdigest()

def _check(name: str, ok: bool, detail: str, warning: bool = False) -> IntegrationCheck:
    return IntegrationCheck(name, VALID if ok else (WARNING if warning else INVALID), detail)

def run_final_system_integration(project_root: str | Path = ".") -> FinalSystemIntegrationReport:
    root = Path(project_root)
    checks: list[IntegrationCheck] = []

    missing_files = [p for p in REQUIRED_FILES if not (root / p).is_file()]
    checks.append(_check(
        "release_file_inventory",
        not missing_files,
        "Required release files are present." if not missing_files else f"Missing files: {missing_files}",
    ))

    service_source = (root / "analytics/production_service.py").read_text(encoding="utf-8", errors="ignore")
    missing_routes = [r for r in REQUIRED_ROUTES if r not in service_source]
    checks.append(_check(
        "critical_route_integration",
        not missing_routes,
        "Critical API routes are integrated." if not missing_routes else f"Missing routes: {missing_routes}",
    ))

    try:
        import analytics.production_service
        import analytics.production_readiness_audit
        import analytics.reproducibility_audit
        import analytics.data_integrity_audit
        import analytics.temporal_safety_audit
        import analytics.performance_scalability_audit
        import analytics.failure_recovery
        import analytics.security_audit
        checks.append(_check("module_integration", True, "Production and hardening modules import successfully."))
    except Exception as exc:
        checks.append(_check("module_integration", False, f"Module integration failed: {type(exc).__name__}"))

    readiness = run_production_readiness_audit(root)
    readiness_summary = production_readiness_summary(readiness)
    checks.append(_check(
        "production_readiness_gate",
        readiness_summary["counts"]["invalid"] == 0,
        f"Phase 98 readiness gate has {readiness_summary['counts']['invalid']} invalid findings and {readiness_summary['counts']['warnings']} warnings.",
    ))

    checks.append(_check(
        "conditional_operational_inputs",
        readiness_summary["counts"]["warnings"] == 0,
        "All operational inputs are available.",
        warning=True,
    ))

    checks.append(_check(
        "frontend_backend_boundary",
        all((root / p).is_file() for p in ("frontend/templates/index.html", "frontend/static/js/app.js", "frontend/static/css/app.css"))
        and "/frontend/config" in service_source,
        "Frontend assets and frontend configuration boundary are integrated.",
    ))

    checks.append(_check(
        "sequential_prediction_boundary",
        all(route in service_source for route in (
            "/v1/model/sequential/status",
            "/v1/model/sequential/retrain",
            "/v1/model/sequential/predict",
            "/v1/model/feedback",
            "/v1/historical/stage1",
            "/v1/historical/stage2",
        )),
        "Sequential Stage 1/Stage 2 prediction and feedback routes are integrated.",
    ))

    checks.append(_check(
        "audit_chain_boundary",
        all(name in service_source for name in (
            "run_reproducibility_audit",
            "run_data_integrity_audit",
            "run_temporal_safety_audit",
            "run_performance_scalability_audit",
            "run_failure_recovery_audit",
            "audit_security_contract",
            "run_production_readiness_audit",
        )),
        "Phase 92–98 audit chain is connected to the production service.",
    ))

    invalid = sum(c.status == INVALID for c in checks)
    warnings = sum(c.status == WARNING for c in checks)
    status = INVALID if invalid else (WARNING if warnings else VALID)
    identity = _identity({"version": FINAL_SYSTEM_INTEGRATION_VERSION, "checks": [(c.name, c.status, c.detail) for c in checks]})
    return FinalSystemIntegrationReport(FINAL_SYSTEM_INTEGRATION_VERSION, status, tuple(checks), identity)

def final_system_integration_summary(report: FinalSystemIntegrationReport) -> dict[str, Any]:
    invalid = sum(c.status == INVALID for c in report.checks)
    warnings = sum(c.status == WARNING for c in report.checks)
    return {
        "status": report.status,
        "version": report.version,
        "boundary": FINAL_SYSTEM_INTEGRATION_BOUNDARY,
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in report.checks],
        "counts": {"total": len(report.checks), "valid": len(report.checks) - invalid - warnings, "warnings": warnings, "invalid": invalid},
        "report_identity": report.report_identity,
    }

def write_final_system_integration_report(report: FinalSystemIntegrationReport, path: str | Path = "reports/final_system_integration.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(final_system_integration_summary(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination
