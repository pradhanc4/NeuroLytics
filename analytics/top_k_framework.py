from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.jodi_ranking import JodiRankingObservation
from analytics.panel_ranking import PanelRankingObservation

TOP_K_FRAMEWORK_VERSION = "44.0.0"
VALID = "VALID"
INVALID = "INVALID"

RankingObservation = PanelRankingObservation | JodiRankingObservation


@dataclass(frozen=True)
class TopKCandidate:
    value: str
    probability: float
    score: float
    rank: int
    panel_family_id: str | None = None
    jodi_family_id: str | None = None


@dataclass(frozen=True)
class TopKSelection:
    source_type: str
    group_id: str
    target_date: date
    target_position: str
    requested_k: int
    available_count: int
    candidates: tuple[TopKCandidate, ...]
    cumulative_probability: float
    selection_identity: str


@dataclass(frozen=True)
class TopKEvaluationRow:
    source_type: str
    group_id: str
    target_date: date
    actual_value: str | None
    actual_rank: int | None
    hit_at_k: tuple[tuple[int, bool], ...]
    reciprocal_rank: float
    top_probability: float
    cumulative_probability_at_max_k: float


@dataclass(frozen=True)
class TopKEvaluationReport:
    version: str
    source_type: str
    source_report_identity: str
    ks: tuple[int, ...]
    rows: tuple[TopKEvaluationRow, ...]
    hit_rates: tuple[tuple[int, float], ...]
    mean_reciprocal_rank: float
    evaluated_observations: int
    actual_available_observations: int
    report_identity: str


@dataclass(frozen=True)
class TopKValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _validate_k(k: int) -> int:
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an integer.")
    if k < 1:
        raise ValueError("k must be positive.")
    return k


def normalize_top_k_values(ks: Sequence[int]) -> tuple[int, ...]:
    values = tuple(_validate_k(k) for k in ks)
    if not values:
        raise ValueError("at least one Top-K value is required.")
    if len(set(values)) != len(values):
        raise ValueError("Top-K values must be unique.")
    return tuple(sorted(values))


def _source_type(ranking: RankingObservation) -> str:
    if isinstance(ranking, PanelRankingObservation):
        return "panel"
    if isinstance(ranking, JodiRankingObservation):
        return "jodi"
    raise TypeError("ranking must be a Panel or Jodi ranking observation.")


def _candidate_fields(ranking: RankingObservation) -> tuple[tuple[str, float, float, int, str | None, str | None], ...]:
    source = _source_type(ranking)
    result = []
    for item in ranking.candidates:
        if source == "panel":
            result.append(
                (item.panel, item.probability, item.score, item.rank,
                 item.panel_family_id, item.jodi_family_id)
            )
        else:
            result.append(
                (item.jodi, item.probability, item.score, item.rank,
                 item.panel_family_id, item.jodi_family_id)
            )
    return tuple(result)


def top_k_selection(
    ranking: RankingObservation,
    k: int,
) -> TopKSelection:
    k = _validate_k(k)
    source = _source_type(ranking)
    fields = _candidate_fields(ranking)
    if not fields:
        raise ValueError("ranking contains no candidates.")
    visible = fields[: min(k, len(fields))]
    candidates = tuple(
        TopKCandidate(value, probability, score, rank, panel_family_id, jodi_family_id)
        for value, probability, score, rank, panel_family_id, jodi_family_id in visible
    )
    cumulative = sum(item.probability for item in candidates)
    identity = _identity(
        "top-k-selection-",
        {
            "version": TOP_K_FRAMEWORK_VERSION,
            "source_type": source,
            "source_ranking_identity": ranking.ranking_identity,
            "k": k,
            "candidates": [
                (item.value, item.probability, item.rank) for item in candidates
            ],
        },
    )
    return TopKSelection(
        source,
        ranking.group_id,
        ranking.target_date,
        ranking.target_position,
        k,
        len(fields),
        candidates,
        cumulative,
        identity,
    )


def top_k_values(ranking: RankingObservation, k: int) -> tuple[str, ...]:
    return tuple(item.value for item in top_k_selection(ranking, k).candidates)


def cumulative_probability(ranking: RankingObservation, k: int) -> float:
    return top_k_selection(ranking, k).cumulative_probability


