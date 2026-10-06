from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.panel_ranking import PanelRankingReport, panel_ranking_summary
from analytics.jodi_ranking import JodiRankingReport, jodi_ranking_summary
from analytics.top_k_framework import TopKEvaluationReport, top_k_summary
from analytics.actual_vs_ranked import ActualVsRankedReport, actual_vs_ranked_summary
from analytics.performance_over_time import PerformanceOverTimeReport, performance_over_time_summary

RANKING_DASHBOARD_VERSION = "81.0.0"
RANKING_DASHBOARD_BOUNDARY = "RANKING_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class RankingDashboardService:
    """Read-only dashboard projection of the existing ranking stack (Phases 40–46)."""

    panel_report: PanelRankingReport | None = None
    jodi_report: JodiRankingReport | None = None
    top_k_report: TopKEvaluationReport | None = None
    actual_vs_ranked_report: ActualVsRankedReport | None = None
    performance_report: PerformanceOverTimeReport | None = None

    @staticmethod
    def _state(report: Any | None, identity_field: str = "report_identity") -> dict[str, object]:
        if report is None:
            return {"status": UNAVAILABLE, "reason": "REPORT_NOT_ATTACHED"}
        identity = getattr(report, identity_field, "")
        return {
            "status": AVAILABLE if identity else INVALID,
            "report_identity": identity,
            "version": getattr(report, "version", None),
        }

    def panel(self) -> dict[str, object]:
        state = self._state(self.panel_report)
        if self.panel_report is None:
            return state
        summary = panel_ranking_summary(self.panel_report)
        observations = tuple(
            {
                "group_id": item.group_id,
                "target_date": item.target_date.isoformat(),
                "target_position": item.target_position,
                "actual_panel": item.actual_panel,
                "top_probability": item.top_probability,
                "probability_margin": item.probability_margin,
                "candidate_count": len(item.candidates),
                "top_candidates": tuple(
                    {
                        "panel": c.panel,
                        "probability": c.probability,
                        "score": c.score,
                        "rank": c.rank,
                        "panel_family_id": c.panel_family_id,
                        "jodi_family_id": c.jodi_family_id,
                    }
                    for c in item.candidates[:10]
                ),
            }
            for item in self.panel_report.observations
        )
        return {**summary, "status": state["status"], "observations_detail": observations}

    def jodi(self) -> dict[str, object]:
        state = self._state(self.jodi_report)
        if self.jodi_report is None:
            return state
        summary = jodi_ranking_summary(self.jodi_report)
        observations = tuple(
            {
                "group_id": item.group_id,
                "target_date": item.target_date.isoformat(),
                "target_position": item.target_position,
                "actual_jodi": item.actual_jodi,
                "top_probability": item.top_probability,
                "probability_margin": item.probability_margin,
                "candidate_count": len(item.candidates),
                "top_candidates": tuple(
                    {
                        "jodi": c.jodi,
                        "probability": c.probability,
                        "score": c.score,
                        "rank": c.rank,
                        "jodi_family_id": c.jodi_family_id,
                        "panel_family_id": c.panel_family_id,
                    }
                    for c in item.candidates[:10]
                ),
            }
            for item in self.jodi_report.observations
        )
        return {**summary, "status": state["status"], "observations_detail": observations}

    def top_k(self) -> dict[str, object]:
        state = self._state(self.top_k_report)
        if self.top_k_report is None:
            return state
        return {**top_k_summary(self.top_k_report), "status": state["status"]}

    def actual_vs_ranked(self) -> dict[str, object]:
        state = self._state(self.actual_vs_ranked_report)
        if self.actual_vs_ranked_report is None:
            return state
        summary = actual_vs_ranked_summary(self.actual_vs_ranked_report)
        return {**summary, "status": state["status"]}

    def performance(self) -> dict[str, object]:
        state = self._state(self.performance_report)
        if self.performance_report is None:
            return state
        summary = performance_over_time_summary(self.performance_report)
        return {**summary, "status": state["status"]}

    def summary(self) -> dict[str, object]:
        sections = {
            "panel": self.panel()["status"],
            "jodi": self.jodi()["status"],
            "top_k": self.top_k()["status"],
            "actual_vs_ranked": self.actual_vs_ranked()["status"],
            "performance_over_time": self.performance()["status"],
        }
        available = sum(value == AVAILABLE for value in sections.values())
        return {
            "status": VALID,
            "version": RANKING_DASHBOARD_VERSION,
            "boundary": RANKING_DASHBOARD_BOUNDARY,
            "read_only": True,
            "available_sections": available,
            "section_count": len(sections),
            "sections": sections,
        }


def ranking_dashboard_summary(service: RankingDashboardService) -> dict[str, object]:
    return service.summary()


def ranking_dashboard_panel(service: RankingDashboardService) -> dict[str, object]:
    return service.panel()


def ranking_dashboard_jodi(service: RankingDashboardService) -> dict[str, object]:
    return service.jodi()


def ranking_dashboard_top_k(service: RankingDashboardService) -> dict[str, object]:
    return service.top_k()


def ranking_dashboard_actual_vs_ranked(service: RankingDashboardService) -> dict[str, object]:
    return service.actual_vs_ranked()


def ranking_dashboard_performance(service: RankingDashboardService) -> dict[str, object]:
    return service.performance()


def ranking_dashboard_contract() -> dict[str, object]:
    return {
        "version": RANKING_DASHBOARD_VERSION,
        "boundary": RANKING_DASHBOARD_BOUNDARY,
        "read_only": True,
        "routes": (
            "/v1/ranking/summary",
            "/v1/ranking/panel",
            "/v1/ranking/jodi",
            "/v1/ranking/top-k",
            "/v1/ranking/actual-vs-ranked",
            "/v1/ranking/performance",
        ),
    }


__all__ = [
    "RANKING_DASHBOARD_VERSION",
    "RANKING_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "RankingDashboardService",
    "ranking_dashboard_summary",
    "ranking_dashboard_panel",
    "ranking_dashboard_jodi",
    "ranking_dashboard_top_k",
    "ranking_dashboard_actual_vs_ranked",
    "ranking_dashboard_performance",
    "ranking_dashboard_contract",
]
