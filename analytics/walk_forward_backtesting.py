from __future__ import annotations
import hashlib, json, math
from dataclasses import dataclass
from typing import Callable, Sequence
from analytics.advanced_ensemble import SequenceConsensusResult, validate_consensus

SEQUENCE_BACKTEST_VERSION = "39.0.0"
VALID, INVALID = "VALID", "INVALID"
DIGITS = tuple(range(10))

@dataclass(frozen=True)
class WalkForwardFold:
    fold_index:int; train_end:int; test_start:int; test_end:int
    train_observations:int; test_observations:int
    train_identity:str; test_identity:str; fold_identity:str

@dataclass(frozen=True)
class BacktestFoldResult:
    fold:WalkForwardFold; probabilities:tuple[tuple[float,...],...]; targets:tuple[int,...]
    log_loss:float; accuracy:float; top_k_accuracy:float; brier_score:float
    probability_margin:float; agreement_score:float; consensus_identity:str; result_identity:str

@dataclass(frozen=True)
class WalkForwardBacktestReport:
    version:str; dataset_identity:str; initial_train_size:int; test_size:int; step_size:int
    folds:tuple[WalkForwardFold,...]; results:tuple[BacktestFoldResult,...]; observations:int
    aggregate_log_loss:float; aggregate_accuracy:float; aggregate_top_k_accuracy:float
    aggregate_brier_score:float; mean_probability_margin:float; mean_agreement_score:float
    report_identity:str

@dataclass(frozen=True)
class ConsensusBacktestResult:
    consensus_identity:str; dataset_identity:str; observations:int
    log_loss:float; accuracy:float; top_k_accuracy:float; brier_score:float
    mean_probability_margin:float; agreement_score:float
    target_sequence:tuple[int,...]; result_identity:str

@dataclass(frozen=True)
class ConsensusEvaluationReport:
    version:str; dataset_identity:str
    consensus_results:tuple[ConsensusBacktestResult,...]
    aggregate_log_loss:float; aggregate_accuracy:float; aggregate_top_k_accuracy:float
    aggregate_brier_score:float; mean_probability_margin:float; mean_agreement_score:float
    report_identity:str

@dataclass(frozen=True)
class BacktestValidationResult:
    status:str; issues:tuple[str,...]
    @property
    def is_valid(self)->bool: return self.status == VALID

def _id(prefix,payload):
    return prefix+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _digits(values,name):
    x=tuple(values)
    if not x or any(isinstance(v,bool) or not isinstance(v,int) or v<0 or v>9 for v in x):
        raise ValueError(f"{name} must contain non-empty digits 0-9.")
    return x

def _row(row):
    x=tuple(float(v) for v in row)
    if len(x)!=10 or any(not math.isfinite(v) or v<0 for v in x) or abs(sum(x)-1)>1e-6:
        raise ValueError("probability rows must contain ten finite non-negative values summing to one.")
    return x

def _rows(rows):
    x=tuple(_row(r) for r in rows)
    if not x: raise ValueError("probability rows must not be empty.")
    return x

def _metrics(p,t,k):
    if len(p)!=len(t) or not p: raise ValueError("probability/target lengths must match.")
    ll=-sum(math.log(max(r[y],1e-15)) for r,y in zip(p,t))/len(t)
    acc=sum(max(DIGITS,key=lambda d:(r[d],-d))==y for r,y in zip(p,t))/len(t)
    top=sum(y in sorted(DIGITS,key=lambda d:(-r[d],d))[:k] for r,y in zip(p,t))/len(t)
    brier=sum(sum((r[d]-(d==y))**2 for d in DIGITS) for r,y in zip(p,t))/len(t)
    margins=[]
    for r in p:
        z=sorted(DIGITS,key=lambda d:(-r[d],d)); margins.append(r[z[0]]-r[z[1]])
    return ll,acc,top,brier,sum(margins)/len(margins)

