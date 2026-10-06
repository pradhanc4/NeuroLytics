from datetime import date,timedelta
import hashlib
import pytest
from features.feature_artifact import FeatureArtifact
from features.feature_versioning import FeatureVersionIdentity
from analytics.retraining_decision import RetrainingEvidence,build_retraining_decision_report
from analytics.retraining_dataset import build_retraining_dataset_report
from analytics.automated_retraining import build_automated_retraining_report
from analytics.post_retraining_validation import *

def fid():
 c='{"feature_version":"65-test"}'; return FeatureVersionIdentity('65-test','feature-'+hashlib.sha256(c.encode()).hexdigest(),'sha256',c)
def dec(): return build_retraining_decision_report('d65','model-old','2026-09-30',(RetrainingEvidence('performance_degradation','miss_rate',.1,.3,.1,True,1,'p','p',''),))
def arts(): return tuple(FeatureArtifact(date(2026,1,1)+timedelta(days=i),'65-test',('f1','f2'),{'f1':float(i),'f2':float(i%3)},(),fid(),'VALID','CLEAN') for i in range(12))
def ds():
 a=arts(); return build_retraining_dataset_report('ds65',dec(),a,{x.target_date:i%2 for i,x in enumerate(a)},'data65')
def rr(): return build_automated_retraining_report('run65',ds())
def vr(**kw): return build_post_retraining_validation_report('v65',rr(),ds(),**kw)
def test_01(): assert POST_RETRAINING_VALIDATION_VERSION=='65.0.0'
def test_02(): assert validate_post_retraining_validation_config(PostRetrainingValidationConfig()) is None
def test_03(): assert vr().status==VALID
def test_04(): assert validate_post_retraining_validation_report(vr()).is_valid
def test_05(): assert vr().dataset_identity==ds().report_identity
def test_06(): assert vr().retraining_report_identity==rr().report_identity
def test_07(): assert vr().model_identity==rr().model_identity
def test_08(): assert vr().artifact_identity==rr().artifact.artifact_identity
def test_09(): assert len(vr().passed_checks)>0
def test_10(): assert len(vr().failed_checks)==0
def test_11(): assert vr().train_accuracy==rr().train_metrics.accuracy
def test_12(): assert vr().validation_accuracy==rr().validation_metrics.accuracy
def test_13(): assert vr().test_accuracy==rr().test_metrics.accuracy
def test_14(): assert vr().train_f1==rr().train_metrics.f1
def test_15(): assert vr().validation_f1==rr().validation_metrics.f1
def test_16(): assert vr().test_f1==rr().test_metrics.f1
def test_17(): assert vr().train_log_loss==rr().train_metrics.log_loss
def test_18(): assert vr().validation_log_loss==rr().validation_metrics.log_loss
def test_19(): assert vr().test_log_loss==rr().test_metrics.log_loss
def test_20(): assert post_retraining_validation_summary(vr())['status']==VALID
def test_21(): assert len(post_retraining_validation_checks(vr()))==len(vr().passed_checks)
def test_22(): assert post_retraining_validation_failures(vr())==()
def test_23(): assert vr().report_identity.startswith('post-retraining-validation-report-')
def test_24(): assert vr().report_identity==vr().report_identity
def test_25():
 with pytest.raises(ValueError): build_post_retraining_validation_report('',rr(),ds())
def test_26():
 with pytest.raises(ValueError): build_post_retraining_validation_report('x',object(),ds())
def test_27():
 with pytest.raises(TypeError): build_post_retraining_validation_report('x',rr(),ds(),config=object())
def test_28():
 with pytest.raises(ValueError): build_post_retraining_validation_report('x',rr(),ds(),config=PostRetrainingValidationConfig(minimum_accuracy=1.1))
def test_29():
 with pytest.raises(ValueError): build_post_retraining_validation_report('x',rr(),ds(),config=PostRetrainingValidationConfig(minimum_f1=-.1))
def test_30():
 with pytest.raises(ValueError): build_post_retraining_validation_report('x',rr(),ds(),config=PostRetrainingValidationConfig(maximum_log_loss=-1))
def test_31(): assert vr(config=PostRetrainingValidationConfig(minimum_accuracy=0)).status==VALID
def test_32():
 assert vr(config=PostRetrainingValidationConfig(minimum_accuracy=1)).status==INVALID
def test_33():
 assert vr(config=PostRetrainingValidationConfig(minimum_f1=1)).status==INVALID
def test_34():
 assert vr(config=PostRetrainingValidationConfig(maximum_log_loss=0)).status==INVALID
