from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable

RETRAINING_DECISION_VERSION = "62.0.0"
VALID = "VALID"
INVALID = "INVALID"
RETRAIN = "RETRAIN"
HOLD = "HOLD"
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
SUPPORTED_SOURCE_TYPES = (
    "performance_degradation", "model_drift", "data_drift",
    "prediction_distribution", "calibration_drift", "ranking_drift",
    "feature_drift", "concept_drift",
)

@dataclass(frozen=True)
class RetrainingEvidence:
    source_type: str
    metric: str
    baseline_value: float
    latest_value: float
    threshold: float
    triggered: bool
    consecutive_periods: int = 1
    source_identity: str = ""
    period_label: str = ""
    details: str = ""

@dataclass(frozen=True)
class RetrainingRule:
    source_type: str
    metric: str
    threshold: float
    min_consecutive_periods: int = 1
    enabled: bool = True

@dataclass(frozen=True)
class RetrainingDecision:
    decision: str
    triggered_evidence: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    reasons: tuple[str, ...]
    source_identities: tuple[str, ...]

@dataclass(frozen=True)
class RetrainingDecisionReport:
    version: str
    decision_id: str
    model_identity: str
    evaluation_date: str
    rules: tuple[RetrainingRule, ...]
    evidence: tuple[RetrainingEvidence, ...]
    decision: RetrainingDecision
    report_identity: str

@dataclass(frozen=True)
class RetrainingDecisionValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self):
        return self.status == VALID

