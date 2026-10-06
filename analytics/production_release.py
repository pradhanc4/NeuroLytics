from __future__ import annotations
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from database.engine import SessionLocal
from database.models import HistoricalResult, Market

PRODUCTION_RELEASE_VERSION = "100.0.0"
PRODUCTION_RELEASE_BOUNDARY = "PRODUCTION_RELEASE"
VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"
RELEASE_READY = "RELEASE_READY"
CONDITIONAL_RELEASE = "CONDITIONAL_RELEASE"
REPORT_PATH = Path("reports/production_release.json")

REQUIRED_REPORTS = (
    "reproducibility_audit.json",
    "data_integrity_audit.json",
    "temporal_safety_audit.json",
    "performance_scalability_audit.json",
    "failure_recovery_audit.json",
    "security_audit.json",
    "production_readiness_audit.json",
    "final_system_integration.json",
)

REQUIRED_FILES = (
    "analytics/production_service.py",
    "analytics/production_serving.py",
    "analytics/production_activation.py",
    "analytics/production_readiness_audit.py",
    "analytics/final_system_integration.py",
    "frontend/templates/index.html",
    "frontend/static/js/app.js",
    "frontend/static/css/app.css",
    "database/neurolytics.db",
)

TEMPORARY_FILES = (
    "scripts/_phase100_frontend_compat_patch.py",
    "scripts/_phase100_frontend_compat_patch2.py",
    "scripts/_phase100_frontend_compat_patch3.py",
)

@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    status: str
    detail: str

