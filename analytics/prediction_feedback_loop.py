from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

PREDICTION_FEEDBACK_VERSION = "76.1.0"
VALID = "VALID"
INVALID = "INVALID"
HOLD = "HOLD"
RETRAIN = "RETRAIN"
PROMOTE = "PROMOTE"
REJECT = "REJECT"
GOOD = "GOOD"
POOR = "POOR"

ERROR_SOURCES = (
    "data_quality", "feature", "model", "ensemble",
    "ranking", "calibration", "distribution_shift", "unknown",
)

@dataclass(frozen=True)
class FeedbackPolicy:
    minimum_top_k: int = 3
    maximum_miss_streak: int = 2
    minimum_recent_accuracy: float = 0.50
    minimum_candidate_gain: float = 0.01
    minimum_validation_accuracy: float = 0.50
    require_walk_forward_improvement: bool = True

@dataclass(frozen=True)
class PredictionEntry:
    prediction_id: str
    target_date: date
    data_identity: str
    feature_identity: str
    model_identity: str
    model_version: str
    ensemble_identity: str
    ranking_identity: str
    prediction: int
    top_k: tuple[int, ...]
    probabilities: tuple[float, ...]
    confidence: float

@dataclass(frozen=True)
class PredictionOutcome:
    prediction_id: str
    actual: int
    correct: bool
    top_k_hit: bool
    prediction_error: int
    actual_rank: int | None
    reciprocal_rank: float
    error_source: str
    error_details: str

@dataclass(frozen=True)
class RetrainingAssessment:
    decision: str
    reasons: tuple[str, ...]
    evidence: tuple[str, ...]
    recommended_actions: tuple[str, ...]

@dataclass(frozen=True)
class ModelComparison:
    champion_accuracy: float
    challenger_accuracy: float
    champion_validation_accuracy: float
    challenger_validation_accuracy: float
    champion_walk_forward_accuracy: float
    challenger_walk_forward_accuracy: float

@dataclass(frozen=True)
class PromotionDecision:
    decision: str
    reasons: tuple[str, ...]
    gain: float

@dataclass(frozen=True)
class FeedbackCycleReport:
    version: str
    cycle_id: str
    entry: PredictionEntry
    outcome: PredictionOutcome
    assessment: RetrainingAssessment
    promotion: PromotionDecision
    report_identity: str

@dataclass(frozen=True)
class FeedbackValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()


def _finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite numeric")


def validate_feedback_policy(policy: FeedbackPolicy) -> None:
    if not isinstance(policy, FeedbackPolicy):
        raise TypeError("policy must be FeedbackPolicy")
    if not 1 <= policy.minimum_top_k <= 10:
        raise ValueError("minimum_top_k must be 1..10")
    if policy.maximum_miss_streak < 1:
        raise ValueError("maximum_miss_streak must be positive")
    for value, name in ((policy.minimum_recent_accuracy, "minimum_recent_accuracy"),
                        (policy.minimum_candidate_gain, "minimum_candidate_gain"),
                        (policy.minimum_validation_accuracy, "minimum_validation_accuracy")):
        _finite(value, name)
    if not 0 <= policy.minimum_recent_accuracy <= 1:
        raise ValueError("minimum_recent_accuracy must be 0..1")
    if policy.minimum_candidate_gain < 0:
        raise ValueError("minimum_candidate_gain must be non-negative")
    if not 0 <= policy.minimum_validation_accuracy <= 1:
        raise ValueError("minimum_validation_accuracy must be 0..1")
    if not isinstance(policy.require_walk_forward_improvement, bool):
        raise ValueError("require_walk_forward_improvement must be boolean")
def _validate_probabilities(probabilities: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(v) for v in probabilities)
    if len(values) != 10:
        raise ValueError("probabilities must contain ten digit probabilities")
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("probabilities must be finite and non-negative")
    if not math.isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-6):
        raise ValueError("probabilities must sum to one")
    return values


