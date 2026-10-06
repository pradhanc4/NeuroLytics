from __future__ import annotations

from dataclasses import dataclass

from analytics.performance_over_time import (
    PerformanceOverTimeReport,
    performance_over_time_summary,
    validate_performance_over_time_report,
)

PERFORMANCE_DASHBOARD_VERSION = "83.0.0"
PERFORMANCE_DASHBOARD_BOUNDARY = "PERFORMANCE_OVER_TIME_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class PerformanceOverTimeDashboardService:
    """Read-only dashboard projection of the authoritative Phase 46 report."""

    report: PerformanceOverTimeReport | None = None
    max_periods: int = 500

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
                "version": PERFORMANCE_DASHBOARD_VERSION,
                "boundary": PERFORMANCE_DASHBOARD_BOUNDARY,
                "read_only": True,
                "report_status": state["status"],
                "reason": state["reason"],
                "period_days": 0,
                "periods": 0,
                "observations": 0,
                "actual_available_observations": 0,
                "missed_observations": 0,
                "trends": (),
            }
        base = performance_over_time_summary(self.report)
        return {
            **base,
            "dashboard_version": PERFORMANCE_DASHBOARD_VERSION,
            "dashboard_boundary": PERFORMANCE_DASHBOARD_BOUNDARY,
            "read_only": True,
            "report_status": state["status"],
        }

    def periods(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        validation = validate_performance_over_time_report(self.report)
        limit = min(max(int(self.max_periods), 1), 2000)
        values = tuple(
            {
                "period_start": item.period_start.isoformat(),
                "period_end": item.period_end.isoformat(),
                "observation_count": item.observation_count,
                "actual_available_observations": item.actual_available_observations,
                "missed_observations": item.missed_observations,
                "mean_actual_rank": item.mean_actual_rank,
                "hit_rates": tuple(
                    {"k": k, "hit_rate": rate, "hit_percent": rate * 100.0}
                    for k, rate in item.hit_rates
                ),
                "mean_reciprocal_rank": item.mean_reciprocal_rank,
                "mean_top_probability": item.mean_top_probability,
                "mean_cumulative_probability": item.mean_cumulative_probability,
                "miss_rate": item.miss_rate,
                "miss_percent": item.miss_rate * 100.0,
            }
            for item in self.report.periods[:limit]
        )
        return {
            "status": validation.status,
            "report_identity": self.report.report_identity,
            "period_days": self.report.period_days,
            "period_count": len(self.report.periods),
            "returned_periods": len(values),
            "periods": values,
        }

    def trends(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        return {
            "status": state["status"],
            "report_identity": self.report.report_identity,
            "trends": tuple(
                {
                    "metric": item.metric,
                    "slope_per_day": item.slope_per_day,
                    "direction": item.direction,
                    "first_value": item.first_value,
                    "last_value": item.last_value,
                    "change": item.change,
                }
                for item in self.report.trends
            ),
        }

    def hit_rates(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        points = []
        for period in self.report.periods:
            for k, rate in period.hit_rates:
                points.append(
                    {
                        "period_start": period.period_start.isoformat(),
                        "period_end": period.period_end.isoformat(),
                        "k": k,
                        "hit_rate": rate,
                        "hit_percent": rate * 100.0,
                    }
                )
        return {
            "status": state["status"],
            "report_identity": self.report.report_identity,
            "points": tuple(points),
        }

    def metrics(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return state
        return {
            "status": state["status"],
            "report_identity": self.report.report_identity,
            "period_days": self.report.period_days,
            "observation_count": self.report.observation_count,
            "actual_available_observations": self.report.actual_available_observations,
            "missed_observations": self.report.missed_observations,
            "actual_coverage": (
                self.report.actual_available_observations / self.report.observation_count
                if self.report.observation_count else 0.0
            ),
            "miss_rate": (
                self.report.missed_observations / self.report.observation_count
                if self.report.observation_count else 0.0
            ),
        }

    def dashboard(self) -> dict[str, object]:
        state = self._state()
        if self.report is None:
            return {
                "status": state["status"],
                "summary": self.summary(),
                "metrics": state,
                "periods": state,
                "trends": state,
                "hit_rates": state,
            }
        return {
            "status": state["status"],
            "summary": self.summary(),
            "metrics": self.metrics(),
            "periods": self.periods(),
            "trends": self.trends(),
            "hit_rates": self.hit_rates(),
        }


def performance_dashboard_summary(service: PerformanceOverTimeDashboardService):
    return service.summary()


def performance_dashboard_periods(service: PerformanceOverTimeDashboardService):
    return service.periods()


def performance_dashboard_trends(service: PerformanceOverTimeDashboardService):
    return service.trends()


def performance_dashboard_hit_rates(service: PerformanceOverTimeDashboardService):
    return service.hit_rates()


def performance_dashboard_metrics(service: PerformanceOverTimeDashboardService):
    return service.metrics()


def performance_dashboard_contract() -> dict[str, object]:
    return {
        "version": PERFORMANCE_DASHBOARD_VERSION,
        "boundary": PERFORMANCE_DASHBOARD_BOUNDARY,
        "read_only": True,
        "routes": (
            "/v1/performance/summary",
            "/v1/performance/periods",
            "/v1/performance/trends",
            "/v1/performance/hit-rates",
            "/v1/performance/metrics",
        ),
    }


__all__ = [
    "PERFORMANCE_DASHBOARD_VERSION",
    "PERFORMANCE_DASHBOARD_BOUNDARY",
    "VALID",
    "INVALID",
    "AVAILABLE",
    "UNAVAILABLE",
    "PerformanceOverTimeDashboardService",
    "performance_dashboard_summary",
    "performance_dashboard_periods",
    "performance_dashboard_trends",
    "performance_dashboard_hit_rates",
    "performance_dashboard_metrics",
    "performance_dashboard_contract",
]
