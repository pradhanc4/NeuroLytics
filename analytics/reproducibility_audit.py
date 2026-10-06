from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from database.engine import Base
from database.models import HistoricalResult, Market

REPRODUCIBILITY_AUDIT_VERSION = "92.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_SEED = 9200

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"


@dataclass(frozen=True)
class ReplayCheck:
    name: str
    first_identity: str
    second_identity: str
    reproducible: bool


@dataclass(frozen=True)
class ReproducibilityAuditReport:
    version: str
    status: str
    dataset_identity: str
    schema_identity: str
    source_identity: str
    environment_identity: str
    configuration_identity: str
    artifact_identities: tuple[tuple[str, str], ...]
    replay_checks: tuple[ReplayCheck, ...]
    issues: tuple[str, ...]
    report_identity: str

    @property
    def is_reproducible(self) -> bool:
        return self.status == VALID


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable_payload(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_payload(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, set):
        return sorted(_stable_payload(item) for item in value)
    if isinstance(value, float):
        return format(value, ".17g")
    return value


def stable_identity(prefix: str, value: Any) -> str:
    encoded = json.dumps(
        _stable_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return prefix + hashlib.sha256(encoded).hexdigest()


def seed_everything(seed: int = DEFAULT_SEED) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer.")
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    os.environ["PYTHONHASHSEED"] = str(seed)
    return seed


def deterministic_configuration(seed: int = DEFAULT_SEED) -> dict[str, Any]:
    return {
        "seed": seed,
        "pythonhashseed": str(seed),
        "random_algorithm": "python.random.MersenneTwister",
        "numpy_seeded_when_available": True,
        "model_random_state_policy": "explicit per-model random_state",
        "parallelism_policy": "deterministic single-worker audit replay",
        "ordering_policy": "stable sorted keys and chronological rows",
    }


def dataset_fingerprint(
    db: Session,
    market_id: int | None = None,
) -> tuple[str, int]:
    statement = select(HistoricalResult).order_by(
        HistoricalResult.market_id,
        HistoricalResult.result_date,
        HistoricalResult.id,
    )
    if market_id is not None:
        statement = statement.where(HistoricalResult.market_id == market_id)
    rows = db.scalars(statement).all()
    payload = [
        {
            "id": row.id,
            "market_id": row.market_id,
            "result_date": row.result_date,
            "open": row.open_result,
            "jodi": row.jodi_result,
            "close": row.close_result,
            "columns": (
                row.col1, row.col2, row.col3, row.col4,
                row.col5, row.col6, row.col7, row.col8,
            ),
        }
        for row in rows
    ]
    return stable_identity("dataset-", payload), len(rows)


def schema_fingerprint() -> str:
    tables = []
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        columns = []
        for column in table.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                }
            )
        constraints = sorted(
            str(constraint)
            for constraint in table.constraints
        )
        tables.append(
            {
                "name": table.name,
                "columns": columns,
                "constraints": constraints,
            }
        )
    return stable_identity("schema-", tables)


