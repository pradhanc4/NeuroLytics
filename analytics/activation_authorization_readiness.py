from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path

VERSION = "101.1.0"
VALID, INVALID = "VALID", "INVALID"
AUTHORIZATION_PENDING, AUTHORIZED = "AUTHORIZATION_PENDING", "AUTHORIZED"

@dataclass(frozen=True)
class AuthorizationRecord:
    authorization_id: str
    authorized_by: str
    purpose: str
    scope: str
    artifact_identity: str
    model_identity: str
    model_version: str
    rollout_id: str
    approval_state: str = AUTHORIZATION_PENDING
    record_identity: str = ""

def _hash(value):
    return "activation-readiness-" + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest()

def build_authorization_record(authorization_id, authorized_by, purpose, scope,
                               model_identity, model_version, artifact_identity, rollout_id):
    vals=(authorization_id,authorized_by,purpose,scope,model_identity,model_version,artifact_identity,rollout_id)
    if not all(isinstance(v,str) and v.strip() for v in vals):
        raise ValueError("authorization fields must be non-empty")
    identity=_hash((VERSION,*vals))
    return AuthorizationRecord(
        authorization_id=authorization_id,
        authorized_by=authorized_by,
        purpose=purpose,
        scope=scope,
        artifact_identity=artifact_identity,
        model_identity=model_identity,
        model_version=model_version,
        rollout_id=rollout_id,
        approval_state=AUTHORIZATION_PENDING,
        record_identity=identity,
    )

def validate_authorization_record(record):
    if not isinstance(record, AuthorizationRecord):
        return INVALID, ("INVALID_AUTHORIZATION_TYPE",)
    issues=[]
    for name,value in record.__dict__.items():
        if name not in ("approval_state",) and (not isinstance(value,str) or not value.strip()):
            issues.append("MISSING_"+name.upper())
    if record.approval_state not in (AUTHORIZATION_PENDING, AUTHORIZED):
        issues.append("INVALID_APPROVAL_STATE")
    expected_identity = _hash((VERSION, record.authorization_id, record.authorized_by, record.purpose, record.scope, record.model_identity, record.model_version, record.artifact_identity, record.rollout_id))
    if record.record_identity != expected_identity:
        issues.append("INVALID_RECORD_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))

def validate_activation_plan_binding(record, plan):
    issues=[]
    if validate_authorization_record(record)[0] != VALID:
        issues.append("INVALID_AUTHORIZATION_RECORD")
    for name in ("artifact_identity","model_identity","model_version"):
        if getattr(record,name) != getattr(plan,name):
            issues.append("AUTH_"+name.upper()+"_MISMATCH")
    if record.rollout_id != plan.rollout_id:
        issues.append("AUTH_ROLLOUT_ID_MISMATCH")
    if not record.authorization_id.strip() or record.authorization_id != plan.authorization_id:
        issues.append("AUTHORIZATION_ID_MISMATCH")
    if record.approval_state != AUTHORIZED:
        issues.append("EXPLICIT_AUTHORIZATION_PENDING")
    return VALID if not issues else INVALID, tuple(sorted(set(issues)))

def write_authorization_readiness_report(record, plan, path="reports/activation_authorization_readiness.json"):
    status, issues=validate_activation_plan_binding(record, plan)
    payload={"version":VERSION,"status":status,"activation_ready":status==VALID and plan.status=="READY_TO_EXECUTE",
             "authorization":record.__dict__,"activation_plan_status":plan.status,
             "issues":list(issues),"identity":_hash((record,plan))}
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return payload

__all__=["VERSION","VALID","INVALID","AUTHORIZATION_PENDING","AUTHORIZED","AuthorizationRecord",
         "build_authorization_record","validate_authorization_record","validate_activation_plan_binding",
         "write_authorization_readiness_report"]
