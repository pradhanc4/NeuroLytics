from datetime import date
from pathlib import Path
import joblib
import pytest
from lightgbm import LGBMClassifier
from analytics.lightgbm import *

def dataset():
    return build_lightgbm_dataset(("f1","f2"),"v1","ds1","col1",tuple(date(2026,1,d) for d in range(1,11)),((0.,0.),(0.,1.),(1.,0.),(1.,1.),(2.,0.),(2.,1.),(3.,0.),(3.,1.),(4.,0.),(4.,1.)),(0,1,0,1,2,2,2,0,1,2))

def bootstrap_dataset():
    return build_lightgbm_dataset(("f1","f2"),"v1","ds-bootstrap","col1",tuple(date(2026,1,d) for d in range(1,21)),tuple((float(i%5),float((i//5)%2)) for i in range(20)),tuple(i%3 for i in range(20)))

def test_default_config():
    c=LightGBMConfig(); validate_lightgbm_config(c); assert c.n_estimators==100 and c.num_leaves==31

@pytest.mark.parametrize("objective",["auto","binary","multiclass"])
def test_supported_objectives(objective): validate_lightgbm_config(LightGBMConfig(objective=objective))

def test_config_validation():
    invalid=[LightGBMConfig(n_estimators=0),LightGBMConfig(num_leaves=1),LightGBMConfig(max_depth=0),LightGBMConfig(max_depth=-2),LightGBMConfig(learning_rate=0),LightGBMConfig(min_child_samples=0),LightGBMConfig(subsample=0),LightGBMConfig(colsample_bytree=1.5),LightGBMConfig(reg_alpha=-1),LightGBMConfig(reg_lambda=-1),LightGBMConfig(objective="bad"),LightGBMConfig(eval_metric=""),LightGBMConfig(early_stopping_rounds=0),LightGBMConfig(n_jobs=0)]
    for c in invalid:
        with pytest.raises(ValueError): validate_lightgbm_config(c)

def test_dataset_zero_and_split():
    ds=dataset(); assert ds.X[0]==(0.,0.) and ds.y[0]==0
    split=split_lightgbm_dataset_temporally(ds,date(2026,1,6)); assert len(split.train.y)==6 and len(split.validation.y)==4
def test_duplicate_dates_rejected():
    ds=dataset()
    with pytest.raises(ValueError): build_lightgbm_dataset(ds.feature_names,ds.feature_version,ds.dataset_identity,ds.target_name,(date(2026,1,1),)*10,ds.X,ds.y)

def test_factory_binary():
    model=build_lightgbm(LightGBMConfig(n_estimators=10),objective="binary"); assert isinstance(model,LGBMClassifier) and model.get_params()["objective"]=="binary"

def test_factory_multiclass():
    model=build_lightgbm(LightGBMConfig(n_estimators=10),objective="multiclass",num_classes=3); assert model.get_params()["objective"]=="multiclass"

def test_training_prediction_and_probability():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=20,min_child_samples=2))
    preds=predict_classes(model,ds.X); probs=predict_probabilities(model,ds.X)
    assert len(preds)==20 and len(probs)==20 and all(abs(sum(row)-1)<1e-9 for row in probs)

def test_multiclass_training():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=20,min_child_samples=2)); assert len(get_model_classes(model))==3

def test_evaluation():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=20,min_child_samples=2)); metrics=evaluate_lightgbm(model,ds)
    assert 0<=metrics.accuracy<=1 and len(metrics.confusion_matrix)==3 and metrics.log_loss>=0

def test_feature_importance():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); imp=get_feature_importances(model,ds.feature_names)
    assert imp.feature_names==ds.feature_names and len(imp.importances)==2

def test_position_models():
    ds=bootstrap_dataset(); models=build_position_models({"col1":ds,"col2":ds},LightGBMConfig(n_estimators=10,min_child_samples=2))
    assert tuple(n for n,_ in models.models)==("col1","col2"); assert get_position_model(models,"col2") is not None
def test_position_model_missing():
    ds=bootstrap_dataset(); models=build_position_models({"col1":ds},LightGBMConfig(n_estimators=10,min_child_samples=2))
    with pytest.raises(ValueError): get_position_model(models,"missing")

