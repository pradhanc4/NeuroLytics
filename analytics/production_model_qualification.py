from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from analytics.baseline_model_comparison import MODEL_NAMES, TARGET_NAMES
from analytics.historical_feature_dataset import HistoricalFeatureDataset
from analytics.model_stability import ModelStabilityReport, validate_model_stability_report
from analytics.temporal_backtesting import TemporalDatasetSplit

QUALIFICATION_VERSION = "C.10.0"
VALID = "VALID"
INVALID = "INVALID"
QUALIFIED = "QUALIFIED"
HOLD = "HOLD"

# Target-specific champions selected from the C.7 five-fold mean Top-1 benchmark.
# Ties are resolved by mean Top-5, then model name.
EXPECTED_TARGET_CHAMPIONS = {
    "jodi_first": "decision_tree",
    "jodi_second": "majority",
    "close_first": "majority",
    "close_second": "majority",
    "close_third": "random_forest",
}


@dataclass(frozen=True)
class TargetQualification:
    target: str
    champion_model: str
    challenger_models: tuple[str, ...]
    mean_top1: float
    mean_top5: float
    mean_log_loss: float
    fold_wins_top1: int
    qualification: str
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class ProductionModelQualificationReport:
    version: str
    dataset_identity: str
    split_identity: str
    status: str
    overall_qualification: str
    target_qualifications: tuple[TargetQualification, ...]
    jodi_first_stability_status: str
    jodi_first_open_dependency: bool
    production_hierarchy: tuple[str, ...]
    safeguards: tuple[str, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    report_identity: str


def _identity(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_c7(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _summaries(c7: dict, target: str) -> list[dict]:
    return [x for x in c7["summaries"] if x["target"] == target]


def build_production_model_qualification(
    dataset: HistoricalFeatureDataset,
    split: TemporalDatasetSplit,
    stability: ModelStabilityReport,
    *,
    comparison_path: str | Path = "reports/baseline_model_comparison.json",
) -> ProductionModelQualificationReport:
    issues: list[str] = []
    if not dataset.temporal_safe:
        issues.append("DATASET_TEMPORAL_SAFETY_FALSE")
    if not split.temporal_safe:
        issues.append("SPLIT_TEMPORAL_SAFETY_FALSE")
    if dataset.dataset_identity != split.dataset_identity:
        issues.append("DATASET_IDENTITY_MISMATCH")
    if stability.dataset_identity != dataset.dataset_identity or stability.split_identity != split.split_identity:
        issues.append("STABILITY_IDENTITY_MISMATCH")
    stability_status, stability_issues = validate_model_stability_report(stability)
    if stability_status != VALID or stability_issues:
        issues.append("INVALID_C9_STABILITY_REPORT")

    c7 = _load_c7(comparison_path)
    if c7.get("status") != VALID:
        issues.append("INVALID_C7_REPORT")
    if tuple(c7.get("models", ())) != MODEL_NAMES:
        issues.append("C7_MODEL_SET_MISMATCH")
    if tuple(c7.get("targets", ())) != TARGET_NAMES:
        issues.append("C7_TARGET_SET_MISMATCH")
    if c7.get("dataset_identity") != dataset.dataset_identity:
        issues.append("C7_DATASET_IDENTITY_MISMATCH")
    if c7.get("split_identity") != split.split_identity:
        issues.append("C7_SPLIT_IDENTITY_MISMATCH")

    qualifications: list[TargetQualification] = []
    for target in TARGET_NAMES:
        rows = _summaries(c7, target)
        if not rows:
            issues.append(f"NO_C7_SUMMARY:{target}")
            continue
        ordered = sorted(rows, key=lambda x: (-float(x["mean_test_top1"]), -float(x["mean_test_top5"]), float(x["mean_test_log_loss"]), x["model"]))
        winner = ordered[0]
        champion = EXPECTED_TARGET_CHAMPIONS[target]
        if winner["model"] != champion:
            issues.append(f"CHAMPION_SELECTION_MISMATCH:{target}")
        rationale = [
            "selected_by_five_fold_mean_test_top1",
            "tie_breaker_mean_test_top5_then_log_loss_then_model_name",
        ]
        if target == "jodi_first":
            rationale.append("C9_confirms_strong_dependence_on_current_open_features")
        qualifications.append(TargetQualification(
            target,
            champion,
            tuple(x["model"] for x in ordered[1:]),
            float(winner["mean_test_top1"]),
            float(winner["mean_test_top5"]),
            float(winner["mean_test_log_loss"]),
            int(winner["top1_fold_wins"]),
            QUALIFIED if target != "jodi_first" or stability.temporal_safe else HOLD,
            tuple(rationale),
        ))

    jodi_stability = "VALID" if stability.temporal_safe and stability.status == VALID else "INVALID"
    open_dependency = any(
        item.mode == "remove_current_open" and item.delta_top1 <= -0.10
        for item in stability.robustness
    )
    hierarchy = (
        "JODI_FIRST",
        "JODI_SECOND",
        "JODI_FAMILY",
        "PANEL_FAMILY",
        "FAMILY_CONSTRAINED_PANEL",
        "JOINT_JODI_PANEL_SCORE",
        "STAGE_1",
        "STAGE_2",
        "EVALUATION",
        "RETRAINING_POLICY",
    )
    safeguards = (
        "STRICT_TEMPORAL_TRAINING",
        "NO_CURRENT_JODI_AS_JODI_FEATURE",
        "AUTHORITATIVE_JODI_FAMILY_CONSTRAINT",
        "AUTHORITATIVE_PANEL_FAMILY_CONSTRAINT",
        "OPERATIONAL_TOP_K_1_2_3_5_10",
        "EXACT_MATCH_EVALUATION",
        "INCREMENTAL_DATABASE_PROCESSING",
        "NO_GUARANTEED_OUTCOME_CLAIM",
        "C9_OPEN_DEPENDENCY_MONITORING",
    )
    overall = QUALIFIED if not issues else HOLD
    payload = {
        "version": QUALIFICATION_VERSION,
        "dataset": dataset.dataset_identity,
        "split": split.split_identity,
        "targets": [asdict(x) for x in qualifications],
        "stability": stability.report_identity,
        "open_dependency": open_dependency,
        "hierarchy": hierarchy,
        "safeguards": safeguards,
        "issues": issues,
    }
    return ProductionModelQualificationReport(
        QUALIFICATION_VERSION,
        dataset.dataset_identity,
        split.split_identity,
        VALID if not issues else INVALID,
        overall,
        tuple(qualifications),
        jodi_stability,
        open_dependency,
        hierarchy,
        safeguards,
        not issues,
        tuple(sorted(set(issues))),
        "production-model-qualification-" + _identity(payload),
    )


def validate_production_model_qualification(report: ProductionModelQualificationReport) -> tuple[str, tuple[str, ...]]:
    issues = list(report.issues)
    if report.version != QUALIFICATION_VERSION:
        issues.append("INVALID_VERSION")
    if report.status != VALID:
        issues.append("REPORT_STATUS_INVALID")
    if report.overall_qualification != QUALIFIED:
        issues.append("OVERALL_NOT_QUALIFIED")
    if not report.temporal_safe:
        issues.append("TEMPORAL_SAFETY_FALSE")
    if len(report.target_qualifications) != len(TARGET_NAMES):
        issues.append("TARGET_QUALIFICATION_COUNT")
    for item in report.target_qualifications:
        if item.target not in TARGET_NAMES:
            issues.append("UNKNOWN_TARGET")
        if item.champion_model not in MODEL_NAMES:
            issues.append("UNKNOWN_CHAMPION_MODEL")
        if item.qualification != QUALIFIED:
            issues.append(f"TARGET_NOT_QUALIFIED:{item.target}")
        if not 0 <= item.mean_top1 <= item.mean_top5 <= 1:
            issues.append(f"INVALID_TOPK:{item.target}")
    if report.jodi_first_stability_status != VALID:
        issues.append("JODI_FIRST_STABILITY_INVALID")
    if not report.jodi_first_open_dependency:
        issues.append("OPEN_DEPENDENCY_NOT_CONFIRMED")
    if not report.report_identity.startswith("production-model-qualification-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_production_model_qualification(report: ProductionModelQualificationReport, path: str | Path = "reports/production_model_qualification.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = [
    "QUALIFICATION_VERSION", "VALID", "INVALID", "QUALIFIED", "HOLD",
    "EXPECTED_TARGET_CHAMPIONS", "TargetQualification", "ProductionModelQualificationReport",
    "build_production_model_qualification", "validate_production_model_qualification",
    "write_production_model_qualification",
]
