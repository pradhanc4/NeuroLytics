# NeuroLytics — Phase 36 Candidate Scoring / Ranking

Status: COMPLETE LOCALLY
Version: 36.0.0
Production module: analytics/candidate_scoring.py

## 1. Scope

Phase 36 converts a validated Phase 35 ensemble probability surface into a
deterministic candidate score and ranking surface.

The phase is downstream-only. It does not retrain models, alter historical
data, change sequence windows, or create additional predictive features.

## 2. Input Contract

Primary input:
- SequenceEnsembleResult from analytics.sequence_ensemble
- ten-class probabilities for digits 0–9
- dataset identity
- selected ensemble identity

The ensemble must pass the existing Phase 35 validation contract.

## 3. Candidate Contract

Each candidate represents one digit in the closed domain 0–9.

For candidate d:
- probability = ensemble probability for d
- score = probability × 100
- rank = deterministic descending probability rank

Tie-breaking rule:
- equal probabilities are ordered by lower digit first.

No candidate is removed because its probability is zero.
## 4. Ranking Contract

SequenceCandidateRanking contains:
- dataset identity
- ensemble identity
- observation index
- candidate scores
- top probability
- probability margin
- predictive entropy
- deterministic ranking identity

The default observation is the final ensemble probability row.

Negative observation indexes are supported using Python-style indexing.

Top-K is constrained to 1–10.

## 5. Report Contract

SequenceCandidateRankingReport contains:
- candidate scoring version
- dataset identity
- ensemble identity
- one ranking per ensemble observation
- configured top-K
- deterministic report identity

The report is suitable as the immediate upstream object for future
walk-forward, actual-vs-ranked, ranking stability, and Top-K phases.

## 6. Determinism

Ranking order is fully deterministic:
1. probability descending
2. candidate digit ascending as the tie-break

Identity hashes include the relevant dataset, ensemble, observation,
candidate values, probabilities, scores, ranks, and version.

## 7. Probability Integrity

Phase 36 requires:
- exactly ten probabilities
- finite values
- non-negative values
- total probability of 1
- valid candidate domain 0–9

Digit 0 remains a normal candidate and is never treated as missing.
## 8. Confidence Context

The ranking layer records two contextual diagnostics without changing the
candidate order:

- probability margin: top candidate probability minus second candidate
  probability
- entropy: Shannon entropy of the complete ten-class distribution

These values are descriptive confidence context. They are not additional
predictive signals.

## 9. Ensemble Consumption

The production flow is:

Phase 34 evaluation/calibration
        ↓
Phase 35 formal comparison / ensemble
        ↓
selected SequenceEnsembleResult
        ↓
Phase 36 candidate scoring
        ↓
deterministic candidate ranking / Top-K surface
        ↓
future walk-forward / backtesting / monitoring

The selected ensemble identity is preserved in every ranking.

## 10. Validation

Ranking validation checks:
- version
- dataset identity
- ensemble identity
- candidate count
- rank sequence
- candidate domain
- probability range
- score range
- margin
- entropy
- ranking identity

Report validation checks:
- version
- report identities
- dataset/ensemble lineage
- non-empty rankings
- Top-K range
- every ranking validation result

## 11. Dedicated Tests

Created:
tests/test_candidate_scoring.py

Coverage includes:
- version contract
- probability ordering
- deterministic tie handling
- Top-K limiting
- zero-probability candidates
- probability margin
- single-candidate margin
- entropy
- selected ensemble consumption
- explicit/negative observation indexing
- invalid ensemble rejection
- probability validation
- Top-K validation
- ranking validation
- ranking identity determinism
- score/probability relationship
- report construction
- report validation
- report identity determinism
- top-candidate helper

Dedicated result:
31 passed, 0 warnings.

Full project regression:
5,041 passed, 0 failures, 0 errors, 0 warnings.
## 12. Milestones

36.1 Phase Boundary Definition — COMPLETE
36.2 Downstream Ensemble Input Contract — COMPLETE
36.3 Candidate Digit Contract — COMPLETE
36.4 Ten-Class Probability Validation — COMPLETE
36.5 Candidate Score Contract — COMPLETE
36.6 Deterministic Rank Ordering — COMPLETE
36.7 Tie-Break Contract — COMPLETE
36.8 Top-K Contract — COMPLETE
36.9 Observation Selection — COMPLETE
36.10 Ensemble Lineage Preservation — COMPLETE
36.11 Probability Margin Diagnostic — COMPLETE
36.12 Entropy Diagnostic — COMPLETE
36.13 Ranking Identity — COMPLETE
36.14 Candidate Ranking Report — COMPLETE
36.15 Ranking Validation — COMPLETE
36.16 Report Validation — COMPLETE
36.17 Deterministic Reproducibility — COMPLETE
36.18 Dedicated Regression Coverage — COMPLETE
36.19 Integration Smoke Test — COMPLETE
36.20 Full Regression Verification — COMPLETE (5,041 passed, 0 failures, 0 errors, 0 warnings)
36.21 Documentation / Blueprint Update — COMPLETE
36.22 Final Integrity Verification — COMPLETE

## 13. Production Outputs

- analytics/candidate_scoring.py
- tests/test_candidate_scoring.py
- docs/PHASE_36_CANDIDATE_SCORING_RANKING.md

## 14. Release State

Phase 36 is complete locally and warning-clean.

No SQL schema was changed.
No historical-data pipeline was duplicated.
No model implementation was replaced.
No third-party dependency was added.

Next roadmap layer:
Phase 37 — Explainability / downstream ranking interpretation.
## 15. Architecture Boundary

Phase 36 is a pure downstream transformation layer.

It consumes:
- validated ensemble probabilities
- ensemble lineage
- dataset identity

It produces:
- candidate-level scores
- deterministic ranks
- Top-K candidate surfaces
- confidence-context diagnostics
- reproducible ranking/report identities

It does not:
- query SQL
- access future observations
- construct historical features
- alter sequence datasets
- train or recalibrate models
- select an ensemble method
- manufacture probabilities

## 16. Compatibility

Phase 36 preserves the Phase 35 ensemble contract and is intentionally
small enough to remain reusable by future backtesting and ranking layers.

The score is a transparent 0–100 rescaling of ensemble probability. Therefore
candidate ordering is exactly the probability ordering, with deterministic
digit tie-breaking.

This prevents the ranking layer from silently introducing an unvalidated
secondary scoring heuristic.