def test_baseline_comparison():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); metrics=evaluate_lightgbm(model,ds); result=compare_with_baseline(metrics,1.0)
    assert result.difference==pytest.approx(metrics.log_loss-1.0)

def test_artifact_identity_deterministic():
    ds=bootstrap_dataset(); config=LightGBMConfig(n_estimators=10,min_child_samples=2); model=train_lightgbm(ds,config); a=build_lightgbm_artifact(model,ds,config); b=build_lightgbm_artifact(model,ds,config)
    assert a.artifact_identity==b.artifact_identity and a.model_version=="26.0.0" and a.model_kind=="lightgbm"

def test_artifact_changes_with_config():
    ds=bootstrap_dataset(); c1=LightGBMConfig(n_estimators=10,min_child_samples=2); c2=LightGBMConfig(n_estimators=11,min_child_samples=2); m1=train_lightgbm(ds,c1); m2=train_lightgbm(ds,c2)
    assert build_lightgbm_artifact(m1,ds,c1).artifact_identity!=build_lightgbm_artifact(m2,ds,c2).artifact_identity

def test_model_validation():
    ds=bootstrap_dataset(); config=LightGBMConfig(n_estimators=10,min_child_samples=2); model=train_lightgbm(ds,config); result=validate_lightgbm_model(model,ds)
    assert result.is_valid and result.issues==()

def test_unfitted_model_validation():
    ds=bootstrap_dataset(); model=LGBMClassifier(n_estimators=10,verbosity=-1); result=validate_lightgbm_model(model,ds)
    assert not result.is_valid and "MODEL_NOT_FITTED" in result.issues

def test_pipeline_validation():
    ds=bootstrap_dataset(); config=LightGBMConfig(n_estimators=10,min_child_samples=2); model=train_lightgbm(ds,config); assert validate_lightgbm_pipeline(ds,config,model).is_valid

def test_pipeline_invalid_config():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); result=validate_lightgbm_pipeline(ds,LightGBMConfig(n_estimators=0),model); assert not result.is_valid
def test_version_references():
    ds=bootstrap_dataset(); feature_ref=FeatureVersionReference(feature_version="v1",identity="feature-1",algorithm="sha256"); dataset_ref=DatasetVersionReference(dataset_version="dsv1",identity="ds-bootstrap",algorithm="sha256",feature_version="v1",feature_identity="feature-1"); validate_lightgbm_version_references(feature_ref,dataset_ref,ds)

def test_version_reference_mismatch():
    ds=bootstrap_dataset()
    with pytest.raises(ValueError): validate_lightgbm_version_references(FeatureVersionReference(feature_version="wrong",identity="feature-1",algorithm="sha256"),DatasetVersionReference(dataset_version="dsv1",identity="ds-bootstrap",algorithm="sha256",feature_version="wrong",feature_identity="feature-1"),ds)

def test_persistence(tmp_path):
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); path=save_lightgbm_model(model,tmp_path/"model.joblib"); loaded=load_lightgbm_model(path)
    assert isinstance(loaded,LGBMClassifier); assert predict_classes(model,ds.X)==predict_classes(loaded,ds.X)

def test_load_wrong_artifact(tmp_path):
    path=tmp_path/"wrong.joblib"; joblib.dump({"not":"model"},path)
    with pytest.raises(TypeError): load_lightgbm_model(path)

def test_reproducibility():
    ds=bootstrap_dataset(); config=LightGBMConfig(n_estimators=10,min_child_samples=2,random_state=0); m1=train_lightgbm(ds,config); m2=train_lightgbm(ds,config)
    result=reproduce_lightgbm_artifact(build_lightgbm_artifact(m1,ds,config),build_lightgbm_artifact(m2,ds,config)); assert result.identical

def test_random_state_changes_artifact():
    ds=bootstrap_dataset(); c1=LightGBMConfig(n_estimators=10,min_child_samples=2,random_state=0); c2=LightGBMConfig(n_estimators=10,min_child_samples=2,random_state=7); m1=train_lightgbm(ds,c1); m2=train_lightgbm(ds,c2)
    assert build_lightgbm_artifact(m1,ds,c1).artifact_identity!=build_lightgbm_artifact(m2,ds,c2).artifact_identity
