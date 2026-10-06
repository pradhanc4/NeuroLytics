from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from analytics.family_master import (
    jodi_family_for,
    panel_family_for_panel,
)
from analytics.panel_family_prediction import rank_family_constrained_panels
from analytics.production_model_qualification import (
    QUALIFIED,
    VALID,
)
from analytics.sequential_prediction import (
    predict_jodi_candidates,
    predict_stage_2,
)

INTEGRATION_VERSION = "C.11.0"
OPERATIONAL_TOP_K = (1, 2, 3, 5, 10)


@dataclass(frozen=True)
class HierarchicalCandidate:
    jodi: str
    jodi_probability: float
    first_panel: str
    first_panel_probability: float
    second_panel: str
    second_panel_probability: float
    joint_score: float
    rank: int
    jodi_family_id: str
    first_panel_family_id: str
    second_panel_family_id: str


@dataclass(frozen=True)
class ProductionHierarchicalPrediction:
    version: str
    status: str
    qualification: str
    target_date: date
    open_result: str
    market_id: int | None
    market_name: str | None
    jodi_candidates: tuple[dict[str, Any], ...]
    selected_jodi: str | None
    selected: HierarchicalCandidate | None
    candidates: tuple[HierarchicalCandidate, ...]
    operational_top_k: tuple[int, ...]
    temporal_safe: bool
    family_constraints_enforced: bool
    issues: tuple[str, ...]
    integration_identity: str


def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "production-hierarchical-" + hashlib.sha256(raw).hexdigest()


def _probability(item: Any) -> float:
    return float(item["probability"] if isinstance(item, dict) else item.probability)


def _candidate_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    return {
        "digit": int(item.digit),
        "probability": float(item.probability),
        "rank": int(getattr(item, "rank", 0)),
    }


