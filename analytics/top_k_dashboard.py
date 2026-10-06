from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.top_k_framework import (
    TopKEvaluationReport,
    top_k_summary,
    validate_top_k_evaluation_report,
)

TOP_K_DASHBOARD_VERSION = "82.0.0"
TOP_K_DASHBOARD_BOUNDARY = "TOP_K_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class TopKDashboardService:
    """Read-only dashboard projection of the authoritative Phase 44 Top-K engine."""

    report: TopKEvaluationReport | None = None
    max_detail_rows: int = 100

    def _state(self) -> dict[str, object]:
        if self.report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        return {
            "status": AVAILABLE if self.report.report_identity else INVALID,
            "report_identity": self.report.report_identity,
            "version": self.report.version,
        }

    def summary(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return {
                "status": VALID,
                "version": TOP_K_DASHBOARD_VERSION,
                "boundary": TOP_K_DASHBOARD_BOUNDARY,
                "read_only": True,
                "report_status": state["status"],
                "reason": state["reason"],
                "evaluated_observations": 0,
                "actual_available_observations": 0,
                "ks": (),
                "hit_rates": (),
                "mean_reciprocal_rank": 0.0,
            }
        base = top_k_summary(self.report)
        return {
            **base,
            "dashboard_version": TOP_K_DASHBOARD_VERSION,
            "dashboard_boundary": TOP_K_DASHBOARD_BOUNDARY,
            "read_only": True,
            "report_status": state["status"],
        }

    def metrics(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        validation = validate_top_k_evaluation_report(self.report)
        hit_rates = tuple(
            {"k": k, "hit_rate": rate, "hit_percent": rate * 100.0}
            for k, rate in self.report.hit_rates
        )
        return {
            "status": validation.status,
            "report_identity": self.report.report_identity,
            "source_type": self.report.source_type,
            "ks": self.report.ks,
            "evaluated_observations": self.report.evaluated_observations,
            "actual_available_observations": self.report.actual_available_observations,
            "hit_rates": hit_rates,
            "mean_reciprocal_rank": self.report.mean_reciprocal_rank,
            "mean_reciprocal_rank_percent": self.report.mean_reciprocal_rank * 100.0,
        }

    def rows(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        limit = min(max(int(self.max_detail_rows), 1), 1000)
        details = tuple(
            {
                "source_type": row.source_type,
                "group_id": row.group_id,
                "target_date": row.target_date.isoformat(),
                "actual_value": row.actual_value,
                "actual_rank": row.actual_rank,
                "reciprocal_rank": row.reciprocal_rank,
                "top_probability": row.top_probability,
                "cumulative_probability_at_max_k": row.cumulative_probability_at_max_k,
                "hit_at_k": tuple(
                    {"k": k, "hit": bool(hit)} for k, hit in row.hit_at_k
                ),
            }
            for row in self.report.rows[:limit]
        )
        return {
            "status": state["status"],
            "report_identity": self.report.report_identity,
            "row_count": len(self.report.rows),
            "returned_rows": len(details),
            "rows": details,
        }
    def hit_rate_series(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        return {
            "status": state["status"],
            "source_type": self.report.source_type,
            "points": tuple(
                {
                    "k": k,
                    "hit_rate": rate,
                    "hit_percent": rate * 100.0,
                }
                for k, rate in self.report.hit_rates
            ),
        }

    def rank_distribution(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        counts: dict[int, int] = {}
        misses = 0
        for row in self.report.rows:
            if row.actual_rank is None:
                misses += 1
            else:
                counts[row.actual_rank] = counts.get(row.actual_rank, 0) + 1
        return {
            "status": state["status"],
            "source_type": self.report.source_type,
            "rank_counts": tuple(
                {"rank": rank, "count": count}
                for rank, count in sorted(counts.items())
            ),
            "unranked_observations": misses,
        }

    def coverage(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        total = self.report.evaluated_observations
        actual = self.report.actual_available_observations
        coverage = actual / total if total else 0.0
        return {
            "status": state["status"],
            "evaluated_observations": total,
            "actual_available_observations": actual,
            "actual_coverage": coverage,
            "actual_coverage_percent": coverage * 100.0,
        }

    def dashboard(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return {
                "status": state["status"],
                "summary": self.summary(),
                "metrics": state,
                "hit_rate_series": state,
                "rank_distribution": state,
                "coverage": state,
                "rows": state,
            }
        return {
            "status": state["status"],
            "summary": self.summary(),
            "metrics": self.metrics(),
            "hit_rate_series": self.hit_rate_series(),
            "rank_distribution": self.rank_distribution(),
            "coverage": self.coverage(),
            "rows": self.rows(),
        }


def top_k_dashboard_summary(service: TopKDashboardService) -> dict[str, object]:
    return service.summary()


def top_k_dashboard_metrics(service: TopKDashboardService) -> dict[str, object]:
    return service.metrics()


def top_k_dashboard_rows(service: TopKDashboardService) -> dict[str, object]:
    return service.rows()


def top_k_dashboard_hit_rate(service: TopKDashboardService) -> dict[str, object]:
    return service.hit_rate_series()


def top_k_dashboard_rank_distribution(service: TopKDashboardService) -> dict[str, object]:
    return service.rank_distribution()


def top_k_dashboard_coverage(service: TopKDashboardService) -> dict[str, object]:
    return service.coverage()


def top_k_dashboard_contract() -> dict[str, object]:
    return {
        "version": TOP_K_DASHBOARD_VERSION,
        "boundary": TOP_K_DASHBOARD_BOUNDARY,
        "read_only": True,
        "routes": (
            "/v1/top-k/summary",
            "/v1/top-k/metrics",
            "/v1/top-k/rows",
            "/v1/top-k/hit-rate",
            "/v1/top-k/rank-distribution",
            "/v1/top-k/coverage",
        ),
    }


__all__ = [
    "TOP_K_DASHBOARD_VERSION",
    "TOP_K_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "TopKDashboardService",
    "top_k_dashboard_summary",
    "top_k_dashboard_metrics",
    "top_k_dashboard_rows",
    "top_k_dashboard_hit_rate",
    "top_k_dashboard_rank_distribution",
    "top_k_dashboard_coverage",
    "top_k_dashboard_contract",
]