def build_walk_forward_folds(observations,initial_train_size,test_size=1,step_size=1,dataset_identity="dataset"):
    if not isinstance(observations,int) or observations<=1: raise ValueError("observations must be > 1.")
    for n,v in (("initial_train_size",initial_train_size),("test_size",test_size),("step_size",step_size)):
        if not isinstance(v,int) or isinstance(v,bool) or v<=0: raise ValueError(f"{n} must be positive.")
    if initial_train_size>=observations: raise ValueError("initial_train_size must leave test observations.")
    out=[]; end=initial_train_size; i=0
    while end<observations:
        ts,te=end,min(end+test_size,observations)
        train_id=_id("walk-forward-train-",(dataset_identity,0,end))
        test_id=_id("walk-forward-test-",(dataset_identity,ts,te))
        fold_id=_id("walk-forward-fold-",(SEQUENCE_BACKTEST_VERSION,i,train_id,test_id))
        out.append(WalkForwardFold(i,end,ts,te,end,te-ts,train_id,test_id,fold_id))
        i+=1; end+=step_size
    return tuple(out)

def build_walk_forward_backtest(sequences:Sequence[int],predictor:Callable,dataset_identity:str,
                                initial_train_size:int,test_size:int=1,step_size:int=1,top_k:int=3):
    target=_digits(sequences,"sequences")
    if not callable(predictor): raise TypeError("predictor must be callable.")
    if not 1<=top_k<=10: raise ValueError("top_k must be 1..10.")
    folds=build_walk_forward_folds(len(target),initial_train_size,test_size,step_size,dataset_identity)
    results=[]
    for f in folds:
        train=target[:f.train_end]; test=target[f.test_start:f.test_end]
        p=_rows(predictor(train,test))
        if len(p)!=len(test): raise ValueError("predictor must return one row per test observation.")
        ll,acc,top,brier,margin=_metrics(p,test,top_k)
        rid=_id("backtest-fold-result-",(f.fold_identity,p,test))
        results.append(BacktestFoldResult(f,p,test,ll,acc,top,brier,margin,1.0,"",rid))
    if not results: raise ValueError("no walk-forward folds produced.")
    p=tuple(r for x in results for r in x.probabilities); t=tuple(y for x in results for y in x.targets)
    ll,acc,top,brier,margin=_metrics(p,t,top_k)
    rid=_id("walk-forward-report-",(SEQUENCE_BACKTEST_VERSION,dataset_identity,initial_train_size,test_size,step_size,
                                    tuple(x.result_identity for x in results)))
    return WalkForwardBacktestReport(SEQUENCE_BACKTEST_VERSION,dataset_identity,initial_train_size,test_size,step_size,
        folds,tuple(results),len(t),ll,acc,top,brier,margin,1.0,rid)

def evaluate_consensus(consensus:SequenceConsensusResult,top_k:int=3):
    v=validate_consensus(consensus)
    if not v.is_valid: raise ValueError("invalid consensus: "+",".join(v.issues))
    if not 1<=top_k<=10: raise ValueError("top_k must be 1..10.")
    p=_rows(consensus.probabilities); t=_digits(consensus.targets,"consensus.targets")
    ll,acc,top,brier,margin=_metrics(p,t,top_k)
    rid=_id("consensus-backtest-result-",(consensus.consensus_identity,top_k,p,t))
    return ConsensusBacktestResult(consensus.consensus_identity,consensus.dataset_identity,len(t),ll,acc,top,brier,margin,
                                   consensus.agreement_score,t,rid)

def evaluate_consensus_backtests(consensuses,top_k=3):
    rows=tuple(consensuses)
    if not rows: raise ValueError("at least one consensus result is required.")
    results=tuple(evaluate_consensus(x,top_k) for x in rows)
    ds=results[0].dataset_identity
    if any(x.dataset_identity!=ds for x in results): raise ValueError("all consensus results must share dataset identity.")
    if len({x.consensus_identity for x in results})!=len(results): raise ValueError("consensus identities must be unique.")
    p=tuple(r for c in rows for r in c.probabilities); t=tuple(y for x in results for y in x.target_sequence)
    ll,acc,top,brier,margin=_metrics(p,t,top_k)
    rid=_id("consensus-evaluation-report-",(SEQUENCE_BACKTEST_VERSION,ds,tuple(x.result_identity for x in results)))
    return ConsensusEvaluationReport(SEQUENCE_BACKTEST_VERSION,ds,results,ll,acc,top,brier,margin,
                                     sum(x.agreement_score for x in results)/len(results),rid)

