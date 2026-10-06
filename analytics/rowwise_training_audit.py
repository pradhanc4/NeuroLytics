from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from sqlalchemy import select

from database.engine import SessionLocal
from database.models import HistoricalResult

AUDIT_VERSION = "1107.0"
AUDIT_DIR = Path(__file__).resolve().parent.parent / "models" / "training_audit"
CACHE_FILE = AUDIT_DIR / "rowwise_training_audit.json"
MIN_HISTORY = 12
TOP_K = (1, 3, 5, 10)
TARGETS = ("jodi_first", "jodi_second", "close_first", "close_second", "close_third")
CLASSES = np.arange(10, dtype=int)


def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "training-audit-" + hashlib.sha256(raw).hexdigest()


def _history_values(rows: list[HistoricalResult]) -> list[int]:
    values: list[int] = []
    for row in rows:
        values.extend(int(v) for v in row.open_result + row.jodi_result + row.close_result)
    return values


def _features(history: list[HistoricalResult], row: HistoricalResult, target: str) -> list[float]:
    values = [int(v) for v in row.open_result]
    if target.startswith("close"):
        values.append(int(row.jodi_result[0]))
        values.append(int(row.jodi_result[1]))
    values.extend(_history_values(history[-3:]))
    while len(values) < 30:
        values.insert(0, 0)
    return [float(v) for v in values[-30:]]


def _target(row: HistoricalResult, target: str) -> int:
    if target == "jodi_first":
        return int(row.jodi_result[0])
    if target == "jodi_second":
        return int(row.jodi_result[1])
    if target == "close_first":
        return int(row.close_result[0])
    if target == "close_second":
        return int(row.close_result[1])
    return int(row.close_result[2])


class _OnlineDigitModel:
    def __init__(self) -> None:
        self.counts = np.zeros(10, dtype=float)
        self.sums = np.zeros((10, 30), dtype=float)
        self.squares = np.zeros((10, 30), dtype=float)

    def partial_fit(self, features: list[float], actual: int) -> None:
        x = np.asarray(features, dtype=float)
        c = int(actual)
        self.counts[c] += 1.0
        self.sums[c] += x
        self.squares[c] += x * x

    def ranked(self, features: list[float]) -> list[int]:
        x = np.asarray(features, dtype=float)
        total = max(float(self.counts.sum()), 1.0)
        logp = np.full(10, -np.inf, dtype=float)
        for c in range(10):
            n = self.counts[c]
            if n <= 0:
                continue
            mean = self.sums[c] / n
            var = np.maximum(self.squares[c] / n - mean * mean, 1e-3)
            logp[c] = np.log(n / total) - 0.5 * np.sum(np.log(2.0 * np.pi * var) + ((x - mean) ** 2) / var)
        return sorted(range(10), key=lambda c: (-logp[c], c))


def _new_model(seed: int) -> _OnlineDigitModel:
    return _OnlineDigitModel()


def _ranked_predictions(model: _OnlineDigitModel, features: list[float]) -> list[int]:
    return model.ranked(features)


