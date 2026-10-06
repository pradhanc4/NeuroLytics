"""NeuroLytics standalone application orchestration boundary.

This module is the single application-level workflow boundary between the
SQLite data store, validation/feature derivation, analytics, ML, prediction,
feedback, and operational readiness contracts.

It deliberately reuses existing model/analytics modules; it does not create
a second prediction engine or a second database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from database.engine import SessionLocal
from database.models import HistoricalResult, Market, PredictionFeedback
from database.models import SequentialPredictionStage
from database.parser import parse_results

SYSTEM_VERSION = "101.0.0"
SYSTEM_BOUNDARY = "STANDALONE_SYSTEM_ORCHESTRATION_BOUNDARY"
SYSTEM_NAME = "NeuroLytics Standalone System"


PIPELINE_FRAMES: tuple[dict[str, Any], ...] = (
    {"id": "01", "name": "Database", "layer": "DATA", "modules": ("database.models", "database.services")},
    {"id": "02", "name": "Validation", "layer": "DATA", "modules": ("database.parser", "database.historical_quality_checker")},
    {"id": "03", "name": "Feature Engineering", "layer": "ML", "modules": ("features", "analytics.sequence_framework")},
    {"id": "04", "name": "Statistical Analytics", "layer": "ANALYTICS", "modules": ("analytics.statistical_descriptive", "analytics.frequency_analysis")},
    {"id": "05", "name": "Classical ML", "layer": "ML", "modules": ("analytics.logistic_regression", "analytics.decision_tree", "analytics.random_forest", "analytics.extra_trees", "analytics.gradient_boosting")},
    {"id": "06", "name": "Boosting ML", "layer": "ML", "modules": ("analytics.xgboost", "analytics.lightgbm", "analytics.catboost")},
    {"id": "07", "name": "Sequence Models", "layer": "ML", "modules": ("analytics.markov_models", "analytics.hidden_markov_models", "analytics.lstm", "analytics.gru", "analytics.transformer")},
    {"id": "08", "name": "Ensemble / Calibration", "layer": "ML", "modules": ("analytics.sequence_ensemble", "analytics.advanced_ensemble", "analytics.model_comparison", "analytics.calibration_drift")},
    {"id": "09", "name": "Ranking", "layer": "ANALYTICS", "modules": ("analytics.panel_ranking", "analytics.jodi_ranking", "analytics.top_k_framework")},
    {"id": "10", "name": "Sequential Prediction", "layer": "PREDICTION", "modules": ("analytics.sequential_prediction", "analytics.end_to_end_prediction")},
    {"id": "11", "name": "Feedback / Retraining", "layer": "LEARNING", "modules": ("analytics.prediction_feedback_loop", "analytics.manual_retraining", "analytics.automated_retraining")},
    {"id": "12", "name": "Monitoring / Audits", "layer": "OPERATIONS", "modules": ("analytics.model_health", "analytics.data_integrity_audit", "analytics.temporal_safety_audit", "analytics.performance_monitoring")},
)


@dataclass(frozen=True)
class WorkflowResult:
    status: str
    payload: dict[str, Any]


class NeuroLyticsSystem:
    """Single application workflow coordinator for local NeuroLytics."""

    version = SYSTEM_VERSION
    boundary = SYSTEM_BOUNDARY

    def _validate_stage1(self, result_date: date, market_name: str, open_result: str, jodi_first: str) -> None:
        if not isinstance(result_date, date):
            raise ValueError("date is required.")
        if not market_name.strip():
            raise ValueError("market_name is required.")
        if len(open_result) != 3 or not open_result.isdigit():
            raise ValueError("Open must contain exactly 3 digits.")
        if len(jodi_first) != 1 or not jodi_first.isdigit():
            raise ValueError("Jodi first digit must contain exactly 1 digit.")

    def save_stage1(self, result_date: date, market_name: str, open_result: str, jodi_first: str) -> WorkflowResult:
        """Persist Stage 1 atomically and return its canonical identity."""
        self._validate_stage1(result_date, market_name, open_result, jodi_first)
        db = SessionLocal()
        try:
            market = db.scalar(select(Market).where(Market.name == market_name.strip()))
            if market is None:
                market = Market(name=market_name.strip())
                db.add(market)
                db.flush()

            existing_result = db.scalar(select(HistoricalResult).where(
                HistoricalResult.market_id == market.id,
                HistoricalResult.result_date == result_date,
            ))
            if existing_result is not None:
                raise ValueError("A completed historical result already exists for this market and date.")

            stage = db.scalar(select(SequentialPredictionStage).where(
                SequentialPredictionStage.market_id == market.id,
                SequentialPredictionStage.result_date == result_date,
            ))
            if stage is None:
                stage = SequentialPredictionStage(
                    market_id=market.id,
                    result_date=result_date,
                    open_result=open_result,
                    jodi_first_digit=jodi_first,
                    status="STAGE_1",
                )
                db.add(stage)
            else:
                stage.open_result = open_result
                stage.jodi_first_digit = jodi_first
                stage.status = "STAGE_1"
            db.commit()
            db.refresh(stage)
            return WorkflowResult("VALID", {
                "stage_id": stage.id,
                "date": result_date.isoformat(),
                "market_id": market.id,
                "market_name": market.name,
                "open": open_result,
                "jodi_first": jodi_first,
                "status": stage.status,
            })
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def complete_stage2(self, stage_id: int, jodi_second: str, close_result: str) -> WorkflowResult:
        """Complete one Stage 1 row and historical result in ONE transaction."""
        if len(jodi_second) != 1 or not jodi_second.isdigit():
            raise ValueError("Jodi second digit must contain exactly 1 digit.")
        if len(close_result) != 3 or not close_result.isdigit():
            raise ValueError("Close must contain exactly 3 digits.")

        db = SessionLocal()
        try:
            stage = db.scalar(select(SequentialPredictionStage).where(
                SequentialPredictionStage.id == int(stage_id)
            ))
            if stage is None:
                raise ValueError("The selected Stage 1 record was not found.")
            if stage.status == "COMPLETED":
                raise ValueError("The selected Stage 1 record is already completed.")

            market = db.get(Market, stage.market_id)
            if market is None:
                raise ValueError("The market for the selected Stage 1 record was not found.")

            existing = db.scalar(select(HistoricalResult).where(
                HistoricalResult.market_id == market.id,
                HistoricalResult.result_date == stage.result_date,
            ))
            if existing is not None:
                stage.status = "COMPLETED"
                db.commit()
                raise ValueError("The historical result already exists; the Stage 1 row was reconciled.")

            parsed = parse_results(
                open_result=stage.open_result,
                jodi_result=stage.jodi_first_digit + jodi_second,
                close_result=close_result,
            )
            result = HistoricalResult(
                market_id=market.id,
                result_date=stage.result_date,
                **parsed,
            )
            db.add(result)
            stage.status = "COMPLETED"
            db.flush()
            db.commit()
            db.refresh(result)

            return WorkflowResult("VALID", {
                "record_id": result.id,
                "stage_id": stage.id,
                "date": result.result_date.isoformat(),
                "market_id": market.id,
                "market_name": market.name,
                "open": result.open_result,
                "jodi": result.jodi_result,
                "close": result.close_result,
                "columns": [getattr(result, f"col{i}") for i in range(1, 9)],
                "stage_status": stage.status,
            })
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def database_snapshot(self) -> dict[str, Any]:
        db = SessionLocal()
        try:
            markets = db.scalar(select(func.count(Market.id))) or 0
            historical = db.scalar(select(func.count(HistoricalResult.id))) or 0
            pending = db.scalar(select(func.count(SequentialPredictionStage.id)).where(
                SequentialPredictionStage.status == "STAGE_1"
            )) or 0
            feedback = db.scalar(select(func.count(PredictionFeedback.id))) or 0
            return {
                "markets": int(markets),
                "historical_results": int(historical),
                "pending_stage1": int(pending),
                "prediction_feedback": int(feedback),
                "database_state": "READY" if historical else "WAITING_FOR_HISTORICAL_DATA",
            }
        finally:
            db.close()

    def pipeline_status(self) -> list[dict[str, Any]]:
        result = []
        for frame in PIPELINE_FRAMES:
            available = all(find_spec(module) is not None for module in frame["modules"])
            result.append({
                "id": frame["id"],
                "name": frame["name"],
                "layer": frame["layer"],
                "status": "AVAILABLE" if available else "INCOMPLETE",
                "modules": list(frame["modules"]),
            })
        return result

    def status(self) -> dict[str, Any]:
        database = self.database_snapshot()
        pipeline = self.pipeline_status()
        return {
            "system": SYSTEM_NAME,
            "version": SYSTEM_VERSION,
            "boundary": SYSTEM_BOUNDARY,
            "architecture": "LOCAL_SINGLE_APPLICATION",
            "database": database,
            "pipeline": {
                "frames": len(pipeline),
                "available": sum(item["status"] == "AVAILABLE" for item in pipeline),
                "incomplete": sum(item["status"] == "INCOMPLETE" for item in pipeline),
            },
            "operational_rule": (
                "All Stage 1/Stage 2 writes use the workflow transaction boundary; "
                "Stage 2 creates the historical result and completes Stage 1 atomically."
            ),
        }
