from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

FAILURE_RECOVERY_VERSION = "96.0.0"
FAILURE_RECOVERY_BOUNDARY = "FAILURE_RECOVERY_BOUNDARY"
VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"

FAILURE_DATABASE = "DATABASE_FAILURE"
FAILURE_ARTIFACT = "ARTIFACT_FAILURE"
FAILURE_CONFIGURATION = "CONFIGURATION_FAILURE"
FAILURE_INPUT = "INPUT_FAILURE"
FAILURE_PREDICTION = "PREDICTION_FAILURE"
FAILURE_RETRAINING = "RETRAINING_FAILURE"
FAILURE_UNKNOWN = "UNKNOWN_FAILURE"

RETRYABLE_FAILURES = frozenset({
    "OperationalError", "TimeoutError", "ConnectionError",
})

@dataclass(frozen=True)
class FailureEvent:
    failure_code: str
    exception_type: str
    message: str
    operation: str
    retryable: bool
    timestamp: float

@dataclass(frozen=True)
class RecoveryResult:
    status: str
    action: str
    attempts: int
    failure_code: str | None
    message: str
    recovered: bool

@dataclass(frozen=True)
class RecoveryAuditReport:
    version: str
    status: str
    checks: tuple[dict[str, Any], ...]
    events: tuple[FailureEvent, ...]
    report_identity: str

def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "failure-recovery-" + hashlib.sha256(raw).hexdigest()

def classify_exception(exc: BaseException) -> str:
    name = type(exc).__name__
    if name in {"OperationalError", "IntegrityError", "DatabaseError"}:
        return FAILURE_DATABASE
    if name in {"FileNotFoundError", "PermissionError", "OSError"}:
        return FAILURE_ARTIFACT
    if name in {"JSONDecodeError", "UnicodeDecodeError"}:
        return FAILURE_CONFIGURATION
    if name in {"ValueError", "TypeError", "KeyError"}:
        return FAILURE_INPUT
    return FAILURE_UNKNOWN

def is_retryable(exc: BaseException) -> bool:
    return type(exc).__name__ in RETRYABLE_FAILURES

def failure_event(exc: BaseException, operation: str) -> FailureEvent:
    return FailureEvent(
        classify_exception(exc), type(exc).__name__, str(exc)[:500],
        str(operation), is_retryable(exc), time.time(),
    )

def rollback_session(session: Any) -> RecoveryResult:
    try:
        session.rollback()
        return RecoveryResult(VALID, "DATABASE_ROLLBACK", 1, None,
                              "Database transaction rolled back safely.", True)
    except Exception as exc:
        return RecoveryResult(INVALID, "DATABASE_ROLLBACK_FAILED", 1,
                              classify_exception(exc), "Database rollback failed.", False)

def retry_operation(
    operation: Callable[[], Any],
    *,
    retries: int = 2,
    delay_seconds: float = 0.0,
    rollback: Callable[[], Any] | None = None,
) -> tuple[Any | None, RecoveryResult, tuple[FailureEvent, ...]]:
    if retries < 0:
        raise ValueError("retries must be non-negative.")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be non-negative.")
    events: list[FailureEvent] = []
    attempts = 0
    while attempts <= retries:
        attempts += 1
        try:
            value = operation()
            return value, RecoveryResult(
                VALID, "RETRY_ORIGINAL_OPERATION", attempts, None,
                "Operation completed successfully.", True,
            ), tuple(events)
        except Exception as exc:
            event = failure_event(exc, "retry_operation")
            events.append(event)
            if rollback is not None:
                try:
                    rollback()
                except Exception as rollback_exc:
                    events.append(failure_event(rollback_exc, "rollback"))
            if not event.retryable or attempts > retries:
                return None, RecoveryResult(
                    INVALID, "SAFE_ABORT", attempts, event.failure_code,
                    "Operation failed and was safely aborted.", False,
                ), tuple(events)
            if delay_seconds:
                time.sleep(delay_seconds)
    return None, RecoveryResult(INVALID, "SAFE_ABORT", attempts,
                                FAILURE_UNKNOWN, "Operation was safely aborted.", False), tuple(events)

