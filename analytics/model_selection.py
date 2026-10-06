from __future__ import annotations
import hashlib,json,math
from dataclasses import dataclass
from analytics.champion_challenger import ChampionChallengerReport,validate_champion_challenger_report
MODEL_SELECTION_VERSION="60.0.0";VALID="VALID";INVALID="INVALID";ELIGIBLE="ELIGIBLE";INELIGIBLE="INELIGIBLE";PROMOTE="PROMOTE";HOLD="HOLD";EPS=1e-12
@dataclass(frozen=True)
class PromotionPolicy:
 min_health_score:float=.80
 min_improvement:float=0.0
 require_healthy_status:bool=True
 require_positive_improvement:bool=True
@dataclass(frozen=True)
class ModelSelectionDecision:
 model_identity:str;champion_identity:str;health_score:float;champion_health_score:float;absolute_change_vs_champion:float;relative_change_vs_champion:float|None;health_status:str;eligibility:str;action:str;reasons:tuple[str,...]
@dataclass(frozen=True)
class ModelSelectionReport:
 version:str;selection_id:str;champion_challenger_source_identity:str;policy:PromotionPolicy;champion_identity:str;decisions:tuple[ModelSelectionDecision,...];selected_model:str|None;promoted_models:tuple[str,...];held_models:tuple[str,...];ineligible_models:tuple[str,...];report_identity:str
@dataclass(frozen=True)
class ModelSelectionValidationResult:
 status:str;issues:tuple[str,...]
 @property
 def is_valid(self):return self.status==VALID
def _id(x):return "model-selection-report-"+hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _rel(b,c):return None if abs(b)<=EPS else (c-b)/abs(b)
def _policy(p):
 if not isinstance(p,PromotionPolicy):raise TypeError("policy must be a PromotionPolicy.")
 if not math.isfinite(p.min_health_score) or not 0<=p.min_health_score<=1:raise ValueError("invalid min_health_score")
 if not math.isfinite(p.min_improvement):raise ValueError("invalid min_improvement")
 if not isinstance(p.require_healthy_status,bool) or not isinstance(p.require_positive_improvement,bool):raise ValueError("policy booleans must be boolean")
def _reasons(x,p):
 r=[]
 if x.health_score<p.min_health_score:r.append("HEALTH_SCORE_BELOW_MINIMUM")
 if p.require_healthy_status and x.health_status!="HEALTHY":r.append("CHALLENGER_NOT_HEALTHY")
 if x.absolute_change_vs_champion<p.min_improvement:r.append("IMPROVEMENT_BELOW_MINIMUM")
 if p.require_positive_improvement and x.absolute_change_vs_champion<=EPS:r.append("NO_POSITIVE_IMPROVEMENT")
 return tuple(r)
def build_model_selection_report(selection_id,champion_challenger_report,*,policy=PromotionPolicy()):
 if not isinstance(selection_id,str) or not selection_id.strip():raise ValueError("selection_id must not be empty.")
 if not isinstance(champion_challenger_report,ChampionChallengerReport):raise TypeError("champion_challenger_report must be a ChampionChallengerReport.")
 v=validate_champion_challenger_report(champion_challenger_report)
 if not v.is_valid:raise ValueError("invalid champion/challenger report: "+", ".join(v.issues))
 _policy(policy);d=[]
 for e in champion_challenger_report.evidence:
  st="HEALTHY" if e.health_score>=.80 else "DEGRADED" if e.health_score>=.50 else "CRITICAL"
  rr=_reasons(type("X",(),{"health_score":e.health_score,"absolute_change_vs_champion":e.absolute_change_vs_champion,"health_status":st})(),policy)
  d.append(ModelSelectionDecision(e.model_identity,e.champion_identity,e.health_score,e.champion_health_score,e.absolute_change_vs_champion,e.relative_change_vs_champion,st,ELIGIBLE if not rr else INELIGIBLE,PROMOTE if not rr else HOLD,rr))
 d=tuple(d);ok=tuple(x for x in d if x.eligibility==ELIGIBLE)
 sel=sorted(ok,key=lambda x:(-x.health_score,-x.absolute_change_vs_champion,x.model_identity))[0].model_identity if ok else None
 pro=(sel,) if sel else ();held=tuple(x.model_identity for x in d if x.eligibility==ELIGIBLE and x.action==HOLD);bad=tuple(x.model_identity for x in d if x.eligibility==INELIGIBLE)
 payload=(MODEL_SELECTION_VERSION,selection_id,champion_challenger_report.report_identity,policy,champion_challenger_report.champion.model_identity,[(x.model_identity,x.health_score,x.absolute_change_vs_champion,x.eligibility,x.action,x.reasons) for x in d],sel,pro,held,bad)
 return ModelSelectionReport(MODEL_SELECTION_VERSION,selection_id,champion_challenger_report.report_identity,policy,champion_challenger_report.champion.model_identity,d,sel,pro,held,bad,_id(payload))