def source_fingerprint(paths: Sequence[Path] | None = None) -> str:
    selected = tuple(paths or (
        PROJECT_ROOT / "analytics" / "end_to_end_prediction.py",
        PROJECT_ROOT / "analytics" / "end_to_end_backtesting.py",
        PROJECT_ROOT / "analytics" / "sequential_prediction.py",
        PROJECT_ROOT / "analytics" / "reproducibility_audit.py",
        PROJECT_ROOT / "features" / "feature_pipeline.py",
    ))
    payload = []
    for path in sorted(selected, key=lambda item: item.as_posix()):
        if not path.exists():
            payload.append({"path": path.as_posix(), "missing": True})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        payload.append(
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
    return stable_identity("source-", payload)


def environment_snapshot() -> dict[str, Any]:
    packages = {}
    for name in (
        "Flask",
        "SQLAlchemy",
        "scikit-learn",
        "joblib",
        "xgboost",
        "lightgbm",
        "catboost",
        "numpy",
        "pandas",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "packages": packages,
    }


def environment_identity() -> str:
    return stable_identity("environment-", environment_snapshot())


def configuration_identity(seed: int = DEFAULT_SEED) -> str:
    return stable_identity("configuration-", deterministic_configuration(seed))


def artifact_fingerprints(model_dir: Path = MODEL_DIR) -> tuple[tuple[str, str], ...]:
    if not model_dir.exists():
        return ()
    artifacts = []
    for path in sorted(model_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"audit.json", "reproducibility_report.json"}:
            continue
        artifacts.append(
            (
                path.relative_to(PROJECT_ROOT).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return tuple(artifacts)


def replay_check(
    name: str,
    operation: Callable[[], Any],
    *,
    seed: int = DEFAULT_SEED,
) -> ReplayCheck:
    seed_everything(seed)
    first = stable_identity(f"{name}-", operation())
    seed_everything(seed)
    second = stable_identity(f"{name}-", operation())
    return ReplayCheck(
        name=name,
        first_identity=first,
        second_identity=second,
        reproducible=first == second,
    )


def database_schema_matches_live(db: Session) -> bool:
    inspector = inspect(db.bind)
    live_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables)
    return expected_tables.issubset(live_tables)


def run_reproducibility_audit(
    db: Session,
    *,
    seed: int = DEFAULT_SEED,
    market_id: int | None = None,
) -> ReproducibilityAuditReport:
    seed_everything(seed)
    dataset_id, row_count = dataset_fingerprint(db, market_id)
    schema_id = schema_fingerprint()
    source_id = source_fingerprint()
    environment_id = environment_identity()
    config_id = configuration_identity(seed)
    artifacts = artifact_fingerprints()

    replay_checks = (
        replay_check(
            "dataset-fingerprint-replay",
            lambda: dataset_fingerprint(db, market_id),
            seed=seed,
        ),
        replay_check(
            "configuration-replay",
            lambda: deterministic_configuration(seed),
            seed=seed,
        ),
        replay_check(
            "environment-replay",
            environment_snapshot,
            seed=seed,
        ),
    )

    issues = []
    if not database_schema_matches_live(db):
        issues.append("DATABASE_SCHEMA_MISMATCH")
    if row_count < 0:
        issues.append("INVALID_DATASET_ROW_COUNT")
    if any(not item.reproducible for item in replay_checks):
        issues.append("NON_REPRODUCIBLE_REPLAY")
    if not dataset_id.startswith("dataset-"):
        issues.append("INVALID_DATASET_IDENTITY")
    if not schema_id.startswith("schema-"):
        issues.append("INVALID_SCHEMA_IDENTITY")
    if not source_id.startswith("source-"):
        issues.append("INVALID_SOURCE_IDENTITY")
    if not environment_id.startswith("environment-"):
        issues.append("INVALID_ENVIRONMENT_IDENTITY")
    if not config_id.startswith("configuration-"):
        issues.append("INVALID_CONFIGURATION_IDENTITY")

    status = VALID if not issues else INVALID
    report_id = stable_identity(
        "reproducibility-audit-",
        {
            "version": REPRODUCIBILITY_AUDIT_VERSION,
            "status": status,
            "dataset": dataset_id,
            "schema": schema_id,
            "source": source_id,
            "environment": environment_id,
            "configuration": config_id,
            "artifacts": artifacts,
            "replay": [
                {
                    "name": item.name,
                    "first": item.first_identity,
                    "second": item.second_identity,
                    "reproducible": item.reproducible,
                }
                for item in replay_checks
            ],
            "issues": tuple(sorted(set(issues))),
        },
    )
    return ReproducibilityAuditReport(
        version=REPRODUCIBILITY_AUDIT_VERSION,
        status=status,
        dataset_identity=dataset_id,
        schema_identity=schema_id,
        source_identity=source_id,
        environment_identity=environment_id,
        configuration_identity=config_id,
        artifact_identities=artifacts,
        replay_checks=replay_checks,
        issues=tuple(sorted(set(issues))),
        report_identity=report_id,
    )


def validate_reproducibility_audit(
    report: ReproducibilityAuditReport,
) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != REPRODUCIBILITY_AUDIT_VERSION:
        issues.append("INVALID_VERSION")
    if not report.report_identity.startswith("reproducibility-audit-"):
        issues.append("INVALID_REPORT_IDENTITY")
    for prefix, identity, code in (
        ("dataset-", report.dataset_identity, "INVALID_DATASET_FINGERPRINT"),
        ("schema-", report.schema_identity, "INVALID_SCHEMA_FINGERPRINT"),
        ("source-", report.source_identity, "INVALID_SOURCE_FINGERPRINT"),
        ("environment-", report.environment_identity, "INVALID_ENVIRONMENT_FINGERPRINT"),
        ("configuration-", report.configuration_identity, "INVALID_CONFIGURATION_FINGERPRINT"),
    ):
        if not identity.startswith(prefix) or len(identity) != len(prefix) + 64:
            issues.append(code)
    for check in report.replay_checks:
        if check.first_identity != check.second_identity:
            issues.append(f"REPLAY_MISMATCH:{check.name}")
    unique = tuple(sorted(set(issues)))
    return (VALID if not unique else INVALID, unique)


def reproducibility_summary(
    report: ReproducibilityAuditReport,
) -> dict[str, Any]:
    status, issues = validate_reproducibility_audit(report)
    return {
        "status": status,
        "version": report.version,
        "dataset_identity": report.dataset_identity,
        "schema_identity": report.schema_identity,
        "source_identity": report.source_identity,
        "environment_identity": report.environment_identity,
        "configuration_identity": report.configuration_identity,
        "artifact_count": len(report.artifact_identities),
        "replay_checks": [
            {
                "name": item.name,
                "reproducible": item.reproducible,
                "first_identity": item.first_identity,
                "second_identity": item.second_identity,
            }
            for item in report.replay_checks
        ],
        "issues": issues,
        "report_identity": report.report_identity,
    }


def write_reproducibility_report(
    report: ReproducibilityAuditReport,
    path: Path | None = None,
) -> Path:
    destination = path or (PROJECT_ROOT / "reports" / "reproducibility_audit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(reproducibility_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "REPRODUCIBILITY_AUDIT_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_SEED",
    "ReplayCheck",
    "ReproducibilityAuditReport",
    "stable_identity",
    "seed_everything",
    "deterministic_configuration",
    "dataset_fingerprint",
    "schema_fingerprint",
    "source_fingerprint",
    "environment_snapshot",
    "environment_identity",
    "configuration_identity",
    "artifact_fingerprints",
    "replay_check",
    "database_schema_matches_live",
    "run_reproducibility_audit",
    "validate_reproducibility_audit",
    "reproducibility_summary",
    "write_reproducibility_report",
]