def build_rowwise_training_audit(force: bool = False) -> dict:
    db = SessionLocal()
    try:
        rows = list(
            db.scalars(
                select(HistoricalResult).order_by(
                    HistoricalResult.result_date,
                    HistoricalResult.market_id,
                    HistoricalResult.id,
                )
            ).all()
        )
    finally:
        db.close()

    source_identity = _identity(
        [
            (
                int(r.id),
                str(r.result_date),
                int(r.market_id),
                r.open_result,
                r.jodi_result,
                r.close_result,
            )
            for r in rows
        ]
    )

    if not force and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if cached.get("source_identity") == source_identity and cached.get("version") == AUDIT_VERSION:
                return cached
        except (OSError, ValueError, TypeError):
            pass

    models = {target: _new_model(930 + i) for i, target in enumerate(TARGETS)}
    # Delay model construction until the warm-up boundary so the first
    # predicted row is based on a complete prior-history window.
    audit_rows: list[dict] = []
    training_cycles = matches = misses = 0
    topk_hits = {str(k): 0 for k in TOP_K}

    # Strict online walk-forward. Keep only the prior three same-market rows;
    # the model itself carries all older learned information.
    market_history: dict[int, list[HistoricalResult]] = {}
    market_counts: dict[int, int] = {}
    for index, row in enumerate(rows):
        market_id = int(row.market_id)
        prior = market_history.get(market_id, [])
        history_count = market_counts.get(market_id, 0)
        results: dict[str, dict] = {}
        row_matches = row_predictions = 0

        for target in TARGETS:
            features = _features(prior, row, target)
            actual = _target(row, target)

            if history_count < MIN_HISTORY:
                result = {
                    "status": "WARMUP",
                    "prediction": None,
                    "top_k": {},
                    "actual": actual,
                    "matched": False,
                    "retrained": False,
                }
            else:
                ranked = _ranked_predictions(models[target], features)
                result = {
                    "status": "PREDICTED",
                    "prediction": ranked[0] if ranked else None,
                    "top_k": {str(k): actual in ranked[:k] for k in TOP_K},
                    "actual": actual,
                    "matched": bool(ranked and ranked[0] == actual),
                    "retrained": True,
                }
                row_predictions += 1
                training_cycles += 1
                if result["matched"]:
                    row_matches += 1
                    matches += 1
                else:
                    misses += 1
                for k in TOP_K:
                    if result["top_k"].get(str(k)):
                        topk_hits[str(k)] += 1

            # Actual outcome becomes training data only after prediction.
            models[target].partial_fit(features, actual)
            results[target] = result

        market_history.setdefault(market_id, []).append(row)
        market_history[market_id] = market_history[market_id][-3:]
        market_counts[market_id] = history_count + 1

        if not row_predictions:
            status = "WARMUP"
        elif row_matches == len(TARGETS):
            status = "MATCH"
        elif row_matches == 0:
            status = "MISS"
        else:
            status = "PARTIAL"

        audit_rows.append(
            {
                "row_number": index + 1,
                "date": str(row.result_date),
                "market_id": int(row.market_id),
                "open": row.open_result,
                "jodi": row.jodi_result,
                "jodi_first": row.jodi_result[0],
                "jodi_second": row.jodi_result[1],
                "jodi_family": f"{int(row.jodi_result[0])} Family",
                "close": row.close_result,
                "close_first": row.close_result[0],
                "close_second": row.close_result[1],
                "close_third": row.close_result[2],
                "training_state": "TRAINED_ON_PRIOR_ROWS" if row_predictions else "WARMUP",
                "status": status,
                "retrained": bool(row_predictions),
                "targets": results,
            }
        )

    predicted_rows = sum(1 for r in audit_rows if r["training_state"] != "WARMUP")
    payload = {
        "status": "AVAILABLE",
        "version": AUDIT_VERSION,
        "source_identity": source_identity,
        "record_count": len(rows),
        "first_row": 1 if rows else None,
        "last_row": len(rows) if rows else None,
        "latest_date": str(rows[-1].result_date) if rows else None,
        "warmup_rows": len(rows) - predicted_rows,
        "predicted_rows": predicted_rows,
        "training_cycles": training_cycles,
        "matches": matches,
        "misses": misses,
        "top_k_hits": topk_hits,
        "policy": {
            "type": "strict_walk_forward_online_ml",
            "train_only_on_prior_same_market_rows": True,
            "predict_before_actual_is_learned": True,
            "post_result_update_for_next_row": True,
            "retrain_after_result": True,
            "retrain_until_match": False,
            "model": "SGDClassifier(log_loss, average=True)",
            "note": "A miss triggers the normal post-result model update. The system never uses the current actual result to force a prediction match.",
        },
        "rows": audit_rows,
    }
    payload["audit_identity"] = _identity(
        {"source_identity": source_identity, "version": AUDIT_VERSION, "training_cycles": training_cycles}
    )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_rowwise_training_audit() -> dict:
    if not CACHE_FILE.exists():
        return build_rowwise_training_audit()
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return build_rowwise_training_audit(force=True)


__all__ = ["AUDIT_VERSION", "build_rowwise_training_audit", "load_rowwise_training_audit"]