def _identity(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "retraining-decision-report-" + hashlib.sha256(raw).hexdigest()

def _finite(value, name):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")

def _validate_rule(rule):
    if not isinstance(rule, RetrainingRule): raise TypeError("rule must be RetrainingRule")
    if rule.source_type not in SUPPORTED_SOURCE_TYPES: raise ValueError("invalid rule source_type")
    if not isinstance(rule.metric, str) or not rule.metric.strip(): raise ValueError("rule metric must not be empty")
    _finite(rule.threshold, "rule threshold")
    if not isinstance(rule.min_consecutive_periods, int) or isinstance(rule.min_consecutive_periods, bool) or rule.min_consecutive_periods < 1:
        raise ValueError("min_consecutive_periods must be a positive integer")
    if not isinstance(rule.enabled, bool): raise ValueError("rule enabled must be boolean")

def _validate_evidence(item):
    if not isinstance(item, RetrainingEvidence): raise TypeError("evidence must be RetrainingEvidence")
    if item.source_type not in SUPPORTED_SOURCE_TYPES: raise ValueError("invalid evidence source_type")
    if not isinstance(item.metric, str) or not item.metric.strip(): raise ValueError("evidence metric must not be empty")
    for value, name in ((item.baseline_value, "baseline_value"), (item.latest_value, "latest_value"), (item.threshold, "threshold")): _finite(value, name)
    if not isinstance(item.triggered, bool): raise ValueError("triggered must be boolean")
    if not isinstance(item.consecutive_periods, int) or isinstance(item.consecutive_periods, bool) or item.consecutive_periods < 1: raise ValueError("consecutive_periods must be positive")
    if not isinstance(item.source_identity, str) or not item.source_identity.strip(): raise ValueError("source_identity must not be empty")
    if not isinstance(item.period_label, str): raise ValueError("period_label must be string")
    if not isinstance(item.details, str): raise ValueError("details must be string")

def _rule_key(rule): return (rule.source_type, rule.metric)
def _evidence_key(item): return (item.source_type, item.metric, item.source_identity)

def build_retraining_decision_report(decision_id, model_identity, evaluation_date, evidence: Iterable[RetrainingEvidence], *, rules: Iterable[RetrainingRule] = ()):
    if not isinstance(decision_id, str) or not decision_id.strip(): raise ValueError("decision_id must not be empty")
    if not isinstance(model_identity, str) or not model_identity.strip(): raise ValueError("model_identity must not be empty")
    if not isinstance(evaluation_date, str) or not evaluation_date.strip(): raise ValueError("evaluation_date must not be empty")
    ee = tuple(evidence); rr = tuple(rules)
    if not ee: raise ValueError("at least one monitoring evidence item is required")
    for x in ee: _validate_evidence(x)
    for x in rr: _validate_rule(x)
    if len({_evidence_key(x) for x in ee}) != len(ee): raise ValueError("duplicate evidence")
    if len({_rule_key(x) for x in rr}) != len(rr): raise ValueError("duplicate rule")
    rule_map = {_rule_key(x): x for x in rr if x.enabled}
    triggered=[]; supporting=[]; reasons=[]; source_ids=[]
    for x in ee:
        key=_evidence_key(x); rule=rule_map.get((x.source_type,x.metric))
        qualifies=x.triggered and (rule is None or x.consecutive_periods >= rule.min_consecutive_periods) and (rule is None or (abs(x.latest_value-x.baseline_value) > rule.threshold or math.isclose(abs(x.latest_value-x.baseline_value), rule.threshold, rel_tol=0, abs_tol=1e-12)))
        if qualifies:
            triggered.append(f"{x.source_type}:{x.metric}"); source_ids.append(x.source_identity)
            reasons.append(f"RETRAINING_TRIGGER:{x.source_type}:{x.metric}")
        elif x.triggered:
            supporting.append(f"{x.source_type}:{x.metric}")
    decision = RETRAIN if triggered else HOLD
    if decision == HOLD: reasons.append("NO_RETRAINING_TRIGGER")
    else: reasons.append("MONITORING_EVIDENCE_THRESHOLD_MET")
    dec=RetrainingDecision(decision,tuple(triggered),tuple(supporting),tuple(reasons),tuple(sorted(set(source_ids))))
    payload=(RETRAINING_DECISION_VERSION,decision_id,model_identity,evaluation_date,rr,ee,dec)
    return RetrainingDecisionReport(RETRAINING_DECISION_VERSION,decision_id,model_identity,evaluation_date,rr,ee,dec,_identity(payload))

def retraining_decision_summary(report):
    v=validate_retraining_decision_report(report)
    return {"status":v.status,"version":report.version,"decision_id":report.decision_id,"model_identity":report.model_identity,"evaluation_date":report.evaluation_date,"decision":report.decision.decision,"triggered_evidence":report.decision.triggered_evidence,"supporting_evidence":report.decision.supporting_evidence,"evidence_count":len(report.evidence),"report_identity":report.report_identity}

def retraining_decision_evidence(report, source_type=None):
    return report.evidence if source_type is None else tuple(x for x in report.evidence if x.source_type == source_type)

def retraining_decision_triggers(report): return report.decision.triggered_evidence

def validate_retraining_decision_report(report):
    if not isinstance(report, RetrainingDecisionReport): return RetrainingDecisionValidationResult(INVALID,("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version != RETRAINING_DECISION_VERSION: issues.append("INVALID_VERSION")
    if not report.decision_id.strip(): issues.append("MISSING_DECISION_ID")
    if not report.model_identity.strip(): issues.append("MISSING_MODEL_IDENTITY")
    if not report.evaluation_date.strip(): issues.append("MISSING_EVALUATION_DATE")
    for x in report.rules:
        try: _validate_rule(x)
        except (TypeError,ValueError): issues.append("INVALID_RULE")
    if len({_rule_key(x) for x in report.rules if isinstance(x,RetrainingRule)}) != len(report.rules): issues.append("DUPLICATE_RULE")
    for x in report.evidence:
        try: _validate_evidence(x)
        except (TypeError,ValueError): issues.append("INVALID_EVIDENCE")
    valid_evidence=[x for x in report.evidence if isinstance(x,RetrainingEvidence)]
    if len({_evidence_key(x) for x in valid_evidence}) != len(valid_evidence): issues.append("DUPLICATE_EVIDENCE")
    rule_map={_rule_key(x):x for x in report.rules if isinstance(x,RetrainingRule) and x.enabled}
    expected=[]; supporting=[]; ids=[]
    for x in valid_evidence:
        rule=rule_map.get((x.source_type,x.metric))
        q=x.triggered and (rule is None or x.consecutive_periods >= rule.min_consecutive_periods) and (rule is None or (abs(x.latest_value-x.baseline_value) > rule.threshold or math.isclose(abs(x.latest_value-x.baseline_value), rule.threshold, rel_tol=0, abs_tol=1e-12)))
        if q: expected.append(f"{x.source_type}:{x.metric}"); ids.append(x.source_identity)
        elif x.triggered: supporting.append(f"{x.source_type}:{x.metric}")
    if report.decision.triggered_evidence != tuple(expected): issues.append("TRIGGER_COLLECTION_MISMATCH")
    if report.decision.supporting_evidence != tuple(supporting): issues.append("SUPPORTING_COLLECTION_MISMATCH")
    if report.decision.source_identities != tuple(sorted(set(ids))): issues.append("SOURCE_COLLECTION_MISMATCH")
    expected_decision=RETRAIN if expected else HOLD
    if report.decision.decision != expected_decision: issues.append("DECISION_MISMATCH")
    expected_reasons=tuple([*(f"RETRAINING_TRIGGER:{x}" for x in expected), *( ["NO_RETRAINING_TRIGGER"] if not expected else ["MONITORING_EVIDENCE_THRESHOLD_MET"] )])
    if report.decision.reasons != expected_reasons: issues.append("REASON_MISMATCH")
    if not report.report_identity.startswith("retraining-decision-report-"): issues.append("INVALID_REPORT_IDENTITY")
    return RetrainingDecisionValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

__all__=["RETRAINING_DECISION_VERSION","VALID","INVALID","RETRAIN","HOLD","ACTIVE","INACTIVE","SUPPORTED_SOURCE_TYPES","RetrainingEvidence","RetrainingRule","RetrainingDecision","RetrainingDecisionReport","RetrainingDecisionValidationResult","build_retraining_decision_report","retraining_decision_summary","retraining_decision_evidence","retraining_decision_triggers","validate_retraining_decision_report"]
