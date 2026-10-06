from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import log_loss

from analytics.historical_feature_dataset import HistoricalFeatureDataset
from analytics.temporal_backtesting import TemporalDatasetSplit, TemporalWindow

BASELINE_VERSION = "C.6.0"
VALID = "VALID"
INVALID = "INVALID"
TARGET_NAMES = ("jodi_first", "jodi_second", "close_first", "close_second", "close_third")
TOP_K = (1, 2, 3, 5, 10)


@dataclass(frozen=True)
class TargetEvaluation:
    target: str
    model: str
    train_count: int
    validation_count: int
    test_count: int
    classes: tuple[int, ...]
    validation_top1: float
    validation_top2: float
    validation_top3: float
    validation_top5: float
    validation_top10: float
    validation_log_loss: float
    test_top1: float
    test_top2: float
    test_top3: float
    test_top5: float
    test_top10: float
    test_log_loss: float


@dataclass(frozen=True)
class WalkForwardEvaluation:
    fold: int
    test_start: str
    test_end: str
    test_count: int
    target_results: tuple[TargetEvaluation, ...]


@dataclass(frozen=True)
class BaselineEvaluationReport:
    version: str
    dataset_identity: str
    split_identity: str
    status: str
    model: str
    record_count: int
    targets: tuple[str, ...]
    train_count: int
    validation_count: int
    test_count: int
    holdout_results: tuple[TargetEvaluation, ...]
    walk_forward_results: tuple[WalkForwardEvaluation, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    report_identity: str


def _identity(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _rows_for_dates(dataset: HistoricalFeatureDataset, start: date | None, end: date | None):
    return [
        row for row in dataset.rows
        if (start is None or date.fromisoformat(row.result_date) >= start)
        and (end is None or date.fromisoformat(row.result_date) <= end)
    ]


def _rows_from_window(dataset: HistoricalFeatureDataset, window: TemporalWindow, partition: str):
    if partition == "train":
        return _rows_for_dates(dataset, date.fromisoformat(window.train_start), date.fromisoformat(window.train_end))
    if partition == "validation":
        return _rows_for_dates(dataset, date.fromisoformat(window.validation_start), date.fromisoformat(window.validation_end))
    if partition == "test":
        return _rows_for_dates(dataset, date.fromisoformat(window.test_start), date.fromisoformat(window.test_end))
    raise ValueError(f"Unknown partition: {partition}")


def _xy(rows, target: str, feature_names: tuple[str, ...]):
    return [[row.features[name] for name in feature_names] for row in rows], [row.targets[target] for row in rows]


def _metrics(model, rows, target: str, feature_names: tuple[str, ...]):
    if not rows:
        raise ValueError("Evaluation partition is empty.")
    X, y = _xy(rows, target, feature_names)
    probabilities = model.predict_proba(X)
    classes = tuple(int(value) for value in model.classes_)
    hits = {}
    for k in TOP_K:
        hit = 0
        for actual, probs in zip(y, probabilities):
            order = sorted(range(len(probs)), key=lambda i: (-float(probs[i]), classes[i]))
            if actual in {classes[i] for i in order[:min(k, len(order))]}:
                hit += 1
        hits[k] = hit / len(y)
    try:
        loss = float(log_loss(y, probabilities, labels=list(classes)))
    except ValueError:
        loss = 0.0
    return hits[1], hits[2], hits[3], hits[5], hits[10], loss, classes


def _fit(train_rows, target: str, model_kind: str, feature_names: tuple[str, ...]):
    X, y = _xy(train_rows, target, feature_names)
    if model_kind == "random_forest":
        model = RandomForestClassifier(n_estimators=10, random_state=600 + TARGET_NAMES.index(target), n_jobs=1, class_weight="balanced_subsample")
    elif model_kind == "majority":
        model = DummyClassifier(strategy="prior")
    else:
        raise ValueError(f"Unknown baseline model: {model_kind}")
    model.fit(X, y)
    return model


def _evaluate_target(train_rows, validation_rows, test_rows, target: str, model_kind: str, feature_names: tuple[str, ...]) -> TargetEvaluation:
    model = _fit(train_rows, target, model_kind, feature_names)
    v1, v2, v3, v5, v10, vl, classes = _metrics(model, validation_rows, target, feature_names)
    t1, t2, t3, t5, t10, tl, _ = _metrics(model, test_rows, target, feature_names)
    return TargetEvaluation(target, model_kind, len(train_rows), len(validation_rows), len(test_rows), classes, v1, v2, v3, v5, v10, vl, t1, t2, t3, t5, t10, tl)


def evaluate_baselines(dataset: HistoricalFeatureDataset, split: TemporalDatasetSplit, *, model_kind: str = "random_forest") -> BaselineEvaluationReport:
    issues: list[str] = []
    if not split.temporal_safe:
        issues.append("TEMPORAL_SPLIT_NOT_SAFE")
    if dataset.dataset_identity != split.dataset_identity:
        issues.append("DATASET_IDENTITY_MISMATCH")
    holdout_train = _rows_for_dates(dataset, date.fromisoformat(split.train_start), date.fromisoformat(split.train_end))
    holdout_validation = _rows_for_dates(dataset, date.fromisoformat(split.validation_start), date.fromisoformat(split.validation_end))
    holdout_test = _rows_for_dates(dataset, date.fromisoformat(split.test_start), date.fromisoformat(split.test_end))
    holdout_results = tuple(_evaluate_target(holdout_train, holdout_validation, holdout_test, target, model_kind, dataset.feature_names) for target in TARGET_NAMES)

    walk_results = []
    for window in split.windows:
        train_rows = _rows_from_window(dataset, window, "train")
        validation_rows = _rows_from_window(dataset, window, "validation")
        test_rows = _rows_from_window(dataset, window, "test")
        results = tuple(_evaluate_target(train_rows, validation_rows, test_rows, target, model_kind, dataset.feature_names) for target in TARGET_NAMES)
        walk_results.append(WalkForwardEvaluation(window.fold, window.test_start, window.test_end, len(test_rows), results))

    if len(holdout_train) != split.train_count or len(holdout_validation) != split.validation_count or len(holdout_test) != split.test_count:
        issues.append("HOLDOUT_COUNT_MISMATCH")
    if not walk_results:
        issues.append("NO_WALK_FORWARD_RESULTS")
    status = VALID if not issues else INVALID
    payload = {"version": BASELINE_VERSION, "dataset_identity": dataset.dataset_identity, "split_identity": split.split_identity, "model": model_kind, "holdout": [asdict(x) for x in holdout_results], "walk_forward": [asdict(x) for x in walk_results], "issues": issues}
    return BaselineEvaluationReport(BASELINE_VERSION, dataset.dataset_identity, split.split_identity, status, model_kind, dataset.record_count, TARGET_NAMES, split.train_count, split.validation_count, split.test_count, holdout_results, tuple(walk_results), not issues and split.temporal_safe, tuple(sorted(set(issues))), f"baseline-evaluation-{_identity(payload)}")


def validate_baseline_report(report: BaselineEvaluationReport) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != BASELINE_VERSION: issues.append("INVALID_VERSION")
    if report.status != VALID: issues.append("REPORT_STATUS_INVALID")
    if not report.temporal_safe: issues.append("TEMPORAL_SAFETY_FALSE")
    if len(report.holdout_results) != len(TARGET_NAMES): issues.append("HOLDOUT_TARGET_COUNT")
    if len(report.walk_forward_results) == 0: issues.append("NO_WALK_FORWARD")
    for fold in report.walk_forward_results:
        if fold.test_count <= 0: issues.append(f"EMPTY_FOLD:{fold.fold}")
        if len(fold.target_results) != len(TARGET_NAMES): issues.append(f"TARGET_COUNT:{fold.fold}")
    if not report.report_identity.startswith("baseline-evaluation-"): issues.append("INVALID_REPORT_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_baseline_report(report: BaselineEvaluationReport, path: str | Path = "reports/baseline_temporal_evaluation.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = ["BASELINE_VERSION", "VALID", "INVALID", "TARGET_NAMES", "TOP_K", "TargetEvaluation", "WalkForwardEvaluation", "BaselineEvaluationReport", "evaluate_baselines", "validate_baseline_report", "write_baseline_report"]