def model_selection_summary(r):
 v=validate_model_selection_report(r);return {"status":v.status,"version":r.version,"selection_id":r.selection_id,"champion_identity":r.champion_identity,"selected_model":r.selected_model,"promoted_models":r.promoted_models,"held_models":r.held_models,"ineligible_models":r.ineligible_models,"decision_count":len(r.decisions),"report_identity":r.report_identity}
def model_selection_decisions(r,model_identity=None):return r.decisions if model_identity is None else tuple(x for x in r.decisions if x.model_identity==model_identity)
def model_selection_candidates(r):return tuple(x.model_identity for x in r.decisions)
def validate_model_selection_report(r):
 if not isinstance(r,ModelSelectionReport):return ModelSelectionValidationResult(INVALID,("INVALID_REPORT_TYPE",))
 q=[]
 if r.version!=MODEL_SELECTION_VERSION:q.append("INVALID_VERSION")
 if not r.selection_id.strip():q.append("MISSING_SELECTION_ID")
 if not r.champion_challenger_source_identity.strip():q.append("MISSING_SOURCE_IDENTITY")
 if not r.champion_identity.strip():q.append("MISSING_CHAMPION_IDENTITY")
 try:_policy(r.policy)
 except (TypeError,ValueError):q.append("INVALID_POLICY")
 if len({x.model_identity for x in r.decisions})!=len(r.decisions):q.append("DUPLICATE_DECISIONS")
 for x in r.decisions:
  if x.champion_identity!=r.champion_identity:q.append("DECISION_CHAMPION_MISMATCH")
  if not math.isfinite(x.health_score) or not 0<=x.health_score<=1:q.append("INVALID_HEALTH_SCORE")
  if not math.isfinite(x.champion_health_score) or not 0<=x.champion_health_score<=1:q.append("INVALID_CHAMPION_SCORE")
  if not math.isfinite(x.absolute_change_vs_champion) or not math.isclose(x.absolute_change_vs_champion,x.health_score-x.champion_health_score,rel_tol=0,abs_tol=EPS):q.append("CHANGE_MISMATCH")
  er=_rel(x.champion_health_score,x.health_score)
  if (x.relative_change_vs_champion is None)!=(er is None) or (er is not None and not math.isclose(x.relative_change_vs_champion,er,rel_tol=0,abs_tol=EPS)):q.append("RELATIVE_CHANGE_MISMATCH")
  rr=_reasons(x,r.policy)
  if x.reasons!=rr:q.append("REASONS_MISMATCH")
  ee=ELIGIBLE if not rr else INELIGIBLE
  if x.eligibility!=ee:q.append("ELIGIBILITY_MISMATCH")
  if x.action!=(PROMOTE if ee==ELIGIBLE else HOLD):q.append("ACTION_MISMATCH")
 ok=[x for x in r.decisions if x.eligibility==ELIGIBLE];sel=sorted(ok,key=lambda x:(-x.health_score,-x.absolute_change_vs_champion,x.model_identity))[0].model_identity if ok else None
 if r.selected_model!=sel:q.append("SELECTED_MODEL_MISMATCH")
 if r.promoted_models!=((sel,) if sel else ()):q.append("PROMOTED_MODELS_MISMATCH")
 if r.held_models!=tuple(x.model_identity for x in r.decisions if x.eligibility==ELIGIBLE and x.action==HOLD):q.append("HELD_MODELS_MISMATCH")
 if r.ineligible_models!=tuple(x.model_identity for x in r.decisions if x.eligibility==INELIGIBLE):q.append("INELIGIBLE_MODELS_MISMATCH")
 if r.selected_model==r.champion_identity:q.append("CHAMPION_SELECTED_AS_CHALLENGER")
 if not r.report_identity.startswith("model-selection-report-"):q.append("INVALID_REPORT_IDENTITY")
 return ModelSelectionValidationResult(VALID if not q else INVALID,tuple(sorted(set(q))))
DEFAULT_MIN_HEALTH_SCORE=.80;DEFAULT_MIN_IMPROVEMENT=0.0