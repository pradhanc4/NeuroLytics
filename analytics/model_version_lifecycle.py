from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from typing import Iterable
from analytics.model_selection import ModelSelectionReport,validate_model_selection_report
MODEL_LIFECYCLE_VERSION="61.0.0"
VALID="VALID";INVALID="INVALID"
CANDIDATE="CANDIDATE";ACTIVE="ACTIVE";DEPRECATED="DEPRECATED";RETIRED="RETIRED";REJECTED="REJECTED"
VALID_STATES=(CANDIDATE,ACTIVE,DEPRECATED,RETIRED,REJECTED)
_ALLOWED_TRANSITIONS={
 CANDIDATE:(ACTIVE,REJECTED),
 ACTIVE:(DEPRECATED,RETIRED),
 DEPRECATED:(RETIRED,ACTIVE),
 RETIRED:(),REJECTED:()
}
@dataclass(frozen=True)
class ModelVersion:
 model_identity:str
 version:str
 state:str
 source_selection_identity:str
 artifact_identity:str
 parent_version:str|None=None
 metadata:tuple[tuple[str,str],...]=()
@dataclass(frozen=True)
class LifecycleTransition:
 model_identity:str
 version:str
 from_state:str
 to_state:str
 reason:str
 source_identity:str
@dataclass(frozen=True)
class ModelVersionLifecycleReport:
 version:str
 lifecycle_id:str
 source_selection_identity:str
 versions:tuple[ModelVersion,...]
 transitions:tuple[LifecycleTransition,...]
 active_versions:tuple[str,...]
 candidate_versions:tuple[str,...]
 deprecated_versions:tuple[str,...]
 retired_versions:tuple[str,...]
 rejected_versions:tuple[str,...]
 report_identity:str
@dataclass(frozen=True)
class ModelVersionLifecycleValidationResult:
 status:str
 issues:tuple[str,...]
 @property
 def is_valid(self): return self.status==VALID
def _identity(payload):
 return "model-version-lifecycle-report-"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _validate_version(v):
 if not isinstance(v,ModelVersion): raise TypeError("model version must be ModelVersion")
 if not v.model_identity.strip() or not v.version.strip(): raise ValueError("model identity/version must not be empty")
 if v.state not in VALID_STATES: raise ValueError("invalid lifecycle state")
 if not v.source_selection_identity.strip() or not v.artifact_identity.strip(): raise ValueError("source/artifact identity must not be empty")
 if v.parent_version is not None and not v.parent_version.strip(): raise ValueError("parent_version must not be blank")
 if len({k for k,_ in v.metadata})!=len(v.metadata): raise ValueError("metadata keys must be unique")
def build_model_version(model_identity,version,state=CANDIDATE,source_selection_identity="",artifact_identity="",parent_version=None,metadata=()):
 v=ModelVersion(model_identity,version,state,source_selection_identity,artifact_identity,parent_version,tuple(metadata))
 _validate_version(v); return v
def transition_model_version(model_version,to_state,reason="",source_identity=""):
 _validate_version(model_version)
 if not isinstance(to_state,str) or to_state not in VALID_STATES: raise ValueError("invalid target state")
 if to_state not in _ALLOWED_TRANSITIONS[model_version.state]: raise ValueError("invalid lifecycle transition")
 if not isinstance(reason,str) or not reason.strip(): raise ValueError("transition reason must not be empty")
 if not isinstance(source_identity,str) or not source_identity.strip(): raise ValueError("transition source identity must not be empty")
 return LifecycleTransition(model_version.model_identity,model_version.version,model_version.state,to_state,reason,source_identity)
def build_model_version_lifecycle_report(lifecycle_id,selection_report,versions,transitions=()):
 if not isinstance(lifecycle_id,str) or not lifecycle_id.strip(): raise ValueError("lifecycle_id must not be empty")
 if not isinstance(selection_report,ModelSelectionReport): raise TypeError("selection_report must be ModelSelectionReport")
 sv=validate_model_selection_report(selection_report)
 if not sv.is_valid: raise ValueError("invalid selection report: "+", ".join(sv.issues))
 vv=tuple(versions); tt=tuple(transitions)
 if not vv: raise ValueError("at least one model version is required")
 for v in vv: _validate_version(v)
 for t in tt:
  if not isinstance(t,LifecycleTransition): raise TypeError("transition must be LifecycleTransition")
  if t.from_state not in VALID_STATES or t.to_state not in VALID_STATES: raise ValueError("invalid transition state")
  if t.to_state not in _ALLOWED_TRANSITIONS[t.from_state]: raise ValueError("invalid lifecycle transition")
  if not t.reason.strip() or not t.source_identity.strip(): raise ValueError("transition lineage/reason required")
 keys=[(v.model_identity,v.version) for v in vv]
 if len(set(keys))!=len(keys): raise ValueError("duplicate model version")
 by_key={k:v for k,v in zip(keys,vv)}
 for t in tt:
  if (t.model_identity,t.version) not in by_key: raise ValueError("transition references unknown model version")
 active=tuple(f"{v.model_identity}:{v.version}" for v in vv if v.state==ACTIVE)
 cand=tuple(f"{v.model_identity}:{v.version}" for v in vv if v.state==CANDIDATE)
 dep=tuple(f"{v.model_identity}:{v.version}" for v in vv if v.state==DEPRECATED)
 ret=tuple(f"{v.model_identity}:{v.version}" for v in vv if v.state==RETIRED)
 rej=tuple(f"{v.model_identity}:{v.version}" for v in vv if v.state==REJECTED)
 payload=(MODEL_LIFECYCLE_VERSION,lifecycle_id,selection_report.report_identity,vv,tt,active,cand,dep,ret,rej)
 return ModelVersionLifecycleReport(MODEL_LIFECYCLE_VERSION,lifecycle_id,selection_report.report_identity,vv,tt,active,cand,dep,ret,rej,_identity(payload))