def _complete_digit_distribution(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    probabilities = {int(item["digit"]): float(item["probability"]) for item in items}
    return [
        {"digit": digit, "probability": probabilities.get(digit, 0.0), "rank": rank}
        for rank, digit in enumerate(
            sorted(range(10), key=lambda d: (-probabilities.get(d, 0.0), d)),
            start=1,
        )
    ]


def _build_panel_inputs(stage2: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    close = stage2["close_digit_candidates"]
    return (
        _complete_digit_distribution([_candidate_dict(x) for x in close["first"]]),
        _complete_digit_distribution([_candidate_dict(x) for x in close["second"]]),
        _complete_digit_distribution([_candidate_dict(x) for x in close["third"]]),
    )


def _validate_candidate(item: HierarchicalCandidate) -> list[str]:
    issues: list[str] = []
    if item.jodi_family_id != jodi_family_for(item.jodi):
        issues.append("JODI_FAMILY_MISMATCH")
    if item.first_panel_family_id != item.jodi[0]:
        issues.append("FIRST_PANEL_FAMILY_MISMATCH")
    if item.second_panel_family_id != item.jodi[1]:
        issues.append("SECOND_PANEL_FAMILY_MISMATCH")
    if panel_family_for_panel(item.first_panel) != item.jodi[0]:
        issues.append("FIRST_PANEL_CROSS_FAMILY")
    if panel_family_for_panel(item.second_panel) != item.jodi[1]:
        issues.append("SECOND_PANEL_CROSS_FAMILY")
    return issues


def _rank_for_jodi(
    jodi_candidate: Any,
    stage2: dict[str, Any],
    *,
    target_date: date,
    group_id: str,
    top_k: int,
) -> list[HierarchicalCandidate]:
    jodi = str(jodi_candidate.jodi)
    first, second, third = _build_panel_inputs(stage2)
    panel_result = rank_family_constrained_panels(
        jodi=jodi,
        first_candidates=first,
        second_candidates=second,
        third_candidates=third,
        target_date=target_date,
        group_id=group_id + ":" + jodi,
        jodi_family_id=jodi_family_for(jodi),
        top_k=top_k,
    )
    first_items = panel_result["digits"]["first"]["ranking"].candidates[:top_k]
    second_items = panel_result["digits"]["second"]["ranking"].candidates[:top_k]
    result: list[HierarchicalCandidate] = []
    for first_item in first_items:
        for second_item in second_items:
            fp = float(first_item.probability)
            sp = float(second_item.probability)
            jp = float(jodi_candidate.probability)
            result.append(
                HierarchicalCandidate(
                    jodi=jodi,
                    jodi_probability=jp,
                    first_panel=str(first_item.panel),
                    first_panel_probability=fp,
                    second_panel=str(second_item.panel),
                    second_panel_probability=sp,
                    joint_score=jp * fp * sp,
                    rank=0,
                    jodi_family_id=jodi_family_for(jodi),
                    first_panel_family_id=jodi[0],
                    second_panel_family_id=jodi[1],
                )
            )
    return result


def _ranked(items: list[HierarchicalCandidate], top_k: int) -> tuple[HierarchicalCandidate, ...]:
    ordered = sorted(
        items,
        key=lambda x: (-x.joint_score, x.jodi, x.first_panel, x.second_panel),
    )
    return tuple(
        HierarchicalCandidate(
            **{
                **asdict(item),
                "rank": index,
            }
        )
        for index, item in enumerate(ordered[:top_k], start=1)
    )


def predict_production_hierarchical(
    *,
    open_result: str,
    target_date: date,
    market_id: int | None = None,
    market_name: str | None = None,
    top_k: int = 10,
    qualification_path: str | Path = "reports/production_model_qualification.json",
) -> ProductionHierarchicalPrediction:
    if len(open_result) != 3 or not open_result.isdigit():
        raise ValueError("open_result must contain exactly 3 digits.")
    if top_k not in OPERATIONAL_TOP_K:
        raise ValueError(f"top_k must be one of {OPERATIONAL_TOP_K}")

    qualification_payload = json.loads(Path(qualification_path).read_text(encoding="utf-8"))
    if qualification_payload.get("status") != VALID:
        raise ValueError("Production model qualification report is not VALID.")
    if qualification_payload.get("overall_qualification") != QUALIFIED:
        raise ValueError("Production model qualification is not QUALIFIED.")
    if not qualification_payload.get("temporal_safe"):
        raise ValueError("Production model qualification is not temporally safe.")

    jodi_result = predict_jodi_candidates(
        open_result,
        target_date=target_date,
        top_k=top_k,
        market_id=market_id,
        market_name=market_name,
    )
    jodi_candidates = tuple(jodi_result["ranking"].candidates)
    if not jodi_candidates:
        raise ValueError("No valid Jodi candidates were produced.")

    all_candidates: list[HierarchicalCandidate] = []
    issues: list[str] = []
    for candidate in jodi_candidates:
        # Panel-family ranking requires the complete 0-9 probability
        # distribution. The production output may still be Top-1/2/3/5/10.
        stage2 = predict_stage_2(
            open_result,
            candidate.jodi[0],
            top_k=10,
            market_id=market_id,
            market_name=market_name,
        )
        all_candidates.extend(
            _rank_for_jodi(
                candidate,
                stage2,
                target_date=target_date,
                group_id=jodi_result["ranking"].group_id,
                top_k=top_k,
            )
        )

    for item in all_candidates:
        issues.extend(_validate_candidate(item))

    selected_jodi = str(jodi_candidates[0].jodi)
    # Production hierarchy is strict: Jodi Top-1 is selected first.
    # Panel ranking is then performed only inside that selected Jodi's
    # two authoritative panel families. Other Jodi candidates remain
    # available in jodi_candidates for Top-K evaluation and analysis.
    selected_jodi_pool = [item for item in all_candidates if item.jodi == selected_jodi]
    ranked = _ranked(selected_jodi_pool, top_k)
    if not ranked:
        raise ValueError("Hierarchical production ranking produced no candidates for selected Jodi.")
    status = VALID if not issues else "INVALID"

    payload = {
        "version": INTEGRATION_VERSION,
        "date": target_date,
        "open": open_result,
        "selected_jodi": selected_jodi,
        "selected": asdict(ranked[0]),
        "qualification": qualification_payload.get("report_identity"),
        "temporal_safe": True,
        "family_constraints_enforced": True,
    }
    return ProductionHierarchicalPrediction(
        version=INTEGRATION_VERSION,
        status=status,
        qualification=QUALIFIED,
        target_date=target_date,
        open_result=open_result,
        market_id=market_id,
        market_name=market_name,
        jodi_candidates=tuple(
            {
                "jodi": str(x.jodi),
                "probability": float(x.probability),
                "rank": int(x.rank),
                "jodi_family_id": str(x.jodi_family_id),
                "first_panel_family_id": str(x.first_panel_family_id),
                "second_panel_family_id": str(x.second_panel_family_id),
            }
            for x in jodi_candidates
        ),
        selected_jodi=selected_jodi,
        selected=ranked[0],
        candidates=ranked,
        operational_top_k=OPERATIONAL_TOP_K,
        temporal_safe=True,
        family_constraints_enforced=not issues,
        issues=tuple(sorted(set(issues))),
        integration_identity=_identity(payload),
    )


__all__ = [
    "INTEGRATION_VERSION",
    "OPERATIONAL_TOP_K",
    "HierarchicalCandidate",
    "ProductionHierarchicalPrediction",
    "predict_production_hierarchical",
]
