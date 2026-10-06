from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sklearn.tree import DecisionTreeClassifier

from analytics.baseline_temporal_evaluation import _metrics, _rows_from_window, _xy
from analytics.historical_feature_dataset import HistoricalFeatureDataset
from analytics.temporal_backtesting import TemporalDatasetSplit

STABILITY_VERSION = "C.9.0"
VALID = "VALID"
INVALID = "INVALID"
TARGET = "jodi_first"
MODEL = "decision_tree"
TOP_K = (1, 5, 10)
PERTURBATION_MODES = ("baseline", "remove_current_open", "shuffle_current_open", "shuffle_history")


@dataclass(frozen=True)
class RobustnessResult:
    fold: int
    mode: str
    test_count: int
    top1: float
    top5: float
    top10: float
    delta_top1: float
    delta_top5: float
    delta_top10: float


@dataclass(frozen=True)
class FoldStability:
    fold: int
    test_start: str
    test_end: str
    baseline_top1: float
    baseline_top5: float
    baseline_top10: float
    top1_min: float
    top1_max: float
    top1_range: float
    robust_modes_passed: int


@dataclass(frozen=True)
class FeatureSensitivity:
    feature_group: str
    features: tuple[str, ...]
    baseline_top1: float
    ablated_top1: float
    delta_top1: float
    sensitivity: float


