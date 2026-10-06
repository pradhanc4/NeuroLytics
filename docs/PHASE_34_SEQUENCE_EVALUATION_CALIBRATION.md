# NeuroLytics — Phase 34: Advanced Sequence Evaluation & Calibration

Date: 2026-09-30
Status: COMPLETE LOCALLY — WARNING CLEAN
Version: 34.0.0

## 1. Scope

Phase 34 formalizes the evaluation and probability-calibration layer above the Phase 33 Advanced Sequence Framework.

The phase does not replace Markov, HMM, LSTM, GRU, or Transformer implementations.
It does not create a second historical-data pipeline.
It does not create a second sequence-dataset pipeline.

Production dependency:

SQL
→ Historical Services
→ Point-in-Time Features
→ Sequence Dataset
→ Sequence Framework
→ Sequence Model
→ Phase 34 Evaluation / Calibration
→ future Comparison / Ensemble / Ranking / Backtesting

## 2. Goals

Phase 34 provides:
- one evaluation contract for all registered sequence model families
- deterministic next-observation probability extraction
- log loss
- accuracy
- Top-K accuracy
- multiclass Brier score
- expected calibration error
- mean predictive entropy
- deterministic temperature calibration
- pre/post calibration metrics
- deterministic evaluation-report identity
- report validation

## 3. Production Module

Created:

analytics/sequence_evaluation.py

Version:

SEQUENCE_EVALUATION_VERSION = 34.0.0

The module is intentionally independent of model mathematics.

## 4. Evaluation Dataset Contract

SequenceEvaluationDataset stores:
- sequences
- deterministic dataset identity
- target name

The contract preserves:
- digit 0
- digit range 0–9
- non-empty sequences
- explicit dataset identity

No missing or future observations are fabricated by the evaluation layer.

## 5. Model Interoperability

The evaluation adapter consumes SequenceModelRun from Phase 33.

Supported model kinds:
- markov
- hidden_markov
- lstm
- gru
- transformer

Window behavior:
- Markov uses configured order
- HMM uses historical prefix context for next-observation probabilities
- LSTM uses configured sequence length
- GRU uses configured sequence length
- Transformer uses configured sequence length

Existing model APIs remain unchanged.

## 6. Probability Extraction

For Markov, LSTM, GRU, and Transformer, the adapter uses predict_proba.

For HMM, the adapter uses predict_next_proba.

Every probability row is validated to:
- contain exactly 10 classes
- contain finite non-negative values
- sum to 1 within tolerance
- use targets from digit 0 through 9

## 7. Core Metrics

### 7.1 Log Loss

Negative mean log probability assigned to the observed target digit.

### 7.2 Accuracy

Deterministic argmax accuracy with lower-digit tie resolution.

### 7.3 Top-K Accuracy

Supports any positive K and caps K at the ten-digit alphabet.

Default evaluation K is 3.

### 7.4 Multiclass Brier Score

Mean squared probability error across the complete ten-class digit distribution.

### 7.5 Expected Calibration Error

Confidence bins compare mean predicted confidence with empirical correctness.

The implementation uses deterministic equal-width confidence bins.

### 7.6 Predictive Entropy

Mean categorical entropy measures uncertainty of the predicted ten-digit distribution.

## 8. Temperature Calibration

Phase 34 adds deterministic scalar temperature calibration.

For each probability row:

log(probability) / temperature

is transformed back through normalized exponential scaling.

Temperature is selected by deterministic search over a fixed positive grid.

The selected temperature minimizes calibration-set log loss.

No stochastic optimizer is introduced.

## 9. Calibration Output

SequenceCalibrationResult records:
- model kind
- model version
- calibration dataset identity
- selected temperature
- pre-calibration log loss
- post-calibration log loss
- pre-calibration Brier score
- post-calibration Brier score

The result preserves model lineage and dataset identity.

## 10. Evaluation Output

SequenceEvaluationResult records:
- model kind
- model version
- dataset identity
- observation count
- log loss
- accuracy
- Top-K accuracy
- Brier score
- expected calibration error
- mean entropy
- probability rows
- target rows

Raw probability and target rows remain available for downstream calibration and comparison.

## 11. Evaluation Report

SequenceEvaluationReport contains:
- evaluation version
- dataset identity
- evaluations
- calibrations
- deterministic report identity

The identity is derived from:
- evaluation version
- dataset identity
- model kinds
- model versions
- calibration temperatures

The report identity is reproducible for identical inputs.

## 12. Validation

validate_sequence_evaluation_report verifies:
- report type
- evaluation version
- dataset identity
- presence of evaluations
- positive observation counts
- evaluation dataset lineage
- calibration dataset lineage
- positive calibration temperature
- report identity format

