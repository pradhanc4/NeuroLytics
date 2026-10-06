from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Iterable

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss
from sqlalchemy import select

from analytics.jodi_ranking import (
    OPERATIONAL_TOP_K,
    jodi_top_k_views,
    panel_candidates_for_jodi,
    rank_jodis_from_b1_outputs,
    validate_jodi_family_constraint,
)
from database.engine import SessionLocal
from database.models import HistoricalResult, Market

SEQUENTIAL_MODEL_VERSION = "93.1.0"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "sequential"
MIN_TRAIN_ROWS = 12

# B.1 deliberately keeps the two Jodi digits as separate targets.
# The second digit is NOT fed the first digit in this phase. Conditioning
# on the actual Stage-1 Jodi-first digit is reserved for the next phase.
JODI_TARGET_NAMES = ("jodi_first", "jodi_second")
CLOSE_TARGET_NAMES = ("close_first", "close_second", "close_third")
TARGET_NAMES = JODI_TARGET_NAMES + CLOSE_TARGET_NAMES
# Keep the operational contract unchanged. Dashboard validation additionally exposes Top-7.
JODI_TOP_K = OPERATIONAL_TOP_K
DASHBOARD_TOP_K = tuple(sorted(set(JODI_TOP_K) | {7}))


def _identity(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return "sequential-" + hashlib.sha256(raw).hexdigest()


def _digits(open_result: str, jodi_first: str | None = None) -> list[int]:
    values = [int(v) for v in open_result]
    if jodi_first is not None:
        values.append(int(jodi_first))
    return values


def _history_values(previous: Iterable[HistoricalResult]) -> list[int]:
    values: list[int] = []
    for row in previous:
        values.extend(
            int(v)
            for v in (
                row.open_result
                + row.jodi_result
                + row.close_result
            )
        )
    return values


def _pad_features(values: list[int], width: int = 28) -> list[int]:
    values = list(values)
    while len(values) < width:
        values.insert(0, 0)
    return values[-width:]


def _jodi_features(
    rows: list[HistoricalResult],
    index: int,
) -> list[int]:
    """Leakage-safe B.1 features for both independent Jodi digit models.

    The current row contributes Open only. Its Jodi result is never used.
    The previous three completed rows contribute Open + Jodi + Close.
    """
    current = rows[index]
    values = _digits(current.open_result)
    values.extend(_history_values(rows[max(0, index - 3):index]))
    return _pad_features(values)


def _stage2_features(
    rows: list[HistoricalResult],
    index: int,
    jodi_first: str,
) -> list[int]:
    """Stage-2 features after the first Jodi digit is known."""
    current = rows[index]
    values = _digits(current.open_result, jodi_first)
    values.extend(_history_values(rows[max(0, index - 3):index]))
    return _pad_features(values)


def _close_features(
    rows: list[HistoricalResult],
    index: int,
) -> list[int]:
    """Leakage-safe features for Close after actual Jodi-first is available."""
    row = rows[index]
    return _stage2_features(rows, index, row.jodi_result[0])


def _targets(row: HistoricalResult) -> list[int]:
    return [
        int(row.jodi_result[0]),
        int(row.jodi_result[1]),
        int(row.close_result[0]),
        int(row.close_result[1]),
        int(row.close_result[2]),
    ]


def _market_training_samples(
    rows: list[HistoricalResult],
) -> list[tuple[list[int], list[int], object]]:
    grouped: dict[int, list[HistoricalResult]] = {}
    for row in rows:
        grouped.setdefault(int(row.market_id), []).append(row)

    samples: list[tuple[list[int], list[int], object]] = []
    for market_id in sorted(grouped):
        market_rows = sorted(
            grouped[market_id],
            key=lambda row: (row.result_date, row.id),
        )
        for index in range(1, len(market_rows)):
            row = market_rows[index]
            samples.append(
                (
                    _jodi_features(market_rows, index),
                    _targets(row),
                    row.result_date,
                )
            )
    return samples


def _close_training_samples(
    rows: list[HistoricalResult],
) -> list[tuple[list[int], list[int], object]]:
    grouped: dict[int, list[HistoricalResult]] = {}
    for row in rows:
        grouped.setdefault(int(row.market_id), []).append(row)

    samples: list[tuple[list[int], list[int], object]] = []
    for market_id in sorted(grouped):
        market_rows = sorted(
            grouped[market_id],
            key=lambda row: (row.result_date, row.id),
        )
        for index in range(1, len(market_rows)):
            row = market_rows[index]
            samples.append(
                (
                    _close_features(market_rows, index),
                    _targets(row),
                    row.result_date,
                )
            )
    return samples


def _split_samples(
    samples: list[tuple[list[int], list[int], object]],
) -> tuple[list, list, object]:
    ordered = sorted(samples, key=lambda item: item[2])
    unique_dates = sorted({item[2] for item in ordered})
    split_date = unique_dates[
        max(0, int(len(unique_dates) * 0.8) - 1)
    ]
    train_samples = [
        item for item in ordered if item[2] <= split_date
    ]
    validation_samples = [
        item for item in ordered if item[2] > split_date
    ]

    if not train_samples or not validation_samples:
        split_index = max(
            1,
            min(
                len(ordered) - 1,
                int(len(ordered) * 0.8),
            ),
        )
        train_samples = ordered[:split_index]
        validation_samples = ordered[split_index:]
        split_date = train_samples[-1][2]

    return train_samples, validation_samples, split_date


def _top_k_metrics(
    y_true: list[int],
    probabilities: list[list[float]],
    classes: list[int],
) -> dict[str, float]:
    class_to_index = {
        int(value): index
        for index, value in enumerate(classes)
    }
    metrics: dict[str, float] = {}
    for k in DASHBOARD_TOP_K:
        hits = 0
        for actual, row_probs in zip(y_true, probabilities):
            order = sorted(
                range(len(row_probs)),
                key=lambda index: (-row_probs[index], classes[index]),
            )
            candidates = {
                int(classes[index])
                for index in order[: min(k, len(order))]
            }
            hits += int(actual in candidates)
        metrics[f"top_{k}_accuracy"] = (
            float(hits / len(y_true))
            if y_true
            else 0.0
        )
    metrics["exact_top_1_accuracy"] = metrics["top_1_accuracy"]

    if y_true:
        valid = [
            actual in class_to_index
            for actual in y_true
        ]
        if all(valid) and len(classes) > 1:
            try:
                metrics["log_loss"] = float(
                    log_loss(
                        y_true,
                        probabilities,
                        labels=classes,
                    )
                )
            except ValueError:
                metrics["log_loss"] = 0.0
        else:
            metrics["log_loss"] = 0.0
    else:
        metrics["log_loss"] = 0.0

    return metrics


def _fit_model(
    name: str,
    target_index: int,
    train_samples: list,
    validation_samples: list,
) -> tuple[RandomForestClassifier, dict]:
    X_train = [item[0] for item in train_samples]
    X_validation = [item[0] for item in validation_samples]
    y_train = [item[1][target_index] for item in train_samples]
    y_validation = [
        item[1][target_index]
        for item in validation_samples
    ]

    model = RandomForestClassifier(
        n_estimators=400,
        random_state=930 + target_index,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    model.fit(X_train, y_train)

    probabilities_array = model.predict_proba(X_validation)
    prediction = model.predict(X_validation)
    classes = [int(value) for value in model.classes_]
    probabilities = [
        [float(value) for value in row]
        for row in probabilities_array
    ]

    metrics = _top_k_metrics(
        y_validation,
        probabilities,
        classes,
    )
    metrics["validation_accuracy"] = float(
        accuracy_score(y_validation, prediction)
    )
    metrics.update(
        {
            "train_rows": len(X_train),
            "validation_rows": len(X_validation),
            "classes": classes,
            "artifact": str(MODEL_DIR / f"{name}.joblib"),
        }
    )

    joblib.dump(
        model,
        MODEL_DIR / f"{name}.joblib",
    )
    return model, metrics


def train_sequential_models() -> dict:
    """Train B.1 independent Jodi digit models plus Stage-2 Close models."""
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

    if len(rows) < MIN_TRAIN_ROWS:
        return {
            "status": "INSUFFICIENT_DATA",
            "version": SEQUENTIAL_MODEL_VERSION,
            "record_count": len(rows),
            "minimum_records": MIN_TRAIN_ROWS,
            "message": (
                "Add more complete historical Open/Jodi/Close rows "
                "before sequential training."
            ),
        }

    jodi_samples = _market_training_samples(rows)
    close_samples = _close_training_samples(rows)

    if len(jodi_samples) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "version": SEQUENTIAL_MODEL_VERSION,
            "record_count": len(rows),
            "training_samples": len(jodi_samples),
            "minimum_records": MIN_TRAIN_ROWS,
            "message": (
                "At least two same-market chronological training "
                "samples are required."
            ),
        }

    jodi_train, jodi_validation, jodi_split_date = _split_samples(
        jodi_samples
    )
    close_train, close_validation, close_split_date = _split_samples(
        close_samples
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    metrics: dict[str, dict] = {}

    for target_index, target_name in enumerate(
        JODI_TARGET_NAMES
    ):
        _, target_metrics = _fit_model(
            target_name,
            target_index,
            jodi_train,
            jodi_validation,
        )
        metrics[target_name] = target_metrics
        metrics[target_name]["feature_mode"] = (
            "open_plus_prior_completed_history"
        )
        metrics[target_name]["independent_jodi_target"] = True

    for offset, target_name in enumerate(
        CLOSE_TARGET_NAMES,
        start=2,
    ):
        _, target_metrics = _fit_model(
            target_name,
            offset,
            close_train,
            close_validation,
        )
        metrics[target_name] = target_metrics
        metrics[target_name]["feature_mode"] = (
            "open_plus_actual_jodi_first_plus_prior_completed_history"
        )
        metrics[target_name]["independent_jodi_target"] = False

    validation_start_candidates = [
        item[2] for item in jodi_validation + close_validation
    ]
    validation_start = min(validation_start_candidates)

    payload = {
        "status": "COMPLETED",
        "version": SEQUENTIAL_MODEL_VERSION,
        "record_count": len(rows),
        "training_samples": len(jodi_samples),
        "train_rows": len(jodi_train),
        "validation_rows": len(jodi_validation),
        "train_end_date": str(jodi_split_date),
        "validation_start_date": str(validation_start),
        "market_specific_history": True,
        "strict_temporal_boundary": True,
        "jodi_b1_independent": True,
        "jodi_prediction_targets": list(JODI_TARGET_NAMES),
        "jodi_operational_top_k": list(JODI_TOP_K),
        "jodi_first_feature_mode": (
            "current_open_plus_prior_completed_history"
        ),
        "jodi_second_feature_mode": (
            "current_open_plus_prior_completed_history"
        ),
        "close_feature_mode": (
            "current_open_plus_actual_jodi_first_plus_prior_completed_history"
        ),
        "metrics": metrics,
        "model_identity": _identity(
            {
                "metrics": metrics,
                "train_end_date": str(jodi_split_date),
                "validation_start_date": str(validation_start),
                "market_specific_history": True,
                "strict_temporal_boundary": True,
                "jodi_b1_independent": True,
            }
        ),
        "message": (
            "Phase B.1 trains Jodi first and second digits as separate "
            "leakage-safe models. Both Jodi targets use only current Open "
            "and prior completed history; Close models use actual Stage-1 "
            "Jodi-first input."
        ),
    }

    (MODEL_DIR / "training_status.json").write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return payload


def load_status() -> dict:
    path = MODEL_DIR / "training_status.json"
    if not path.exists():
        return {
            "status": "NOT_TRAINED",
            "version": SEQUENTIAL_MODEL_VERSION,
            "message": "Sequential model has not been trained yet.",
        }
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )
    if payload.get("version") != SEQUENTIAL_MODEL_VERSION:
        return {
            "status": "NOT_TRAINED",
            "version": SEQUENTIAL_MODEL_VERSION,
            "previous_version": payload.get("version"),
            "message": (
                "Sequential model artifact is stale and must be retrained "
                "for the current model version."
            ),
        }
    return payload


def _load_models() -> dict[str, RandomForestClassifier]:
    status = load_status()
    if status.get("status") != "COMPLETED":
        raise ValueError("Sequential model is not trained.")
    if not status.get("strict_temporal_boundary") or not status.get(
        "market_specific_history"
    ):
        raise ValueError(
            "Sequential model artifact does not satisfy "
            "temporal-safety requirements."
        )

    result: dict[str, RandomForestClassifier] = {}
    for name in TARGET_NAMES:
        path = MODEL_DIR / f"{name}.joblib"
        if not path.exists():
            raise ValueError(
                f"Sequential model artifact is missing: {name}"
            )
        result[name] = joblib.load(path)
    return result


def _prediction_history(
    market_id: int | None,
) -> list[HistoricalResult]:
    db = SessionLocal()
    try:
        query = select(HistoricalResult).order_by(
            HistoricalResult.result_date,
            HistoricalResult.id,
        )
        if market_id is not None:
            query = query.where(
                HistoricalResult.market_id == market_id
            )
        return list(db.scalars(query).all())
    finally:
        db.close()


def _resolve_market_id(
    market_id: int | None,
    market_name: str | None,
) -> int | None:
    if market_id is not None:
        return int(market_id)

    db = SessionLocal()
    try:
        if market_name:
            market = db.scalar(
                select(Market).where(
                    Market.name == market_name
                )
            )
            if market is None:
                raise ValueError("Market not found.")
            return int(market.id)

        markets = list(
            db.scalars(
                select(Market).order_by(Market.id)
            ).all()
        )
        if len(markets) == 1:
            return int(markets[0].id)
        if len(markets) == 0:
            return None
        raise ValueError(
            "market_id or market_name is required when "
            "multiple markets exist."
        )
    finally:
        db.close()


def _rank_prediction(
    model: RandomForestClassifier,
    features: list[int],
    top_k: int,
) -> list[dict[str, float | int]]:
    probabilities = model.predict_proba([features])[0]
    pairs = sorted(
        (
            (int(cls), float(probability))
            for cls, probability in zip(
                model.classes_,
                probabilities,
            )
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return [
        {
            "digit": digit,
            "probability": probability,
            "rank": rank,
        }
        for rank, (digit, probability) in enumerate(
            pairs[:top_k],
            start=1,
        )
    ]


def predict_jodi_digits(
    open_result: str,
    top_k: int = 10,
    market_id: int | None = None,
    market_name: str | None = None,
) -> dict:
    """Predict Jodi first and second digits independently.

    B.1 intentionally does not use the actual Jodi-first digit as a
    feature for the second-digit model. This prevents the two outputs
    from becoming a hidden joint/leaky target.
    """
    if not (
        len(open_result) == 3
        and open_result.isdigit()
    ):
        raise ValueError(
            "Open must contain exactly 3 digits."
        )
    if (
        isinstance(top_k, bool)
        or top_k < 1
        or top_k > 10
    ):
        raise ValueError(
            "top_k must be between 1 and 10."
        )

    resolved_market_id = _resolve_market_id(
        market_id,
        market_name,
    )
    models = _load_models()
    rows = _prediction_history(
        resolved_market_id
    )
    features = _jodi_features_for_prediction(
        rows,
        open_result,
    )

    first = _rank_prediction(
        models["jodi_first"],
        features,
        top_k,
    )
    second = _rank_prediction(
        models["jodi_second"],
        features,
        top_k,
    )

    return {
        "status": "VALID",
        "version": SEQUENTIAL_MODEL_VERSION,
        "stage": "JODI_B1",
        "independent": True,
        "condition": {
            "open": open_result,
            "market_id": resolved_market_id,
            "market_name": market_name,
        },
        "jodi_first_candidates": first,
        "jodi_second_candidates": second,
        "operational_top_k": (
            [1, 2, 3, 5, 10]
        ),
        "model_identities": {
            "jodi_first": load_status()
            .get("metrics", {})
            .get("jodi_first", {})
            .get("artifact"),
            "jodi_second": load_status()
            .get("metrics", {})
            .get("jodi_second", {})
            .get("artifact"),
        },
        "temporal_safety": {
            "strict_boundary": True,
            "market_specific_history": True,
            "no_jodi_target_leakage": True,
        },
    }


def predict_jodi_candidates(
    open_result: str,
    *,
    target_date: date,
    top_k: int = 10,
    market_id: int | None = None,
    market_name: str | None = None,
) -> dict:
    """Phase B.2: rank the complete Jodi universe and enforce families."""
    b1 = predict_jodi_digits(
        open_result,
        top_k=10,
        market_id=market_id,
        market_name=market_name,
    )
    group_id = (
        f"{market_id if market_id is not None else market_name or 'market'}:"
        f"{target_date.isoformat()}:{open_result}"
    )
    ranking = rank_jodis_from_b1_outputs(
        b1["jodi_first_candidates"],
        b1["jodi_second_candidates"],
        group_id=group_id,
        target_date=target_date,
        top_k=top_k,
    )
    family_validation = validate_jodi_family_constraint(ranking)
    if not family_validation.is_valid:
        raise ValueError(
            "Jodi family constraint failed: "
            + ", ".join(family_validation.issues)
        )
    return {
        **b1,
        "stage": "JODI_B2",
        "independent": True,
        "ranking": ranking,
        "candidates": ranking.candidates,
        "top_k_views": jodi_top_k_views(ranking),
        "top_candidate_panel_constraints": panel_candidates_for_jodi(ranking.candidates[0].jodi),
        "family_constraint": {
            "status": family_validation.status,
            "jodi_family_enforced": True,
            "panel_family_mapping_enforced": True,
        },
        "operational_top_k": list(JODI_TOP_K),
        "ranking_identity": ranking.ranking_identity,
        "model_identity": b1.get("model_identities", {}).get("jodi_first"),
    }


def _jodi_features_for_prediction(
    rows: list[HistoricalResult],
    open_result: str,
) -> list[int]:
    values = _digits(open_result)
    values.extend(
        _history_values(rows[-3:])
    )
    return _pad_features(values)


def predict_stage_2(
    open_result: str,
    jodi_first: str,
    top_k: int = 10,
    market_id: int | None = None,
    market_name: str | None = None,
) -> dict:
    """Predict Stage-2 Jodi-second and Close digits.

    Jodi-second remains the independent B.1 model. The actual Stage-1
    Jodi-first is used for Close models, which is the authoritative
    Stage-2 conditioning boundary.
    """
    if not (
        len(open_result) == 3
        and open_result.isdigit()
    ):
        raise ValueError(
            "Open must contain exactly 3 digits."
        )
    if not (
        len(jodi_first) == 1
        and jodi_first.isdigit()
    ):
        raise ValueError(
            "Jodi first digit must contain exactly 1 digit."
        )
    if (
        isinstance(top_k, bool)
        or top_k < 1
        or top_k > 10
    ):
        raise ValueError(
            "top_k must be between 1 and 10."
        )

    resolved_market_id = _resolve_market_id(
        market_id,
        market_name,
    )
    models = _load_models()
    rows = _prediction_history(
        resolved_market_id
    )

    jodi_features = _jodi_features_for_prediction(
        rows,
        open_result,
    )
    close_values = _digits(
        open_result,
        jodi_first,
    )
    close_values.extend(
        _history_values(rows[-3:])
    )
    close_features = _pad_features(
        close_values
    )

    return {
        "status": "VALID",
        "version": SEQUENTIAL_MODEL_VERSION,
        "stage": "STAGE_2",
        "condition": {
            "open": open_result,
            "jodi_first": jodi_first,
            "market_id": resolved_market_id,
            "market_name": market_name,
        },
        "jodi_second_candidates": _rank_prediction(
            models["jodi_second"],
            jodi_features,
            top_k,
        ),
        "close_digit_candidates": {
            "first": _rank_prediction(
                models["close_first"],
                close_features,
                top_k,
            ),
            "second": _rank_prediction(
                models["close_second"],
                close_features,
                top_k,
            ),
            "third": _rank_prediction(
                models["close_third"],
                close_features,
                top_k,
            ),
        },
        "model_identity": load_status().get(
            "model_identity"
        ),
        "temporal_safety": {
            "strict_boundary": True,
            "market_specific_history": True,
            "jodi_second_independent": True,
            "close_uses_actual_jodi_first": True,
        },
    }


__all__ = [
    "SEQUENTIAL_MODEL_VERSION",
    "MIN_TRAIN_ROWS",
    "JODI_TARGET_NAMES",
    "CLOSE_TARGET_NAMES",
    "TARGET_NAMES",
    "JODI_TOP_K",
    "train_sequential_models",
    "load_status",
    "predict_jodi_digits",
    "predict_jodi_candidates",
    "predict_stage_2",
]