def actual_rank(ranking: RankingObservation) -> int | None:
    actual = ranking.actual_panel if isinstance(ranking, PanelRankingObservation) else ranking.actual_jodi
    if actual is None:
        return None
    for item in ranking.candidates:
        value = item.panel if isinstance(ranking, PanelRankingObservation) else item.jodi
        if value == actual:
            return item.rank
    return None


def hit_at_k(ranking: RankingObservation, k: int) -> bool:
    k = _validate_k(k)
    rank = actual_rank(ranking)
    return rank is not None and rank <= k


def reciprocal_rank(ranking: RankingObservation) -> float:
    rank = actual_rank(ranking)
    return 1.0 / rank if rank is not None else 0.0


def _validate_row(row: TopKEvaluationRow) -> TopKValidationResult:
    issues: list[str] = []
    if row.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not row.group_id.strip():
        issues.append("MISSING_GROUP_ID")
    if not isinstance(row.target_date, date):
        issues.append("INVALID_TARGET_DATE")
    if row.actual_rank is not None and row.actual_rank < 1:
        issues.append("INVALID_ACTUAL_RANK")
    if not math.isfinite(row.reciprocal_rank) or not 0 <= row.reciprocal_rank <= 1:
        issues.append("INVALID_RECIPROCAL_RANK")
    if not math.isfinite(row.top_probability) or not 0 <= row.top_probability <= 1:
        issues.append("INVALID_TOP_PROBABILITY")
    if not math.isfinite(row.cumulative_probability_at_max_k) or not 0 <= row.cumulative_probability_at_max_k <= 1 + 1e-9:
        issues.append("INVALID_CUMULATIVE_PROBABILITY")
    ks = [k for k, _ in row.hit_at_k]
    if ks != sorted(ks) or len(set(ks)) != len(ks) or any(k < 1 for k in ks):
        issues.append("INVALID_K_VALUES")
    if row.actual_rank is not None:
        for k, hit in row.hit_at_k:
            if bool(hit) != (row.actual_rank <= k):
                issues.append("INCONSISTENT_HIT_AT_K")
                break
    return TopKValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def build_top_k_evaluation_row(
    ranking: RankingObservation,
    ks: Sequence[int],
) -> TopKEvaluationRow:
    normalized = normalize_top_k_values(ks)
    source = _source_type(ranking)
    rank = actual_rank(ranking)
    top_probability = ranking.candidates[0].probability if ranking.candidates else 0.0
    max_k = normalized[-1]
    max_selection = top_k_selection(ranking, max_k)
    row = TopKEvaluationRow(
        source,
        ranking.group_id,
        ranking.target_date,
        ranking.actual_panel if source == "panel" else ranking.actual_jodi,
        rank,
        tuple((k, rank is not None and rank <= k) for k in normalized),
        1.0 / rank if rank is not None else 0.0,
        top_probability,
        max_selection.cumulative_probability,
    )
    validation = _validate_row(row)
    if not validation.is_valid:
        raise ValueError("invalid Top-K evaluation row: " + ", ".join(validation.issues))
    return row
def build_top_k_evaluation_report(
    observations: Sequence[RankingObservation],
    source_report_identity: str,
    ks: Sequence[int],
) -> TopKEvaluationReport:
    normalized = normalize_top_k_values(ks)
    materialized = tuple(observations)
    if not materialized:
        raise ValueError("at least one ranking observation is required.")
    if not source_report_identity.strip():
        raise ValueError("source_report_identity must be non-empty.")
    source_types = {_source_type(item) for item in materialized}
    if len(source_types) != 1:
        raise ValueError("all observations must have the same source type.")
    if len({item.group_id for item in materialized}) != len(materialized):
        raise ValueError("observation group_id values must be unique.")
    rows = tuple(build_top_k_evaluation_row(item, normalized) for item in materialized)
    hit_rates = []
    actual_count = sum(row.actual_rank is not None for row in rows)
    for k in normalized:
        hits = sum(dict(row.hit_at_k)[k] for row in rows if row.actual_rank is not None)
        hit_rates.append((k, hits / actual_count if actual_count else 0.0))
    mrr = (
        sum(row.reciprocal_rank for row in rows if row.actual_rank is not None)
        / actual_count
        if actual_count
        else 0.0
    )
    source = next(iter(source_types))
    payload = {
        "version": TOP_K_FRAMEWORK_VERSION,
        "source_type": source,
        "source_report_identity": source_report_identity,
        "ks": normalized,
        "rows": [
            (
                row.group_id,
                row.actual_value,
                row.actual_rank,
                row.hit_at_k,
                row.reciprocal_rank,
            )
            for row in rows
        ],
    }
    return TopKEvaluationReport(
        TOP_K_FRAMEWORK_VERSION,
        source,
        source_report_identity,
        normalized,
        rows,
        tuple(hit_rates),
        mrr,
        len(rows),
        actual_count,
        _identity("top-k-evaluation-report-", payload),
    )