Invalid reports return a structured INVALID result with deterministic issue codes.

## 13. Leakage Boundary

Phase 34 is downstream of the established temporal boundary.

It consumes a supplied evaluation dataset and does not:
- query future observations
- manufacture target dates
- alter feature engineering
- alter sequence window construction
- bypass SQL source-of-truth rules

Calibration is explicitly scoped to the dataset supplied by the caller.

Production workflows should provide a chronologically appropriate calibration split rather than calibrating on a final holdout.

## 14. Architecture Connection

Phase 33:

Sequence Dataset
→ Sequence Framework
→ Sequence Model Run

Phase 34:

Sequence Model Run
→ Probability Extraction
→ Evaluation Metrics
→ Calibration
→ Evaluation Report

Forward:

Evaluation Report
→ Formal Model Comparison
→ Ensemble
→ Candidate Scoring
→ Ranking
→ Walk-Forward / Backtesting
→ Monitoring
→ API / UI

## 15. Dedicated Tests

Created:

tests/test_sequence_evaluation.py

Dedicated coverage includes:
- version contract
- evaluation dataset validation
- zero-digit preservation
- invalid digit rejection
- log loss
- accuracy
- Top-K accuracy
- Brier score
- calibration error
- entropy
- temperature fitting
- temperature validation
- Markov integration
- identity mismatch detection
- insufficient evaluation windows
- calibration result
- calibration lineage
- report construction
- report validation
- report mismatch rejection
- deterministic report identity
- probability shape validation
- probability normalization validation
- target validation
- K validation
- bin validation
- probability preservation
- model metadata preservation

Dedicated result:

29 passed, 0 warnings.

## 16. Five-Model Smoke Verification

A production smoke run evaluated all five Phase 33 sequence families through the Phase 34 adapter:

- GRU — 10 observations
- Hidden Markov — 18 observations
- LSTM — 10 observations
- Markov — 18 observations
- Transformer — 10 observations

This confirms the common probability/evaluation adapter interoperates with all registered sequence model families.

## 17. Full Regression

Phase 33 baseline:

4,951 passed

Phase 34 result:

4,980 passed

Increase:

+29 tests

Final:
- 4,980 passed
- 0 failures
- 0 errors
- 0 warnings

Runtime:

59.52 seconds

## 18. Integrity Verification

compileall:

PASS

git diff --check:

PASS

No new third-party dependency was introduced.

## 19. Milestones

34.1 Phase Boundary Definition — COMPLETE
34.2 Evaluation Dataset Contract — COMPLETE
34.3 Probability Extraction Contract — COMPLETE
34.4 Markov Evaluation Adapter — COMPLETE
34.5 HMM Evaluation Adapter — COMPLETE
34.6 LSTM Evaluation Adapter — COMPLETE
34.7 GRU Evaluation Adapter — COMPLETE
34.8 Transformer Evaluation Adapter — COMPLETE
34.9 Probability Integrity Validation — COMPLETE
34.10 Log Loss Metric — COMPLETE
34.11 Accuracy Metric — COMPLETE
34.12 Top-K Accuracy Metric — COMPLETE
34.13 Multiclass Brier Score — COMPLETE
34.14 Expected Calibration Error — COMPLETE
34.15 Predictive Entropy — COMPLETE
34.16 Deterministic Temperature Calibration — COMPLETE
34.17 Calibration Lineage Contract — COMPLETE
34.18 Evaluation Result Contract — COMPLETE
34.19 Evaluation Report Contract — COMPLETE
34.20 Deterministic Report Identity — COMPLETE
34.21 Report Validation — COMPLETE
34.22 Dedicated Regression Coverage — COMPLETE
34.23 Five-Model Smoke Verification — COMPLETE
34.24 Full Regression Verification — COMPLETE
34.25 Documentation / Blueprint Update — COMPLETE
34.26 Final Verification — COMPLETE

## 20. Production Outputs

analytics/sequence_evaluation.py
tests/test_sequence_evaluation.py
docs/PHASE_34_SEQUENCE_EVALUATION_CALIBRATION.md

## 21. Compatibility

No Phase 28–33 model implementation was replaced.

No SQL schema was changed.

No historical loader was duplicated.

No sequence dataset implementation was duplicated.

Phase 34 consumes Phase 33 SequenceModelRun objects.

## 22. Release State

Phase 34 is complete locally and warning-clean.

GitHub commit/push was not performed.

Next roadmap phase:

Phase 35 — next formal model-comparison / ensemble layer.
