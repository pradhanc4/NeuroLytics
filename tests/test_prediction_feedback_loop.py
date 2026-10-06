from datetime import date
import pytest
from analytics.prediction_feedback_loop import *

def entry():
    return build_prediction_entry("p77", date(2026,10,1), "data-1", "feature-1",
        "model-1", "1.0", "ensemble-1", "rank-1", 3,
        (0.02,0.03,0.05,0.60,0.08,0.05,0.04,0.04,0.04,0.05), (3,8,9))

def comparison(gain=0.10):
    return ModelComparison(.50,.50+gain,.55,.56,.50,.51)

def test_version(): assert PREDICTION_FEEDBACK_VERSION=="76.1.0"
def test_entry(): assert entry().confidence==.60
def test_bad_probability_count():
    with pytest.raises(ValueError): build_prediction_entry("p",date.today(),"d","f","m","v","e","r",1,(1.0,),(1,))
def test_bad_probability_sum():
    with pytest.raises(ValueError): build_prediction_entry("p",date.today(),"d","f","m","v","e","r",1,(.11,)*10,(1,))
def test_prediction_must_be_top_k():
    with pytest.raises(ValueError): build_prediction_entry("p",date.today(),"d","f","m","v","e","r",1,(.1,)*10,(2,))
def test_correct_outcome():
    o=evaluate_prediction_entry(entry(),3); assert o.correct and o.top_k_hit and o.actual_rank==1
def test_miss_outcome():
    o=evaluate_prediction_entry(entry(),1); assert not o.correct and not o.top_k_hit and o.actual_rank==9
def test_data_error():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),1),data_valid=False); assert o.error_source=="data_quality"
def test_model_error():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),1),model_stable=False); assert o.error_source=="model"
def test_policy(): assert validate_feedback_policy(FeedbackPolicy()) is None
def test_good_prediction_holds():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),3)); assert assess_retraining(o).decision==HOLD
def test_miss_triggers_retrain():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),1)); assert assess_retraining(o,policy=FeedbackPolicy(maximum_miss_streak=1)).decision==RETRAIN
def test_candidate_promoted():
    assert compare_candidate(comparison(.10)).decision==PROMOTE

def test_candidate_small_gain_rejected():
    assert compare_candidate(comparison(.001)).decision==REJECT

def test_candidate_validation_rejected():
    c=ModelComparison(.50,.60,.55,.40,.50,.60)
    assert compare_candidate(c).decision==REJECT

def test_candidate_walk_forward_rejected():
    c=ModelComparison(.50,.60,.55,.60,.50,.40)
    assert compare_candidate(c).decision==REJECT

def test_cycle_correct():
    r=build_feedback_cycle("c1",entry(),3)
    assert r.assessment.decision==HOLD and r.promotion.decision==REJECT

def test_cycle_retrain_promotes():
    r=build_feedback_cycle("c2",entry(),1,
        policy=FeedbackPolicy(maximum_miss_streak=1),comparison=comparison(.10))
    assert r.assessment.decision==RETRAIN and r.promotion.decision==PROMOTE

def test_cycle_retrain_rejects():
    r=build_feedback_cycle("c3",entry(),1,
        policy=FeedbackPolicy(maximum_miss_streak=1),comparison=comparison(.001))
    assert r.promotion.decision==REJECT

def test_cycle_diagnostics():
    r=build_feedback_cycle("c4",entry(),1,
        policy=FeedbackPolicy(maximum_miss_streak=1),diagnostics={"model_stable":False})
    assert r.outcome.error_source=="model"

def test_cycle_validates():
    r=build_feedback_cycle("c5",entry(),3)
    v=validate_feedback_cycle(r)
    assert v.is_valid and v.issues==()

def test_cycle_summary():
    r=build_feedback_cycle("c6",entry(),1,policy=FeedbackPolicy(maximum_miss_streak=1))
    assert feedback_cycle_summary(r)["retraining_decision"]==RETRAIN

def test_error_breakdown():
    e=entry()
    a=classify_prediction_error(evaluate_prediction_entry(e,1),model_stable=False)
    b=classify_prediction_error(evaluate_prediction_entry(e,2),feature_stable=False)
    counts=feedback_error_breakdown((a,b))
    assert counts["model"]==1 and counts["feature"]==1
def test_identity_deterministic():
    a=build_feedback_cycle("same",entry(),3)
    b=build_feedback_cycle("same",entry(),3)
    assert a.report_identity==b.report_identity

def test_identity_changes_cycle():
    a=build_feedback_cycle("a",entry(),3)
    b=build_feedback_cycle("b",entry(),3)
    assert a.report_identity!=b.report_identity

def test_breakdown_rejects_bad_type():
    with pytest.raises(TypeError): feedback_error_breakdown((object(),))

def test_reciprocal_rank():
    assert evaluate_prediction_entry(entry(),1).reciprocal_rank==1/9

def test_prediction_error():
    assert evaluate_prediction_entry(entry(),1).prediction_error==2

def test_lineage():
    r=build_feedback_cycle("lineage",entry(),3)
    assert r.entry.model_identity=="model-1"
    assert r.entry.feature_identity=="feature-1"

def test_ensemble_lineage():
    r=build_feedback_cycle("lineage2",entry(),3)
    assert r.entry.ensemble_identity=="ensemble-1"
    assert r.entry.ranking_identity=="rank-1"

def test_walk_forward_gate_can_be_disabled():
    c=ModelComparison(.5,.7,.6,.7,.5,.5)
    p=FeedbackPolicy(require_walk_forward_improvement=False)
    assert compare_candidate(c,p).decision==PROMOTE

def test_validation_floor():
    c=ModelComparison(.5,.7,.55,.56,.5,.51)
    p=FeedbackPolicy(minimum_validation_accuracy=.95)
    assert compare_candidate(c,p).decision==REJECT

def test_current_miss_evidence():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),1))
    a=assess_retraining(o,policy=FeedbackPolicy(maximum_miss_streak=1))
    assert "CURRENT_PREDICTION_MISS" in a.evidence

def test_top_k_miss_evidence():
    o=classify_prediction_error(evaluate_prediction_entry(entry(),1))
    a=assess_retraining(o,policy=FeedbackPolicy(maximum_miss_streak=1))
    assert "CURRENT_TOP_K_MISS" in a.evidence
