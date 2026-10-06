from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence


C19_VERSION = "C.19.0"


@dataclass(frozen=True)
class PromotionGateResult:
    status: str
    promotion_allowed: bool
    gates: dict[str, bool]
    identity: str


def run_gate(
    c17_report: dict,
    c18_report: dict,
    regression_passed: bool,
    production_path_exists: bool,
) -> PromotionGateResult:
    gates = {
        "c17_valid": c17_report.get("status") == "VALID",
        "c17_temporal_safe": c17_report.get("temporal_safe") is True,
        "c18_valid": c18_report.get("status") == "VALID",
        "c18_temporal_order_valid": c18_report.get("temporal_order_valid") is True,
        "c18_artifact_integrity": c18_report.get("artifact_integrity_valid") is True,
        "c18_stage1_reproducible": c18_report.get("stage1_reproducible") is True,
        "c18_stage2_reproducible": c18_report.get("stage2_reproducible") is True,
        "regression_tests_passed": regression_passed,
        "existing_production_path_present": production_path_exists,
        # Relationship-aware artifacts remain non-promoted by design.
        "relationship_aware_auto_promotion_disabled": True,
    }
    # This gate certifies engineering integrity only. It never promotes
    # relationship-aware outcome-prediction artifacts automatically.
    promotion_allowed = False
    payload = {
        "version": C19_VERSION,
        "status": "VALID" if all(gates.values()) else "INVALID",
        "promotion_allowed": promotion_allowed,
        "gates": gates,
        "policy": "relationship-aware artifacts are not automatically promoted",
    }
    identity = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return PromotionGateResult(payload["status"], promotion_allowed, gates, identity)


def write_report(result: PromotionGateResult, path: str | Path) -> None:
    payload = {
        "version": C19_VERSION,
        "status": result.status,
        "promotion_allowed": result.promotion_allowed,
        "gates": result.gates,
        "identity": result.identity,
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["C19_VERSION", "PromotionGateResult", "run_gate", "write_report"]
