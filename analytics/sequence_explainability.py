from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.candidate_scoring import (
    SequenceCandidateRanking,
    SequenceCandidateScore,
    validate_sequence_candidate_ranking,
)
from analytics.sequence_ensemble import (
    SequenceEnsembleResult,
    validate_sequence_ensemble,
)
from analytics.sequence_evaluation import SequenceEvaluationResult

SEQUENCE_EXPLAINABILITY_VERSION = "37.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class SequenceCandidateExplanation:
    candidate: int
    rank: int
    probability: float
    score: float
    probability_share: float
    rank_percentile: float
    gap_to_previous: float
    gap_to_next: float
    cumulative_probability_through_rank: float
    entropy: float
    normalized_entropy: float
    effective_candidate_count: float
    explanation_identity: str


@dataclass(frozen=True)
class SequenceModelCandidateAttribution:
    model_kind: str
    model_version: str
    weight: float
    candidate_probability: float
    weighted_contribution: float
    contribution_share: float


@dataclass(frozen=True)
class SequenceCandidateExplainability:
    version: str
    dataset_identity: str
    ensemble_identity: str
    observation_index: int
    ensemble_method: str
    ensemble_weights: tuple[tuple[str, float], ...]
    candidate_explanations: tuple[SequenceCandidateExplanation, ...]
    selected_candidate: int
    selected_rank: int
    selected_probability: float
    selected_score: float
    probability_margin: float
    entropy: float
    normalized_entropy: float
    effective_candidate_count: float
    model_attributions: tuple[SequenceModelCandidateAttribution, ...]
    attribution_available: bool
    explanation_identity: str
@dataclass(frozen=True)
class SequenceExplainabilityReport:
    version: str
    dataset_identity: str
    ensemble_identity: str
    explanations: tuple[SequenceCandidateExplainability, ...]
    report_identity: str


@dataclass(frozen=True)
class SequenceExplainabilityValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _entropy(probabilities: Sequence[float]) -> float:
    return sum(
        -float(p) * math.log(max(float(p), 1e-15))
        for p in probabilities
    )


def _validate_full_probability_row(
    probabilities: Sequence[float],
) -> tuple[float, ...]:
    row = tuple(float(p) for p in probabilities)
    if len(row) != 10:
        raise ValueError("probability rows must contain exactly 10 digits.")
    if any(not math.isfinite(p) or p < 0 for p in row):
        raise ValueError("probabilities must be finite and non-negative.")
    total = sum(row)
    if total <= 0 or abs(total - 1.0) > 1e-6:
        raise ValueError("probability rows must have total mass 1.")
    return row