@dataclass(frozen=True)
class ModelStabilityReport:
    version: str
    dataset_identity: str
    split_identity: str
    status: str
    model: str
    target: str
    robustness: tuple[RobustnessResult, ...]
    fold_stability: tuple[FoldStability, ...]
    feature_sensitivity: tuple[FeatureSensitivity, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    conclusion: str
    report_identity: str


def _identity(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _fit(train_rows, features, seed=901):
    X, y = _xy(train_rows, TARGET, features)
    model = DecisionTreeClassifier(max_depth=12, min_samples_leaf=3, random_state=seed)
    model.fit(X, y)
    return model


def _rows_with_features(rows, features, replacements=None):
    replacements = replacements or {}
    result = []
    for row in rows:
        clone = type(row)(row.result_date, row.market_id, dict(row.features), dict(row.targets), row.source_history_end_date)
        for name, values in replacements.items():
            clone.features[name] = values[len(result)]
        result.append(clone)
    return result


def _evaluate(model, rows, features):
    top1, _, _, top5, top10, _, _ = _metrics(model, rows, TARGET, features)
    return float(top1), float(top5), float(top10)


def _deterministic_permutation(values, seed):
    # Deterministic cyclic permutation avoids random/non-reproducible reports.
    if not values:
        return values
    shift = seed % len(values)
    return values[shift:] + values[:shift]


def _perturbed_rows(rows, mode, features, fold):
    if mode == "baseline":
        return list(rows), features
    cloned = [type(row)(row.result_date, row.market_id, dict(row.features), dict(row.targets), row.source_history_end_date) for row in rows]
    if mode in ("remove_current_open", "shuffle_current_open"):
        open_features = [f"current_open_{i}" for i in range(1, 4)]
        if mode == "remove_current_open":
            for row in cloned:
                for feature in open_features:
                    row.features[feature] = 0
        else:
            for feature in open_features:
                vals = [row.features[feature] for row in cloned]
                vals = _deterministic_permutation(vals, fold + len(feature))
                for row, value in zip(cloned, vals):
                    row.features[feature] = value
        return cloned, features
    if mode == "shuffle_history":
        historical = [f for f in features if not f.startswith("current_open_")]
        for feature in historical:
            vals = [row.features[feature] for row in cloned]
            vals = _deterministic_permutation(vals, fold + len(feature) * 3)
            for row, value in zip(cloned, vals):
                row.features[feature] = value
        return cloned, features
    raise ValueError(f"Unsupported perturbation mode: {mode}")


def _feature_groups(features):
    groups = {
        "current_open": tuple(f for f in features if f.startswith("current_open_")),
        "lags": tuple(f for f in features if f.startswith("lag")),
        "rolling": tuple(f for f in features if f.startswith("rolling")),
        "date": tuple(f for f in features if f in {"day_of_week", "day_of_month", "month", "quarter", "year"}),
        "transitions": tuple(f for f in features if f.endswith("change_sum")),
    }
    return {name: values for name, values in groups.items() if values}


def build_model_stability_report(dataset: HistoricalFeatureDataset, split: TemporalDatasetSplit) -> ModelStabilityReport:
    issues = []
    if not dataset.temporal_safe: issues.append("DATASET_TEMPORAL_SAFETY_FALSE")
    if not split.temporal_safe: issues.append("SPLIT_TEMPORAL_SAFETY_FALSE")
    if dataset.dataset_identity != split.dataset_identity: issues.append("DATASET_IDENTITY_MISMATCH")
    robustness = []
    folds = []
    sensitivity_rows = []

    for window in split.windows:
        train = _rows_from_window(dataset, window, "train")
        test = _rows_from_window(dataset, window, "test")
        features = dataset.feature_names
        model = _fit(train, features, seed=901 + window.fold)
        base = _evaluate(model, test, features)
        mode_results = {}
        for mode in PERTURBATION_MODES:
            eval_rows, eval_features = _perturbed_rows(test, mode, features, window.fold)
            # Fit on equivalently perturbed training data for fair ablation/robustness measurement.
            train_eval, _ = _perturbed_rows(train, mode, features, window.fold)
            eval_model = _fit(train_eval, eval_features, seed=901 + window.fold)
            scores = _evaluate(eval_model, eval_rows, eval_features)
            mode_results[mode] = scores
            robustness.append(RobustnessResult(window.fold, mode, len(test), scores[0], scores[1], scores[2], scores[0]-base[0], scores[1]-base[1], scores[2]-base[2]))
        vals = [mode_results[m][0] for m in PERTURBATION_MODES]
        folds.append(FoldStability(window.fold, window.test_start, window.test_end, base[0], base[1], base[2], min(vals), max(vals), max(vals)-min(vals), sum(mode_results[m][0] >= 0.05 for m in PERTURBATION_MODES)))

        for group, group_features in _feature_groups(features).items():
            reduced = tuple(f for f in features if f not in group_features)
            if not reduced:
                continue
            reduced_model = _fit(train, reduced, seed=901 + window.fold)
            ablated = _evaluate(reduced_model, test, reduced)
            sensitivity_rows.append(FeatureSensitivity(group, group_features, base[0], ablated[0], ablated[0]-base[0], abs(ablated[0]-base[0])))

    conclusion = (
        "Jodi-First stability is strongly dependent on current Open features."
        if any(r.mode == "remove_current_open" and r.delta_top1 < -0.10 for r in robustness)
        else "Jodi-First performance remains broadly robust to the tested feature perturbations."
    )
    payload = {"version": STABILITY_VERSION, "dataset": dataset.dataset_identity, "split": split.split_identity, "robustness": [asdict(x) for x in robustness], "folds": [asdict(x) for x in folds], "sensitivity": [asdict(x) for x in sensitivity_rows], "issues": issues}
    status = VALID if not issues and len(folds) == len(split.windows) else INVALID
    return ModelStabilityReport(STABILITY_VERSION, dataset.dataset_identity, split.split_identity, status, MODEL, TARGET, tuple(robustness), tuple(folds), tuple(sensitivity_rows), status == VALID, tuple(sorted(set(issues))), conclusion, f"model-stability-{_identity(payload)}")


def validate_model_stability_report(report: ModelStabilityReport) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != STABILITY_VERSION: issues.append("INVALID_VERSION")
    if report.status != VALID: issues.append("REPORT_STATUS_INVALID")
    if not report.temporal_safe: issues.append("TEMPORAL_SAFETY_FALSE")
    if report.model != MODEL or report.target != TARGET: issues.append("FOCUS_MISMATCH")
    if not report.fold_stability: issues.append("NO_FOLD_STABILITY")
    expected = len(report.fold_stability) * len(PERTURBATION_MODES)
    if len(report.robustness) != expected: issues.append("ROBUSTNESS_RESULT_COUNT")
    if not report.feature_sensitivity: issues.append("NO_FEATURE_SENSITIVITY")
    for row in report.robustness:
        if not all(0.0 <= value <= 1.0 for value in (row.top1, row.top5, row.top10)): issues.append(f"INVALID_TOPK:{row.fold}:{row.mode}")
    if not report.report_identity.startswith("model-stability-"): issues.append("INVALID_REPORT_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_model_stability_report(report: ModelStabilityReport, path: str | Path = "reports/model_stability.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = ["STABILITY_VERSION", "PERTURBATION_MODES", "RobustnessResult", "FoldStability", "FeatureSensitivity", "ModelStabilityReport", "build_model_stability_report", "validate_model_stability_report", "write_model_stability_report"]
