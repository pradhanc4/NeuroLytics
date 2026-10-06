from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.sequence_ensemble import (
    SequenceEnsembleResult,
    validate_sequence_ensemble,
)

SEQUENCE_ADVANCED_ENSEMBLE_VERSION = "38.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class SequenceEnsembleAgreement:
    ensemble_identities: tuple[str, ...]
    mean_pairwise_js_divergence: float
    max_pairwise_js_divergence: float
    mean_pairwise_total_variation: float
    agreement_score: float
    identity: str


@dataclass(frozen=True)
class SequenceConsensusWeights:
    ensemble_identities: tuple[str, ...]
    weights: tuple[float, ...]
    method: str
    identity: str


@dataclass(frozen=True)
class SequenceConsensusResult:
    version: str
    dataset_identity: str
    ensemble_identities: tuple[str, ...]
    weights: tuple[float, ...]
    probabilities: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]
    observations: int
    top_candidates: tuple[tuple[int, ...], ...]
    probability_margin: tuple[float, ...]
    entropy: tuple[float, ...]
    normalized_entropy: tuple[float, ...]
    effective_candidate_count: tuple[float, ...]
    agreement_score: float
    mean_pairwise_js_divergence: float
    mean_pairwise_total_variation: float
    consensus_identity: str


@dataclass(frozen=True)
class SequenceAdvancedEnsembleReport:
    version: str
    dataset_identity: str
    agreement: SequenceEnsembleAgreement
    weights: SequenceConsensusWeights
    consensus: SequenceConsensusResult
    report_identity: str


@dataclass(frozen=True)
class SequenceAdvancedEnsembleValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _row(row: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(v) for v in row)
    if len(values) != 10 or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("probability rows must contain ten finite non-negative values.")
    total = sum(values)
    if total <= 0 or abs(total - 1.0) > 1e-6:
        raise ValueError("probability rows must sum to one.")
    return values


def _js(a: Sequence[float], b: Sequence[float]) -> float:
    left, right = _row(a), _row(b)
    midpoint = tuple((x + y) / 2.0 for x, y in zip(left, right))
    def kl(source, target):
        return sum(x * math.log(x / max(y, 1e-15)) for x, y in zip(source, target) if x > 0)
    return max(0.0, min(1.0, 0.5 * kl(left, midpoint) + 0.5 * kl(right, midpoint)))


def _tv(a: Sequence[float], b: Sequence[float]) -> float:
    return 0.5 * sum(abs(x - y) for x, y in zip(_row(a), _row(b)))


def _entropy(row: Sequence[float]) -> float:
    return sum(-p * math.log(max(p, 1e-15)) for p in _row(row))