def build_prediction_entry(
    prediction_id: str,
    target_date: date,
    data_identity: str,
    feature_identity: str,
    model_identity: str,
    model_version: str,
    ensemble_identity: str,
    ranking_identity: str,
    prediction: int,
    probabilities: Sequence[float],
    top_k: Sequence[int],
) -> PredictionEntry:
    values = _validate_probabilities(probabilities)
    if not isinstance(target_date, date):
        raise TypeError("target_date must be date")
    for value, name in ((prediction, "prediction"),):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
            raise ValueError(f"{name} must be digit 0..9")
    candidates = tuple(top_k)
    if not candidates or len(candidates) > 10 or len(set(candidates)) != len(candidates):
        raise ValueError("top_k must contain unique digits")
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 9 for v in candidates):
        raise ValueError("top_k values must be digits 0..9")
    if prediction not in candidates:
        raise ValueError("prediction must be present in top_k")
    text_fields = (prediction_id, data_identity, feature_identity, model_identity,
                   model_version, ensemble_identity, ranking_identity)
    if any(not isinstance(v, str) or not v.strip() for v in text_fields):
        raise ValueError("prediction lineage fields must not be empty")
    confidence = values[prediction]
    return PredictionEntry(prediction_id, target_date, data_identity, feature_identity,
                           model_identity, model_version, ensemble_identity, ranking_identity,
                           prediction, candidates, values, confidence)


def evaluate_prediction_entry(entry: PredictionEntry, actual: int) -> PredictionOutcome:
    if not isinstance(entry, PredictionEntry):
        raise TypeError("entry must be PredictionEntry")
    if isinstance(actual, bool) or not isinstance(actual, int) or not 0 <= actual <= 9:
        raise ValueError("actual must be digit 0..9")
    ordered = sorted(range(10), key=lambda d: (-entry.probabilities[d], d))
    rank = ordered.index(actual) + 1
    correct = entry.prediction == actual
    top_hit = actual in entry.top_k
    return PredictionOutcome(entry.prediction_id, actual, correct, top_hit,
                             entry.prediction - actual, rank, 1.0 / rank,
                             "unknown" if correct else "unknown",
                             "prediction outcome requires diagnostic classification")


def classify_prediction_error(
    outcome: PredictionOutcome,
    *,
    data_valid: bool = True,
    feature_stable: bool = True,
    model_stable: bool = True,
    ensemble_stable: bool = True,
    ranking_stable: bool = True,
    calibration_stable: bool = True,
    distribution_stable: bool = True,
) -> PredictionOutcome:
    if outcome.correct:
        return PredictionOutcome(outcome.prediction_id, outcome.actual, outcome.correct,
                                 outcome.top_k_hit, outcome.prediction_error, outcome.actual_rank,
                                 outcome.reciprocal_rank, "unknown", "prediction was correct")
    flags = ((not data_valid, "data_quality"), (not feature_stable, "feature"),
             (not model_stable, "model"), (not ensemble_stable, "ensemble"),
             (not ranking_stable, "ranking"), (not calibration_stable, "calibration"),
             (not distribution_stable, "distribution_shift"))
    source = next((name for bad, name in flags if bad), "unknown")
    details = "diagnostic evidence: " + ",".join(name for bad, name in flags if bad)
    return PredictionOutcome(outcome.prediction_id, outcome.actual, outcome.correct,
                             outcome.top_k_hit, outcome.prediction_error, outcome.actual_rank,
                             outcome.reciprocal_rank, source, details)


