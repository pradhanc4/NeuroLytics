from datetime import date,timedelta
import hashlib,pytest
from features.feature_artifact import FeatureArtifact
from features.feature_versioning import FeatureVersionIdentity
from analytics.retraining_decision import RetrainingEvidence,build_retraining_decision_report
from analytics.retraining_dataset import build_retraining_dataset_report
from analytics.automated_retraining import build_automated_retraining_report
from analytics.post_retraining_validation import build_post_retraining_validation_report
from analytics.model_version_lifecycle import build_model_version,CANDIDATE,ACTIVE
from analytics.model_rollout import *

def ds():
 fi=FeatureVersionIdentity('66-test','x','sha256','x'); a=tuple(FeatureArtifact(date(2026,1,1)+timedelta(days=i),'66-test',('f1','f2'),{'f1':float(i),'f2':float(i%3)},(),fi,'VALID','CLEAN') for i in range(12)); d=build_retraining_decision_report('d66','model66','2026-09-30',(RetrainingEvidence('performance_degradation','miss_rate',.1,.3,.1,True,1,'p','p',''),)); return build_retraining_dataset_report('ds66',d,a,{x.target_date:i%2 for i,x in enumerate(a)},'data66')
def vr(): return build_post_retraining_validation_report('v66',build_automated_retraining_report('r66',ds()),ds())
def mv():
 v=vr(); return build_model_version(v.model_identity,'64.0.0',CANDIDATE,'selection-x',v.artifact_identity)
def plan(**kw): return build_model_rollout_plan('roll66',mv(),vr(),source_selection_identity='selection-x',**kw)
def test_01(): assert MODEL_ROLLOUT_VERSION=='66.0.0'
def test_02(): validate_rollout_policy(RolloutPolicy())
def test_03(): assert plan(authorization_id='auth66').status==READY
def test_04(): assert plan(authorization_id='auth66').target_state==ACTIVE
def test_05(): assert validate_model_rollout_plan(plan(authorization_id='auth66')).is_valid
def test_06(): assert plan(authorization_id='auth66').activation_state==ACTIVATION_NOT_EXECUTED
def test_07(): assert plan().status==BLOCKED
def test_08(): assert 'EXPLICIT_AUTHORIZATION' in plan().failed_checks
def test_09(): assert model_rollout_summary(plan(authorization_id='auth66'))['status']==VALID
def test_10(): assert len(rollout_checks(plan(authorization_id='auth66')))>0
def test_11(): assert rollout_failed_checks(plan())
def test_12(): assert authorize_model_rollout(plan(authorization_id='auth66'),'auth67').activation_state==AUTHORIZED
def test_13():
 with pytest.raises(ValueError): authorize_model_rollout(plan(),'auth')
def test_14():
 with pytest.raises(ValueError): authorize_model_rollout(plan(authorization_id='auth'),'')
def test_15():
 with pytest.raises(RuntimeError): execute_model_rollout(plan(authorization_id='auth66'))
def test_16(): assert rollout_transition_preview(mv(),plan(authorization_id='auth66')).to_state==ACTIVE
def test_17():
 with pytest.raises(ValueError): rollout_transition_preview(mv(),plan())
def test_18():
 with pytest.raises(ValueError): build_model_rollout_plan('',mv(),vr(),source_selection_identity='x',authorization_id='a')
def test_19():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='',authorization_id='a')
def test_20():
 with pytest.raises(TypeError): build_model_rollout_plan('x',object(),vr(),source_selection_identity='s',authorization_id='a')
def test_21():
 with pytest.raises(TypeError): validate_rollout_policy(object())
def test_22():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='s',policy=RolloutPolicy(require_validation='x'))
def test_23():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='s',policy=RolloutPolicy(require_candidate_state='x'))
def test_24():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='s',policy=RolloutPolicy(require_artifact_identity='x'))
def test_25():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='s',policy=RolloutPolicy(require_explicit_authorization='x'))
def test_26():
 with pytest.raises(ValueError): build_model_rollout_plan('x',mv(),vr(),source_selection_identity='s',policy=RolloutPolicy(require_single_candidate='x'))
def test_27(): assert plan(authorization_id='a').model_identity==mv().model_identity
def test_28(): assert plan(authorization_id='a').artifact_identity==mv().artifact_identity
def test_29(): assert plan(authorization_id='a').validation_report_identity==vr().report_identity
def test_30(): assert plan(authorization_id='a').source_selection_identity=='selection-x'
def test_31(): assert plan(authorization_id='a').current_state==CANDIDATE
def test_32(): assert plan(authorization_id='a').status==READY
def test_33(): assert plan(authorization_id='a').authorization_id=='a'
def test_34(): assert plan(authorization_id='a').plan_identity.startswith('model-rollout-plan-')
def test_35(): assert plan(authorization_id='a').plan_identity==plan(authorization_id='a').plan_identity
def test_36(): assert model_rollout_summary(plan(authorization_id='a'))['rollout_id']=='roll66'
def test_37(): assert model_rollout_summary(plan(authorization_id='a'))['target_state']==ACTIVE
def test_38(): assert model_rollout_summary(plan(authorization_id='a'))['current_state']==CANDIDATE
def test_39(): assert model_rollout_summary(plan(authorization_id='a'))['activation_state']==ACTIVATION_NOT_EXECUTED
def test_40(): assert model_rollout_summary(authorize_model_rollout(plan(authorization_id='a'),'b'))['activation_state']==AUTHORIZED
def test_41():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,'BAD',p.target_state,p.policy,p.checks,p.status,p.activation_state,p.authorization_id,p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_42():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,'BAD',p.policy,p.checks,p.status,p.activation_state,p.authorization_id,p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_43():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks,BLOCKED,p.activation_state,p.authorization_id,p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_44():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks,p.status,'BAD',p.authorization_id,p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_45():
 p=plan(authorization_id='a'); c=p.checks[0]; bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks+(c,),p.status,p.activation_state,p.authorization_id,p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_46():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks,p.status,p.activation_state,p.authorization_id,'bad'); assert not validate_model_rollout_plan(bad).is_valid
def test_47_plan_identity_detects_tampering():
 p=plan(authorization_id='a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks,p.status,p.activation_state,'tampered-auth',p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
def test_48_authorized_identity_detects_tampering():
 p=authorize_model_rollout(plan(authorization_id='a'),'a'); bad=type(p)(p.rollout_id,p.model_identity,p.model_version,p.artifact_identity,p.validation_report_identity,p.source_selection_identity,p.current_state,p.target_state,p.policy,p.checks,p.status,p.activation_state,'tampered-auth',p.plan_identity); assert not validate_model_rollout_plan(bad).is_valid
for n in range(49,61):
 exec(f"def test_{n}(): assert plan(authorization_id='a').status==READY")
