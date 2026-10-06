from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.sequence_framework import SequenceFrameworkDataset, SequenceModelRun

SEQUENCE_EVALUATION_VERSION = "34.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class SequenceEvaluationDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class SequenceEvaluationResult:
    model_kind: str
    model_version: str
    dataset_identity: str
    observations: int
    log_loss: float
    accuracy: float
    top_k_accuracy: float
    brier_score: float
    expected_calibration_error: float
    mean_entropy: float
    probabilities: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]


@dataclass(frozen=True)
class SequenceCalibrationResult:
    model_kind: str
    model_version: str
    calibration_dataset_identity: str
    temperature: float
    pre_log_loss: float
    post_log_loss: float
    pre_brier_score: float
    post_brier_score: float


@dataclass(frozen=True)
class SequenceEvaluationReport:
    evaluation_version: str
    dataset_identity: str
    evaluations: tuple[SequenceEvaluationResult, ...]
    calibrations: tuple[SequenceCalibrationResult, ...]
    report_identity: str


@dataclass(frozen=True)
class SequenceEvaluationValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def build_sequence_evaluation_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> SequenceEvaluationDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = tuple(tuple(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    for row in rows:
        if not row:
            raise ValueError("sequence cannot be empty.")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in row):
            raise ValueError("sequence values must be integers.")
        if any(v < 0 or v > 9 for v in row):
            raise ValueError("sequence values must be digits 0-9.")
    return SequenceEvaluationDataset(rows, identity, target_name)


def _window_size(run: SequenceModelRun) -> int:
    if run.model_kind == "markov":
        return int(run.model.config.order)
    if run.model_kind == "hidden_markov":
        return 1
    return int(run.model.config.sequence_length)


def _probability_rows(
    run: SequenceModelRun,
    dataset: SequenceEvaluationDataset,
) -> tuple[tuple[tuple[float, ...], ...], tuple[int, ...]]:
    if not run.model.fitted:
        raise ValueError("model run must contain a fitted model.")
    width = _window_size(run)
    probabilities = []
    targets = []
    for sequence in dataset.sequences:
        if run.model_kind == "hidden_markov":
            for index in range(1, len(sequence)):
                probabilities.append(
                    tuple(float(v) for v in run.model.predict_next_proba(sequence[:index]))
                )
                targets.append(sequence[index])
            continue
        if len(sequence) <= width:
            continue
        windows = [
            sequence[index - width:index]
            for index in range(width, len(sequence))
        ]
        probabilities.extend(
            tuple(float(v) for v in row)
            for row in run.model.predict_proba(windows)
        )
        targets.extend(sequence[width:])
    if not probabilities:
        raise ValueError("dataset has no evaluable sequence windows.")
    return tuple(probabilities), tuple(targets)


def _validate_probability_rows(
    probabilities: Sequence[Sequence[float]],
    targets: Sequence[int],
) -> tuple[tuple[tuple[float, ...], ...], tuple[int, ...]]:
    rows = tuple(tuple(float(v) for v in row) for row in probabilities)
    labels = tuple(int(v) for v in targets)
    if not rows or len(rows) != len(labels):
        raise ValueError("probabilities and targets must have equal non-zero length.")
    for row, target in zip(rows, labels):
        if len(row) != 10:
            raise ValueError("probability rows must contain exactly 10 digits.")
        if not 0 <= target <= 9:
            raise ValueError("targets must be digits 0-9.")
        if any(not math.isfinite(v) or v < 0 for v in row):
            raise ValueError("probabilities must be finite and non-negative.")
        if abs(sum(row) - 1.0) > 1e-6:
            raise ValueError("each probability row must sum to 1.")
    return rows, labels


def log_loss(probabilities: Sequence[Sequence[float]], targets: Sequence[int]) -> float:
    rows, labels = _validate_probability_rows(probabilities, targets)
    return -sum(math.log(max(row[target], 1e-15)) for row, target in zip(rows, labels)) / len(labels)


def accuracy(probabilities: Sequence[Sequence[float]], targets: Sequence[int]) -> float:
    rows, labels = _validate_probability_rows(probabilities, targets)
    correct = sum(max(range(10), key=lambda d: (row[d], -d)) == target for row, target in zip(rows, labels))
    return correct / len(labels)


def top_k_accuracy(
    probabilities: Sequence[Sequence[float]],
    targets: Sequence[int],
    top_k: int = 3,
) -> float:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    rows, labels = _validate_probability_rows(probabilities, targets)
    k = min(top_k, 10)
    correct = 0
    for row, target in zip(rows, labels):
        ranked = sorted(range(10), key=lambda d: (-row[d], d))
        correct += int(target in ranked[:k])
    return correct / len(labels)


def brier_score(probabilities: Sequence[Sequence[float]], targets: Sequence[int]) -> float:
    rows, labels = _validate_probability_rows(probabilities, targets)
    return sum(sum((p - float(d == target)) ** 2 for d, p in enumerate(row)) for row, target in zip(rows, labels)) / len(labels)


def expected_calibration_error(
    probabilities: Sequence[Sequence[float]],
    targets: Sequence[int],
    bins: int = 10,
) -> float:
    if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
        raise ValueError("bins must be a positive integer.")
    rows, labels = _validate_probability_rows(probabilities, targets)
    buckets = [[] for _ in range(bins)]
    for row, target in zip(rows, labels):
        prediction = max(range(10), key=lambda d: (row[d], -d))
        confidence = row[prediction]
        index = min(bins - 1, int(confidence * bins))
        buckets[index].append((confidence, float(prediction == target)))
    total = len(labels)
    return sum(
        (len(bucket) / total) * abs(
            sum(conf for conf, _ in bucket) / len(bucket)
            - sum(correct for _, correct in bucket) / len(bucket)
        )
        for bucket in buckets if bucket
    )


def mean_entropy(probabilities: Sequence[Sequence[float]]) -> float:
    rows, _ = _validate_probability_rows(probabilities, [0] * len(probabilities))
    return sum(
        sum(-p * math.log(max(p, 1e-15)) for p in row) for row in rows
    ) / len(rows)


def evaluate_sequence_model(
    run: SequenceModelRun,
    dataset: SequenceEvaluationDataset,
    top_k: int = 3,
    calibration_bins: int = 10,
) -> SequenceEvaluationResult:
    if run.dataset_identity != dataset.identity:
        raise ValueError("model run dataset identity must match evaluation dataset.")
    probabilities, targets = _probability_rows(run, dataset)
    return SequenceEvaluationResult(
        run.model_kind,
        run.model_version,
        dataset.identity,
        len(targets),
        log_loss(probabilities, targets),
        accuracy(probabilities, targets),
        top_k_accuracy(probabilities, targets, top_k),
        brier_score(probabilities, targets),
        expected_calibration_error(probabilities, targets, calibration_bins),
        mean_entropy(probabilities),
        probabilities,
        targets,
    )


def _temperature_scale(
    probabilities: Sequence[Sequence[float]],
    temperature: float,
) -> tuple[tuple[float, ...], ...]:
    if temperature <= 0 or not math.isfinite(temperature):
        raise ValueError("temperature must be positive and finite.")
    rows, _ = _validate_probability_rows(probabilities, [0] * len(probabilities))
    scaled = []
    for row in rows:
        logits = [math.log(max(p, 1e-15)) / temperature for p in row]
        pivot = max(logits)
        exp_values = [math.exp(min(60.0, value - pivot)) for value in logits]
        denominator = sum(exp_values)
        scaled.append(tuple(value / denominator for value in exp_values))
    return tuple(scaled)


def fit_temperature(
    probabilities: Sequence[Sequence[float]],
    targets: Sequence[int],
) -> float:
    rows, labels = _validate_probability_rows(probabilities, targets)
    best_temperature = 1.0
    best_loss = log_loss(rows, labels)
    for step in range(1, 151):
        temperature = 0.25 + step * 0.025
        candidate = _temperature_scale(rows, temperature)
        candidate_loss = log_loss(candidate, labels)
        if candidate_loss < best_loss - 1e-12:
            best_loss = candidate_loss
            best_temperature = temperature
    return best_temperature


def calibrate_sequence_model(
    run: SequenceModelRun,
    calibration_dataset: SequenceEvaluationDataset,
) -> SequenceCalibrationResult:
    if run.dataset_identity != calibration_dataset.identity:
        raise ValueError("model run dataset identity must match calibration dataset.")
    probabilities, targets = _probability_rows(run, calibration_dataset)
    temperature = fit_temperature(probabilities, targets)
    calibrated = _temperature_scale(probabilities, temperature)
    return SequenceCalibrationResult(
        run.model_kind,
        run.model_version,
        calibration_dataset.identity,
        temperature,
        log_loss(probabilities, targets),
        log_loss(calibrated, targets),
        brier_score(probabilities, targets),
        brier_score(calibrated, targets),
    )


def build_sequence_evaluation_report(
    dataset: SequenceEvaluationDataset,
    evaluations: Sequence[SequenceEvaluationResult],
    calibrations: Sequence[SequenceCalibrationResult] = (),
) -> SequenceEvaluationReport:
    normalized_evaluations = tuple(evaluations)
    normalized_calibrations = tuple(calibrations)
    for item in normalized_evaluations:
        if item.dataset_identity != dataset.identity:
            raise ValueError("evaluation dataset identity mismatch.")
    for item in normalized_calibrations:
        if item.calibration_dataset_identity != dataset.identity:
            raise ValueError("calibration dataset identity mismatch.")
    payload = {
        "version": SEQUENCE_EVALUATION_VERSION,
        "dataset": dataset.identity,
        "evaluations": [(x.model_kind, x.model_version) for x in normalized_evaluations],
        "calibrations": [(x.model_kind, x.temperature) for x in normalized_calibrations],
    }
    identity = "sequence-evaluation-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceEvaluationReport(
        SEQUENCE_EVALUATION_VERSION,
        dataset.identity,
        normalized_evaluations,
        normalized_calibrations,
        identity,
    )