def assess_retraining(
    outcome: PredictionOutcome,
    *,
    recent_outcomes: Sequence[PredictionOutcome] = (),
    policy: FeedbackPolicy = FeedbackPolicy(),
) -> RetrainingAssessment:
    validate_feedback_policy(policy)
    history = tuple(recent_outcomes) + (outcome,)
    recent_accuracy = sum(x.correct for x in history) / len(history)
    miss_streak = 0
    for item in reversed(history):
        if item.correct:
            break
        miss_streak += 1
    reasons = []
    evidence = []
    actions = []
    if not outcome.correct:
        evidence.append("CURRENT_PREDICTION_MISS")
    if not outcome.top_k_hit:
        evidence.append("CURRENT_TOP_K_MISS")
    if recent_accuracy < policy.minimum_recent_accuracy:
        reasons.append("RECENT_ACCURACY_BELOW_THRESHOLD")
        evidence.append(f"RECENT_ACCURACY={recent_accuracy:.6f}")
    if miss_streak >= policy.maximum_miss_streak:
        reasons.append("MISS_STREAK_THRESHOLD_REACHED")
        evidence.append(f"MISS_STREAK={miss_streak}")
    if outcome.error_source != "unknown" and not outcome.correct:
        reasons.append("DIAGNOSTIC_ERROR_SIGNAL")
        evidence.append("ERROR_SOURCE=" + outcome.error_source)
    triggered = bool(reasons)
    if triggered:
        actions.extend(("rebuild_point_in_time_training_dataset",
                        "retrain_candidate_models", "run_validation",
                        "run_walk_forward_evaluation", "compare_champion_vs_challenger"))
    return RetrainingAssessment(RETRAIN if triggered else HOLD, tuple(reasons),
                                tuple(evidence), tuple(actions))
def compare_candidate(
    comparison: ModelComparison,
    policy: FeedbackPolicy = FeedbackPolicy(),
) -> PromotionDecision:
    validate_feedback_policy(policy)
    values = (comparison.champion_accuracy, comparison.challenger_accuracy,
              comparison.champion_validation_accuracy, comparison.challenger_validation_accuracy,
              comparison.champion_walk_forward_accuracy, comparison.challenger_walk_forward_accuracy)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) for v in values):
        raise ValueError("comparison metrics must be finite numeric")
    if any(v < 0 or v > 1 for v in values):
        raise ValueError("comparison accuracy metrics must be 0..1")
    gain = comparison.challenger_accuracy - comparison.champion_accuracy
    reasons = []
    if comparison.challenger_accuracy < policy.minimum_validation_accuracy:
        reasons.append("CHALLENGER_VALIDATION_FLOOR_NOT_MET")
    if comparison.challenger_validation_accuracy < comparison.champion_validation_accuracy:
        reasons.append("CHALLENGER_VALIDATION_NOT_BETTER")
    if policy.require_walk_forward_improvement and comparison.challenger_walk_forward_accuracy < comparison.champion_walk_forward_accuracy:
        reasons.append("CHALLENGER_WALK_FORWARD_NOT_BETTER")
    if gain < policy.minimum_candidate_gain:
        reasons.append("CANDIDATE_GAIN_BELOW_THRESHOLD")
    if reasons:
        return PromotionDecision(REJECT, tuple(reasons), gain)
    return PromotionDecision(PROMOTE, ("CHALLENGER_PASSED_PROMOTION_GATES",), gain)


def build_feedback_cycle(
    cycle_id: str,
    entry: PredictionEntry,
    actual: int,
    *,
    recent_outcomes: Sequence[PredictionOutcome] = (),
    policy: FeedbackPolicy = FeedbackPolicy(),
    diagnostics: Mapping[str, bool] | None = None,
    comparison: ModelComparison | None = None,
) -> FeedbackCycleReport:
    if not isinstance(cycle_id, str) or not cycle_id.strip():
        raise ValueError("cycle_id must not be empty")
    outcome = evaluate_prediction_entry(entry, actual)
    diagnostics = dict(diagnostics or {})
    outcome = classify_prediction_error(
        outcome,
        data_valid=diagnostics.get("data_valid", True),
        feature_stable=diagnostics.get("feature_stable", True),
        model_stable=diagnostics.get("model_stable", True),
        ensemble_stable=diagnostics.get("ensemble_stable", True),
        ranking_stable=diagnostics.get("ranking_stable", True),
        calibration_stable=diagnostics.get("calibration_stable", True),
        distribution_stable=diagnostics.get("distribution_stable", True),
    )
    assessment = assess_retraining(outcome, recent_outcomes=recent_outcomes, policy=policy)
    if comparison is None:
        promotion = PromotionDecision(REJECT, ("NO_CHALLENGER_COMPARISON_AVAILABLE",), 0.0)
    elif assessment.decision == RETRAIN:
        promotion = compare_candidate(comparison, policy)
    else:
        promotion = PromotionDecision(REJECT, ("RETRAINING_NOT_TRIGGERED",), 0.0)
    identity = _identity("prediction-feedback-report-",
                         (PREDICTION_FEEDBACK_VERSION, cycle_id, entry, outcome,
                          assessment, promotion))
    return FeedbackCycleReport(PREDICTION_FEEDBACK_VERSION, cycle_id, entry, outcome,
                               assessment, promotion, identity)