@dataclass(frozen=True)
class ProductionReleaseReport:
    version: str
    boundary: str
    status: str
    release_state: str
    operational_prediction_release: bool
    checks: tuple[ReleaseCheck, ...]
    release_identity: str

    @property
    def invalid_count(self) -> int:
        return sum(c.status == INVALID for c in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(c.status == WARNING for c in self.checks)

    @property
    def valid_count(self) -> int:
        return sum(c.status == VALID for c in self.checks)

def _identity(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "production-release-" + hashlib.sha256(raw).hexdigest()

def _check(name: str, status: str, detail: str) -> ReleaseCheck:
    return ReleaseCheck(name, status, detail)

def _root() -> Path:
    return Path(__file__).resolve().parents[1]

def _read_report(name: str) -> dict[str, Any] | None:
    path = _root() / "reports" / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def _database_counts() -> tuple[int, int]:
    db = SessionLocal()
    try:
        return db.query(Market).count(), db.query(HistoricalResult).count()
    finally:
        db.close()

def run_production_release_audit() -> ProductionReleaseReport:
    root = _root()
    checks: list[ReleaseCheck] = []

    missing = [p for p in REQUIRED_FILES if not (root / p).is_file()]
    checks.append(_check(
        "release_file_inventory",
        INVALID if missing else VALID,
        "Required release files are present." if not missing
        else "Missing release files: " + ", ".join(missing),
    ))

    report_states = {}
    for name in REQUIRED_REPORTS:
        report = _read_report(name)
        report_states[name] = report
        if report is None:
            checks.append(_check("audit_" + name, INVALID, "Required persisted audit report is missing or unreadable."))
        elif report.get("status") == "VALID":
            checks.append(_check("audit_" + name, VALID, "Persisted audit report is VALID."))
        elif report.get("status") == "WARNING":
            checks.append(_check("audit_" + name, WARNING, "Persisted audit report contains warnings."))
        else:
            checks.append(_check("audit_" + name, INVALID, "Persisted audit report is not VALID."))

    temporary = [p for p in TEMPORARY_FILES if (root / p).exists()]
    checks.append(_check(
        "temporary_release_files",
        WARNING if temporary else VALID,
        "No temporary Phase 100 repair files remain."
        if not temporary else "Temporary files remain: " + ", ".join(temporary),
    ))

    try:
        market_count, historical_count = _database_counts()
        checks.append(_check(
            "database_access",
            VALID,
            f"Database reachable; markets={market_count}, historical_results={historical_count}.",
        ))
    except Exception as exc:
        market_count, historical_count = 0, 0
        checks.append(_check("database_access", INVALID, f"Database access failed: {exc}"))

    model_dir = root / "models"
    artifacts = tuple(
        str(p.relative_to(root)).replace("\\", "/")
        for p in model_dir.rglob("*")
        if p.is_file()
    ) if model_dir.exists() else ()
    checks.append(_check(
        "model_artifact_readiness",
        VALID if artifacts else WARNING,
        f"{len(artifacts)} persisted model artifact(s) available."
        if artifacts else "No persisted model artifacts are available.",
    ))

    checks.append(_check(
        "historical_data_readiness",
        VALID if historical_count > 0 else WARNING,
        f"{historical_count} historical result row(s) available."
        if historical_count > 0 else "No historical result rows are available.",
    ))

    checks.append(_check(
        "runtime_environment",
        VALID,
        f"Runtime={platform.system()} Python={platform.python_version()}",
    ))

    # Artifact presence is not the same as production activation authorization.
    # C.20 keeps relationship-aware artifacts experimental, and the activation
    # contract requires an explicit rollout/authorization/activation lineage.
    boundary_report = _read_report("production_artifact_boundary.json")
    approved_nonexperimental = False
    if isinstance(boundary_report, dict) and boundary_report.get("status") == VALID:
        approved_nonexperimental = any(
            entry.get("approved") and not entry.get("experimental")
            for entry in boundary_report.get("artifacts", [])
            if isinstance(entry, dict)
        )
    checks.append(_check(
        "operational_activation_gate",
        VALID if approved_nonexperimental else WARNING,
        (
            "An explicitly approved non-experimental artifact is available."
            if approved_nonexperimental
            else "No explicitly approved non-experimental artifact is present; operational activation remains blocked by the explicit activation gate."
        ),
    ))

    all_required_audits_valid = all(
        report_states[name] is not None
        and report_states[name].get("status") == VALID
        for name in REQUIRED_REPORTS
    )
    operational = (
        not missing
        and not temporary
        and historical_count > 0
        and bool(artifacts)
        and all_required_audits_valid
        and approved_nonexperimental
        and not any(c.status == INVALID for c in checks)
    )
    invalid = any(c.status == INVALID for c in checks)
    release_state = RELEASE_READY if operational and not invalid else CONDITIONAL_RELEASE
    # A conditional release with all engineering checks valid is a healthy
    # release state; activation remains separately gated by explicit approval.
    status = INVALID if invalid else VALID

    payload = {
        "version": PRODUCTION_RELEASE_VERSION,
        "boundary": PRODUCTION_RELEASE_BOUNDARY,
        "status": status,
        "release_state": release_state,
        "operational_prediction_release": operational,
        "checks": checks,
        "database": {"markets": market_count, "historical_results": historical_count},
        "model_artifacts": artifacts,
        "audit_reports": {
            name: (report_states[name] or {}).get("status", "MISSING")
            for name in REQUIRED_REPORTS
        },
    }
    return ProductionReleaseReport(
        PRODUCTION_RELEASE_VERSION,
        PRODUCTION_RELEASE_BOUNDARY,
        status,
        release_state,
        operational,
        tuple(checks),
        _identity(payload),
    )
def validate_production_release(report: ProductionReleaseReport) -> ProductionReleaseReport:
    if not isinstance(report, ProductionReleaseReport):
        raise TypeError("report must be ProductionReleaseReport")
    if report.status == INVALID:
        return report
    expected = RELEASE_READY if report.operational_prediction_release else CONDITIONAL_RELEASE
    if report.release_state != expected:
        raise ValueError("release_state does not match operational release state")
    if report.invalid_count and report.status != INVALID:
        raise ValueError("invalid checks require INVALID status")
    return report

def production_release_summary(report: ProductionReleaseReport) -> dict[str, Any]:
    validate_production_release(report)
    return {
        "version": report.version,
        "boundary": report.boundary,
        "status": report.status,
        "release_state": report.release_state,
        "operational_prediction_release": report.operational_prediction_release,
        "counts": {
            "total": len(report.checks),
            "valid": report.valid_count,
            "warnings": report.warning_count,
            "invalid": report.invalid_count,
        },
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail}
            for c in report.checks
        ],
        "release_identity": report.release_identity,
    }

def write_production_release_report(
    report: ProductionReleaseReport,
    path: str | Path = REPORT_PATH,
) -> Path:
    validate_production_release(report)
    target = Path(path)
    if not target.is_absolute():
        target = _root() / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(production_release_summary(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target

def release_gate(report: ProductionReleaseReport) -> dict[str, Any]:
    validate_production_release(report)
    return {
        "release_allowed": report.status != INVALID,
        "operational_prediction_release_allowed": report.operational_prediction_release,
        "release_state": report.release_state,
        "reason": (
            "All operational release inputs are present."
            if report.operational_prediction_release
            else "Operational prediction release is blocked until validated model artifacts and historical results are available."
        ),
    }

__all__ = [
    "PRODUCTION_RELEASE_VERSION",
    "PRODUCTION_RELEASE_BOUNDARY",
    "VALID",
    "WARNING",
    "INVALID",
    "RELEASE_READY",
    "CONDITIONAL_RELEASE",
    "ProductionReleaseReport",
    "ReleaseCheck",
    "run_production_release_audit",
    "validate_production_release",
    "production_release_summary",
    "write_production_release_report",
    "release_gate",
]