def _explanation_identity(
    dataset_identity: str,
    ensemble_identity: str,
    observation_index: int,
    candidate_explanations: Sequence[SequenceCandidateExplanation],
    attributions: Sequence[SequenceModelCandidateAttribution],
) -> str:
    payload = {
        "version": SEQUENCE_EXPLAINABILITY_VERSION,
        "dataset": dataset_identity,
        "ensemble": ensemble_identity,
        "observation": observation_index,
        "candidates": [
            (
                item.candidate,
                item.rank,
                item.probability,
                item.score,
                item.gap_to_previous,
                item.gap_to_next,
            )
            for item in candidate_explanations
        ],
        "attributions": [
            (
                item.model_kind,
                item.model_version,
                item.weight,
                item.candidate_probability,
                item.weighted_contribution,
                item.contribution_share,
            )
            for item in attributions
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return "sequence-explanation-" + digest
def _rank_candidate_explanations(
    ranking: SequenceCandidateRanking,
) -> tuple[SequenceCandidateExplanation, ...]:
    probabilities = [item.probability for item in ranking.candidates]
    total_visible = sum(probabilities)
    explanations = []
    for index, item in enumerate(ranking.candidates):
        previous_probability = (
            ranking.candidates[index - 1].probability
            if index > 0
            else item.probability
        )
        next_probability = (
            ranking.candidates[index + 1].probability
            if index + 1 < len(ranking.candidates)
            else 0.0
        )
        cumulative = sum(probabilities[: index + 1])
        explanations.append(
            SequenceCandidateExplanation(
                candidate=item.candidate,
                rank=item.rank,
                probability=item.probability,
                score=item.score,
                probability_share=(
                    item.probability / total_visible if total_visible > 0 else 0.0
                ),
                rank_percentile=(10 - item.rank + 1) / 10.0,
                gap_to_previous=item.probability - previous_probability,
                gap_to_next=item.probability - next_probability,
                cumulative_probability_through_rank=cumulative,
                entropy=ranking.entropy,
                normalized_entropy=ranking.entropy / math.log(10.0),
                effective_candidate_count=math.exp(ranking.entropy),
                explanation_identity="",
            )
        )
    return tuple(explanations)


def _build_model_attributions(
    ensemble: SequenceEnsembleResult,
    candidate: int,
    observation_index: int,
    evaluations: Sequence[SequenceEvaluationResult],
) -> tuple[SequenceModelCandidateAttribution, ...]:
    rows = tuple(evaluations)
    if not rows:
        return ()
    if len(rows) != len(ensemble.model_kinds):
        raise ValueError("evaluation count must match ensemble model count.")
    for evaluation, model_kind in zip(rows, ensemble.model_kinds):
        if evaluation.model_kind != model_kind:
            raise ValueError("evaluation model order must match ensemble model order.")
        if evaluation.dataset_identity != ensemble.dataset_identity:
            raise ValueError("evaluation dataset identity mismatch.")
        if evaluation.observations != ensemble.observations:
            raise ValueError("evaluation observation count mismatch.")
        if len(evaluation.probabilities) != ensemble.observations:
            raise ValueError("evaluation probability count mismatch.")
    if observation_index < 0 or observation_index >= ensemble.observations:
        raise IndexError("observation_index is outside ensemble observations.")
    raw = []
    for weight, evaluation in zip(ensemble.weights, rows):
        probability = _validate_full_probability_row(
            evaluation.probabilities[observation_index]
        )[candidate]
        raw.append((evaluation, float(weight), probability))
    weighted_total = sum(weight * probability for _, weight, probability in raw)
    if weighted_total <= 0:
        return tuple(
            SequenceModelCandidateAttribution(
                evaluation.model_kind,
                evaluation.model_version,
                weight,
                probability,
                0.0,
                0.0,
            )
            for evaluation, weight, probability in raw
        )
    return tuple(
        SequenceModelCandidateAttribution(
            evaluation.model_kind,
            evaluation.model_version,
            weight,
            probability,
            weight * probability,
            (weight * probability) / weighted_total,
        )
        for evaluation, weight, probability in raw
    )
def explain_candidate_ranking(
    ranking: SequenceCandidateRanking,
    ensemble: SequenceEnsembleResult,
    evaluations: Sequence[SequenceEvaluationResult] = (),
) -> SequenceCandidateExplainability:
    ranking_validation = validate_sequence_candidate_ranking(ranking)
    if not ranking_validation.is_valid:
        raise ValueError(
            "ranking is invalid: " + ",".join(ranking_validation.issues)
        )
    ensemble_validation = validate_sequence_ensemble(ensemble)
    if not ensemble_validation.is_valid:
        raise ValueError(
            "ensemble is invalid: " + ",".join(ensemble_validation.issues)
        )
    if ranking.dataset_identity != ensemble.dataset_identity:
        raise ValueError("ranking dataset identity mismatch.")
    if ranking.ensemble_identity != ensemble.ensemble_identity:
        raise ValueError("ranking ensemble identity mismatch.")
    if ranking.observation_index >= ensemble.observations:
        raise IndexError("ranking observation exceeds ensemble observations.")

    candidate_explanations = _rank_candidate_explanations(ranking)
    attributions = _build_model_attributions(
        ensemble,
        ranking.candidates[0].candidate,
        ranking.observation_index,
        evaluations,
    )
    selected = candidate_explanations[0]
    identity = _explanation_identity(
        ensemble.dataset_identity,
        ensemble.ensemble_identity,
        ranking.observation_index,
        candidate_explanations,
        attributions,
    )
    return SequenceCandidateExplainability(
        SEQUENCE_EXPLAINABILITY_VERSION,
        ensemble.dataset_identity,
        ensemble.ensemble_identity,
        ranking.observation_index,
        ensemble.method,
        tuple(zip(ensemble.model_kinds, ensemble.weights)),
        candidate_explanations,
        selected.candidate,
        selected.rank,
        selected.probability,
        selected.score,
        ranking.probability_margin,
        ranking.entropy,
        ranking.entropy / math.log(10.0),
        math.exp(ranking.entropy),
        attributions,
        bool(attributions),
        identity,
    )


def explain_ensemble_observation(
    ensemble: SequenceEnsembleResult,
    observation_index: int = -1,
    top_k: int = 10,
    evaluations: Sequence[SequenceEvaluationResult] = (),
) -> SequenceCandidateExplainability:
    from analytics.candidate_scoring import rank_ensemble_candidates

    validation = validate_sequence_ensemble(ensemble)
    if not validation.is_valid:
        raise ValueError(
            "ensemble is invalid: " + ",".join(validation.issues)
        )
    ranking = rank_ensemble_candidates(
        ensemble,
        observation_index=observation_index,
        top_k=top_k,
    )
    return explain_candidate_ranking(ranking, ensemble, evaluations)


def build_explainability_report(
    ensemble: SequenceEnsembleResult,
    top_k: int = 10,
    evaluations: Sequence[SequenceEvaluationResult] = (),
) -> SequenceExplainabilityReport:
    if top_k <= 0 or top_k > 10:
        raise ValueError("top_k must be between 1 and 10.")
    explanations = tuple(
        explain_ensemble_observation(
            ensemble,
            observation_index=index,
            top_k=top_k,
            evaluations=evaluations,
        )
        for index in range(ensemble.observations)
    )
    payload = {
        "version": SEQUENCE_EXPLAINABILITY_VERSION,
        "dataset": ensemble.dataset_identity,
        "ensemble": ensemble.ensemble_identity,
        "top_k": top_k,
        "explanations": [item.explanation_identity for item in explanations],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceExplainabilityReport(
        SEQUENCE_EXPLAINABILITY_VERSION,
        ensemble.dataset_identity,
        ensemble.ensemble_identity,
        explanations,
        "sequence-explainability-report-" + digest,
    )
def validate_sequence_explainability(
    explanation: SequenceCandidateExplainability,
) -> SequenceExplainabilityValidationResult:
    if not isinstance(explanation, SequenceCandidateExplainability):
        return SequenceExplainabilityValidationResult(
            INVALID, ("INVALID_EXPLANATION_TYPE",)
        )
    issues: list[str] = []
    if explanation.version != SEQUENCE_EXPLAINABILITY_VERSION:
        issues.append("INVALID_VERSION")
    if not explanation.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not explanation.ensemble_identity:
        issues.append("MISSING_ENSEMBLE_IDENTITY")
    if explanation.observation_index < 0:
        issues.append("INVALID_OBSERVATION_INDEX")
    if not explanation.candidate_explanations:
        issues.append("NO_CANDIDATE_EXPLANATIONS")
    if len(explanation.ensemble_weights) != len(explanation.model_attributions) and explanation.attribution_available:
        issues.append("ATTRIBUTION_MODEL_COUNT_MISMATCH")
    if explanation.selected_rank <= 0 or explanation.selected_rank > 10:
        issues.append("INVALID_SELECTED_RANK")
    if not 0 <= explanation.selected_candidate <= 9:
        issues.append("INVALID_SELECTED_CANDIDATE")
    for item in explanation.candidate_explanations:
        if not 0 <= item.candidate <= 9:
            issues.append("INVALID_CANDIDATE")
        if item.rank <= 0 or item.rank > 10:
            issues.append("INVALID_RANK")
        if not math.isfinite(item.probability) or not 0 <= item.probability <= 1:
            issues.append("INVALID_PROBABILITY")
        if not math.isfinite(item.score) or not 0 <= item.score <= 100:
            issues.append("INVALID_SCORE")
        if not math.isfinite(item.normalized_entropy) or item.normalized_entropy < 0:
            issues.append("INVALID_NORMALIZED_ENTROPY")
        if not math.isfinite(item.effective_candidate_count) or item.effective_candidate_count <= 0:
            issues.append("INVALID_EFFECTIVE_COUNT")
    for item in explanation.model_attributions:
        if not math.isfinite(item.weight) or item.weight < 0:
            issues.append("INVALID_ATTRIBUTION_WEIGHT")
        if not math.isfinite(item.candidate_probability) or not 0 <= item.candidate_probability <= 1:
            issues.append("INVALID_ATTRIBUTION_PROBABILITY")
        if not math.isfinite(item.weighted_contribution) or item.weighted_contribution < 0:
            issues.append("INVALID_WEIGHTED_CONTRIBUTION")
        if not math.isfinite(item.contribution_share) or not 0 <= item.contribution_share <= 1:
            issues.append("INVALID_CONTRIBUTION_SHARE")
    if not explanation.explanation_identity.startswith("sequence-explanation-"):
        issues.append("INVALID_EXPLANATION_IDENTITY")
    return SequenceExplainabilityValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def validate_explainability_report(
    report: SequenceExplainabilityReport,
) -> SequenceExplainabilityValidationResult:
    if not isinstance(report, SequenceExplainabilityReport):
        return SequenceExplainabilityValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != SEQUENCE_EXPLAINABILITY_VERSION:
        issues.append("INVALID_VERSION")
    if not report.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not report.ensemble_identity:
        issues.append("MISSING_ENSEMBLE_IDENTITY")
    if not report.explanations:
        issues.append("NO_EXPLANATIONS")
    for explanation in report.explanations:
        if explanation.dataset_identity != report.dataset_identity:
            issues.append("DATASET_IDENTITY_MISMATCH")
        if explanation.ensemble_identity != report.ensemble_identity:
            issues.append("ENSEMBLE_IDENTITY_MISMATCH")
        if not validate_sequence_explainability(explanation).is_valid:
            issues.append("INVALID_EXPLANATION")
    if not report.report_identity.startswith("sequence-explainability-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return SequenceExplainabilityValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def explanation_summary(
    explanation: SequenceCandidateExplainability,
) -> str:
    selected = explanation.selected_candidate
    return (
        f"Candidate {selected} is rank {explanation.selected_rank} with "
        f"probability {explanation.selected_probability:.6f} and score "
        f"{explanation.selected_score:.2f}; probability margin is "
        f"{explanation.probability_margin:.6f}, normalized entropy is "
        f"{explanation.normalized_entropy:.6f}."
    )


__all__ = [
    "SEQUENCE_EXPLAINABILITY_VERSION",
    "VALID",
    "INVALID",
    "SequenceCandidateExplanation",
    "SequenceModelCandidateAttribution",
    "SequenceCandidateExplainability",
    "SequenceExplainabilityReport",
    "SequenceExplainabilityValidationResult",
    "explain_candidate_ranking",
    "explain_ensemble_observation",
    "build_explainability_report",
    "validate_sequence_explainability",
    "validate_explainability_report",
    "explanation_summary",
]
