from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market

ANALYTICS_DASHBOARD_VERSION = "79.0.0"
ANALYTICS_DASHBOARD_BOUNDARY = "ANALYTICS_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class AnalyticsDashboardService:
    db: Session

    def _rows(self, market_id: int | None = None) -> list[tuple[HistoricalResult, str]]:
        query = select(HistoricalResult, Market.name).join(Market)
        if market_id is not None:
            query = query.where(HistoricalResult.market_id == market_id)
        return list(self.db.execute(query.order_by(HistoricalResult.result_date)).all())

    def markets(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(Market).order_by(Market.name)).all()
        return [{"id": m.id, "name": m.name, "active": m.is_active} for m in rows]

    def summary(self, market_id: int | None = None) -> dict[str, Any]:
        rows = self._rows(market_id)
        dates = [row.result_date for row, _ in rows]
        unique_dates = sorted(set(dates))
        calendar_days = ((max(unique_dates) - min(unique_dates)).days + 1) if unique_dates else 0
        missing_days = max(calendar_days - len(unique_dates), 0)
        return {
            "version": ANALYTICS_DASHBOARD_VERSION,
            "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
            "status": VALID,
            "market_id": market_id,
            "record_count": len(rows),
            "market_count": len({row.market_id for row, _ in rows}),
            "start_date": min(dates).isoformat() if dates else None,
            "end_date": max(dates).isoformat() if dates else None,
            "calendar_days": calendar_days,
            "unique_dates": len(unique_dates),
            "missing_calendar_days": missing_days,
            "coverage_percent": (len(unique_dates) / calendar_days * 100.0) if calendar_days else 0.0,
            "available_markets": self.markets(),
        }

    def distribution(self, market_id: int | None = None) -> dict[str, Any]:
        rows = self._rows(market_id)
        counts = {str(i): 0 for i in range(10)}
        observations = 0
        for row, _ in rows:
            for index in range(1, 9):
                value = getattr(row, f"col{index}")
                if isinstance(value, int) and 0 <= value <= 9:
                    counts[str(value)] += 1
                    observations += 1
        digits = [
            {
                "digit": int(d),
                "count": count,
                "percentage": (count / observations * 100.0) if observations else 0.0,
            }
            for d, count in counts.items()
        ]
        entropy = 0.0
        if observations:
            for item in digits:
                if item["count"]:
                    p = item["count"] / observations
                    entropy -= p * math.log2(p)
        return {
            "version": ANALYTICS_DASHBOARD_VERSION,
            "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
            "status": VALID,
            "record_count": len(rows),
            "total_digit_observations": observations,
            "digit_entropy": entropy,
            "digits": digits,
        }

    def column_statistics(self, market_id: int | None = None) -> dict[str, Any]:
        rows = self._rows(market_id)
        columns = []
        for index in range(1, 9):
            values = [
                getattr(row, f"col{index}")
                for row, _ in rows
                if isinstance(getattr(row, f"col{index}"), (int, float))
            ]
            columns.append({
                "column": f"col{index}",
                "count": len(values),
                "mean": mean(values) if values else 0.0,
                "std": pstdev(values) if len(values) > 1 else 0.0,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            })
        return {
            "version": ANALYTICS_DASHBOARD_VERSION,
            "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
            "status": VALID,
            "columns": columns,
        }

    def trends(self, market_id: int | None = None) -> dict[str, Any]:
        rows = self._rows(market_id)
        points = []
        for row, market in rows:
            values = [getattr(row, f"col{i}") for i in range(1, 9)]
            numeric = [v for v in values if isinstance(v, (int, float))]
            points.append({
                "date": row.result_date.isoformat(),
                "market": market,
                "row_mean": mean(numeric) if numeric else 0.0,
                "row_std": pstdev(numeric) if len(numeric) > 1 else 0.0,
            })
        ordered = sorted(points, key=lambda item: item["date"])
        y = [item["row_mean"] for item in ordered]
        slope = 0.0
        if len(y) > 1:
            x_mean = (len(y) - 1) / 2
            y_mean = mean(y)
            denominator = sum((i - x_mean) ** 2 for i in range(len(y)))
            slope = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(y)) / denominator if denominator else 0.0
        direction = "FLAT" if abs(slope) < 1e-9 else ("UP" if slope > 0 else "DOWN")
        return {
            "version": ANALYTICS_DASHBOARD_VERSION,
            "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
            "status": VALID,
            "point_count": len(ordered),
            "slope": slope,
            "direction": direction,
            "min_row_mean": min(y) if y else None,
            "max_row_mean": max(y) if y else None,
            "latest_row_mean": y[-1] if y else None,
            "points": ordered,
        }

    def insights(self, market_id: int | None = None) -> dict[str, Any]:
        summary = self.summary(market_id)
        distribution = self.distribution(market_id)
        trends = self.trends(market_id)
        stats = self.column_statistics(market_id)
        insights: list[dict[str, str]] = []
        if not summary["record_count"]:
            insights.append({"type": "DATA_STATE", "message": "No historical records are currently available."})
        else:
            top = max(distribution["digits"], key=lambda item: item["count"])
            low = min(distribution["digits"], key=lambda item: item["count"])
            insights.append({"type": "VOLUME", "message": f"{summary['record_count']} historical records are available."})
            insights.append({"type": "COVERAGE", "message": f"Calendar coverage is {summary['coverage_percent']:.2f}% with {summary['missing_calendar_days']} missing day(s)."})
            insights.append({"type": "DIGIT", "message": f"Digit {top['digit']} has the highest observed frequency; digit {low['digit']} has the lowest."})
            insights.append({"type": "TREND", "message": f"Row-mean trend direction is {trends['direction']}."})
            spread = max((item["std"] for item in stats["columns"]), default=0.0)
            insights.append({"type": "VARIABILITY", "message": f"Maximum column standard deviation is {spread:.4f}."})
        return {
            "version": ANALYTICS_DASHBOARD_VERSION,
            "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
            "status": VALID,
            "insights": insights,
        }


def analytics_dashboard_summary() -> dict[str, Any]:
    return {
        "version": ANALYTICS_DASHBOARD_VERSION,
        "boundary": ANALYTICS_DASHBOARD_BOUNDARY,
        "routes": (
            "/v1/analytics/summary",
            "/v1/analytics/distribution",
            "/v1/analytics/columns",
            "/v1/analytics/trends",
            "/v1/analytics/insights",
        ),
        "read_only": True,
    }


__all__ = [
    "ANALYTICS_DASHBOARD_VERSION",
    "ANALYTICS_DASHBOARD_BOUNDARY",
    "AnalyticsDashboardService",
    "analytics_dashboard_summary",
]

