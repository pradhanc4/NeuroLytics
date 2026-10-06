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

SEQUENCE_CANDIDATE_VERSION = "36.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class SequenceCandidateScore:
    candidate: int
    probability: float
    score: float
    rank: int


@dataclass(frozen=True)
class SequenceCandidateRanking:
    version: str
    dataset_identity: str
    ensemble_identity: str
    observation_index: int
    candidates: tuple[SequenceCandidateScore, ...]
    top_probability: float
    probability_margin: float
    entropy: float
    ranking_identity: str
@dataclass(frozen=True)
class SequenceCandidateRankingReport:
    version: str
    dataset_identity: str
    ensemble_identity: str
    rankings: tuple[SequenceCandidateRanking, ...]
    top_k: int
    report_identity: str


@dataclass(frozen=True)
class SequenceCandidateValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _validate_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")
    if top_k <= 0:
        raise ValueError("top_k must be positive.")
    return min(top_k, 10)


def _validate_probability_row(
    probabilities: Sequence[float],
) -> tuple[float, ...]:
    row = tuple(float(value) for value in probabilities)
    if len(row) != 10:
        raise ValueError("candidate probabilities must contain exactly 10 digits.")
    if any(not math.isfinite(value) or value < 0 for value in row):
        raise ValueError("candidate probabilities must be finite and non-negative.")
    total = sum(row)
    if total <= 0:
        raise ValueError("candidate probabilities must have positive mass.")
    if abs(total - 1.0) > 1e-6:
        raise ValueError("candidate probabilities must sum to 1.")
    return row
def _entropy(probabilities: Sequence[float]) -> float:
    return sum(
        -probability * math.log(max(probability, 1e-15))
        for probability in probabilities
    )


