from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, stdev
from datetime import date

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from analytics.baseline_temporal_evaluation import TARGET_NAMES, TOP_K, _metrics, _rows_for_dates, _rows_from_window, _xy
from analytics.historical_feature_dataset import HistoricalFeatureDataset
from analytics.temporal_backtesting import TemporalDatasetSplit

COMPARISON_VERSION = "C.7.0"
VALID = "VALID"
INVALID = "INVALID"
MODEL_NAMES = ("majority", "decision_tree", "random_forest", "extra_trees")

@dataclass(frozen=True)
class ModelTargetBenchmark:
    model: str
    target: str
    validation_top1: float
    validation_top5: float
    validation_top10: float
    validation_log_loss: float
    test_top1: float
    test_top5: float
    test_top10: float
    test_log_loss: float

@dataclass(frozen=True)
class FoldBenchmark:
    fold: int
    test_start: str
    test_end: str
    test_count: int
    results: tuple[ModelTargetBenchmark, ...]

@dataclass(frozen=True)
class ModelSummary:
    model: str
    target: str
    folds: int
    mean_test_top1: float
    std_test_top1: float
    mean_test_top5: float
    mean_test_log_loss: float
    top1_fold_wins: int
    top5_fold_wins: int

@dataclass(frozen=True)
class ComparisonReport:
    version: str
    dataset_identity: str
    split_identity: str
    status: str
    models: tuple[str, ...]
    targets: tuple[str, ...]
    holdout_results: tuple[ModelTargetBenchmark, ...]
    walk_forward_results: tuple[FoldBenchmark, ...]
    summaries: tuple[ModelSummary, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    report_identity: str


def _identity(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _fit(train_rows, target, model, features):
    X, y = _xy(train_rows, target, features)
    if model == "majority":
        estimator = DummyClassifier(strategy="prior")
    elif model == "decision_tree":
        estimator = DecisionTreeClassifier(max_depth=12, min_samples_leaf=3, random_state=701)
    elif model == "random_forest":
        estimator = RandomForestClassifier(n_estimators=5, max_depth=None, min_samples_leaf=2, random_state=702, n_jobs=1, class_weight="balanced_subsample")
    elif model == "extra_trees":
        estimator = ExtraTreesClassifier(n_estimators=5, max_depth=None, min_samples_leaf=2, random_state=703, n_jobs=1, class_weight="balanced")
    else:
        raise ValueError(f"Unsupported model: {model}")
    estimator.fit(X, y)
    return estimator


def _benchmark(train_rows, validation_rows, test_rows, model, target, features):
    estimator = _fit(train_rows, target, model, features)
    v1, _, _, v5, v10, vl, _ = _metrics(estimator, validation_rows, target, features)
    t1, _, _, t5, t10, tl, _ = _metrics(estimator, test_rows, target, features)
    return ModelTargetBenchmark(model, target, v1, v5, v10, vl, t1, t5, t10, tl)


def _partition(dataset, split):
    train = _rows_for_dates(dataset, date.fromisoformat(split.train_start), date.fromisoformat(split.train_end))
    validation = _rows_for_dates(dataset, date.fromisoformat(split.validation_start), date.fromisoformat(split.validation_end))
    test = _rows_for_dates(dataset, date.fromisoformat(split.test_start), date.fromisoformat(split.test_end))
    return train, validation, test


def compare_baselines(dataset: HistoricalFeatureDataset, split: TemporalDatasetSplit) -> ComparisonReport:
    issues = []
    if not split.temporal_safe: issues.append("TEMPORAL_SPLIT_NOT_SAFE")
    if dataset.dataset_identity != split.dataset_identity: issues.append("DATASET_IDENTITY_MISMATCH")
    train, validation, test = _partition(dataset, split)
    holdout = tuple(_benchmark(train, validation, test, model, target, dataset.feature_names) for model in MODEL_NAMES for target in TARGET_NAMES)
    folds = []
    for window in split.windows:
        tr = _rows_from_window(dataset, window, "train")
        va = _rows_from_window(dataset, window, "validation")
        te = _rows_from_window(dataset, window, "test")
        results = tuple(_benchmark(tr, va, te, model, target, dataset.feature_names) for model in MODEL_NAMES for target in TARGET_NAMES)
        folds.append(FoldBenchmark(window.fold, window.test_start, window.test_end, len(te), results))
    summaries = []
    for model in MODEL_NAMES:
        for target in TARGET_NAMES:
            values = [r.test_top1 for f in folds for r in f.results if r.model == model and r.target == target]
            top5 = [r.test_top5 for f in folds for r in f.results if r.model == model and r.target == target]
            losses = [r.test_log_loss for f in folds for r in f.results if r.model == model and r.target == target]
            wins1 = wins5 = 0
            for f in folds:
                candidates = [r for r in f.results if r.target == target]
                best1 = max(r.test_top1 for r in candidates)
                best5 = max(r.test_top5 for r in candidates)
                wins1 += int(next(r for r in candidates if r.model == model).test_top1 == best1)
                wins5 += int(next(r for r in candidates if r.model == model).test_top5 == best5)
            summaries.append(ModelSummary(model, target, len(values), mean(values), stdev(values) if len(values) > 1 else 0.0, mean(top5), mean(losses), wins1, wins5))
    payload = {"version": COMPARISON_VERSION, "dataset": dataset.dataset_identity, "split": split.split_identity, "holdout": [asdict(x) for x in holdout], "folds": [asdict(x) for x in folds], "summaries": [asdict(x) for x in summaries], "issues": issues}
    status = VALID if not issues and folds else INVALID
    if not folds: issues.append("NO_WALK_FORWARD_RESULTS"); status = INVALID
    return ComparisonReport(COMPARISON_VERSION, dataset.dataset_identity, split.split_identity, status, MODEL_NAMES, TARGET_NAMES, holdout, tuple(folds), tuple(summaries), status == VALID and split.temporal_safe, tuple(sorted(set(issues))), f"baseline-comparison-{_identity(payload)}")


def validate_comparison_report(report: ComparisonReport) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != COMPARISON_VERSION: issues.append("INVALID_VERSION")
    if report.status != VALID: issues.append("REPORT_STATUS_INVALID")
    if not report.temporal_safe: issues.append("TEMPORAL_SAFETY_FALSE")
    if tuple(report.models) != MODEL_NAMES: issues.append("MODEL_SET_MISMATCH")
    if tuple(report.targets) != TARGET_NAMES: issues.append("TARGET_SET_MISMATCH")
    expected = len(MODEL_NAMES) * len(TARGET_NAMES)
    if len(report.holdout_results) != expected: issues.append("HOLDOUT_RESULT_COUNT")
    if not report.walk_forward_results: issues.append("NO_WALK_FORWARD")
    for fold in report.walk_forward_results:
        if len(fold.results) != expected: issues.append(f"FOLD_RESULT_COUNT:{fold.fold}")
        if fold.test_count <= 0: issues.append(f"EMPTY_FOLD:{fold.fold}")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_comparison_report(report: ComparisonReport, path: str | Path = "reports/baseline_model_comparison.json") -> Path:
    destination = Path(path); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination

__all__ = ["COMPARISON_VERSION", "MODEL_NAMES", "TARGET_NAMES", "ComparisonReport", "ModelTargetBenchmark", "FoldBenchmark", "ModelSummary", "compare_baselines", "validate_comparison_report", "write_comparison_report"]
