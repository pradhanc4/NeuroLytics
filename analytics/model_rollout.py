from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from typing import Sequence
from analytics.post_retraining_validation import PostRetrainingValidationReport,validate_post_retraining_validation_report,VALID as VALIDATION_VALID
from analytics.model_version_lifecycle import ModelVersion,CANDIDATE,ACTIVE,transition_model_version

MODEL_ROLLOUT_VERSION="66.0.0"
VALID="VALID"; INVALID="INVALID"
READY="READY"; BLOCKED="BLOCKED"; AUTHORIZED="AUTHORIZED"
ROLLOUT_PENDING="ROLLOUT_PENDING"; ACTIVATION_NOT_EXECUTED="ACTIVATION_NOT_EXECUTED"

@dataclass(frozen=True)
class RolloutPolicy:
    require_validation: bool=True
    require_candidate_state: bool=True
    require_artifact_identity: bool=True
    require_explicit_authorization: bool=True
    require_single_candidate: bool=True

@dataclass(frozen=True)
class RolloutCheck:
    check_id:str
    status:str
    detail:str

@dataclass(frozen=True)
class ModelRolloutPlan:
    rollout_id:str
    model_identity:str
    model_version:str
    artifact_identity:str
    validation_report_identity:str
    source_selection_identity:str
    current_state:str
    target_state:str
    policy:RolloutPolicy
    checks:tuple[RolloutCheck,...]
    status:str
    activation_state:str
    authorization_id:str
    plan_identity:str
    @property
    def failed_checks(self): return tuple(c.check_id for c in self.checks if c.status=="FAIL")

@dataclass(frozen=True)
class ModelRolloutValidationResult:
    status:str
    issues:tuple[str,...]
    @property
    def is_valid(self): return self.status==VALID

def _hash(payload):
    return "model-rollout-plan-"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _check(cid,ok,detail): return RolloutCheck(cid,"PASS" if ok else "FAIL",detail)

def validate_rollout_policy(policy):
    if not isinstance(policy,RolloutPolicy): raise TypeError("policy must be RolloutPolicy")
    for v in (policy.require_validation,policy.require_candidate_state,policy.require_artifact_identity,policy.require_explicit_authorization,policy.require_single_candidate):
        if not isinstance(v,bool): raise ValueError("rollout policy fields must be boolean")

def build_model_rollout_plan(rollout_id:str, model_version:ModelVersion, validation_report:PostRetrainingValidationReport, *, source_selection_identity:str, authorization_id:str="", policy:RolloutPolicy=RolloutPolicy()):
    if not isinstance(rollout_id,str) or not rollout_id.strip(): raise ValueError("rollout_id must not be empty")
    if not isinstance(source_selection_identity,str) or not source_selection_identity.strip(): raise ValueError("source_selection_identity must not be empty")
    validate_rollout_policy(policy)
    vv=validate_post_retraining_validation_report(validation_report)
    if not vv.is_valid: raise ValueError("post-retraining validation report is invalid")
    if not isinstance(model_version,ModelVersion): raise TypeError("model_version must be ModelVersion")
    checks=[]
    checks.append(_check("VALIDATION_STATUS",validation_report.status==VALIDATION_VALID,"Phase 65 validation is VALID"))
    checks.append(_check("VALIDATION_LINEAGE",validation_report.model_identity==model_version.model_identity,"validation model identity matches lifecycle model"))
    checks.append(_check("ARTIFACT_LINEAGE",validation_report.artifact_identity==model_version.artifact_identity,"validation artifact matches lifecycle artifact"))
    checks.append(_check("CANDIDATE_STATE",model_version.state==CANDIDATE,"model is currently CANDIDATE"))
    checks.append(_check("MODEL_VERSION",bool(model_version.version.strip()),"model version is present"))
    checks.append(_check("SOURCE_SELECTION",bool(source_selection_identity.strip()),"selection lineage is present"))
    if policy.require_artifact_identity: checks.append(_check("ARTIFACT_IDENTITY",bool(model_version.artifact_identity.strip()),"artifact identity is required"))
    if policy.require_explicit_authorization: checks.append(_check("EXPLICIT_AUTHORIZATION",bool(authorization_id.strip()),"explicit authorization is required"))
    failed=tuple(c.check_id for c in checks if c.status=="FAIL")
    status=READY if not failed else BLOCKED
    activation=ACTIVATION_NOT_EXECUTED
    plan_identity=_hash((
        MODEL_ROLLOUT_VERSION,
        rollout_id,
        (
            model_version.model_identity,
            model_version.version,
            model_version.artifact_identity,
            model_version.state,
            ACTIVE,
        ),
        validation_report.report_identity,
        source_selection_identity,
        policy,
        tuple(checks),
        status,
        activation,
        authorization_id,
    ))
    return ModelRolloutPlan(rollout_id,model_version.model_identity,model_version.version,model_version.artifact_identity,validation_report.report_identity,source_selection_identity,model_version.state,ACTIVE,policy,tuple(checks),status,activation,authorization_id,plan_identity)

def authorize_model_rollout(plan:ModelRolloutPlan, authorization_id:str):
    if not isinstance(plan,ModelRolloutPlan): raise TypeError("plan must be ModelRolloutPlan")
    if plan.status!=READY: raise ValueError("rollout plan is not READY")
    if not isinstance(authorization_id,str) or not authorization_id.strip(): raise ValueError("authorization_id must not be empty")
    return ModelRolloutPlan(plan.rollout_id,plan.model_identity,plan.model_version,plan.artifact_identity,plan.validation_report_identity,plan.source_selection_identity,plan.current_state,plan.target_state,plan.policy,plan.checks,plan.status,AUTHORIZED,authorization_id,_hash((plan,AUTHORIZED,authorization_id)))

