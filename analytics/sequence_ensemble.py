from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from analytics.sequence_evaluation import (
    SequenceEvaluationResult,
    accuracy,
    brier_score,
    expected_calibration_error,
    log_loss,
    top_k_accuracy,
)


SEQUENCE_ENSEMBLE_VERSION = "35.0.0"
VALID = "VALID"
INVALID = "INVALID"
ENSEMBLE_METHODS = ("equal_weight", "inverse_log_loss", "softmax_score")


@dataclass(frozen=True)
class SequenceModelComparisonResult:
    model_kind: str
    model_version: str
    observations: int
    log_loss: float
    accuracy: float
    top_k_accuracy: float
    brier_score: float
    expected_calibration_error: float
    score: float
    log_loss_delta: float
    accuracy_delta: float


@dataclass(frozen=True)
class SequenceComparisonReport:
    version: str
    dataset_identity: str
    results: tuple[SequenceModelComparisonResult, ...]
    comparison_identity: str


@dataclass(frozen=True)
class SequenceEnsembleWeights:
    method: str
    model_kinds: tuple[str, ...]
    weights: tuple[float, ...]
    identity: str


@dataclass(frozen=True)
class SequenceEnsembleResult:
    version: str
    dataset_identity: str
    method: str
    model_kinds: tuple[str, ...]
    weights: tuple[float, ...]
    probabilities: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]
    observations: int
    log_loss: float
    accuracy: float
    top_k_accuracy: float
    brier_score: float
    expected_calibration_error: float
    ensemble_identity: str


@dataclass(frozen=True)
class SequenceEnsembleReport:
    version: str
    dataset_identity: str
    comparison: SequenceComparisonReport
    ensembles: tuple[SequenceEnsembleResult, ...]
    selected_method: str
    selected_ensemble_identity: str
    report_identity: str


@dataclass(frozen=True)
class SequenceEnsembleValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _validate_evaluations(
    evaluations: Sequence[SequenceEvaluationResult],
) -> tuple[SequenceEvaluationResult, ...]:
    rows = tuple(evaluations)
    if not rows:
        raise ValueError("at least one evaluation result is required.")
    dataset_identity = rows[0].dataset_identity
    observations = rows[0].observations
    targets = rows[0].targets
    for item in rows:
        if item.dataset_identity != dataset_identity:
            raise ValueError("all evaluations must share dataset identity.")
        if item.observations != observations:
            raise ValueError("all evaluations must have equal observation counts.")
        if item.targets != targets:
            raise ValueError("all evaluations must share identical targets.")
        if len(item.probabilities) != observations:
            raise ValueError("evaluation probability count mismatch.")
    return rows


def _score_from_metrics(log_loss_value: float, accuracy_value: float) -> float:
    if log_loss_value < 0 or not 0 <= accuracy_value <= 1:
        raise ValueError("invalid evaluation metrics.")
    return accuracy_value / max(log_loss_value, 1e-12)


def compare_sequence_evaluations(
    evaluations: Sequence[SequenceEvaluationResult],
    baseline_log_loss: float | None = None,
    baseline_accuracy: float | None = None,
) -> SequenceComparisonReport:
    rows = _validate_evaluations(evaluations)
    if baseline_log_loss is not None and baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    if baseline_accuracy is not None and not 0 <= baseline_accuracy <= 1:
        raise ValueError("baseline_accuracy must be between 0 and 1.")
    results = tuple(
        SequenceModelComparisonResult(
            item.model_kind,
            item.model_version,
            item.observations,
            item.log_loss,
            item.accuracy,
            item.top_k_accuracy,
            item.brier_score,
            item.expected_calibration_error,
            _score_from_metrics(item.log_loss, item.accuracy),
            item.log_loss - baseline_log_loss if baseline_log_loss is not None else 0.0,
            item.accuracy - baseline_accuracy if baseline_accuracy is not None else 0.0,
        )
        for item in rows
    )
    payload = {
        "version": SEQUENCE_ENSEMBLE_VERSION,
        "dataset": rows[0].dataset_identity,
        "models": [
            (item.model_kind, item.model_version, item.log_loss, item.accuracy)
            for item in results
        ],
    }
    identity = "sequence-comparison-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceComparisonReport(
        SEQUENCE_ENSEMBLE_VERSION,
        rows[0].dataset_identity,
        results,
        identity,
    )


def _normalize_weights(raw: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in raw)
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("weights must be finite and non-negative.")
    total = sum(values)
    if total <= 0:
        return tuple(1.0 / len(values) for _ in values)
    return tuple(value / total for value in values)


