from __future__ import annotations

from datetime import date
import hashlib
import math

from sqlalchemy import select
import joblib
from pathlib import Path

from database.engine import SessionLocal
from database.models import HistoricalResult
from analytics.sequential_prediction import (
    _jodi_features,
    _load_models,
    _stage2_features,
    load_status,
)
from analytics.learning_to_rank_model import LearningToRankPrediction
from analytics.jodi_ranking import (
    build_authoritative_jodi_candidates,
    build_jodi_ranking_report,
    rank_jodis,
)
from analytics.panel_ranking import (
    PanelCandidateInput,
    build_panel_ranking_report,
    rank_panels,
)
from analytics.top_k_framework import build_top_k_evaluation_report
from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_over_time import build_performance_over_time_report
from analytics.family_master import (
    jodi_family_for,
    panel_family_for_panel,
    panels_for_digit,
)

LIVE_RANKING_VERSION = "101.1.0"
TOP_K = (1, 2, 3, 5, 7, 10)


def _prediction(group_id: str, target_date: date, model, features) -> LearningToRankPrediction:
    probabilities = [0.0] * 10
    for cls, probability in zip(model.classes_, model.predict_proba([features])[0]):
        probabilities[int(cls)] = float(probability)
    order = sorted(range(10), key=lambda i: (-probabilities[i], i))
    ranks = [0] * 10
    for rank, index in enumerate(order, start=1):
        ranks[index] = rank
    scores = tuple(math.log(max(value, 1e-15)) for value in probabilities)
    return LearningToRankPrediction(
        group_id=group_id,
        target_date=target_date.isoformat(),
        candidate_digits=tuple(range(10)),
        scores=scores,
        probabilities=tuple(probabilities),
        ranks=tuple(ranks),
        actual_digit=0,
        top_candidate=order[0],
        top_k_candidates=tuple(order[:10]),
    )


def _digit_candidates(model, features) -> list[dict]:
    probabilities = [0.0] * 10
    for cls, probability in zip(model.classes_, model.predict_proba([features])[0]):
        probabilities[int(cls)] = float(probability)
    order = sorted(range(10), key=lambda i: (-probabilities[i], i))
    return [
        {"digit": digit, "probability": probabilities[digit], "rank": rank}
        for rank, digit in enumerate(order, start=1)
    ]


def _artifact_id(model_identity: str, target: str) -> str:
    return "sequential-artifact-" + hashlib.sha256(
        f"{model_identity}:{target}".encode()
    ).hexdigest()