def validate_walk_forward_report(report):
    if not isinstance(report,WalkForwardBacktestReport): return BacktestValidationResult(INVALID,("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version!=SEQUENCE_BACKTEST_VERSION: issues.append("INVALID_VERSION")
    if not report.dataset_identity: issues.append("MISSING_DATASET_IDENTITY")
    if len(report.folds)!=len(report.results) or not report.folds: issues.append("FOLD_RESULT_LENGTH_MISMATCH")
    prev=-1
    for f,r in zip(report.folds,report.results):
        if f.train_end!=f.test_start: issues.append("TRAIN_TEST_BOUNDARY_VIOLATION")
        if f.test_end<=f.test_start: issues.append("EMPTY_TEST_WINDOW")
        if f.test_start<prev: issues.append("OVERLAPPING_TEST_WINDOWS")
        prev=f.test_end
        try:
            p=_rows(r.probabilities); t=_digits(r.targets,"result.targets")
            if len(p)!=len(t): issues.append("PROBABILITY_TARGET_MISMATCH")
        except ValueError: issues.append("INVALID_FOLD_PROBABILITIES")
        if r.fold!=f: issues.append("FOLD_LINEAGE_MISMATCH")
        if not r.result_identity.startswith("backtest-fold-result-"): issues.append("INVALID_RESULT_IDENTITY")
    if report.observations!=sum(x.fold.test_observations for x in report.results): issues.append("OBSERVATION_COUNT_MISMATCH")
    if not report.report_identity.startswith("walk-forward-report-"): issues.append("INVALID_REPORT_IDENTITY")
    return BacktestValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

def validate_consensus_evaluation_report(report):
    if not isinstance(report,ConsensusEvaluationReport): return BacktestValidationResult(INVALID,("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version!=SEQUENCE_BACKTEST_VERSION: issues.append("INVALID_VERSION")
    if not report.dataset_identity: issues.append("MISSING_DATASET_IDENTITY")
    if not report.consensus_results: issues.append("EMPTY_RESULTS")
    ids=[x.consensus_identity for x in report.consensus_results]
    if len(set(ids))!=len(ids): issues.append("DUPLICATE_CONSENSUS_IDENTITIES")
    if any(x.dataset_identity!=report.dataset_identity for x in report.consensus_results): issues.append("DATASET_IDENTITY_MISMATCH")
    if not report.report_identity.startswith("consensus-evaluation-report-"): issues.append("INVALID_REPORT_IDENTITY")
    for x in report.consensus_results:
        if x.observations<=0 or len(x.target_sequence)!=x.observations: issues.append("INVALID_OBSERVATIONS")
    return BacktestValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

def walk_forward_summary(report):
    return f"Walk-forward evaluated {report.observations} observations across {len(report.folds)} expanding-window folds; log loss {report.aggregate_log_loss:.6f}, accuracy {report.aggregate_accuracy:.6f}, Top-K accuracy {report.aggregate_top_k_accuracy:.6f}."

def consensus_evaluation_summary(report):
    return f"Consensus backtesting evaluated {len(report.consensus_results)} result sets; log loss {report.aggregate_log_loss:.6f}, accuracy {report.aggregate_accuracy:.6f}, mean agreement {report.mean_agreement_score:.6f}."

__all__=["SEQUENCE_BACKTEST_VERSION","VALID","INVALID","WalkForwardFold","BacktestFoldResult","WalkForwardBacktestReport",
"ConsensusBacktestResult","ConsensusEvaluationReport","BacktestValidationResult","build_walk_forward_folds",
"build_walk_forward_backtest","evaluate_consensus","evaluate_consensus_backtests","validate_walk_forward_report",
"validate_consensus_evaluation_report","walk_forward_summary","consensus_evaluation_summary"]
