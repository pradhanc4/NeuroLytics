from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from sklearn.inspection import permutation_importance
from sklearn.tree import DecisionTreeClassifier, export_text

from analytics.baseline_model_comparison import MODEL_NAMES, _fit
from analytics.baseline_temporal_evaluation import TARGET_NAMES, _metrics, _rows_for_dates, _rows_from_window, _xy
from analytics.historical_feature_dataset import HistoricalFeatureDataset
from analytics.temporal_backtesting import TemporalDatasetSplit

EXPLAINABILITY_VERSION = "C.8.0"
VALID = "VALID"
INVALID = "INVALID"
TOP_FEATURES = 15
TARGET_DIGITS = tuple(range(10))


@dataclass(frozen=True)
class FeatureImportance:
    feature: str
    importance: float
    normalized_importance: float
    rank: int


@dataclass(frozen=True)
class FoldExplainability:
    fold: int
    model: str
    target: str
    test_start: str
    test_end: str
    test_count: int
    top_features: tuple[FeatureImportance, ...]
    test_top1: float
    test_top5: float
    test_top10: float
    temporal_safe: bool


@dataclass(frozen=True)
class DigitPerformance:
    model: str
    target: str
    digit: int
    support: int
    top1_hits: int
    top1_rate: float
    top5_hits: int
    top5_rate: float


@dataclass(frozen=True)
class DecisionPathExplanation:
    model: str
    target: str
    fold: int
    test_row_date: str
    actual_digit: int
    predicted_digit: int
    decision_path: str