def build_sequence_ensemble_weights(
    evaluations: Sequence[SequenceEvaluationResult],
    method: str = "inverse_log_loss",
) -> SequenceEnsembleWeights:
    rows = _validate_evaluations(evaluations)
    if method not in ENSEMBLE_METHODS:
        raise ValueError(f"unsupported ensemble method: {method}")
    if method == "equal_weight":
        raw = [1.0] * len(rows)
    elif method == "inverse_log_loss":
        raw = [1.0 / max(item.log_loss, 1e-12) for item in rows]
    else:
        raw = [
            math.exp(max(-40.0, min(40.0, _score_from_metrics(item.log_loss, item.accuracy))))
            for item in rows
        ]
    weights = _normalize_weights(raw)
    kinds = tuple(item.model_kind for item in rows)
    payload = {"method": method, "models": kinds, "weights": weights}
    identity = "sequence-weights-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceEnsembleWeights(method, kinds, weights, identity)


def _blend_probabilities(
    evaluations: Sequence[SequenceEvaluationResult],
    weights: Sequence[float],
) -> tuple[tuple[float, ...], ...]:
    rows = _validate_evaluations(evaluations)
    normalized = _normalize_weights(weights)
    observations = rows[0].observations
    blended = []
    for index in range(observations):
        probability_row = tuple(
            sum(
                weight * float(evaluation.probabilities[index][digit])
                for weight, evaluation in zip(normalized, rows)
            )
            for digit in range(10)
        )
        total = sum(probability_row)
        if total <= 0:
            raise ValueError("ensemble produced a zero probability row.")
        blended.append(tuple(value / total for value in probability_row))
    return tuple(blended)


def build_sequence_ensemble(
    evaluations: Sequence[SequenceEvaluationResult],
    method: str = "inverse_log_loss",
) -> SequenceEnsembleResult:
    rows = _validate_evaluations(evaluations)
    weights_result = build_sequence_ensemble_weights(rows, method)
    probabilities = _blend_probabilities(rows, weights_result.weights)
    targets = rows[0].targets
    payload = {
        "version": SEQUENCE_ENSEMBLE_VERSION,
        "dataset": rows[0].dataset_identity,
        "method": method,
        "models": weights_result.model_kinds,
        "weights": weights_result.weights,
    }
    identity = "sequence-ensemble-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceEnsembleResult(
        SEQUENCE_ENSEMBLE_VERSION,
        rows[0].dataset_identity,
        method,
        weights_result.model_kinds,
        weights_result.weights,
        probabilities,
        targets,
        len(targets),
        log_loss(probabilities, targets),
        accuracy(probabilities, targets),
        top_k_accuracy(probabilities, targets, 3),
        brier_score(probabilities, targets),
        expected_calibration_error(probabilities, targets, 10),
        identity,
    )


def select_best_ensemble(
    ensembles: Sequence[SequenceEnsembleResult],
) -> SequenceEnsembleResult:
    rows = tuple(ensembles)
    if not rows:
        raise ValueError("at least one ensemble result is required.")
    return min(
        rows,
        key=lambda item: (
            item.log_loss,
            -item.accuracy,
            -item.top_k_accuracy,
            item.brier_score,
            item.method,
        ),
    )


def build_sequence_ensemble_report(
    evaluations: Sequence[SequenceEvaluationResult],
    methods: Sequence[str] = ENSEMBLE_METHODS,
    baseline_log_loss: float | None = None,
    baseline_accuracy: float | None = None,
) -> SequenceEnsembleReport:
    rows = _validate_evaluations(evaluations)
    method_values = tuple(dict.fromkeys(methods))
    if not method_values:
        raise ValueError("at least one ensemble method is required.")
    for method in method_values:
        if method not in ENSEMBLE_METHODS:
            raise ValueError(f"unsupported ensemble method: {method}")
    comparison = compare_sequence_evaluations(
        rows,
        baseline_log_loss,
        baseline_accuracy,
    )
    ensembles = tuple(build_sequence_ensemble(rows, method) for method in method_values)
    selected = select_best_ensemble(ensembles)
    payload = {
        "version": SEQUENCE_ENSEMBLE_VERSION,
        "comparison": comparison.comparison_identity,
        "ensembles": [item.ensemble_identity for item in ensembles],
        "selected": selected.ensemble_identity,
    }
    report_identity = "sequence-ensemble-report-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceEnsembleReport(
        SEQUENCE_ENSEMBLE_VERSION,
        rows[0].dataset_identity,
        comparison,
        ensembles,
        selected.method,
        selected.ensemble_identity,
        report_identity,
    )


