from __future__ import annotations

import json

import pytest

from analytics.failure_recovery import (
    FAILURE_ARTIFACT,
    FAILURE_CONFIGURATION,
    FAILURE_DATABASE,
    FAILURE_INPUT,
    INVALID,
    VALID,
    WARNING,
    atomic_write_json,
    classify_exception,
    failure_event,
    load_json_with_recovery,
    quarantine_artifact,
    recovery_status,
    retry_operation,
    rollback_session,
    run_failure_recovery_audit,
    validate_model_artifact,
)


def test_exception_classification():
    from sqlalchemy.exc import OperationalError
    assert classify_exception(OperationalError("statement", {}, Exception("db"))) == FAILURE_DATABASE
    assert classify_exception(FileNotFoundError("missing")) == FAILURE_ARTIFACT
    assert classify_exception(json.JSONDecodeError("bad", "{", 0)) == FAILURE_CONFIGURATION
    assert classify_exception(ValueError("bad input")) == FAILURE_INPUT


def test_retry_recovers_transient_failure():
    state = {"calls": 0}

    def operation():
        state["calls"] += 1
        if state["calls"] == 1:
            raise TimeoutError("temporary")
        return "ok"

    value, result, events = retry_operation(operation, retries=2)
    assert value == "ok"
    assert result.status == VALID
    assert result.recovered is True
    assert result.attempts == 2
    assert len(events) == 1


def test_non_retryable_failure_aborts_safely():
    value, result, events = retry_operation(lambda: (_ for _ in ()).throw(ValueError("bad")), retries=3)
    assert value is None
    assert result.status == INVALID
    assert result.action == "SAFE_ABORT"
    assert result.recovered is False
    assert len(events) == 1


def test_retry_rollback_callback_runs():
    state = {"rollback": 0}

    def rollback():
        state["rollback"] += 1

    value, result, events = retry_operation(
        lambda: (_ for _ in ()).throw(TimeoutError("temporary")),
        retries=0,
        rollback=rollback,
    )
    assert value is None
    assert state["rollback"] == 1
    assert result.action == "SAFE_ABORT"


def test_missing_json_can_use_safe_default(tmp_path):
    value, result = load_json_with_recovery(
        tmp_path / "missing.json",
        default={"status": "SAFE_DEFAULT"},
    )
    assert value == {"status": "SAFE_DEFAULT"}
    assert result.status == WARNING
    assert result.recovered is True


def test_invalid_json_can_use_safe_default(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    value, result = load_json_with_recovery(path, default={"status": "SAFE_DEFAULT"})
    assert value == {"status": "SAFE_DEFAULT"}
    assert result.status == WARNING
    assert result.failure_code == FAILURE_CONFIGURATION


def test_missing_required_json_without_default_aborts(tmp_path):
    value, result = load_json_with_recovery(tmp_path / "missing.json")
    assert value is None
    assert result.status == INVALID
    assert result.failure_code == FAILURE_ARTIFACT


def test_atomic_json_write(tmp_path):
    path = tmp_path / "artifact.json"
    result = atomic_write_json(path, {"phase": 96})
    assert result.status == VALID
    assert json.loads(path.read_text(encoding="utf-8")) == {"phase": 96}


def test_model_artifact_validation(tmp_path):
    path = tmp_path / "model.json"
    path.write_text('{"model": "demo"}', encoding="utf-8")
    result = validate_model_artifact(path, required_keys=("model",))
    assert result.status == VALID


def test_model_artifact_missing(tmp_path):
    result = validate_model_artifact(tmp_path / "missing.joblib")
    assert result.status == INVALID
    assert result.failure_code == FAILURE_ARTIFACT


def test_quarantine_moves_invalid_artifact(tmp_path):
    source = tmp_path / "bad.json"
    quarantine = tmp_path / "quarantine"
    source.write_text("bad", encoding="utf-8")
    result = quarantine_artifact(source, quarantine_dir=quarantine)
    assert result.status == VALID
    assert not source.exists()
    assert list(quarantine.iterdir())


def test_rollback_session():
    class Session:
        def __init__(self):
            self.called = False
        def rollback(self):
            self.called = True

    session = Session()
    result = rollback_session(session)
    assert session.called is True
    assert result.status == VALID


def test_recovery_status_is_non_destructive():
    status = recovery_status()
    assert status["status"] == VALID
    assert status["policy"]["automatic_delete"] is False
    assert status["policy"]["automatic_data_fabrication"] is False
    assert status["policy"]["automatic_model_replacement"] is False


def test_failure_event_is_bounded():
    event = failure_event(ValueError("x" * 1000), "test")
    assert len(event.message) <= 500
    assert event.failure_code == FAILURE_INPUT


def test_full_phase96_audit():
    report = run_failure_recovery_audit()
    assert report.status == VALID
    assert len(report.checks) == 6
    assert any(event.failure_code == "UNKNOWN_FAILURE" or event.failure_code == "ARTIFACT_FAILURE"
               for event in report.events)


@pytest.mark.parametrize("value", [-1, -0.1])
def test_invalid_retry_arguments(value):
    with pytest.raises(ValueError):
        retry_operation(lambda: "ok", retries=value)