def test_early_stopping_requires_validation():
    ds=bootstrap_dataset()
    with pytest.raises(ValueError): train_lightgbm(ds,LightGBMConfig(n_estimators=20,min_child_samples=2,early_stopping_rounds=5))

def test_early_stopping_training():
    ds=bootstrap_dataset(); split=split_lightgbm_dataset_temporally(ds,date(2026,1,14)); config=LightGBMConfig(n_estimators=30,min_child_samples=2,early_stopping_rounds=5); model=train_lightgbm(split.train,config,split.validation)
    assert hasattr(model,"best_iteration_")

def test_validation_class_mismatch():
    ds=bootstrap_dataset(); bad=build_lightgbm_dataset(ds.feature_names,ds.feature_version,"bad","col1",tuple(date(2026,2,d) for d in range(1,6)),ds.X[:5],(0,1,0,1,9))
    with pytest.raises(ValueError): train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2),bad)

def test_temporal_split_empty_validation_allowed():
    ds=bootstrap_dataset(); split=split_lightgbm_dataset_temporally(ds,date(2026,1,20)); assert len(split.validation.y)==0

def test_temporal_split_requires_two_train_classes():
    ds=build_lightgbm_dataset(("f1",),"v1","one","col1",(date(2026,1,1),date(2026,1,2),date(2026,1,3)),((1.,),(2.,),(3.,)),(0,0,1))
    with pytest.raises(ValueError): split_lightgbm_dataset_temporally(ds,date(2026,1,1))

def test_empty_mapping_rejected():
    with pytest.raises(ValueError): build_position_models({})

def test_baseline_negative_rejected():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); metrics=evaluate_lightgbm(model,ds)
    with pytest.raises(ValueError): compare_with_baseline(metrics,-1)
def test_sequence_adapter_and_temporal_helper():
    ds=bootstrap_dataset()
    assert build_temporal_split_from_sequence_dataset is not None
    assert build_lightgbm_dataset_from_sequence_dataset is not None

def test_matrix_validation():
    with pytest.raises(ValueError): predict_classes(build_lightgbm(LightGBMConfig(n_estimators=5)),((1,), (1,2)))

def test_feature_width_mismatch():
    ds=bootstrap_dataset(); model=train_lightgbm(ds,LightGBMConfig(n_estimators=10,min_child_samples=2)); bad=build_lightgbm_dataset(("f1",),"v1","bad","col1",ds.dates,tuple((1.,) for _ in ds.dates),ds.y)
    result=validate_lightgbm_model(model,bad); assert not result.is_valid and "FEATURE_WIDTH_MISMATCH" in result.issues

def test_dataset_feature_name_duplicate():
    with pytest.raises(ValueError): build_lightgbm_dataset(("f1","f1"),"v1","dup","col1",(date(2026,1,1),date(2026,1,2)),((1.,2.),(2.,3.)),(0,1))

def test_dataset_chronology():
    with pytest.raises(ValueError): build_lightgbm_dataset(("f1",),"v1","order","col1",(date(2026,1,2),date(2026,1,1)),((1.,),(2.,)),(0,1))

def test_artifact_classes():
    ds=bootstrap_dataset(); c=LightGBMConfig(n_estimators=10,min_child_samples=2); m=train_lightgbm(ds,c); artifact=build_lightgbm_artifact(m,ds,c)
    assert artifact.classes==(0,1,2) and len(artifact.configuration)>0

def test_model_classes_unfitted():
    with pytest.raises(ValueError): get_model_classes(LGBMClassifier(n_estimators=5,verbosity=-1))

def test_invalid_model_type():
    ds=bootstrap_dataset(); result=validate_lightgbm_model(object(),ds); assert not result.is_valid and result.issues==("INVALID_MODEL_TYPE",)

def test_save_returns_path(tmp_path):
    ds=bootstrap_dataset(); m=train_lightgbm(ds,LightGBMConfig(n_estimators=5,min_child_samples=2)); p=save_lightgbm_model(m,tmp_path/"nested"/"m.joblib"); assert Path(p).exists()
