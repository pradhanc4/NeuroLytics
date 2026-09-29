from datetime import date
from pathlib import Path
import joblib
import pytest
from sklearn.ensemble import GradientBoostingClassifier
from analytics.gradient_boosting import *

def dataset():
    return build_gradient_boosting_dataset(
        ("f1", "f2"), "v1", "ds1", "col1",
        tuple(date(2026, 1, d) for d in range(1, 11)),
        ((0.,0.),(0.,1.),(1.,0.),(1.,1.),(2.,0.),(2.,1.),(3.,0.),(3.,1.),(4.,0.),(4.,1.)),
        (0,1,0,1,2,2,2,0,1,2),
    )

def test_default_config():
    c=GradientBoostingConfig(); validate_gradient_boosting_config(c)
    assert c.n_estimators==100 and c.learning_rate==0.1 and c.max_depth==3

@pytest.mark.parametrize("criterion", ["friedman_mse","squared_error","absolute_error","huber"])
def test_supported_criteria(criterion):
    validate_gradient_boosting_config(GradientBoostingConfig(criterion=criterion))

def test_config_validation():
    for c in [GradientBoostingConfig(n_estimators=0),GradientBoostingConfig(learning_rate=0),
              GradientBoostingConfig(max_depth=0),GradientBoostingConfig(min_samples_split=1),
              GradientBoostingConfig(min_samples_leaf=0),GradientBoostingConfig(subsample=0),
              GradientBoostingConfig(subsample=1.5),GradientBoostingConfig(max_features=0),
              GradientBoostingConfig(max_features=1.5),GradientBoostingConfig(max_features="bad"),
              GradientBoostingConfig(n_iter_no_change=0),GradientBoostingConfig(validation_fraction=0),
              GradientBoostingConfig(tol=-1)]:
        with pytest.raises(ValueError): validate_gradient_boosting_config(c)

def test_dataset_zero_and_split():
    ds=dataset(); assert ds.X[0]==(0.,0.) and ds.y[0]==0
    sd,tr,va=split_gradient_boosting_dataset_temporally(ds,date(2026,1,6))
    assert sd==date(2026,1,6) and len(tr.y)==6 and len(va.y)==4

def test_duplicate_dates():
    with pytest.raises(ValueError):
        build_gradient_boosting_dataset(("f1",),"v","d","y",
            (date(2026,1,1),date(2026,1,1)),((0.,),(1.,)),(0,1))

def test_factory_training():
    m=build_gradient_boosting(GradientBoostingConfig(n_estimators=10))
    assert isinstance(m,GradientBoostingClassifier) and not hasattr(m,"classes_")
    m=train_gradient_boosting(dataset(),GradientBoostingConfig(n_estimators=25))
    assert len(m.estimators_)==25 and len(m.classes_)>=2

def test_predictions_probabilities():
    ds=dataset(); m=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=10))
    p=predict_classes(m,ds.X); q=predict_probabilities(m,ds.X)
    assert len(p)==len(ds.y) and len(q)==len(ds.y)
    assert all(abs(sum(row)-1)<1e-9 for row in q)

def test_evaluation():
    ds=dataset(); x=evaluate_gradient_boosting(train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=10)),ds)
    assert 0<=x.accuracy<=1 and 0<=x.f1<=1 and x.log_loss>=0 and x.confusion_matrix

def test_importance():
    ds=dataset(); m=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=10))
    r=get_feature_importances(m,ds.feature_names)
    assert r.feature_names==ds.feature_names and sum(r.importances)==pytest.approx(1)

def test_position_models():
    ds=dataset(); ms=build_position_models({"col2":ds,"col1":ds},GradientBoostingConfig(n_estimators=5))
    assert tuple(n for n,_ in ms.models)==("col1","col2")
    assert isinstance(get_position_model(ms,"col1"),GradientBoostingClassifier)
    with pytest.raises(ValueError): get_position_model(ms,"missing")

def test_empty_positions():
    with pytest.raises(ValueError): build_position_models({})

def test_baseline():
    ds=dataset(); met=evaluate_gradient_boosting(train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=5)),ds)
    r=compare_with_baseline(met,1); assert r.difference==pytest.approx(met.log_loss-1)
    with pytest.raises(ValueError): compare_with_baseline(met,-1)
def test_artifact_reproducibility():
    ds=dataset(); c=GradientBoostingConfig(n_estimators=10,random_state=7)
    a=build_gradient_boosting_artifact(train_gradient_boosting(ds,c),ds,c)
    b=build_gradient_boosting_artifact(train_gradient_boosting(ds,c),ds,c)
    assert a.model_version==GRADIENT_BOOSTING_VERSION
    assert a.artifact_identity.startswith("gradient-boosting-")
    assert reproduce_gradient_boosting_artifact(a,b).identical