def validate_sequence_evaluation_report(
    report: SequenceEvaluationReport,
) -> SequenceEvaluationValidationResult:
    if not isinstance(report, SequenceEvaluationReport):
        return SequenceEvaluationValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.evaluation_version != SEQUENCE_EVALUATION_VERSION:
        issues.append("INVALID_VERSION")
    if not report.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not report.evaluations:
        issues.append("NO_EVALUATIONS")
    for item in report.evaluations:
        if item.dataset_identity != report.dataset_identity:
            issues.append("EVALUATION_DATASET_MISMATCH")
        if item.observations <= 0:
            issues.append("INVALID_OBSERVATION_COUNT")
    for item in report.calibrations:
        if item.calibration_dataset_identity != report.dataset_identity:
            issues.append("CALIBRATION_DATASET_MISMATCH")
        if item.temperature <= 0:
            issues.append("INVALID_TEMPERATURE")
    if not report.report_identity.startswith("sequence-evaluation-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return SequenceEvaluationValidationResult(
        VALID if not issues else INVALID, tuple(sorted(set(issues)))
    )


__all__ = [
    "SEQUENCE_EVALUATION_VERSION",
    "VALID",
    "INVALID",
    "SequenceEvaluationDataset",
    "SequenceEvaluationResult",
    "SequenceCalibrationResult",
    "SequenceEvaluationReport",
    "SequenceEvaluationValidationResult",
    "build_sequence_evaluation_dataset",
    "log_loss",
    "accuracy",
    "top_k_accuracy",
    "brier_score",
    "expected_calibration_error",
    "mean_entropy",
    "evaluate_sequence_model",
    "fit_temperature",
    "calibrate_sequence_model",
    "build_sequence_evaluation_report",
    "validate_sequence_evaluation_report",
]
