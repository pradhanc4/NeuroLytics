import pytest
from analytics.walk_forward_backtesting import (
    SEQUENCE_BACKTEST_VERSION, VALID, build_walk_forward_folds,
    build_walk_forward_backtest, evaluate_consensus, evaluate_consensus_backtests,
    validate_walk_forward_report, validate_consensus_evaluation_report,
    walk_forward_summary, consensus_evaluation_summary,
)
from analytics.sequence_ensemble import build_sequence_ensemble
from tests.test_sequence_ensemble import make_evaluations
from analytics.advanced_ensemble import build_consensus

def uniform(train,test):
    return tuple((0.1,)*10 for _ in test)

def frequency(train,test):
    counts=[1.0]*10
    for x in train: counts[x]+=1.0
    total=sum(counts)
    row=tuple(v/total for v in counts)
    return tuple(row for _ in test)

def make_consensus():
    ev=make_evaluations()
    return build_consensus((build_sequence_ensemble(ev,"equal_weight"),
                            build_sequence_ensemble(ev,"inverse_log_loss"),
                            build_sequence_ensemble(ev,"softmax_score")))

def test_version(): assert SEQUENCE_BACKTEST_VERSION=="39.0.0"
def test_folds_expand_without_lookahead():
    folds=build_walk_forward_folds(10,4,2,2,"ds")
    assert [(f.train_end,f.test_start,f.test_end) for f in folds]==[(4,4,6),(6,6,8),(8,8,10)]
    assert all(f.train_end==f.test_start for f in folds)
def test_folds_deterministic():
    assert build_walk_forward_folds(12,5,2,1,"x")==build_walk_forward_folds(12,5,2,1,"x")
def test_folds_reject_bad_initial():
    with pytest.raises(ValueError): build_walk_forward_folds(5,5)
def test_folds_reject_bad_step():
    with pytest.raises(ValueError): build_walk_forward_folds(5,2,1,0)
def test_backtest_builds():
    r=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    assert r.observations==6 and len(r.folds)==3
    assert r.aggregate_accuracy>=0
def test_backtest_frequency_predictor():
    r=build_walk_forward_backtest((0,0,0,1,1,2,2,2,3,3),frequency,"ds",4,1,1)
    assert 0<=r.aggregate_log_loss
def test_backtest_validation():
    r=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    assert validate_walk_forward_report(r).status==VALID
def test_backtest_deterministic():
    a=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    b=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    assert a.report_identity==b.report_identity
def test_backtest_zero_supported():
    r=build_walk_forward_backtest((0,1,0,2,0,3,0,4),frequency,"ds",3)
    assert all(0<=x<=1 for x in (r.aggregate_accuracy,r.aggregate_top_k_accuracy))
def test_predictor_length_rejected():
    with pytest.raises(ValueError):
        build_walk_forward_backtest(tuple(range(6)),lambda a,b: ((0.1,)*10,),"ds",3,2)
def test_predictor_probability_rejected():
    with pytest.raises(ValueError):
        build_walk_forward_backtest(tuple(range(6)),lambda a,b: ((0.2,)*10 for _ in b),"ds",3)
def test_top_k_validation():
    with pytest.raises(ValueError): build_walk_forward_backtest(tuple(range(6)),uniform,"ds",3,top_k=11)
def test_summary():
    r=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    assert "Walk-forward evaluated" in walk_forward_summary(r)
def test_consensus_evaluation():
    c=make_consensus(); r=evaluate_consensus(c)
    assert r.observations==c.observations and r.dataset_identity==c.dataset_identity
def test_consensus_validation_pipeline():
    c=make_consensus(); r=evaluate_consensus(c)
    assert r.result_identity.startswith("consensus-backtest-result-")
def test_consensus_backtests():
    c=make_consensus(); report=evaluate_consensus_backtests((c,))
    assert report.aggregate_log_loss>=0
    assert validate_consensus_evaluation_report(report).status==VALID
def test_consensus_multiple_unique():
    c=make_consensus()
    object.__setattr__(c,"consensus_identity",c.consensus_identity+"x")
    report=evaluate_consensus_backtests((make_consensus(),c))
    assert len(report.consensus_results)==2
def test_consensus_duplicate_rejected():
    c=make_consensus()
    with pytest.raises(ValueError): evaluate_consensus_backtests((c,c))
def test_consensus_summary():
    c=make_consensus(); report=evaluate_consensus_backtests((c,))
    assert "Consensus backtesting evaluated" in consensus_evaluation_summary(report)
def test_consensus_top_k_rejected():
    with pytest.raises(ValueError): evaluate_consensus(make_consensus(),11)
def test_consensus_invalid_rejected():
    c=make_consensus(); object.__setattr__(c,"agreement_score",2.0)
    with pytest.raises(ValueError): evaluate_consensus(c)
def test_report_identity_stable():
    c=make_consensus()
    assert evaluate_consensus_backtests((c,)).report_identity==evaluate_consensus_backtests((c,)).report_identity
def test_report_dataset_mismatch_detected():
    c=make_consensus(); report=evaluate_consensus_backtests((c,))
    object.__setattr__(report,"dataset_identity","other")
    assert validate_consensus_evaluation_report(report).status!=VALID
def test_backtest_lineage_detected():
    r=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    object.__setattr__(r.results[0],"fold",r.folds[1])
    assert validate_walk_forward_report(r).status!=VALID
def test_fold_identity_changes_with_dataset():
    assert build_walk_forward_folds(8,3,dataset_identity="a")[0].fold_identity != build_walk_forward_folds(8,3,dataset_identity="b")[0].fold_identity
def test_metrics_are_bounded():
    r=build_walk_forward_backtest(tuple(range(10)),uniform,"ds",4,2,2)
    assert 0<=r.aggregate_accuracy<=1 and 0<=r.aggregate_top_k_accuracy<=1 and r.aggregate_brier_score>=0