def validate_feedback_cycle(report: FeedbackCycleReport) -> FeedbackValidationResult:
    if not isinstance(report, FeedbackCycleReport):
        return FeedbackValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != PREDICTION_FEEDBACK_VERSION:
        issues.append("INVALID_VERSION")
    if not report.cycle_id.strip():
        issues.append("MISSING_CYCLE_ID")
    if report.outcome.prediction_id != report.entry.prediction_id:
        issues.append("PREDICTION_ID_MISMATCH")
    if report.outcome.actual < 0 or report.outcome.actual > 9:
        issues.append("INVALID_ACTUAL")
    if report.entry.prediction != report.outcome.actual and report.outcome.correct:
        issues.append("CORRECTNESS_MISMATCH")
    if (report.outcome.actual in report.entry.top_k) != report.outcome.top_k_hit:
        issues.append("TOP_K_HIT_MISMATCH")
    if report.outcome.actual_rank is not None:
        if not 1 <= report.outcome.actual_rank <= 10:
            issues.append("INVALID_ACTUAL_RANK")
        expected_rr = 1.0 / report.outcome.actual_rank
        if not math.isclose(report.outcome.reciprocal_rank, expected_rr, rel_tol=0, abs_tol=1e-12):
            issues.append("RECIPROCAL_RANK_MISMATCH")
    if report.outcome.error_source not in ERROR_SOURCES:
        issues.append("INVALID_ERROR_SOURCE")
    if report.assessment.decision not in (HOLD, RETRAIN):
        issues.append("INVALID_RETRAINING_DECISION")
    if report.promotion.decision not in (PROMOTE, REJECT):
        issues.append("INVALID_PROMOTION_DECISION")
    if not report.report_identity.startswith("prediction-feedback-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return FeedbackValidationResult(VALID if not issues else INVALID,
                                    tuple(sorted(set(issues))))


def feedback_cycle_summary(report: FeedbackCycleReport) -> dict[str, object]:
    validation = validate_feedback_cycle(report)
    return {
        "status": validation.status,
        "version": report.version,
        "cycle_id": report.cycle_id,
        "prediction_id": report.entry.prediction_id,
        "correct": report.outcome.correct,
        "top_k_hit": report.outcome.top_k_hit,
        "actual_rank": report.outcome.actual_rank,
        "error_source": report.outcome.error_source,
        "retraining_decision": report.assessment.decision,
        "promotion_decision": report.promotion.decision,
        "candidate_gain": report.promotion.gain,
        "report_identity": report.report_identity,
    }


def feedback_error_breakdown(outcomes: Sequence[PredictionOutcome]) -> dict[str, int]:
    counts = {name: 0 for name in ERROR_SOURCES}
    for outcome in outcomes:
        if not isinstance(outcome, PredictionOutcome):
            raise TypeError("outcomes must contain PredictionOutcome")
        if not outcome.correct:
            counts[outcome.error_source] += 1
    return counts


__all__ = [
    "PREDICTION_FEEDBACK_VERSION", "VALID", "INVALID", "HOLD", "RETRAIN",
    "PROMOTE", "REJECT", "GOOD", "POOR", "ERROR_SOURCES", "FeedbackPolicy",
    "PredictionEntry", "PredictionOutcome", "RetrainingAssessment",
    "ModelComparison", "PromotionDecision", "FeedbackCycleReport",
    "FeedbackValidationResult", "validate_feedback_policy", "build_prediction_entry",
    "evaluate_prediction_entry", "classify_prediction_error", "assess_retraining",
    "compare_candidate", "build_feedback_cycle", "validate_feedback_cycle",
    "feedback_cycle_summary", "feedback_error_breakdown",
]