def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> RecoveryResult:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, destination)
        return RecoveryResult(VALID, "ATOMIC_WRITE", 1, None,
                              "JSON artifact committed atomically.", True)
    except Exception as exc:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        return RecoveryResult(INVALID, "ATOMIC_WRITE_ABORT", 1,
                              classify_exception(exc), "Artifact write was aborted safely.", False)

def load_json_with_recovery(
    path: str | Path,
    *,
    default: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, RecoveryResult]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON root must be an object.")
        return value, RecoveryResult(VALID, "LOAD_ARTIFACT", 1, None,
                                     "JSON artifact loaded.", True)
    except FileNotFoundError:
        if default is not None:
            return dict(default), RecoveryResult(WARNING, "SAFE_DEFAULT", 1,
                FAILURE_ARTIFACT, "Artifact was missing; safe default returned.", True)
        return None, RecoveryResult(INVALID, "SAFE_ABORT", 1, FAILURE_ARTIFACT,
                                    "Required artifact is missing.", False)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        if default is not None:
            return dict(default), RecoveryResult(WARNING, "SAFE_DEFAULT", 1,
                FAILURE_CONFIGURATION, "Artifact was invalid; safe default returned.", True)
        return None, RecoveryResult(INVALID, "SAFE_ABORT", 1,
                                    classify_exception(exc), "Artifact is invalid.", False)

def validate_model_artifact(
    path: str | Path,
    *,
    required_keys: tuple[str, ...] = (),
) -> RecoveryResult:
    source = Path(path)
    if not source.exists():
        return RecoveryResult(INVALID, "ARTIFACT_MISSING", 1,
                              FAILURE_ARTIFACT, "Model artifact does not exist.", False)
    try:
        if source.stat().st_size <= 0:
            return RecoveryResult(INVALID, "ARTIFACT_EMPTY", 1,
                                  FAILURE_ARTIFACT, "Model artifact is empty.", False)
        if source.suffix.lower() == ".json":
            value = json.loads(source.read_text(encoding="utf-8"))
            missing = [key for key in required_keys if key not in value]
            if missing:
                return RecoveryResult(INVALID, "ARTIFACT_SCHEMA_INVALID", 1,
                    FAILURE_ARTIFACT, "Required artifact metadata is missing.", False)
        return RecoveryResult(VALID, "ARTIFACT_VALIDATED", 1, None,
                              "Model artifact passed basic recovery validation.", True)
    except Exception as exc:
        return RecoveryResult(INVALID, "ARTIFACT_INVALID", 1,
                              classify_exception(exc), "Model artifact could not be validated.", False)

