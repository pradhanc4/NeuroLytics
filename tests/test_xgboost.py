from datetime import date
from pathlib import Path
import joblib
import pytest
from xgboost import XGBClassifier
from analytics.xgboost import *

def dataset():
    return build_xgboost_dataset(("f1","f2"),"v1","ds1","col1",tuple(date(2026,1,d) for d in range(1,11)),((0.,0.),(0.,1.),(1.,0.),(1.,1.),(2.,0.),(2.,1.),(3.,0.),(3.,1.),(4.,0.),(4.,1.)),(0,1,0,1,2,2,2,0,1,2))

def bootstrap_dataset():
    return build_xgboost_dataset(("f1","f2"),"v1","ds-bootstrap","col1",tuple(date(2026,1,d) for d in range(1,21)),tuple((float(i%5),float((i//5)%2)) for i in range(20)),tuple(i%3 for i in range(20)))

def test_default_config():
    c=XGBoostConfig(); validate_xgboost_config(c); assert c.n_estimators==100 and c.max_depth==6 and c.tree_method=="hist"

@pytest.mark.parametrize("objective",["auto","binary:logistic","multi:softprob","multi:softmax"])
def test_supported_objectives(objective): validate_xgboost_config(XGBoostConfig(objective=objective))

def test_config_validation():
    invalid=[XGBoostConfig(n_estimators=0),XGBoostConfig(max_depth=-1),XGBoostConfig(learning_rate=0),XGBoostConfig(min_child_weight=-1),XGBoostConfig(subsample=0),XGBoostConfig(colsample_bytree=1.5),XGBoostConfig(gamma=-1),XGBoostConfig(reg_alpha=-1),XGBoostConfig(reg_lambda=-1),XGBoostConfig(objective="bad"),XGBoostConfig(eval_metric=""),XGBoostConfig(early_stopping_rounds=0),XGBoostConfig(n_jobs=0),XGBoostConfig(tree_method="bad")]
    for c in invalid:
        with pytest.raises(ValueError): validate_xgboost_config(c)

def test_dataset_zero_and_split():
    ds=dataset(); assert ds.X[0]==(0.,0.) and ds.y[0]==0
    split=split_xgboost_dataset_temporally(ds,date(2026,1,6)); assert len(split.train.y)==6 and len(split.validation.y)==4

def test_duplicate_dates():
    with pytest.raises(ValueError): build_xgboost_dataset(("f1",),"v","d","y",(date(2026,1,1),date(2026,1,1)),((0.,),(1.,)),(0,1))

def test_factory_and_training():
    m=build_xgboost(XGBoostConfig(n_estimators=10)); assert isinstance(m,XGBClassifier) and not hasattr(m,"classes_")
    m=train_xgboost(dataset(),XGBoostConfig(n_estimators=20)); assert len(m.classes_)>=2

def test_binary_and_multiclass_probability_prediction():
    ds=dataset(); m=train_xgboost(ds,XGBoostConfig(n_estimators=15)); p=predict_classes(m,ds.X); q=predict_probabilities(m,ds.X)
    assert len(p)==len(ds.y) and len(q)==len(ds.y); assert all(abs(sum(row)-1)<1e-7 for row in q)

def test_evaluation():
    ds=dataset(); x=evaluate_xgboost(train_xgboost(ds,XGBoostConfig(n_estimators=10)),ds); assert 0<=x.accuracy<=1 and 0<=x.f1<=1 and x.log_loss>=0 and x.confusion_matrix

def test_importance():
    ds=dataset(); r=get_feature_importances(train_xgboost(ds,XGBoostConfig(n_estimators=10)),ds.feature_names); assert r.feature_names==ds.feature_names and len(r.importances)==2

def test_position_models():
    ds=dataset(); ms=build_position_models({"col2":ds,"col1":ds},XGBoostConfig(n_estimators=5)); assert tuple(n for n,_ in ms.models)==("col1","col2"); assert isinstance(get_position_model(ms,"col1"),XGBClassifier)
    with pytest.raises(ValueError): get_position_model(ms,"missing")

def test_empty_positions():
    with pytest.raises(ValueError): build_position_models({})

def test_baseline():
    ds=dataset(); met=evaluate_xgboost(train_xgboost(ds,XGBoostConfig(n_estimators=5)),ds); r=compare_with_baseline(met,1); assert r.difference==pytest.approx(met.log_loss-1)
    with pytest.raises(ValueError): compare_with_baseline(met,-1)

def test_artifact_reproducibility():
    ds=dataset(); c=XGBoostConfig(n_estimators=10,random_state=7); a=build_xgboost_artifact(train_xgboost(ds,c),ds,c); b=build_xgboost_artifact(train_xgboost(ds,c),ds,c)
    assert a.model_version==XGBOOST_VERSION and a.artifact_identity.startswith("xgboost-") and reproduce_xgboost_artifact(a,b).identical

def test_artifact_changes():
    ds=dataset(); a=XGBoostConfig(n_estimators=5); b=XGBoostConfig(n_estimators=10); x=build_xgboost_artifact(train_xgboost(ds,a),ds,a); y=build_xgboost_artifact(train_xgboost(ds,b),ds,b); assert x.artifact_identity!=y.artifact_identity

def test_validation():
    ds=dataset(); c=XGBoostConfig(n_estimators=5); m=train_xgboost(ds,c); assert validate_xgboost_model(m,ds).status==VALID and validate_xgboost_pipeline(ds,c,m).is_valid and validate_xgboost_model("bad",ds).status==INVALID

def test_unfitted_validation():
    ds=dataset(); c=XGBoostConfig(n_estimators=5); r=validate_xgboost_pipeline(ds,c,build_xgboost(c)); assert r.status==INVALID and "MODEL_NOT_FITTED" in r.issues

def test_classes_and_persistence(tmp_path:Path):
    ds=dataset(); m=train_xgboost(ds,XGBoostConfig(n_estimators=5)); assert get_model_classes(m)==tuple(int(v) for v in m.classes_); path=save_xgboost_model(m,tmp_path/"model.joblib"); loaded=load_xgboost_model(path); assert predict_classes(loaded,ds.X)==predict_classes(m,ds.X)

def test_bad_persistence(tmp_path:Path):
    p=tmp_path/"bad.joblib"; joblib.dump({"bad":1},p)
    with pytest.raises(TypeError): load_xgboost_model(p)

def test_boosting_controls():
    c=XGBoostConfig(n_estimators=10,learning_rate=.05,max_depth=2,min_child_weight=2,subsample=.8,colsample_bytree=.8,gamma=.1,reg_alpha=.1,reg_lambda=2); m=train_xgboost(dataset(),c); assert m.learning_rate==.05 and m.max_depth==2 and m.subsample==.8

def test_early_stopping():
    ds=bootstrap_dataset(); split=split_xgboost_dataset_temporally(ds,date(2026,1,12)); c=XGBoostConfig(n_estimators=30,early_stopping_rounds=3); m=train_xgboost(split.train,c,split.validation); assert m.early_stopping_rounds==3

def test_importance_width():
    ds=dataset(); m=train_xgboost(ds,XGBoostConfig(n_estimators=5));
    with pytest.raises(ValueError): get_feature_importances(m,("one",))

def test_invalid_target():
    with pytest.raises(ValueError): build_xgboost_dataset(("f1",),"v","d","y",(date(2026,1,1),),((1.,),),(True,))

def test_prediction_width():
    m=train_xgboost(dataset(),XGBoostConfig(n_estimators=5));
    with pytest.raises(ValueError): predict_classes(m,((1.,),))

def test_determinism():
    ds=dataset(); c=XGBoostConfig(n_estimators=10,random_state=7); assert predict_classes(train_xgboost(ds,c),ds.X)==predict_classes(train_xgboost(ds,c),ds.X)

def test_random_state():
    ds=dataset(); a=train_xgboost(ds,XGBoostConfig(n_estimators=5,random_state=1)); b=train_xgboost(ds,XGBoostConfig(n_estimators=5,random_state=2)); assert a.random_state!=b.random_state

def test_unfitted_classes():
    with pytest.raises(ValueError): get_model_classes(build_xgboost(XGBoostConfig(n_estimators=5)))

def test_dataset_width():
    with pytest.raises(ValueError): build_xgboost_dataset(("f1","f2"),"v","d","y",(date(2026,1,1),),((1.,),),(0,))

def test_model_kind():
    ds=dataset(); c=XGBoostConfig(n_estimators=5); a=build_xgboost_artifact(train_xgboost(ds,c),ds,c); assert a.model_kind=="xgboost"

def test_probability_range():
    m=train_xgboost(dataset(),XGBoostConfig(n_estimators=5)); assert all(0<=v<=1 for row in predict_probabilities(m,dataset().X) for v in row)

def test_factory_objective_auto():
    assert build_xgboost(XGBoostConfig(objective="auto")).objective=="binary:logistic"

def test_invalid_config_type():
    with pytest.raises(TypeError): validate_xgboost_config("bad")

def test_dataset_type():
    with pytest.raises(TypeError): validate_xgboost_dataset("bad")

def test_version_references():
    from features.versioning_contract import FeatureVersionReference,DatasetVersionReference
    ds=dataset(); fr=FeatureVersionReference(feature_version=ds.feature_version,identity="feature-id",algorithm="sha256"); dr=DatasetVersionReference(dataset_version="dataset-v1",identity=ds.dataset_identity,algorithm="sha256",feature_version=ds.feature_version,feature_identity="feature-id")
    validate_xgboost_version_references(fr,dr,ds)

def test_sequence_adapter_empty_rejected():
    from unittest.mock import Mock
    s=Mock(); s.samples=()
    with pytest.raises(TypeError): build_xgboost_dataset_from_sequence_dataset(s,"id")

def test_temporal_sequence_split_import_exists():
    assert callable(build_temporal_split_from_sequence_dataset)
