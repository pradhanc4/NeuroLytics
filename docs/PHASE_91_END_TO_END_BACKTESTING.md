# Phase 91 — End-to-End Backtesting

## Objective

Validate the complete Phase 90 data-to-prediction pipeline against historical outcomes using chronological, leakage-safe walk-forward evaluation.

Phase 91 is an evaluation layer. It does not create a second ML stack, retrain production models automatically, or introduce MLOps/CI/CD/cloud infrastructure.

## Reused architecture

Phase 91 composes the existing contracts:

- Phase 39 walk-forward backtesting and temporal fold concepts.
- Phase 40–41 learning-to-rank outputs.
- Phase 42 panel ranking.
- Phase 43 Jodi ranking.
- Phase 44 Top-K selection and evaluation.
- Phase 45 actual-vs-ranked analysis.
- Phase 46 performance-over-time analysis.
- Phase 90 end-to-end prediction pipeline.
- Existing feature validation and leakage gates.

## Pipeline

Historical dates and actual outcomes
→ chronological expanding-window folds
→ training boundary strictly before target date
→ Phase 90 prediction callback
→ panel/Jodi actual outcome attachment
→ Top-K hit/miss evaluation
→ Actual-vs-Ranked metrics
→ Performance-over-Time metrics
→ deterministic report identity
→ validation and summary.

## Module

analytics/end_to_end_backtesting.py

Version: 91.0.0

## Public contracts

- BacktestFold
- BacktestActual
- EndToEndBacktestObservation
- EndToEndBacktestReport
- EndToEndBacktestValidationResult
- build_backtest_folds()
- run_end_to_end_backtest()
- validate_end_to_end_backtest()
- end_to_end_backtest_summary()

## Milestones

### 91.1 Existing backtesting inventory — COMPLETE
Reused the existing Phase 39 walk-forward implementation rather than replacing it.

### 91.2 Existing ranking inventory — COMPLETE
Reused Panel, Jodi, Top-K, Actual-vs-Ranked, and Performance-over-Time contracts.

### 91.3 Phase 90 integration boundary — COMPLETE
The backtester accepts EndToEndPredictionResult as the prediction artifact.

### 91.4 Chronological fold builder — COMPLETE
Builds expanding-window folds from ordered unique historical dates.

### 91.5 Training boundary contract — COMPLETE
Every fold requires train_end_date < target_date and train_end_index < target_index.

### 91.6 Target-date alignment — COMPLETE
The returned prediction must match the fold target date.

### 91.7 Historical actual contract — COMPLETE
Panel, Jodi, and optional eight-position actual digits can be carried with each fold.

### 91.8 Panel actual attachment — COMPLETE
Historical panel outcomes are attached only for evaluation after prediction generation.

### 91.9 Jodi actual attachment — COMPLETE
Historical Jodi outcomes are attached only for evaluation after prediction generation.

### 91.10 Top-K evaluation — COMPLETE
Panel and Jodi Top-K reports are generated for configurable K values.

### 91.11 Hit-rate measurement — COMPLETE
Hit@K is calculated through the existing Top-K framework.

### 91.12 Reciprocal-rank measurement — COMPLETE
MRR is inherited from the existing Top-K evaluation contract.

### 91.13 Actual-vs-Ranked composition — COMPLETE
Both panel and Jodi evaluations feed Phase 45 analysis.

### 91.14 Performance-over-Time composition — COMPLETE
Both panel and Jodi evaluations feed Phase 46 period/trend analysis.

### 91.15 Missing-actual handling — COMPLETE
Unknown historical actuals remain unavailable observations rather than fabricated hits.

### 91.16 Predictor contract — COMPLETE
The fold callback must return a validated EndToEndPredictionResult.

### 91.17 Deterministic observation identity — COMPLETE
Each fold receives a deterministic identity containing fold, pipeline, actuals, and K configuration.

### 91.18 Deterministic report identity — COMPLETE
The complete report identity is derived from observation and downstream report identities.

### 91.19 Temporal validation — COMPLETE
Validation rejects equal/reversed train-target boundaries and non-chronological targets.

### 91.20 Output summary — COMPLETE
A compact user-facing summary exposes panel/Jodi hit rates, MRR, downstream report identities, and total observations.

### 91.21 Dedicated regression suite — COMPLETE
tests/test_phase91_end_to_end_backtesting.py covers fold construction, leakage boundaries, prediction alignment, panel/Jodi evaluation, Top-K metrics, missing actuals, identities, and summaries.

### 91.22 Documentation and roadmap handoff — COMPLETE
Roadmap updated to mark Phase 91 complete and Phase 92 as the next implementation phase.

## Output

Phase 91 produces:

1. Chronological backtest folds.
2. Fold-level prediction lineage.
3. Historical panel and Jodi actual outcomes.
4. Panel Top-K hit rates and MRR.
5. Jodi Top-K hit rates and MRR.
6. Actual-vs-Ranked reports.
7. Performance-over-Time reports.
8. Temporal validation status.
9. Deterministic observation and report identities.
10. A compact end-to-end backtesting summary.

## Leakage model

The critical invariant is:

all training data < target date

The backtesting layer does not infer or fabricate the training set. The fold callback receives the exact fold boundary and is responsible for constructing the Phase 90 feature/model prediction using only observations available before that target.

This separation keeps the evaluation contract explicit and auditable.

## Model behavior

Phase 91 is model-agnostic. It does not claim that any model is accurate or production-ready. It measures historical behavior of the supplied Phase 90 predictor artifacts.

## Verification

- Dedicated Phase 91 tests.
- Phase 88–91 regression.
- Python compilation.
- git diff --check.

## Scope exclusions

No new MLOps, CI/CD, Docker, Kubernetes, cloud deployment, distributed infrastructure, or automatic production retraining is introduced.

## Next phase

**Phase 92 — Reproducibility Audit**

The next phase audits deterministic identities, feature/model metadata, repeated execution, artifact lineage, and reproducibility across the completed prediction and backtesting pipeline.
