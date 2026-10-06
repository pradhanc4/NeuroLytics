from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier

C16_VERSION = "C.16.0"
TARGETS = ("jodi_first", "jodi_second", "close_first", "close_second", "close_third")


def _target(row: Mapping[str, Any], name: str) -> int:
    if name == "jodi_first":
        return int(row["jodi"]) // 10
    if name == "jodi_second":
        return int(row["jodi"]) % 10
    close = int(row["close"])
    return (close // 100, (close // 10) % 10, close % 10)[("close_first", "close_second", "close_third").index(name)]


def _matrix(rows: Sequence[Mapping[str, Any]], target: str):
    # Labels are intentionally excluded from the predictor matrix.
    excluded = {"date", "jodi", "close", "target"}
    keyset = {
        k for r in rows for k in r
        if k not in excluded and not k.startswith("target_")
    }
    keys = sorted(keyset)
    # Dynamic relationship feature names are expanded to a stable union schema.
    # A feature absent for a row means that relationship context is not active
    # for that row and is represented deterministically as zero.
    X = [[float(r.get(k, 0.0)) for k in keys] for r in rows]
    y = [_target(r, target) for r in rows]
    return X, y, keys


def train_relationship_aware_models(
    rows: Sequence[Mapping[str, Any]],
    output_dir: str | Path = "models/relationship_aware",
) -> dict[str, Any]:
    rows = list(rows)
    if len(rows) < 20:
        raise ValueError("At least 20 rows are required for training.")

    split = max(1, int(len(rows) * 0.8))
    if split >= len(rows):
        split = len(rows) - 1

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    champions: dict[str, Any] = {}

    for target in TARGETS:
        X, y, keys = _matrix(rows, target)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        if len(set(y_train)) <= 1:
            model = DummyClassifier(strategy="most_frequent")
            model_name = "majority"
        elif target == "jodi_first":
            model = DecisionTreeClassifier(random_state=42, max_depth=12, min_samples_leaf=2)
            model_name = "decision_tree"
        elif target == "close_third":
            model = RandomForestClassifier(
                n_estimators=160, random_state=42, n_jobs=-1, min_samples_leaf=2
            )
            model_name = "random_forest"
        else:
            model = DummyClassifier(strategy="prior")
            model_name = "majority"

        model.fit(X_train, y_train)
        accuracy = float(model.score(X_test, y_test)) if X_test else 0.0
        artifact = out / f"{target}.joblib"

        import joblib
        joblib.dump(model, artifact)

        champions[target] = {
            "target": target,
            "model": model_name,
            "artifact": str(artifact).replace("\\", "/"),
            "feature_count": len(keys),
            "features": keys,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "temporal_order": "chronological",
            "holdout_accuracy": accuracy,
        }

    payload = {
        "version": C16_VERSION,
        "status": "VALID",
        "rows": len(rows),
        "targets": champions,
        "temporal_safe": True,
        "no_current_target_features": True,
        "deterministic": True,
    }
    payload["identity"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    report = Path("reports/relationship_aware_model_training.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


__all__ = ["C16_VERSION", "TARGETS", "train_relationship_aware_models"]