def _ranking_identity(
    dataset_identity: str,
    ensemble_identity: str,
    observation_index: int,
    candidates: Sequence[SequenceCandidateScore],
) -> str:
    payload = {
        "version": SEQUENCE_CANDIDATE_VERSION,
        "dataset": dataset_identity,
        "ensemble": ensemble_identity,
        "observation": observation_index,
        "candidates": [
            (item.candidate, item.probability, item.score, item.rank)
            for item in candidates
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return "sequence-candidate-ranking-" + digest


def rank_candidate_probabilities(
    probabilities: Sequence[float],
    dataset_identity: str,
    ensemble_identity: str,
    observation_index: int,
    top_k: int = 10,
) -> SequenceCandidateRanking:
    _validate_top_k(top_k)
    if not dataset_identity:
        raise ValueError("dataset_identity must be non-empty.")
    if not ensemble_identity:
        raise ValueError("ensemble_identity must be non-empty.")
    if isinstance(observation_index, bool) or not isinstance(observation_index, int):
        raise TypeError("observation_index must be an integer.")
    if observation_index < 0:
        raise ValueError("observation_index must be non-negative.")
    row = _validate_probability_row(probabilities)
    ordered = sorted(range(10), key=lambda digit: (-row[digit], digit))
    candidates = tuple(
        SequenceCandidateScore(
            candidate=digit,
            probability=row[digit],
            score=row[digit] * 100.0,
            rank=rank,
        )
        for rank, digit in enumerate(ordered, start=1)
    )
    visible = candidates[:top_k]
    margin = (
        visible[0].probability - visible[1].probability
        if len(visible) > 1
        else visible[0].probability
    )
    identity = _ranking_identity(
        dataset_identity, ensemble_identity, observation_index, visible
    )
    return SequenceCandidateRanking(
        SEQUENCE_CANDIDATE_VERSION,
        dataset_identity,
        ensemble_identity,
        observation_index,
        visible,
        visible[0].probability,
        margin,
        _entropy(row),
        identity,
    )
def rank_ensemble_candidates(
    ensemble: SequenceEnsembleResult,
    observation_index: int = -1,
    top_k: int = 10,
) -> SequenceCandidateRanking:
    validation = validate_sequence_ensemble(ensemble)
    if not validation.is_valid:
        raise ValueError(
            "ensemble is invalid: " + ",".join(validation.issues)
        )
    if not ensemble.probabilities:
        raise ValueError("ensemble contains no probability rows.")
    index = observation_index
    if index < 0:
        index = len(ensemble.probabilities) + index
    if index < 0 or index >= len(ensemble.probabilities):
        raise IndexError("observation_index is outside ensemble probability rows.")
    return rank_candidate_probabilities(
        ensemble.probabilities[index],
        ensemble.dataset_identity,
        ensemble.ensemble_identity,
        index,
        top_k,
    )


def build_candidate_ranking_report(
    ensemble: SequenceEnsembleResult,
    top_k: int = 10,
) -> SequenceCandidateRankingReport:
    _validate_top_k(top_k)
    validation = validate_sequence_ensemble(ensemble)
    if not validation.is_valid:
        raise ValueError(
            "ensemble is invalid: " + ",".join(validation.issues)
        )
    rankings = tuple(
        rank_candidate_probabilities(
            probabilities,
            ensemble.dataset_identity,
            ensemble.ensemble_identity,
            index,
            top_k,
        )
        for index, probabilities in enumerate(ensemble.probabilities)
    )
    payload = {
        "version": SEQUENCE_CANDIDATE_VERSION,
        "dataset": ensemble.dataset_identity,
        "ensemble": ensemble.ensemble_identity,
        "top_k": top_k,
        "rankings": [item.ranking_identity for item in rankings],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceCandidateRankingReport(
        SEQUENCE_CANDIDATE_VERSION,
        ensemble.dataset_identity,
        ensemble.ensemble_identity,
        rankings,
        top_k,
        "sequence-candidate-report-" + digest,
    )
def validate_sequence_candidate_ranking(
    ranking: SequenceCandidateRanking,
) -> SequenceCandidateValidationResult:
    if not isinstance(ranking, SequenceCandidateRanking):
        return SequenceCandidateValidationResult(INVALID, ("INVALID_RANKING_TYPE",))
    issues: list[str] = []
    if ranking.version != SEQUENCE_CANDIDATE_VERSION:
        issues.append("INVALID_VERSION")
    if not ranking.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not ranking.ensemble_identity:
        issues.append("MISSING_ENSEMBLE_IDENTITY")
    if ranking.observation_index < 0:
        issues.append("INVALID_OBSERVATION_INDEX")
    if not ranking.candidates:
        issues.append("NO_CANDIDATES")
    if len(ranking.candidates) > 10:
        issues.append("TOO_MANY_CANDIDATES")
    expected_ranks = list(range(1, len(ranking.candidates) + 1))
    actual_ranks = [item.rank for item in ranking.candidates]
    if actual_ranks != expected_ranks:
        issues.append("INVALID_RANKS")
    digits = [item.candidate for item in ranking.candidates]
    if len(set(digits)) != len(digits) or any(d < 0 or d > 9 for d in digits):
        issues.append("INVALID_CANDIDATES")
    for item in ranking.candidates:
        if not math.isfinite(item.probability) or not 0 <= item.probability <= 1:
            issues.append("INVALID_PROBABILITY")
        if not math.isfinite(item.score) or not 0 <= item.score <= 100:
            issues.append("INVALID_SCORE")
    if not math.isfinite(ranking.top_probability):
        issues.append("INVALID_TOP_PROBABILITY")
    if not math.isfinite(ranking.probability_margin):
        issues.append("INVALID_MARGIN")
    if not math.isfinite(ranking.entropy) or ranking.entropy < 0:
        issues.append("INVALID_ENTROPY")
    if not ranking.ranking_identity.startswith("sequence-candidate-ranking-"):
        issues.append("INVALID_RANKING_IDENTITY")
    return SequenceCandidateValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def validate_candidate_ranking_report(
    report: SequenceCandidateRankingReport,
) -> SequenceCandidateValidationResult:
    if not isinstance(report, SequenceCandidateRankingReport):
        return SequenceCandidateValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != SEQUENCE_CANDIDATE_VERSION:
        issues.append("INVALID_VERSION")
    if not report.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not report.ensemble_identity:
        issues.append("MISSING_ENSEMBLE_IDENTITY")
    if not report.rankings:
        issues.append("NO_RANKINGS")
    if report.top_k <= 0 or report.top_k > 10:
        issues.append("INVALID_TOP_K")
    for ranking in report.rankings:
        if ranking.dataset_identity != report.dataset_identity:
            issues.append("DATASET_IDENTITY_MISMATCH")
        if ranking.ensemble_identity != report.ensemble_identity:
            issues.append("ENSEMBLE_IDENTITY_MISMATCH")
        if not validate_sequence_candidate_ranking(ranking).is_valid:
            issues.append("INVALID_RANKING")
    if not report.report_identity.startswith("sequence-candidate-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return SequenceCandidateValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def candidate_values(ranking: SequenceCandidateRanking) -> tuple[int, ...]:
    return tuple(item.candidate for item in ranking.candidates)


def top_candidate(ranking: SequenceCandidateRanking) -> SequenceCandidateScore:
    if not ranking.candidates:
        raise ValueError("ranking contains no candidates.")
    return ranking.candidates[0]


__all__ = [
    "SEQUENCE_CANDIDATE_VERSION",
    "VALID",
    "INVALID",
    "SequenceCandidateScore",
    "SequenceCandidateRanking",
    "SequenceCandidateRankingReport",
    "SequenceCandidateValidationResult",
    "rank_candidate_probabilities",
    "rank_ensemble_candidates",
    "build_candidate_ranking_report",
    "validate_sequence_candidate_ranking",
    "validate_candidate_ranking_report",
    "candidate_values",
    "top_candidate",
]
