from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market

HISTORICAL_DASHBOARD_VERSION = "78.0.0"
HISTORICAL_DASHBOARD_BOUNDARY = "HISTORICAL_DATA_DASHBOARD_BOUNDARY"
VALID = "VALID"
INVALID = "INVALID"


def _row_payload(row: HistoricalResult, market_name: str) -> dict[str, Any]:
    return {
        "id": row.id,
        "market": market_name,
        "date": row.result_date.isoformat(),
        "open": row.open_result,
        "jodi": row.jodi_result,
        "close": row.close_result,
        "columns": [getattr(row, f"col{i}") for i in range(1, 9)],
    }


class HistoricalDashboardService:
    """Read-only historical data query boundary for the Phase 78 UI."""

    def __init__(self, db: Session) -> None:
        if not isinstance(db, Session):
            raise TypeError("db must be a SQLAlchemy Session")
        self.db = db

    def markets(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(Market).order_by(Market.name)).all()
        return [{"id": m.id, "name": m.name, "active": m.is_active} for m in rows]

    def summary(self, market_id: int | None = None) -> dict[str, Any]:
        query = select(HistoricalResult, Market.name).join(Market)
        if market_id is not None:
            query = query.where(HistoricalResult.market_id == market_id)
        rows = self.db.execute(query.order_by(HistoricalResult.result_date)).all()
        dates = [r.HistoricalResult.result_date for r in rows]
        return {
            "version": HISTORICAL_DASHBOARD_VERSION,
            "boundary": HISTORICAL_DASHBOARD_BOUNDARY,
            "status": "VALID",
            "market_id": market_id,
            "record_count": len(rows),
            "market_count": len({r.HistoricalResult.market_id for r in rows}),
            "start_date": min(dates).isoformat() if dates else None,
            "end_date": max(dates).isoformat() if dates else None,
            "available_markets": self.markets(),
        }

    def records(
        self,
        *,
        market_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        query = select(HistoricalResult, Market.name).join(Market)
        if market_id is not None:
            query = query.where(HistoricalResult.market_id == market_id)
        if start_date is not None:
            query = query.where(HistoricalResult.result_date >= start_date)
        if end_date is not None:
            query = query.where(HistoricalResult.result_date <= end_date)
        query = query.order_by(HistoricalResult.result_date.desc()).limit(limit)
        rows = self.db.execute(query).all()
        return {
            "version": HISTORICAL_DASHBOARD_VERSION,
            "boundary": HISTORICAL_DASHBOARD_BOUNDARY,
            "status": VALID,
            "count": len(rows),
            "records": [_row_payload(row, name) for row, name in rows],
        }

    def frequency(self, market_id: int | None = None) -> dict[str, Any]:
        query = select(HistoricalResult)
        if market_id is not None:
            query = query.where(HistoricalResult.market_id == market_id)
        rows = self.db.scalars(query).all()
        counts = {str(i): 0 for i in range(10)}
        for row in rows:
            for position in range(1, 9):
                value = getattr(row, f"col{position}")
                if value in range(10):
                    counts[str(value)] += 1
        total = sum(counts.values())
        return {
            "version": HISTORICAL_DASHBOARD_VERSION,
            "boundary": HISTORICAL_DASHBOARD_BOUNDARY,
            "status": VALID,
            "record_count": len(rows),
            "total_digit_observations": total,
            "digits": [
                {"digit": int(d), "count": c, "percentage": (c / total * 100) if total else 0.0}
                for d, c in counts.items()
            ],
        }

    def daily_series(self, market_id: int | None = None) -> dict[str, Any]:
        query = select(HistoricalResult, Market.name).join(Market)
        if market_id is not None:
            query = query.where(HistoricalResult.market_id == market_id)
        rows = self.db.execute(query.order_by(HistoricalResult.result_date)).all()
        return {
            "version": HISTORICAL_DASHBOARD_VERSION,
            "boundary": HISTORICAL_DASHBOARD_BOUNDARY,
            "status": VALID,
            "points": [
                {
                    "date": row.result_date.isoformat(),
                    "market": name,
                    "row_mean": sum(getattr(row, f"col{i}") for i in range(1, 9)) / 8,
                }
                for row, name in rows
            ],
        }


def historical_dashboard_summary(service: HistoricalDashboardService) -> dict[str, Any]:
    return {
        "version": HISTORICAL_DASHBOARD_VERSION,
        "boundary": HISTORICAL_DASHBOARD_BOUNDARY,
        "routes": (
            "/v1/historical/summary",
            "/v1/historical/records",
            "/v1/historical/frequency",
            "/v1/historical/daily",
        ),
    }


__all__ = [
    "HISTORICAL_DASHBOARD_VERSION",
    "HISTORICAL_DASHBOARD_BOUNDARY",
    "HistoricalDashboardService",
    "historical_dashboard_summary",
]