def _identity(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return prefix + digest


def _validate_inputs(ensembles: Sequence[SequenceEnsembleResult]) -> tuple[SequenceEnsembleResult, ...]:
    rows = tuple(ensembles)
    if not rows:
        raise ValueError("at least two ensemble results are required.")
    if len(rows) < 2:
        raise ValueError("advanced consensus requires at least two ensemble results.")
    first = rows[0]
    first_validation = validate_sequence_ensemble(first)
    if not first_validation.is_valid:
        raise ValueError("invalid ensemble: " + ",".join(first_validation.issues))
    for item in rows[1:]:
        validation = validate_sequence_ensemble(item)
        if not validation.is_valid:
            raise ValueError("invalid ensemble: " + ",".join(validation.issues))
        if item.dataset_identity != first.dataset_identity:
            raise ValueError("all ensembles must share dataset identity.")
        if item.observations != first.observations or item.targets != first.targets:
            raise ValueError("all ensembles must share observations and targets.")
        if len(item.probabilities) != first.observations:
            raise ValueError("ensemble probability count mismatch.")
    identities = [item.ensemble_identity for item in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("ensemble identities must be unique.")
    return rows


def analyze_ensemble_agreement(ensembles: Sequence[SequenceEnsembleResult]) -> SequenceEnsembleAgreement:
    rows = _validate_inputs(ensembles)
    js_values, tv_values = [], []
    for left_index in range(len(rows)):
        for right_index in range(left_index + 1, len(rows)):
            for observation in range(rows[0].observations):
                js_values.append(_js(rows[left_index].probabilities[observation], rows[right_index].probabilities[observation]))
                tv_values.append(_tv(rows[left_index].probabilities[observation], rows[right_index].probabilities[observation]))
    mean_js = sum(js_values) / len(js_values)
    mean_tv = sum(tv_values) / len(tv_values)
    max_js = max(js_values)
    agreement = max(0.0, min(1.0, 1.0 - mean_js))
    ids = tuple(item.ensemble_identity for item in rows)
    return SequenceEnsembleAgreement(
        ids, mean_js, max_js, mean_tv, agreement,
        _identity("sequence-agreement-", (SEQUENCE_ADVANCED_ENSEMBLE_VERSION, ids, mean_js, max_js, mean_tv, agreement)),
    )


def build_consensus_weights(
    ensembles: Sequence[SequenceEnsembleResult],
    method: str = "inverse_disagreement",
) -> SequenceConsensusWeights:
    rows = _validate_inputs(ensembles)
    if method not in ("equal_weight", "inverse_disagreement"):
        raise ValueError("unsupported consensus weight method.")
    if method == "equal_weight":
        raw = [1.0] * len(rows)
    else:
        raw = []
        for index, item in enumerate(rows):
            disagreements = []
            for other_index, other in enumerate(rows):
                if index == other_index:
                    continue
                disagreements.extend(
                    _js(item.probabilities[obs], other.probabilities[obs])
                    for obs in range(rows[0].observations)
                )
            raw.append(1.0 / max(sum(disagreements) / len(disagreements), 1e-12))
    total = sum(raw)
    weights = tuple(value / total for value in raw)
    ids = tuple(item.ensemble_identity for item in rows)
    return SequenceConsensusWeights(
        ids, weights, method,
        _identity("sequence-consensus-weights-", (SEQUENCE_ADVANCED_ENSEMBLE_VERSION, ids, weights, method)),
    )


def _blend(rows: tuple[SequenceEnsembleResult, ...], weights: Sequence[float]) -> tuple[tuple[float, ...], ...]:
    if len(rows) != len(weights):
        raise ValueError("ensemble/weight count mismatch.")
    total = sum(float(v) for v in weights)
    if total <= 0:
        raise ValueError("consensus weights must have positive mass.")
    normalized = tuple(float(v) / total for v in weights)
    output = []
    for obs in range(rows[0].observations):
        values = tuple(sum(weight * row.probabilities[obs][digit] for weight, row in zip(normalized, rows)) for digit in range(10))
        output.append(_row(values))
    return tuple(output)


def _rank_row(row: Sequence[float]) -> tuple[int, ...]:
    return tuple(sorted(range(10), key=lambda digit: (-float(row[digit]), digit)))


def build_consensus(
    ensembles: Sequence[SequenceEnsembleResult],
    weight_method: str = "inverse_disagreement",
) -> SequenceConsensusResult:
    rows = _validate_inputs(ensembles)
    agreement = analyze_ensemble_agreement(rows)
    weights_result = build_consensus_weights(rows, weight_method)
    probabilities = _blend(rows, weights_result.weights)
    top_candidates = tuple(_rank_row(row) for row in probabilities)
    margins = tuple(row[top[0]] - row[top[1]] for row, top in zip(probabilities, top_candidates))
    entropy = tuple(_entropy(row) for row in probabilities)
    normalized_entropy = tuple(value / math.log(10.0) for value in entropy)
    effective = tuple(math.exp(value) for value in entropy)
    ids = tuple(item.ensemble_identity for item in rows)
    identity = _identity(
        "sequence-consensus-",
        (SEQUENCE_ADVANCED_ENSEMBLE_VERSION, rows[0].dataset_identity, ids, weights_result.weights, probabilities),
    )
    return SequenceConsensusResult(
        SEQUENCE_ADVANCED_ENSEMBLE_VERSION,
        rows[0].dataset_identity,
        ids,
        weights_result.weights,
        probabilities,
        rows[0].targets,
        rows[0].observations,
        top_candidates,
        margins,
        entropy,
        normalized_entropy,
        effective,
        agreement.agreement_score,
        agreement.mean_pairwise_js_divergence,
        agreement.mean_pairwise_total_variation,
        identity,
    )


def build_advanced_ensemble_report(
    ensembles: Sequence[SequenceEnsembleResult],
    weight_method: str = "inverse_disagreement",
) -> SequenceAdvancedEnsembleReport:
    rows = _validate_inputs(ensembles)
    agreement = analyze_ensemble_agreement(rows)
    weights = build_consensus_weights(rows, weight_method)
    consensus = build_consensus(rows, weight_method)
    identity = _identity(
        "sequence-advanced-ensemble-report-",
        (SEQUENCE_ADVANCED_ENSEMBLE_VERSION, rows[0].dataset_identity, agreement.identity, weights.identity, consensus.consensus_identity),
    )
    return SequenceAdvancedEnsembleReport(
        SEQUENCE_ADVANCED_ENSEMBLE_VERSION,
        rows[0].dataset_identity,
        agreement,
        weights,
        consensus,
        identity,
    )
def validate_consensus_weights(weights: SequenceConsensusWeights) -> SequenceAdvancedEnsembleValidationResult:
    if not isinstance(weights, SequenceConsensusWeights):
        return SequenceAdvancedEnsembleValidationResult(INVALID, ("INVALID_WEIGHT_TYPE",))
    issues = []
    if weights.method not in ("equal_weight", "inverse_disagreement"):
        issues.append("INVALID_METHOD")
    if len(weights.ensemble_identities) < 2:
        issues.append("INSUFFICIENT_ENSEMBLES")
    if len(weights.ensemble_identities) != len(weights.weights):
        issues.append("WEIGHT_LENGTH_MISMATCH")
    if any(not math.isfinite(v) or v < 0 for v in weights.weights):
        issues.append("INVALID_WEIGHT")
    if weights.weights and abs(sum(weights.weights) - 1.0) > 1e-8:
        issues.append("WEIGHTS_NOT_NORMALIZED")
    if not weights.identity.startswith("sequence-consensus-weights-"):
        issues.append("INVALID_WEIGHT_IDENTITY")
    return SequenceAdvancedEnsembleValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def validate_consensus(consensus: SequenceConsensusResult) -> SequenceAdvancedEnsembleValidationResult:
    if not isinstance(consensus, SequenceConsensusResult):
        return SequenceAdvancedEnsembleValidationResult(INVALID, ("INVALID_CONSENSUS_TYPE",))
    issues = []
    if consensus.version != SEQUENCE_ADVANCED_ENSEMBLE_VERSION:
        issues.append("INVALID_VERSION")
    if not consensus.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if len(consensus.ensemble_identities) < 2:
        issues.append("INSUFFICIENT_ENSEMBLES")
    if len(consensus.ensemble_identities) != len(consensus.weights):
        issues.append("WEIGHT_LENGTH_MISMATCH")
    if consensus.observations <= 0 or len(consensus.probabilities) != consensus.observations:
        issues.append("INVALID_OBSERVATIONS")
    if len(consensus.targets) != consensus.observations:
        issues.append("TARGET_LENGTH_MISMATCH")
    if len(consensus.top_candidates) != consensus.observations:
        issues.append("TOP_CANDIDATE_LENGTH_MISMATCH")
    for row in consensus.probabilities:
        try:
            _row(row)
        except ValueError:
            issues.append("INVALID_PROBABILITY_ROW")
    for value in consensus.agreement_score, consensus.mean_pairwise_js_divergence, consensus.mean_pairwise_total_variation:
        if not math.isfinite(value) or value < 0:
            issues.append("INVALID_AGREEMENT_DIAGNOSTIC")
    if not 0 <= consensus.agreement_score <= 1:
        issues.append("AGREEMENT_SCORE_OUT_OF_RANGE")
    if not consensus.consensus_identity.startswith("sequence-consensus-"):
        issues.append("INVALID_CONSENSUS_IDENTITY")
    return SequenceAdvancedEnsembleValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def validate_advanced_ensemble_report(report: SequenceAdvancedEnsembleReport) -> SequenceAdvancedEnsembleValidationResult:
    if not isinstance(report, SequenceAdvancedEnsembleReport):
        return SequenceAdvancedEnsembleValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != SEQUENCE_ADVANCED_ENSEMBLE_VERSION:
        issues.append("INVALID_VERSION")
    if report.dataset_identity != report.consensus.dataset_identity:
        issues.append("DATASET_IDENTITY_MISMATCH")
    if not validate_consensus_weights(report.weights).is_valid:
        issues.append("INVALID_WEIGHTS")
    if not validate_consensus(report.consensus).is_valid:
        issues.append("INVALID_CONSENSUS")
    if report.agreement.ensemble_identities != report.weights.ensemble_identities:
        issues.append("AGREEMENT_WEIGHT_IDENTITY_MISMATCH")
    if not report.report_identity.startswith("sequence-advanced-ensemble-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return SequenceAdvancedEnsembleValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def consensus_top_candidate(consensus: SequenceConsensusResult, observation_index: int = -1) -> int:
    if observation_index < 0:
        observation_index += consensus.observations
    if observation_index < 0 or observation_index >= consensus.observations:
        raise IndexError("observation_index is outside consensus observations.")
    return consensus.top_candidates[observation_index][0]


def consensus_summary(consensus: SequenceConsensusResult) -> str:
    candidate = consensus_top_candidate(consensus)
    index = consensus.observations - 1
    probability = consensus.probabilities[index][candidate]
    return (
        f"Consensus candidate {candidate} has probability {probability:.6f}; "
        f"agreement score is {consensus.agreement_score:.6f}, "
        f"mean JS divergence is {consensus.mean_pairwise_js_divergence:.6f}."
    )


__all__ = [
    "SEQUENCE_ADVANCED_ENSEMBLE_VERSION",
    "VALID",
    "INVALID",
    "SequenceEnsembleAgreement",
    "SequenceConsensusWeights",
    "SequenceConsensusResult",
    "SequenceAdvancedEnsembleReport",
    "SequenceAdvancedEnsembleValidationResult",
    "analyze_ensemble_agreement",
    "build_consensus_weights",
    "build_consensus",
    "build_advanced_ensemble_report",
    "validate_consensus_weights",
    "validate_consensus",
    "validate_advanced_ensemble_report",
    "consensus_top_candidate",
    "consensus_summary",
]
