from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.top_k_framework import (
    TopKEvaluationReport,
    TopKEvaluationRow,
    validate_top_k_evaluation_report,
)

ACTUAL_VS_RANKED_VERSION = "45.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class ActualVsRankedObservation:
    source_type: str
    group_id: str
    target_date: date
    actual_value: str | None
    actual_rank: int | None
    reciprocal_rank: float
    hit_at_k: tuple[tuple[int, bool], ...]
    rank_bucket: str
    top_probability: float
    cumulative_probability_at_max_k: float


@dataclass(frozen=True)
class ActualVsRankedReport:
    version: str
    source_type: str
    source_report_identity: str
    observations: tuple[ActualVsRankedObservation, ...]
    rank_distribution: tuple[tuple[int, int], ...]
    rank_bucket_counts: tuple[tuple[str, int], ...]
    hit_rates: tuple[tuple[int, float], ...]
    actual_available_observations: int
    missed_observations: int
    mean_actual_rank: float | None
    median_actual_rank: float | None
    mean_reciprocal_rank: float
    top_probability_mean: float
    cumulative_probability_mean: float
    report_identity: str


@dataclass(frozen=True)
class ActualVsRankedValidationResult:
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


def _rank_bucket(rank: int | None) -> str:
    if rank is None:
        return "UNAVAILABLE"
    if rank == 1:
        return "TOP_1"
    if rank <= 3:
        return "TOP_3"
    if rank <= 5:
        return "TOP_5"
    if rank <= 10:
        return "TOP_10"
    return "OUTSIDE_TOP_10"