def quarantine_artifact(
    path: str | Path,
    *,
    quarantine_dir: str | Path = "reports/quarantine",
) -> RecoveryResult:
    source = Path(path)
    if not source.exists():
        return RecoveryResult(INVALID, "QUARANTINE_SOURCE_MISSING", 1,
                              FAILURE_ARTIFACT, "Artifact to quarantine is missing.", False)
    destination_dir = Path(quarantine_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    if destination.exists():
        destination = destination_dir / f"{source.stem}-{int(time.time() * 1000)}{source.suffix}"
    try:
        shutil.move(str(source), str(destination))
        return RecoveryResult(VALID, "ARTIFACT_QUARANTINED", 1, None,
                              f"Invalid artifact moved to quarantine: {destination}", True)
    except Exception as exc:
        return RecoveryResult(INVALID, "QUARANTINE_FAILED", 1,
                              classify_exception(exc), "Artifact quarantine failed; source retained.", False)

def recovery_status() -> dict[str, Any]:
    return {
        "status": VALID,
        "version": FAILURE_RECOVERY_VERSION,
        "boundary": FAILURE_RECOVERY_BOUNDARY,
        "policy": {
            "automatic_delete": False,
            "automatic_data_fabrication": False,
            "automatic_model_replacement": False,
            "database_rollback": True,
            "retry_transient_operations": True,
            "invalid_artifact_quarantine": True,
            "safe_abort_on_unrecoverable_failure": True,
        },
    }

def run_failure_recovery_audit() -> RecoveryAuditReport:
    checks: list[dict[str, Any]] = []
    events: list[FailureEvent] = []

    attempts = {"count": 0}
    def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("injected transient failure")
        return "ok"

    value, result, retry_events = retry_operation(flaky, retries=2)
    events.extend(retry_events)
    checks.append({
        "name": "transient_retry",
        "status": VALID if value == "ok" and result.recovered else INVALID,
        "attempts": result.attempts,
    })

    default_value, default_result = load_json_with_recovery(
        "__phase96_missing__.json", default={"status": "SAFE_DEFAULT"}
    )
    checks.append({
        "name": "missing_artifact_safe_default",
        "status": VALID if default_value == {"status": "SAFE_DEFAULT"} and default_result.recovered else INVALID,
    })

    root = Path("reports") / ".phase96-recovery-audit"
    root.mkdir(parents=True, exist_ok=True)
    config = root / "config.json"
    write_result = atomic_write_json(config, {"phase": 96, "status": "ok"})
    checks.append({
        "name": "atomic_artifact_write",
        "status": VALID if write_result.recovered and config.exists() else INVALID,
    })

    corrupt = root / "corrupt.json"
    corrupt.write_text("{broken", encoding="utf-8")
    value, corrupt_result = load_json_with_recovery(corrupt, default={"status": "SAFE_DEFAULT"})
    checks.append({
        "name": "corrupt_artifact_safe_default",
        "status": VALID if value == {"status": "SAFE_DEFAULT"} and corrupt_result.recovered else INVALID,
    })

    artifact = root / "artifact.json"
    artifact.write_text('{"model": "phase96"}', encoding="utf-8")
    artifact_result = validate_model_artifact(artifact, required_keys=("model",))
    checks.append({
        "name": "artifact_validation",
        "status": artifact_result.status,
    })

    checks.append({
        "name": "safe_policy",
        "status": VALID,
        "automatic_delete": False,
        "automatic_data_fabrication": False,
        "automatic_model_replacement": False,
    })

    status = VALID if all(check["status"] == VALID for check in checks) else INVALID
    identity = _identity({
        "version": FAILURE_RECOVERY_VERSION,
        "checks": checks,
        "events": [
            (event.failure_code, event.exception_type, event.operation)
            for event in events
        ],
    })
    return RecoveryAuditReport(
        FAILURE_RECOVERY_VERSION, status, tuple(checks), tuple(events), identity
    )

def failure_recovery_summary(report: RecoveryAuditReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "version": report.version,
        "boundary": FAILURE_RECOVERY_BOUNDARY,
        "checks": list(report.checks),
        "events": [
            {
                "failure_code": event.failure_code,
                "exception_type": event.exception_type,
                "message": event.message,
                "operation": event.operation,
                "retryable": event.retryable,
            }
            for event in report.events
        ],
        "report_identity": report.report_identity,
    }

def write_failure_recovery_report(
    report: RecoveryAuditReport,
    path: str | Path = "reports/failure_recovery_audit.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(failure_recovery_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination

__all__ = [
    "FAILURE_RECOVERY_VERSION", "FAILURE_RECOVERY_BOUNDARY",
    "VALID", "WARNING", "INVALID",
    "FAILURE_DATABASE", "FAILURE_ARTIFACT", "FAILURE_CONFIGURATION",
    "FAILURE_INPUT", "FAILURE_PREDICTION", "FAILURE_RETRAINING", "FAILURE_UNKNOWN",
    "FailureEvent", "RecoveryResult", "RecoveryAuditReport",
    "classify_exception", "is_retryable", "failure_event",
    "rollback_session", "retry_operation", "atomic_write_json",
    "load_json_with_recovery", "validate_model_artifact", "quarantine_artifact",
    "recovery_status", "run_failure_recovery_audit",
    "failure_recovery_summary", "write_failure_recovery_report",
]
