from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

VERSION = "101.0.0"
BOUNDARY = "PRODUCTION_ARTIFACT_QUALIFICATION"
VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"

TARGETS = ("jodi_first", "jodi_second", "close_first", "close_second", "close_third")
ARTIFACT_DIR = Path("models/sequential")
STATUS_FILE = ARTIFACT_DIR / "training_status.json"
BOUNDARY_REPORT = Path("reports/production_artifact_boundary.json")
QUALIFICATION_REPORT = Path("reports/production_model_qualification.json")
REQUIRED_FEATURE_COUNT = 28


@dataclass(frozen=True)
class QualificationCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ProductionArtifactQualificationReport:
    version: str
    status: str
    activation_ready: bool
    checks: tuple[QualificationCheck, ...]
    artifact_identities: dict[str, str]
    report_identity: str


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _check(name: str, ok: bool, detail: str, warning: bool = False) -> QualificationCheck:
    return QualificationCheck(name, VALID if ok else (WARNING if warning else INVALID), detail)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def run_production_artifact_qualification(project_root: str | Path = ".") -> ProductionArtifactQualificationReport:
    root = Path(project_root)
    checks: list[QualificationCheck] = []
    artifact_ids: dict[str, str] = {}

    status = _load_json(root / STATUS_FILE)
    checks.append(_check(
        "training_status",
        bool(status) and status.get("status") == "COMPLETED",
        "Sequential training status is COMPLETED." if status and status.get("status") == "COMPLETED"
        else "Sequential training status is missing or not COMPLETED.",
    ))

    if status:
        checks.append(_check(
            "temporal_boundary",
            status.get("strict_temporal_boundary") is True,
            "Training declares a strict temporal boundary.",
        ))
        checks.append(_check(
            "dataset_completeness",
            status.get("record_count") == 1990 and status.get("training_samples") == 1989,
            f"Training metadata records={status.get('record_count')} samples={status.get('training_samples')}.",
        ))
        checks.append(_check(
            "validation_holdout",
            status.get("validation_rows") == 398 and bool(status.get("validation_start_date")),
            "Chronological validation holdout is persisted.",
        ))
        checks.append(_check(
            "independent_jodi_targets",
            status.get("jodi_b1_independent") is True,
            "Jodi first/second targets are independently trained.",
        ))
    else:
        checks.extend([
            _check("temporal_boundary", False, "Training metadata unavailable."),
            _check("dataset_completeness", False, "Training metadata unavailable."),
            _check("validation_holdout", False, "Training metadata unavailable."),
            _check("independent_jodi_targets", False, "Training metadata unavailable."),
        ])

    boundary = _load_json(root / BOUNDARY_REPORT)
    boundary_entries = {
        entry.get("path", "").replace("\\", "/"): entry
        for entry in (boundary or {}).get("artifacts", [])
        if isinstance(entry, dict)
    }

    checks.append(_check(
        "artifact_boundary",
        bool(boundary) and boundary.get("status") == VALID and boundary.get("boundary_valid") is True,
        "C.20 artifact boundary is VALID.",
    ))

    all_loadable = True
    all_schema_compatible = True
    hashes_match = True
    missing: list[str] = []

    for target in TARGETS:
        path = root / ARTIFACT_DIR / f"{target}.joblib"
        key = f"NeuroLytics/models/sequential/{target}.joblib"
        if not path.is_file():
            missing.append(target)
            all_loadable = False
            continue
        try:
            model = joblib.load(path)
            if not hasattr(model, "predict_proba") or getattr(model, "n_features_in_", None) != REQUIRED_FEATURE_COUNT:
                all_schema_compatible = False
            artifact_ids[target] = _file_sha256(path)
            boundary_entry = boundary_entries.get(key)
            if not boundary_entry or boundary_entry.get("sha256") != artifact_ids[target]:
                hashes_match = False
        except Exception:
            all_loadable = False

    checks.append(_check(
        "artifact_presence_loadability",
        all_loadable and not missing,
        "All five sequential artifacts are present and loadable."
        if all_loadable and not missing else f"Missing/unloadable targets: {missing}.",
    ))
    checks.append(_check(
        "feature_schema_compatibility",
        all_schema_compatible,
        f"All sequential artifacts expose n_features_in_={REQUIRED_FEATURE_COUNT}.",
    ))
    checks.append(_check(
        "artifact_hash_integrity",
        hashes_match,
        "Persisted artifact hashes match the C.20 boundary manifest.",
    ))

    checks.append(_check(
        "explicit_activation_authorization",
        False,
        "No explicit production authorization/activation lineage exists; candidate is NOT activation-ready.",
        warning=True,
    ))

    invalid = sum(c.status == INVALID for c in checks)
    warnings = sum(c.status == WARNING for c in checks)
    status_value = INVALID if invalid else (WARNING if warnings else VALID)
    activation_ready = status_value == VALID and all(c.status == VALID for c in checks)

    identity = _hash({
        "version": VERSION,
        "checks": [(c.name, c.status, c.detail) for c in checks],
        "artifacts": artifact_ids,
    })
    return ProductionArtifactQualificationReport(
        VERSION, status_value, activation_ready, tuple(checks), artifact_ids, identity
    )


def summary(report: ProductionArtifactQualificationReport) -> dict[str, Any]:
    invalid = sum(c.status == INVALID for c in report.checks)
    warnings = sum(c.status == WARNING for c in report.checks)
    return {
        "version": report.version,
        "boundary": BOUNDARY,
        "status": report.status,
        "activation_ready": report.activation_ready,
        "counts": {
            "total": len(report.checks),
            "valid": len(report.checks) - invalid - warnings,
            "warnings": warnings,
            "invalid": invalid,
        },
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in report.checks],
        "artifact_identities": report.artifact_identities,
        "report_identity": report.report_identity,
    }


def write_report(report: ProductionArtifactQualificationReport, path: str | Path = "reports/production_artifact_qualification.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
