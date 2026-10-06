from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from database.engine import SessionLocal
from database.models import HistoricalResult

MANUAL_RETRAINING_VERSION = "92.1.0"
STATUS_PATH = Path(__file__).resolve().parent.parent / "reports" / "manual_retraining_status.json"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "manual_retrained"


def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "manual-retraining-" + hashlib.sha256(raw).hexdigest()


def _features(rows, index: int, lookback: int = 3):
    values = []
    start = max(0, index - lookback)
    for row in rows[start:index]:
        values.extend([getattr(row, f"col{i}") for i in range(1, 9)])
    while len(values) < lookback * 8:
        values.insert(0, 0)
    return values


def _write_status(payload: dict) -> dict:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def training_status() -> dict:
    if not STATUS_PATH.exists():
        return {
            "status": "NOT_TRAINED",
            "version": MANUAL_RETRAINING_VERSION,
            "message": "No manual retraining run has been completed.",
        }
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "INVALID",
            "version": MANUAL_RETRAINING_VERSION,
            "message": "Retraining status file could not be read.",
        }


def retrain_models() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    db = SessionLocal()
    try:
        rows = list(
            db.query(HistoricalResult)
            .order_by(HistoricalResult.market_id, HistoricalResult.result_date)
            .all()
        )
    finally:
        db.close()

    if len(rows) < 10:
        return _write_status({
            "status": "INSUFFICIENT_DATA",
            "version": MANUAL_RETRAINING_VERSION,
            "started_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(rows),
            "minimum_records": 10,
            "message": "At least 10 historical records are required before retraining.",
        })

    # Chronological holdout: the final 20% is never used for fitting.
    split = max(8, int(len(rows) * 0.80))
    if split >= len(rows):
        split = len(rows) - 1

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    positions = {}
    validation_scores = []
    trained = []

    for position in range(8):
        X = [_features(rows, i) for i in range(1, len(rows))]
        y = [getattr(rows[i], f"col{position + 1}") for i in range(1, len(rows))]
        train_count = max(6, min(split - 1, len(X) - 1))
        X_train, X_test = X[:train_count], X[train_count:]
        y_train, y_test = y[:train_count], y[train_count:]

        if len(set(y_train)) < 2:
            continue

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42 + position,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        prediction = model.predict(X_test) if X_test else []
        accuracy = float(accuracy_score(y_test, prediction)) if y_test else None
        f1 = float(f1_score(y_test, prediction, average="weighted", zero_division=0)) if y_test else None
        artifact_path = MODEL_DIR / f"position_{position + 1}.joblib"
        joblib.dump(model, artifact_path)

        positions[str(position + 1)] = {
            "model_path": str(artifact_path),
            "train_rows": len(X_train),
            "validation_rows": len(X_test),
            "validation_accuracy": accuracy,
            "validation_f1": f1,
            "classes": [int(v) for v in model.classes_],
        }
        if accuracy is not None:
            validation_scores.append(accuracy)
        trained.append(position + 1)

    mean_accuracy = sum(validation_scores) / len(validation_scores) if validation_scores else None
    payload = {
        "status": "COMPLETED" if trained else "FAILED",
        "version": MANUAL_RETRAINING_VERSION,
        "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(rows),
        "train_rows": max(0, split - 1),
        "validation_rows": max(0, len(rows) - split),
        "trained_positions": trained,
        "position_metrics": positions,
        "mean_validation_accuracy": mean_accuracy,
        "best_possible_validation_accuracy": 1.0,
        "model_activation": "NOT_AUTOMATIC",
        "message": (
            "Retraining completed. Validation accuracy is measured on held-out historical rows; "
            "this does not guarantee future or perfect prediction."
            if trained else
            "No position model could be trained from the current data."
        ),
    }
    payload["run_identity"] = _identity(payload)
    return _write_status(payload)


__all__ = ["MANUAL_RETRAINING_VERSION", "training_status", "retrain_models"]