def test_35(): assert vr(config=PostRetrainingValidationConfig(require_persistence=False)).status==VALID
def test_36(): assert vr(persistence_path='D:/NeuroLytics/tests/nonexistent65.joblib').status==INVALID
def test_37(): assert vr(config=PostRetrainingValidationConfig(require_persistence=True)).status==INVALID
def test_38():
 r=vr(); bad=type(r)('bad',r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks,r.passed_checks,r.failed_checks,r.train_accuracy,r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_39():
 r=vr(); bad=type(r)(r.version,r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks,r.passed_checks,r.failed_checks,r.train_accuracy,r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,'bad'); assert not validate_post_retraining_validation_report(bad).is_valid
def test_40():
 r=vr(); bad=type(r)(r.version,r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks,r.passed_checks,r.passed_checks,r.train_accuracy,r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_41():
 r=vr(); c=ValidationCheck('X','BAD','x'); bad=type(r)(r.version,r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks+(c,),r.passed_checks+('X',),r.failed_checks,r.train_accuracy,r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_42():
 r=vr(); c=ValidationCheck('X',PASS,'x'); bad=type(r)(r.version,r.validation_id,VALID,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks+(c,),r.passed_checks,r.failed_checks,r.train_accuracy,r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_43():
 r=vr(); bad=type(r)(r.version,r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks,r.passed_checks,r.failed_checks,r.train_accuracy,2,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_44():
 r=vr(); bad=type(r)(r.version,r.validation_id,r.status,r.dataset_identity,r.retraining_report_identity,r.model_identity,r.artifact_identity,r.checks,r.passed_checks,r.failed_checks,float('nan'),r.validation_accuracy,r.test_accuracy,r.train_f1,r.validation_f1,r.test_f1,r.train_log_loss,r.validation_log_loss,r.test_log_loss,r.report_identity); assert not validate_post_retraining_validation_report(bad).is_valid
def test_45(): assert 'DATASET_LINEAGE' in post_retraining_validation_checks(vr())[0].check_id
def test_46(): assert any(c.check_id=='MODEL_ARTIFACT_LINEAGE' and c.status==PASS for c in vr().checks)
def test_47(): assert any(c.check_id=='FEATURE_VERSION_LINEAGE' for c in vr().checks)
def test_48(): assert any(c.check_id=='FEATURE_NAME_LINEAGE' for c in vr().checks)
def test_49(): assert any(c.check_id=='TRAIN_ROWS' for c in vr().checks)
def test_50(): assert any(c.check_id=='VALIDATION_ROWS' for c in vr().checks)
def test_51(): assert any(c.check_id=='TEST_ROWS' for c in vr().checks)
def test_52(): assert any(c.check_id=='MODEL_CLASSES' for c in vr().checks)
def test_53(): assert any(c.check_id=='TRAIN_METRIC_BOUNDS' for c in vr().checks)
def test_54(): assert any(c.check_id=='VALIDATION_METRIC_BOUNDS' for c in vr().checks)
def test_55(): assert any(c.check_id=='TEST_METRIC_BOUNDS' for c in vr().checks)
def test_56(): assert any(c.check_id=='VALIDATION_REQUIRED' for c in vr().checks)
def test_57(): assert any(c.check_id=='TEST_REQUIRED' for c in vr().checks)
def test_58(): assert post_retraining_validation_summary(vr())['failed_checks']==0
def test_59(): assert post_retraining_validation_summary(vr())['passed_checks']==len(vr().checks)
def test_60(): assert vr().version=='65.0.0'
def test_61(): assert vr().validation_id=='v65'
def test_62(): assert vr().status==VALID
def test_63(): assert validate_post_retraining_validation_report(vr()).issues==()
def test_64(): assert post_retraining_validation_summary(vr())['artifact_identity'].startswith('retrained-artifact-')
def test_65(): assert post_retraining_validation_summary(vr())['model_identity'].startswith('model-version-')
def test_66(): assert len(post_retraining_validation_checks(vr()))>=15
def test_67(): assert vr(config=PostRetrainingValidationConfig(minimum_accuracy=0.0,minimum_f1=0.0)).status==VALID
def test_68(): assert vr(config=PostRetrainingValidationConfig(require_validation=True,require_test=True)).status==VALID
def test_69(): assert vr(config=PostRetrainingValidationConfig(require_validation=False,require_test=False)).status==VALID
def test_70(): assert vr().report_identity==build_post_retraining_validation_report('v65',rr(),ds()).report_identity