def validate_top_k_selection(selection: TopKSelection) -> TopKValidationResult:
    if not isinstance(selection, TopKSelection):
        return TopKValidationResult(INVALID, ("INVALID_SELECTION_TYPE",))
    issues: list[str] = []
    if selection.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not selection.group_id.strip():
        issues.append("MISSING_GROUP_ID")
    if selection.requested_k < 1:
        issues.append("INVALID_REQUESTED_K")
    if selection.available_count < 1:
        issues.append("INVALID_AVAILABLE_COUNT")
    if not selection.candidates:
        issues.append("NO_SELECTED_CANDIDATES")
    ranks = [item.rank for item in selection.candidates]
    if ranks != list(range(1, len(ranks) + 1)):
        issues.append("INVALID_RANKS")
    values = [item.value for item in selection.candidates]
    if len(values) != len(set(values)):
        issues.append("DUPLICATE_VALUES")
    probabilities = [item.probability for item in selection.candidates]
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
        issues.append("INVALID_PROBABILITIES")
    if not math.isfinite(selection.cumulative_probability) or not 0 <= selection.cumulative_probability <= 1 + 1e-9:
        issues.append("INVALID_CUMULATIVE_PROBABILITY")
    if not selection.selection_identity.startswith("top-k-selection-"):
        issues.append("INVALID_SELECTION_IDENTITY")
    return TopKValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def validate_top_k_evaluation_report(
    report: TopKEvaluationReport,
) -> TopKValidationResult:
    if not isinstance(report, TopKEvaluationReport):
        return TopKValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != TOP_K_FRAMEWORK_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if not report.ks or tuple(sorted(report.ks)) != report.ks:
        issues.append("INVALID_KS")
    if len(set(report.ks)) != len(report.ks):
        issues.append("DUPLICATE_KS")
    if len(report.rows) != report.evaluated_observations:
        issues.append("ROW_COUNT_MISMATCH")
    if report.actual_available_observations > report.evaluated_observations:
        issues.append("INVALID_ACTUAL_COUNT")
    for row in report.rows:
        validation = _validate_row(row)
        if not validation.is_valid:
            issues.append("INVALID_ROW")
    reported_rates = dict(report.hit_rates)
    if set(reported_rates) != set(report.ks):
        issues.append("HIT_RATE_K_MISMATCH")
    for k, value in report.hit_rates:
        if not math.isfinite(value) or not 0 <= value <= 1:
            issues.append("INVALID_HIT_RATE")
    if not math.isfinite(report.mean_reciprocal_rank) or not 0 <= report.mean_reciprocal_rank <= 1:
        issues.append("INVALID_MRR")
    if not report.report_identity.startswith("top-k-evaluation-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return TopKValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def top_k_summary(report: TopKEvaluationReport) -> dict[str, object]:
    validation = validate_top_k_evaluation_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "ks": report.ks,
        "evaluated_observations": report.evaluated_observations,
        "actual_available_observations": report.actual_available_observations,
        "hit_rates": report.hit_rates,
        "mean_reciprocal_rank": report.mean_reciprocal_rank,
        "report_identity": report.report_identity,
    }


__all__ = [
    "TOP_K_FRAMEWORK_VERSION",
    "VALID",
    "INVALID",
    "TopKCandidate",
    "TopKSelection",
    "TopKEvaluationRow",
    "TopKEvaluationReport",
    "TopKValidationResult",
    "normalize_top_k_values",
    "top_k_selection",
    "top_k_values",
    "cumulative_probability",
    "actual_rank",
    "hit_at_k",
    "reciprocal_rank",
    "build_top_k_evaluation_row",
    "build_top_k_evaluation_report",
    "validate_top_k_selection",
    "validate_top_k_evaluation_report",
    "top_k_summary",
]