@dataclass(frozen=True)
class ExplainabilityReport:
    version: str
    dataset_identity: str
    split_identity: str
    status: str
    focus_model: str
    focus_target: str
    fold_explanations: tuple[FoldExplainability, ...]
    aggregate_features: tuple[FeatureImportance, ...]
    digit_performance: tuple[DigitPerformance, ...]
    decision_paths: tuple[DecisionPathExplanation, ...]
    feature_temporal_stability: tuple[FeatureImportance, ...]
    leakage_checks: tuple[str, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    report_identity: str


def _identity(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _importance(estimator, features: tuple[str, ...]) -> tuple[FeatureImportance, ...]:
    raw = getattr(estimator, "feature_importances_", None)
    if raw is None:
        X = None
        raise ValueError("Explainability requires a tree-based model with feature_importances_.")
    values = [(name, float(value)) for name, value in zip(features, raw)]
    total = sum(value for _, value in values)
    values.sort(key=lambda item: (-item[1], item[0]))
    return tuple(
        FeatureImportance(name, value, value / total if total else 0.0, index + 1)
        for index, (name, value) in enumerate(values[:TOP_FEATURES])
    )


def _aggregate_importance(rows: list[tuple[FeatureImportance, ...]]) -> tuple[FeatureImportance, ...]:
    scores: dict[str, list[float]] = {}
    for row in rows:
        for item in row:
            scores.setdefault(item.feature, []).append(item.normalized_importance)
    ranked = sorted(((name, sum(values) / len(values)) for name, values in scores.items()), key=lambda x: (-x[1], x[0]))
    total = sum(value for _, value in ranked)
    return tuple(FeatureImportance(name, value, value / total if total else 0.0, i + 1) for i, (name, value) in enumerate(ranked[:TOP_FEATURES]))


def _digit_metrics(estimator, rows, target, features):
    X, y = _xy(rows, target, features)
    probabilities = estimator.predict_proba(X)
    classes = tuple(int(x) for x in estimator.classes_)
    ranked = [sorted(range(len(classes)), key=lambda i: (-float(probabilities[row_i][i]), classes[i])) for row_i in range(len(rows))]
    result = []
    for digit in TARGET_DIGITS:
        indexes = [i for i, actual in enumerate(y) if int(actual) == digit]
        support = len(indexes)
        top1 = sum(classes[ranked[i][0]] == digit for i in indexes)
        top5 = sum(digit in [classes[j] for j in ranked[i][:5]] for i in indexes)
        result.append((digit, support, top1, top5))
    return result


def _decision_path(estimator: DecisionTreeClassifier, row, features, actual, result_date, fold, model, target):
    if not hasattr(estimator, "decision_path"):
        return None
    X_rows, _ = _xy([row], target, features)
    X = [X_rows[0]]
    node_indicator = estimator.decision_path(X)
    leaf_id = estimator.apply(X)[0]
    tree = estimator.tree_
    lines = []
    node_ids = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
    for node_id in node_ids:
        if node_id == leaf_id:
            lines.append(f"LEAF node={node_id}")
            continue
        feature_index = tree.feature[node_id]
        threshold = tree.threshold[node_id]
        feature_name = features[feature_index]
        value = float(X[0][feature_index])
        direction = "<=" if value <= threshold else ">"
        lines.append(f"node={node_id}: {feature_name}={value:g} {direction} {threshold:.6g}")
    predicted = int(estimator.predict(X)[0])
    return DecisionPathExplanation(model, target, fold, result_date, int(actual), predicted, " | ".join(lines))


def build_explainability_report(dataset: HistoricalFeatureDataset, split: TemporalDatasetSplit) -> ExplainabilityReport:
    issues: list[str] = []
    if not dataset.temporal_safe:
        issues.append("DATASET_TEMPORAL_SAFETY_FALSE")
    if not split.temporal_safe:
        issues.append("SPLIT_TEMPORAL_SAFETY_FALSE")
    if dataset.dataset_identity != split.dataset_identity:
        issues.append("DATASET_IDENTITY_MISMATCH")

    focus_model = "decision_tree"
    focus_target = "jodi_first"
    fold_rows: list[FoldExplainability] = []
    importance_rows: list[tuple[FeatureImportance, ...]] = []
    digit_rows: list[DigitPerformance] = []
    paths: list[DecisionPathExplanation] = []

    for window in split.windows:
        train = _rows_from_window(dataset, window, "train")
        test = _rows_from_window(dataset, window, "test")
        estimator = _fit(train, focus_target, focus_model, dataset.feature_names)
        top = _importance(estimator, dataset.feature_names)
        importance_rows.append(top)
        top1, _, _, top5, top10, _, _ = _metrics(estimator, test, focus_target, dataset.feature_names)
        fold_rows.append(FoldExplainability(window.fold, focus_model, focus_target, window.test_start, window.test_end, len(test), top, top1, top5, top10, True))
        for digit, support, hits1, hits5 in _digit_metrics(estimator, test, focus_target, dataset.feature_names):
            digit_rows.append(DigitPerformance(focus_model, focus_target, digit, support, hits1, hits1 / support if support else 0.0, hits5, hits5 / support if support else 0.0))
        # Explain one deterministic test observation per fold.
        if test:
            example = test[0]
            path = _decision_path(estimator, example, dataset.feature_names, example.targets[focus_target], example.result_date, window.fold, focus_model, focus_target)
            if path:
                paths.append(path)

    aggregate = _aggregate_importance(importance_rows)
    stability_scores: dict[str, list[float]] = {}
    for row in importance_rows:
        for item in row:
            stability_scores.setdefault(item.feature, []).append(item.normalized_importance)
    stability = []
    for name, values in stability_scores.items():
        mean_value = sum(values) / len(values)
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        stability.append(FeatureImportance(name, mean_value, math.sqrt(variance), 0))
    stability.sort(key=lambda x: (x.importance, x.feature))
    stability = [FeatureImportance(x.feature, x.importance, x.normalized_importance, i + 1) for i, x in enumerate(stability[:TOP_FEATURES])]

    leakage_checks = ("C.3_TEMPORAL_FEATURE_DATASET", "C.4_FEATURE_QUALITY_AUDIT", "C.5_TEMPORAL_SPLIT", "C.7_BENCHMARK_INPUTS")
    payload = {"version": EXPLAINABILITY_VERSION, "dataset": dataset.dataset_identity, "split": split.split_identity, "folds": [asdict(x) for x in fold_rows], "aggregate": [asdict(x) for x in aggregate], "digits": [asdict(x) for x in digit_rows], "paths": [asdict(x) for x in paths], "stability": [asdict(x) for x in stability], "issues": issues}
    status = VALID if not issues and len(fold_rows) == len(split.windows) else INVALID
    return ExplainabilityReport(EXPLAINABILITY_VERSION, dataset.dataset_identity, split.split_identity, status, focus_model, focus_target, tuple(fold_rows), aggregate, tuple(digit_rows), tuple(paths), tuple(stability), leakage_checks, status == VALID, tuple(sorted(set(issues))), f"model-explainability-{_identity(payload)}")


def validate_explainability_report(report: ExplainabilityReport) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != EXPLAINABILITY_VERSION: issues.append("INVALID_VERSION")
    if report.status != VALID: issues.append("REPORT_STATUS_INVALID")
    if not report.temporal_safe: issues.append("TEMPORAL_SAFETY_FALSE")
    if report.focus_model != "decision_tree" or report.focus_target != "jodi_first": issues.append("FOCUS_MISMATCH")
    if len(report.fold_explanations) == 0: issues.append("NO_FOLD_EXPLANATIONS")
    for fold in report.fold_explanations:
        if fold.test_count <= 0: issues.append(f"EMPTY_FOLD:{fold.fold}")
        if not (0.0 <= fold.test_top1 <= fold.test_top5 <= fold.test_top10 <= 1.0): issues.append(f"INVALID_TOPK:{fold.fold}")
        if not fold.top_features: issues.append(f"NO_FEATURES:{fold.fold}")
    if len(report.digit_performance) != len(report.fold_explanations) * 10: issues.append("DIGIT_RESULT_COUNT")
    if len(report.decision_paths) != len(report.fold_explanations): issues.append("DECISION_PATH_COUNT")
    if not report.report_identity.startswith("model-explainability-"): issues.append("INVALID_REPORT_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_explainability_report(report: ExplainabilityReport, path: str | Path = "reports/model_explainability.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = ["EXPLAINABILITY_VERSION", "FeatureImportance", "FoldExplainability", "DigitPerformance", "DecisionPathExplanation", "ExplainabilityReport", "build_explainability_report", "validate_explainability_report", "write_explainability_report"]
