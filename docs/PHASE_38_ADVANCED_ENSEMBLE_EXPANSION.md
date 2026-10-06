# NeuroLytics — Phase 38 Advanced Ensemble Expansion / Consensus

Date: 2026-09-30
Status: COMPLETE LOCALLY — WARNING CLEAN
Version: 38.0.0

## 1. Scope

Phase 38 extends the Phase 35 ensemble layer without replacing it. It consumes already-built SequenceEnsembleResult objects and adds a second-order consensus layer across ensemble methods.

The architecture remains:

Historical SQL → point-in-time features → sequence dataset → sequence models
→ evaluation/calibration → formal ensemble → candidate scoring/ranking
→ explainability → Phase 38 advanced ensemble consensus.

No second historical-data pipeline, feature pipeline, or model-training pipeline was introduced.

## 2. Production Output

Created:

- analytics/advanced_ensemble.py
- tests/test_advanced_ensemble.py
- docs/PHASE_38_ADVANCED_ENSEMBLE_EXPANSION.md

Production version:

SEQUENCE_ADVANCED_ENSEMBLE_VERSION = "38.0.0"

## 3. Ensemble Agreement

Phase 38 compares the probability distributions emitted by multiple Phase 35 ensembles.

For every ensemble pair and observation it computes:

- Jensen-Shannon divergence
- Total variation distance

It aggregates these into:

- mean pairwise JS divergence
- maximum pairwise JS divergence
- mean pairwise total variation
- agreement score

Agreement score is a bounded descriptive diagnostic:

agreement = 1 - mean_JS_divergence

It is an interpretation diagnostic, not a new predictive feature.
## 4. Diversity-Aware Consensus Weights

Two deterministic weighting modes are supported:

- equal_weight
- inverse_disagreement

inverse_disagreement assigns larger normalized weight to ensembles with lower average JS disagreement against the other supplied ensembles.

Weights are finite, non-negative, normalized, lineage-bound, and deterministic.

The phase does not silently discard an ensemble. All supplied ensembles must pass validation and share:

- dataset identity
- observation count
- target sequence
- ten-class probability contract
- unique ensemble identity

## 5. Probability Consensus

For each observation and digit 0–9:

consensus_probability = sum(weight_i × ensemble_probability_i)

Rows are normalized and validated as ten-class probability distributions.

Digit 0 remains a first-class valid candidate.

## 6. Rank Consensus

The consensus probability row is deterministically ordered by:

1. probability descending
2. digit ascending for ties

Phase 38 records the full ten-digit ranking for every observation.

It also exposes the probability margin between the first and second candidates.

## 7. Consensus Diagnostics

Each observation records:

- top candidate ranking
- probability margin
- entropy
- normalized entropy
- effective candidate count

The report also preserves cross-ensemble agreement diagnostics.

These values describe the consensus distribution and do not claim certainty or introduce hidden predictive signal.

## 8. Lineage and Determinism

Every output preserves:

- dataset identity
- contributing ensemble identities
- consensus weight method
- normalized consensus weights
- targets
- observation count

Agreement, weights, consensus, and report identities are SHA-256 derived and deterministic.

Identical inputs produce identical identities and probabilities.
## 9. Validation Boundary

Phase 38 validation rejects:

- invalid Phase 35 ensembles
- fewer than two ensembles
- mixed dataset identities
- mismatched observations
- mismatched target sequences
- duplicate ensemble identities
- malformed probability rows
- invalid weights
- unnormalized weights
- invalid consensus identities
- invalid report lineage

This prevents incompatible ensemble outputs from being silently blended.

## 10. Integration Boundary

Phase 38 consumes:

analytics.sequence_ensemble.SequenceEnsembleResult

It does not modify:

- Markov
- HMM
- LSTM
- GRU
- Transformer
- Sequence Framework
- Evaluation / Calibration
- Phase 35 ensemble mathematics
- Phase 36 candidate scoring
- Phase 37 explainability

The layer is intentionally downstream and compositional.

## 11. Dedicated Regression

Created:

tests/test_advanced_ensemble.py

Dedicated Phase 38 result:

- 42 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes agreement metrics, weight construction, probability blending, ranking, entropy diagnostics, lineage, determinism, invalid-input rejection, report validation, and helper outputs.

## 12. Integration and Integrity

Integration smoke test: PASS.

The smoke path builds three Phase 35 ensemble methods, constructs the Phase 38 consensus report, validates it, and confirms deterministic output identity.

Python compileall: PASS.

git diff --check: PASS.

No new third-party dependency was added.
## 13. Full Regression

Phase 37 baseline:

5,079 passed

Phase 38 dedicated increase:

+42 tests

Final full project regression:

5,121 passed in 61.37s

Failures: 0

Errors: 0

Warnings: 0

## 14. Phase 38 Milestones

38.1 Phase Boundary Definition — COMPLETE
38.2 Phase 35 Ensemble Input Contract — COMPLETE
38.3 Ensemble Identity Contract — COMPLETE
38.4 Cross-Ensemble Alignment — COMPLETE
38.5 Ten-Class Probability Contract — COMPLETE
38.6 Pairwise JS Divergence — COMPLETE
38.7 Pairwise Total Variation — COMPLETE
38.8 Agreement Aggregation — COMPLETE
38.9 Agreement Score — COMPLETE
38.10 Equal Consensus Weighting — COMPLETE
38.11 Inverse-Disagreement Weighting — COMPLETE
38.12 Weight Normalization — COMPLETE
38.13 Diversity-Aware Weight Identity — COMPLETE
38.14 Probability Consensus — COMPLETE
38.15 Probability Integrity — COMPLETE
38.16 Deterministic Rank Consensus — COMPLETE
38.17 Probability Margin Diagnostic — COMPLETE
38.18 Entropy Diagnostics — COMPLETE
38.19 Effective Candidate Count — COMPLETE
38.20 Consensus Lineage — COMPLETE
38.21 Deterministic Consensus Identity — COMPLETE
38.22 Advanced Ensemble Report — COMPLETE
38.23 Consensus Validation — COMPLETE
38.24 Report Validation — COMPLETE
38.25 Dedicated Regression Coverage — COMPLETE
38.26 Integration Smoke Test — COMPLETE
38.27 Full Regression Verification — COMPLETE
38.28 Documentation / Blueprint Update — COMPLETE
38.29 Final Integrity Verification — COMPLETE

## 15. Release State

Phase 38 is complete locally and warning-clean.

The next architecture layer remains downstream backtesting / walk-forward validation before production monitoring and lifecycle controls.

GitHub commit/push was not performed.