def test_artifact_changes():
    ds=dataset(); a=GradientBoostingConfig(n_estimators=5); b=GradientBoostingConfig(n_estimators=10)
    x=build_gradient_boosting_artifact(train_gradient_boosting(ds,a),ds,a)
    y=build_gradient_boosting_artifact(train_gradient_boosting(ds,b),ds,b)
    assert x.artifact_identity!=y.artifact_identity

def test_validation():
    ds=dataset(); c=GradientBoostingConfig(n_estimators=5); m=train_gradient_boosting(ds,c)
    assert validate_gradient_boosting_model(m,ds).status==VALID
    assert validate_gradient_boosting_pipeline(ds,c,m).is_valid
    assert validate_gradient_boosting_model("bad",ds).status==INVALID

def test_unfitted_validation():
    ds=dataset(); c=GradientBoostingConfig(n_estimators=5)
    r=validate_gradient_boosting_pipeline(ds,c,build_gradient_boosting(c))
    assert r.status==INVALID and "MODEL_NOT_FITTED" in r.issues

def test_classes_and_persistence(tmp_path: Path):
    ds=dataset(); m=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=5))
    assert get_model_classes(m)==tuple(int(v) for v in m.classes_)
    path=save_gradient_boosting_model(m,tmp_path/"model.joblib")
    loaded=load_gradient_boosting_model(path)
    assert predict_classes(loaded,ds.X)==predict_classes(m,ds.X)

def test_bad_persistence(tmp_path: Path):
    p=tmp_path/"bad.joblib"; joblib.dump({"bad":1},p)
    with pytest.raises(TypeError): load_gradient_boosting_model(p)

def test_boosting_controls():
    c=GradientBoostingConfig(n_estimators=10,learning_rate=.05,max_depth=2,min_samples_leaf=2,subsample=.8)
    m=train_gradient_boosting(dataset(),c)
    assert m.learning_rate==.05 and m.max_depth==2 and m.subsample==.8

def test_early_stopping():
    c=GradientBoostingConfig(n_estimators=10,n_iter_no_change=3,validation_fraction=.5)
    m=train_gradient_boosting(dataset(),c)
    assert m.n_iter_no_change==3 and m.validation_fraction==.5

def test_importance_width():
    ds=dataset(); m=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=5))
    with pytest.raises(ValueError): get_feature_importances(m,("one",))

def test_invalid_target():
    with pytest.raises(ValueError):
        build_gradient_boosting_dataset(("f1",),"v","d","y",(date(2026,1,1),),((1.,),),(True,))

def test_prediction_width():
    m=train_gradient_boosting(dataset(),GradientBoostingConfig(n_estimators=5))
    with pytest.raises(ValueError): predict_classes(m,((1.,),))

def test_determinism():
    ds=dataset(); c=GradientBoostingConfig(n_estimators=10,random_state=7)
    assert predict_classes(train_gradient_boosting(ds,c),ds.X)==predict_classes(train_gradient_boosting(ds,c),ds.X)

def test_random_state():
    ds=dataset()
    a=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=5,random_state=1))
    b=train_gradient_boosting(ds,GradientBoostingConfig(n_estimators=5,random_state=2))
    assert a.random_state!=b.random_state

def test_unfitted_classes():
    with pytest.raises(ValueError): get_model_classes(build_gradient_boosting(GradientBoostingConfig(n_estimators=5)))

def test_dataset_width():
    with pytest.raises(ValueError):
        build_gradient_boosting_dataset(("f1","f2"),"v","d","y",(date(2026,1,1),),((1.,),),(0,))

def test_model_kind():
    ds=dataset(); c=GradientBoostingConfig(n_estimators=5)
    a=build_gradient_boosting_artifact(train_gradient_boosting(ds,c),ds,c)
    assert a.model_kind=="gradient_boosting"

def test_probability_range():
    m=train_gradient_boosting(dataset(),GradientBoostingConfig(n_estimators=5))
    assert all(0<=v<=1 for row in predict_probabilities(m,dataset().X) for v in row)

def test_importance_sum():
    m=train_gradient_boosting(dataset(),GradientBoostingConfig(n_estimators=5))
    assert sum(get_feature_importances(m,("f1","f2")).importances)==pytest.approx(1)

def test_factory_from_config():
    c=GradientBoostingConfig(n_estimators=7)
    assert build_gradient_boosting(c).n_estimators==7

def test_invalid_config_type():
    with pytest.raises(TypeError): validate_gradient_boosting_config("bad")

def test_dataset_type():
    with pytest.raises(TypeError): validate_gradient_boosting_dataset("bad")