def validate_sequence_ensemble_weights(
    weights: SequenceEnsembleWeights,
) -> SequenceEnsembleValidationResult:
    issues = []
    if not isinstance(weights, SequenceEnsembleWeights):
        return SequenceEnsembleValidationResult(INVALID, ("INVALID_WEIGHT_TYPE",))
    if weights.method not in ENSEMBLE_METHODS:
        issues.append("INVALID_METHOD")
    if not weights.model_kinds:
        issues.append("NO_MODELS")
    if len(weights.model_kinds) != len(weights.weights):
        issues.append("WEIGHT_LENGTH_MISMATCH")
    if weights.weights:
        if any(v < 0 or not math.isfinite(v) for v in weights.weights):
            issues.append("INVALID_WEIGHT")
        elif abs(sum(weights.weights) - 1.0) > 1e-8:
            issues.append("WEIGHTS_NOT_NORMALIZED")
    if not weights.identity.startswith("sequence-weights-"):
        issues.append("INVALID_WEIGHT_IDENTITY")
    return SequenceEnsembleValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def validate_sequence_ensemble(
    ensemble: SequenceEnsembleResult,
) -> SequenceEnsembleValidationResult:
    if not isinstance(ensemble, SequenceEnsembleResult):
        return SequenceEnsembleValidationResult(INVALID, ("INVALID_ENSEMBLE_TYPE",))
    issues = []
    if ensemble.version != SEQUENCE_ENSEMBLE_VERSION:
        issues.append("INVALID_VERSION")
    if ensemble.method not in ENSEMBLE_METHODS:
        issues.append("INVALID_METHOD")
    if not ensemble.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if len(ensemble.model_kinds) != len(ensemble.weights):
        issues.append("WEIGHT_LENGTH_MISMATCH")
    if ensemble.observations <= 0:
        issues.append("INVALID_OBSERVATIONS")
    try:
        _validate_evaluations(
            (
                SequenceEvaluationResult(
                    ensemble.model_kinds[0],
                    "ensemble",
                    ensemble.dataset_identity,
                    ensemble.observations,
                    ensemble.log_loss,
                    ensemble.accuracy,
                    ensemble.top_k_accuracy,
                    ensemble.brier_score,
                    ensemble.expected_calibration_error,
                    0.0,
                    ensemble.probabilities,
                    ensemble.targets,
                ),
            )
        )
    except (ValueError, IndexError):
        issues.append("INVALID_PROBABILITY_CONTRACT")
    if not ensemble.ensemble_identity.startswith("sequence-ensemble-"):
        issues.append("INVALID_ENSEMBLE_IDENTITY")
    return SequenceEnsembleValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def validate_sequence_ensemble_report(
    report: SequenceEnsembleReport,
) -> SequenceEnsembleValidationResult:
    if not isinstance(report, SequenceEnsembleReport):
        return SequenceEnsembleValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != SEQUENCE_ENSEMBLE_VERSION:
        issues.append("INVALID_VERSION")
    if report.dataset_identity != report.comparison.dataset_identity:
        issues.append("COMPARISON_DATASET_MISMATCH")
    if not report.ensembles:
        issues.append("NO_ENSEMBLES")
    for ensemble in report.ensembles:
        if ensemble.dataset_identity != report.dataset_identity:
            issues.append("ENSEMBLE_DATASET_MISMATCH")
        if not validate_sequence_ensemble(ensemble).is_valid:
            issues.append("INVALID_ENSEMBLE")
    selected = {item.ensemble_identity for item in report.ensembles}
    if report.selected_ensemble_identity not in selected:
        issues.append("SELECTED_ENSEMBLE_MISSING")
    if report.selected_method not in ENSEMBLE_METHODS:
        issues.append("INVALID_SELECTED_METHOD")
    if not report.report_identity.startswith("sequence-ensemble-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return SequenceEnsembleValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def ensemble_model_versions(
    evaluations: Sequence[SequenceEvaluationResult],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (item.model_kind, item.model_version)
        for item in _validate_evaluations(evaluations)
    )


__all__ = [
    "SEQUENCE_ENSEMBLE_VERSION",
    "VALID",
    "INVALID",
    "ENSEMBLE_METHODS",
    "SequenceModelComparisonResult",
    "SequenceComparisonReport",
    "SequenceEnsembleWeights",
    "SequenceEnsembleResult",
    "SequenceEnsembleReport",
    "SequenceEnsembleValidationResult",
    "compare_sequence_evaluations",
    "build_sequence_ensemble_weights",
    "build_sequence_ensemble",
    "select_best_ensemble",
    "build_sequence_ensemble_report",
    "validate_sequence_ensemble_weights",
    "validate_sequence_ensemble",
    "validate_sequence_ensemble_report",
    "ensemble_model_versions",
]