def lifecycle_versions(report,state=None):
 return report.versions if state is None else tuple(v for v in report.versions if v.state==state)
def lifecycle_transitions(report,model_identity=None):
 return report.transitions if model_identity is None else tuple(t for t in report.transitions if t.model_identity==model_identity)
def lifecycle_summary(report):
 v=validate_model_version_lifecycle_report(report)
 return {"status":v.status,"version":report.version,"lifecycle_id":report.lifecycle_id,"source_selection_identity":report.source_selection_identity,"version_count":len(report.versions),"transition_count":len(report.transitions),"active_versions":report.active_versions,"candidate_versions":report.candidate_versions,"deprecated_versions":report.deprecated_versions,"retired_versions":report.retired_versions,"rejected_versions":report.rejected_versions,"report_identity":report.report_identity}
def validate_model_version_lifecycle_report(report):
 if not isinstance(report,ModelVersionLifecycleReport): return ModelVersionLifecycleValidationResult(INVALID,("INVALID_REPORT_TYPE",))
 issues=[]
 if report.version!=MODEL_LIFECYCLE_VERSION: issues.append("INVALID_VERSION")
 if not report.lifecycle_id.strip(): issues.append("MISSING_LIFECYCLE_ID")
 if not report.source_selection_identity.strip(): issues.append("MISSING_SOURCE_IDENTITY")
 keys=[]
 for v in report.versions:
  try: _validate_version(v)
  except (TypeError,ValueError) as e: issues.append("INVALID_MODEL_VERSION")
  keys.append((v.model_identity,v.version))
 if len(set(keys))!=len(keys): issues.append("DUPLICATE_MODEL_VERSION")
 keyset=set(keys)
 for t in report.transitions:
  if not isinstance(t,LifecycleTransition): issues.append("INVALID_TRANSITION"); continue
  if (t.model_identity,t.version) not in keyset: issues.append("UNKNOWN_TRANSITION_VERSION")
  if t.from_state not in VALID_STATES or t.to_state not in VALID_STATES: issues.append("INVALID_TRANSITION_STATE")
  elif t.to_state not in _ALLOWED_TRANSITIONS[t.from_state]: issues.append("INVALID_TRANSITION_PATH")
  if not t.reason.strip() or not t.source_identity.strip(): issues.append("MISSING_TRANSITION_LINEAGE")
 expected={
 "active_versions":tuple(f"{v.model_identity}:{v.version}" for v in report.versions if v.state==ACTIVE),
 "candidate_versions":tuple(f"{v.model_identity}:{v.version}" for v in report.versions if v.state==CANDIDATE),
 "deprecated_versions":tuple(f"{v.model_identity}:{v.version}" for v in report.versions if v.state==DEPRECATED),
 "retired_versions":tuple(f"{v.model_identity}:{v.version}" for v in report.versions if v.state==RETIRED),
 "rejected_versions":tuple(f"{v.model_identity}:{v.version}" for v in report.versions if v.state==REJECTED)}
 for name,value in expected.items():
  if getattr(report,name)!=value: issues.append(name.upper()+"_MISMATCH")
 if not report.report_identity.startswith("model-version-lifecycle-report-"): issues.append("INVALID_REPORT_IDENTITY")
 return ModelVersionLifecycleValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))
__all__=["MODEL_LIFECYCLE_VERSION","VALID","INVALID","CANDIDATE","ACTIVE","DEPRECATED","RETIRED","REJECTED","VALID_STATES","ModelVersion","LifecycleTransition","ModelVersionLifecycleReport","ModelVersionLifecycleValidationResult","build_model_version","transition_model_version","build_model_version_lifecycle_report","lifecycle_versions","lifecycle_transitions","lifecycle_summary","validate_model_version_lifecycle_report"]