def build_validation_ranking_reports():
    """Build truthful Phase 42–46 reports from the held-out sequential split.

    This is evaluation only. It never changes serving state, rollout state,
    authorization state, or production activation.
    """
    status = load_status()
    if status.get("status") != "COMPLETED":
        return None

    models = _load_models()
    validation_start = date.fromisoformat(str(status["validation_start_date"]))

    db = SessionLocal()
    try:
        rows = list(
            db.scalars(
                select(HistoricalResult).order_by(
                    HistoricalResult.result_date,
                    HistoricalResult.market_id,
                    HistoricalResult.id,
                )
            ).all()
        )
    finally:
        db.close()

    grouped: dict[int, list[HistoricalResult]] = {}
    for row in rows:
        grouped.setdefault(int(row.market_id), []).append(row)

    panel_observations = []
    jodi_observations = []

    # Keep dashboard refresh bounded while preserving chronological evaluation.
    validation_candidates = []
    for market_id in sorted(grouped):
        for row in sorted(grouped[market_id], key=lambda item: (item.result_date, item.id)):
            if row.result_date >= validation_start:
                validation_candidates.append((market_id, row))
    validation_candidates = sorted(
        validation_candidates,
        key=lambda item: (item[1].result_date, item[1].id),
    )[-20:]
    allowed_ids = {(market_id, row.id) for market_id, row in validation_candidates}

    for market_id in sorted(grouped):
        market_rows = sorted(
            grouped[market_id],
            key=lambda row: (row.result_date, row.id),
        )
        for index, row in enumerate(market_rows):
            if row.result_date < validation_start or index < 1:
                continue
            if (market_id, row.id) not in allowed_ids:
                continue

            jodi_features = _jodi_features(market_rows, index)
            first = _prediction(
                f"validation:{market_id}:{row.id}:jodi-first",
                row.result_date,
                models["jodi_first"],
                jodi_features,
            )
            second = _prediction(
                f"validation:{market_id}:{row.id}:jodi-second",
                row.result_date,
                models["jodi_second"],
                jodi_features,
            )

            jodi_observations.append(
                rank_jodis(
                    first,
                    second,
                    build_authoritative_jodi_candidates(),
                    group_id=f"validation-jodi:{market_id}:{row.id}",
                    target_date=row.result_date,
                    actual_jodi=row.jodi_result,
                    top_k=20,
                )
            )

            predicted_jodi_first = str(first.top_candidate)
            close_features = _stage2_features(
                market_rows,
                index,
                predicted_jodi_first,
            )
            close_first = _prediction(
                f"validation:{market_id}:{row.id}:close-first",
                row.result_date,
                models["close_first"],
                close_features,
            )
            close_second = _prediction(
                f"validation:{market_id}:{row.id}:close-second",
                row.result_date,
                models["close_second"],
                close_features,
            )
            close_third = _prediction(
                f"validation:{market_id}:{row.id}:close-third",
                row.result_date,
                models["close_third"],
                close_features,
            )

            # Use both predicted Jodi digits to enforce the family-aware
            # panel candidate universe without using the actual Jodi.
            predicted_jodi = jodi_observations[-1].candidates[0].jodi
            panels = set(panels_for_digit(predicted_jodi[0]))
            panels.update(panels_for_digit(predicted_jodi[1]))

            panel_candidates = tuple(
                PanelCandidateInput(
                    panel=panel,
                    panel_family_id=panel_family_for_panel(panel),
                    jodi_family_id=jodi_family_for(predicted_jodi),
                )
                for panel in sorted(panels)
            )
            panel_observations.append(
                rank_panels(
                    close_first,
                    close_second,
                    close_third,
                    panel_candidates,
                    group_id=f"validation-panel:{market_id}:{row.id}",
                    target_date=row.result_date,
                    actual_panel=row.close_result,
                    top_k=20,
                )
            )

    if not jodi_observations or not panel_observations:
        return None

    model_identity = str(status.get("model_identity", "sequential-model"))
    panel_report = build_panel_ranking_report(
        panel_observations,
        (
            _artifact_id(model_identity, "close_first"),
            _artifact_id(model_identity, "close_second"),
            _artifact_id(model_identity, "close_third"),
        ),
        20,
    )
    jodi_report = build_jodi_ranking_report(
        jodi_observations,
        (
            _artifact_id(model_identity, "jodi_first"),
            _artifact_id(model_identity, "jodi_second"),
        ),
        20,
    )
    panel_top_k = build_top_k_evaluation_report(
        panel_report.observations,
        panel_report.report_identity,
        TOP_K,
    )
    panel_actual = build_actual_vs_ranked_report(panel_top_k)
    panel_performance = build_performance_over_time_report(
        panel_actual,
        period_days=7,
        hit_ks=TOP_K,
    )
    return {
        "panel": panel_report,
        "jodi": jodi_report,
        "top_k": panel_top_k,
        "actual_vs_ranked": panel_actual,
        "performance": panel_performance,
        "validation_start_date": validation_start,
        "model_identity": model_identity,
        "observation_count": len(panel_observations),
    }


__all__ = ["LIVE_RANKING_VERSION", "TOP_K", "build_validation_ranking_reports"]

CACHE_PATH = Path(__file__).resolve().parent.parent / "models" / "ranking" / "validation_ranking_reports.joblib"


def get_validation_ranking_reports():
    model_identity = str(load_status().get("model_identity", ""))
    if not model_identity:
        return None
    if CACHE_PATH.exists():
        try:
            cached = joblib.load(CACHE_PATH)
            if cached.get("model_identity") == model_identity:
                return cached
        except Exception:
            pass
    result = build_validation_ranking_reports()
    if result is not None:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(result, CACHE_PATH)
    return result


__all__.append("get_validation_ranking_reports")