def execute_model_rollout(plan:ModelRolloutPlan):
    if not isinstance(plan,ModelRolloutPlan): raise TypeError("plan must be ModelRolloutPlan")
    raise RuntimeError("Phase 66 is a controlled activation boundary; production activation is not executed by this framework")

def rollout_transition_preview(model_version:ModelVersion, plan:ModelRolloutPlan):
    if plan.model_identity!=model_version.model_identity or plan.model_version!=model_version.version: raise ValueError("rollout/model version mismatch")
    if plan.status!=READY: raise ValueError("rollout plan is not READY")
    return transition_model_version(model_version,ACTIVE,"Phase 66 authorized rollout transition preview",plan.plan_identity)

def model_rollout_summary(plan):
    v=validate_model_rollout_plan(plan)
    return {"status":v.status,"version":plan.version if hasattr(plan,"version") else MODEL_ROLLOUT_VERSION,"rollout_id":plan.rollout_id,"model_identity":plan.model_identity,"model_version":plan.model_version,"artifact_identity":plan.artifact_identity,"validation_report_identity":plan.validation_report_identity,"current_state":plan.current_state,"target_state":plan.target_state,"rollout_status":plan.status,"activation_state":plan.activation_state,"authorization_id":plan.authorization_id,"failed_checks":plan.failed_checks,"plan_identity":plan.plan_identity}

def rollout_checks(plan): return plan.checks
def rollout_failed_checks(plan): return plan.failed_checks

def validate_model_rollout_plan(plan):
    if not isinstance(plan,ModelRolloutPlan): return ModelRolloutValidationResult(INVALID,("INVALID_PLAN_TYPE",))
    issues=[]
    if plan.current_state not in (CANDIDATE,ACTIVE): issues.append("INVALID_CURRENT_STATE")
    if plan.target_state!=ACTIVE: issues.append("INVALID_TARGET_STATE")
    if plan.status not in (READY,BLOCKED): issues.append("INVALID_ROLLOUT_STATUS")
    if plan.activation_state not in (ACTIVATION_NOT_EXECUTED,AUTHORIZED): issues.append("INVALID_ACTIVATION_STATE")
    if not plan.rollout_id.strip(): issues.append("MISSING_ROLLOUT_ID")
    if not plan.model_identity.strip() or not plan.model_version.strip(): issues.append("MISSING_MODEL_IDENTITY")
    if not plan.artifact_identity.strip(): issues.append("MISSING_ARTIFACT_IDENTITY")
    if not plan.validation_report_identity.strip(): issues.append("MISSING_VALIDATION_IDENTITY")
    if not plan.source_selection_identity.strip(): issues.append("MISSING_SELECTION_IDENTITY")
    ids=tuple(c.check_id for c in plan.checks)
    if len(ids)!=len(set(ids)): issues.append("DUPLICATE_CHECK_IDS")
    expected_failed=tuple(c.check_id for c in plan.checks if c.status=="FAIL")
    if expected_failed!=plan.failed_checks: issues.append("FAILED_CHECK_RECONCILIATION")
    if plan.status==READY and plan.failed_checks: issues.append("READY_WITH_FAILED_CHECKS")
    if plan.status==BLOCKED and not plan.failed_checks: issues.append("BLOCKED_WITHOUT_FAILED_CHECKS")
    if plan.activation_state==AUTHORIZED and not plan.authorization_id.strip(): issues.append("AUTHORIZED_WITHOUT_AUTHORIZATION_ID")
    if plan.activation_state == AUTHORIZED:
        base_identity = _hash((
            MODEL_ROLLOUT_VERSION,
            plan.rollout_id,
            (
                plan.model_identity,
                plan.model_version,
                plan.artifact_identity,
                plan.current_state,
                plan.target_state,
            ),
            plan.validation_report_identity,
            plan.source_selection_identity,
            plan.policy,
            plan.checks,
            plan.status,
            ACTIVATION_NOT_EXECUTED,
            plan.authorization_id,
        ))
        base_plan = ModelRolloutPlan(
            plan.rollout_id,
            plan.model_identity,
            plan.model_version,
            plan.artifact_identity,
            plan.validation_report_identity,
            plan.source_selection_identity,
            plan.current_state,
            plan.target_state,
            plan.policy,
            plan.checks,
            plan.status,
            ACTIVATION_NOT_EXECUTED,
            plan.authorization_id,
            base_identity,
        )
        expected_identity = _hash((base_plan, AUTHORIZED, plan.authorization_id))
    else:
        expected_identity = _hash((
            MODEL_ROLLOUT_VERSION,
            plan.rollout_id,
            (
                plan.model_identity,
                plan.model_version,
                plan.artifact_identity,
                plan.current_state,
                plan.target_state,
            ),
            plan.validation_report_identity,
            plan.source_selection_identity,
            plan.policy,
            plan.checks,
            plan.status,
            plan.activation_state,
            plan.authorization_id,
        ))
    if plan.plan_identity != expected_identity:
        issues.append("INVALID_PLAN_IDENTITY")
    return ModelRolloutValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

__all__=["MODEL_ROLLOUT_VERSION","VALID","INVALID","READY","BLOCKED","AUTHORIZED","ROLLOUT_PENDING","ACTIVATION_NOT_EXECUTED","RolloutPolicy","RolloutCheck","ModelRolloutPlan","ModelRolloutValidationResult","validate_rollout_policy","build_model_rollout_plan","authorize_model_rollout","execute_model_rollout","rollout_transition_preview","model_rollout_summary","rollout_checks","rollout_failed_checks","validate_model_rollout_plan"]
