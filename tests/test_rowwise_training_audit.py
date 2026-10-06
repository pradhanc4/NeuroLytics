from __future__ import annotations

import json

from analytics.rowwise_training_audit import (
    AUDIT_VERSION,
    _features,
    _target,
    build_rowwise_training_audit,
)
from database.models import HistoricalResult


def _row(i: int, market: int = 1) -> HistoricalResult:
    row = HistoricalResult(
        id=i,
        market_id=market,
        result_date=f"2026-01-{i:02d}",
        open_result=[i % 10, (i + 1) % 10, (i + 2) % 10],
        jodi_result=[i % 10, (i + 3) % 10],
        close_result=[(i + 4) % 10, (i + 5) % 10, (i + 6) % 10],
    )
    return row


def test_target_mapping():
    row = _row(1)
    assert _target(row, "jodi_first") == 1
    assert _target(row, "jodi_second") == 4
    assert _target(row, "close_first") == 5
    assert _target(row, "close_second") == 6
    assert _target(row, "close_third") == 7


def test_feature_vector_is_fixed_length_and_target_aware():
    history = [_row(i) for i in range(1, 4)]
    row = _row(4)
    jodi_features = _features(history, row, "jodi_first")
    close_features = _features(history, row, "close_first")
    assert len(jodi_features) == 30
    assert len(close_features) == 30
    assert close_features != jodi_features


def test_build_audit_is_available_and_strict(monkeypatch, tmp_path):
    rows = [_row(i) for i in range(1, 16)]

    class FakeScalars:
        def all(self):
            return rows

    class FakeDB:
        def scalars(self, statement):
            return FakeScalars()
        def close(self):
            pass

    monkeypatch.setattr("analytics.rowwise_training_audit.SessionLocal", lambda: FakeDB())
    monkeypatch.setattr("analytics.rowwise_training_audit.CACHE_FILE", tmp_path / "audit.json")
    monkeypatch.setattr("analytics.rowwise_training_audit.AUDIT_DIR", tmp_path)

    result = build_rowwise_training_audit(force=True)

    assert result["status"] == "AVAILABLE"
    assert result["version"] == AUDIT_VERSION
    assert result["record_count"] == 15
    assert result["warmup_rows"] >= 1
    assert result["predicted_rows"] + result["warmup_rows"] == 15
    assert result["policy"]["train_only_on_prior_same_market_rows"] is True
    assert result["policy"]["predict_before_actual_is_learned"] is True
    assert result["policy"]["retrain_until_match"] is False
    assert len(result["rows"]) == 15
    assert (tmp_path / "audit.json").exists()

    payload = json.loads((tmp_path / "audit.json").read_text(encoding="utf-8"))
    assert payload["audit_identity"] == result["audit_identity"]


def test_market_history_is_isolated():
    first = _row(1, market=1)
    second = _row(2, market=2)
    assert first.market_id != second.market_id