def _median(values: Sequence[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _row_to_observation(row: TopKEvaluationRow) -> ActualVsRankedObservation:
    return ActualVsRankedObservation(
        row.source_type,
        row.group_id,
        row.target_date,
        row.actual_value,
        row.actual_rank,
        row.reciprocal_rank,
        row.hit_at_k,
        _rank_bucket(row.actual_rank),
        row.top_probability,
        row.cumulative_probability_at_max_k,
    )


def build_actual_vs_ranked_report(
    source: TopKEvaluationReport,
) -> ActualVsRankedReport:
    if not isinstance(source, TopKEvaluationReport):
        raise TypeError("source must be a TopKEvaluationReport.")
    source_validation = validate_top_k_evaluation_report(source)
    if not source_validation.is_valid:
        raise ValueError(
            "invalid Phase 44 source report: "
            + ", ".join(source_validation.issues)
        )
    observations = tuple(_row_to_observation(row) for row in source.rows)
    if not observations:
        raise ValueError("source report contains no observations.")
    ranks = sorted(
        observation.actual_rank
        for observation in observations
        if observation.actual_rank is not None
    )
    distribution: dict[int, int] = {}
    for rank in ranks:
        distribution[rank] = distribution.get(rank, 0) + 1
    buckets: dict[str, int] = {}
    for observation in observations:
        buckets[observation.rank_bucket] = buckets.get(
            observation.rank_bucket, 0
        ) + 1
    actual_count = len(ranks)
    missed = sum(
        1 for observation in observations if observation.actual_rank is None
    )
    hit_rates = tuple(source.hit_rates)
    mean_rank = sum(ranks) / actual_count if actual_count else None
    mrr = (
        sum(observation.reciprocal_rank for observation in observations)
        / actual_count
        if actual_count
        else 0.0
    )
    top_probability_mean = (
        sum(observation.top_probability for observation in observations)
        / len(observations)
    )
    cumulative_probability_mean = (
        sum(
            observation.cumulative_probability_at_max_k
            for observation in observations
        )
        / len(observations)
    )
    payload = {
        "version": ACTUAL_VS_RANKED_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "observations": [
            (
                item.group_id,
                item.target_date,
                item.actual_value,
                item.actual_rank,
                item.hit_at_k,
            )
            for item in observations
        ],
        "hit_rates": hit_rates,
    }
    return ActualVsRankedReport(
        ACTUAL_VS_RANKED_VERSION,
        source.source_type,
        source.report_identity,
        observations,
        tuple(sorted(distribution.items())),
        tuple(sorted(buckets.items())),
        hit_rates,
        actual_count,
        missed,
        mean_rank,
        _median(ranks),
        mrr,
        top_probability_mean,
        cumulative_probability_mean,
        _identity("actual-vs-ranked-report-", payload),
    )


def actual_vs_ranked_summary(
    report: ActualVsRankedReport,
) -> dict[str, object]:
    validation = validate_actual_vs_ranked_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "observations": len(report.observations),
        "actual_available_observations": report.actual_available_observations,
        "missed_observations": report.missed_observations,
        "mean_actual_rank": report.mean_actual_rank,
        "median_actual_rank": report.median_actual_rank,
        "mean_reciprocal_rank": report.mean_reciprocal_rank,
        "hit_rates": report.hit_rates,
        "rank_distribution": report.rank_distribution,
        "rank_bucket_counts": report.rank_bucket_counts,
        "report_identity": report.report_identity,
    }


def validate_actual_vs_ranked_report(
    report: ActualVsRankedReport,
) -> ActualVsRankedValidationResult:
    if not isinstance(report, ActualVsRankedReport):
        return ActualVsRankedValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != ACTUAL_VS_RANKED_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if not report.observations:
        issues.append("NO_OBSERVATIONS")
    group_ids = [item.group_id for item in report.observations]
    if len(group_ids) != len(set(group_ids)):
        issues.append("DUPLICATE_GROUP_IDS")
    for item in report.observations:
        if not item.group_id.strip():
            issues.append("MISSING_GROUP_ID")
        if not isinstance(item.target_date, date):
            issues.append("INVALID_TARGET_DATE")
        if item.actual_rank is not None and item.actual_rank < 1:
            issues.append("INVALID_ACTUAL_RANK")
        if item.actual_rank is None and item.rank_bucket != "UNAVAILABLE":
            issues.append("INVALID_UNAVAILABLE_BUCKET")
        if item.actual_rank is not None and item.rank_bucket != _rank_bucket(
            item.actual_rank
        ):
            issues.append("INVALID_RANK_BUCKET")
        if not math.isfinite(item.reciprocal_rank) or not 0 <= item.reciprocal_rank <= 1:
            issues.append("INVALID_RECIPROCAL_RANK")
        if not math.isfinite(item.top_probability) or not 0 <= item.top_probability <= 1:
            issues.append("INVALID_TOP_PROBABILITY")
        if (
            not math.isfinite(item.cumulative_probability_at_max_k)
            or not 0 <= item.cumulative_probability_at_max_k <= 1 + 1e-9
        ):
            issues.append("INVALID_CUMULATIVE_PROBABILITY")
    actual_count = sum(
        item.actual_rank is not None for item in report.observations
    )
    missed = sum(
        item.actual_rank is None for item in report.observations
    )
    if actual_count != report.actual_available_observations:
        issues.append("ACTUAL_COUNT_MISMATCH")
    if missed != report.missed_observations:
        issues.append("MISSED_COUNT_MISMATCH")
    if report.mean_actual_rank is not None and (
        not math.isfinite(report.mean_actual_rank)
        or report.mean_actual_rank < 1
    ):
        issues.append("INVALID_MEAN_RANK")
    if report.median_actual_rank is not None and (
        not math.isfinite(report.median_actual_rank)
        or report.median_actual_rank < 1
    ):
        issues.append("INVALID_MEDIAN_RANK")
    if not math.isfinite(report.mean_reciprocal_rank) or not 0 <= report.mean_reciprocal_rank <= 1:
        issues.append("INVALID_MRR")
    if not math.isfinite(report.top_probability_mean) or not 0 <= report.top_probability_mean <= 1:
        issues.append("INVALID_TOP_PROBABILITY_MEAN")
    if not math.isfinite(report.cumulative_probability_mean) or not 0 <= report.cumulative_probability_mean <= 1 + 1e-9:
        issues.append("INVALID_CUMULATIVE_PROBABILITY_MEAN")
    if not report.report_identity.startswith("actual-vs-ranked-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ActualVsRankedValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "ACTUAL_VS_RANKED_VERSION",
    "VALID",
    "INVALID",
    "ActualVsRankedObservation",
    "ActualVsRankedReport",
    "ActualVsRankedValidationResult",
    "build_actual_vs_ranked_report",
    "actual_vs_ranked_summary",
    "validate_actual_vs_ranked_report",
]
