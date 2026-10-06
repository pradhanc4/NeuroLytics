# NeuroLytics — Phase 37 Explainability / Downstream Ranking Interpretation

Status: COMPLETE LOCALLY
Version: 37.0.0
Production module: analytics/sequence_explainability.py

## 1. Scope

Phase 37 adds a downstream explainability layer above the Phase 36 candidate
ranking and Phase 35 ensemble.

It explains the ranking using evidence already present in the ranking and
ensemble contracts. It does not change probabilities, scores, ranks, model
weights, or ensemble selection.

## 2. Core Explanation Contract

For each ranked candidate, Phase 37 exposes:
- candidate digit
- rank
- ensemble probability
- Phase 36 score
- probability share within the visible ranked set
- rank percentile
- probability gap to the previous candidate
- probability gap to the next candidate
- cumulative probability through the candidate rank

These are descriptive interpretations of existing outputs.

## 3. Distribution Diagnostics

The explanation also exposes:
- Shannon entropy
- normalized entropy = entropy / log(10)
- effective candidate count = exp(entropy)

These diagnostics describe distribution concentration. They are not additional
predictive features and do not alter candidate ordering.

## 4. Ensemble Lineage

Every explanation preserves:
- dataset identity
- ensemble identity
- ensemble method
- model kinds
- ensemble weights
- observation index

The explainability layer does not choose a different ensemble.

## 5. Model Attribution Boundary

A Phase 35 SequenceEnsembleResult stores model kinds and weights, but not the
individual component probability rows.

Therefore base explainability does not invent model-level contributions.

Optional model attribution is available only when aligned
SequenceEvaluationResult objects are explicitly supplied.

The attribution contract requires:
- same dataset identity
- same observation count
- same model order
- same probability-row count
- valid ten-class probability rows

For candidate c:
weighted contribution = ensemble weight × component probability(c)

contribution share is the normalized share of these weighted contributions.

## 6. Determinism

Explanation and report identities are SHA-256 based and include the
relevant version, dataset, ensemble, observation, ranking explanation, and
optional attribution information.

Identical inputs produce identical identities.

## 7. Report Contract

SequenceExplainabilityReport contains:
- explainability version
- dataset identity
- ensemble identity
- one explanation per ensemble observation
- deterministic report identity

The report is designed for future explainability UI, prediction history,
actual-vs-ranked analysis, and monitoring.

## 8. Validation

Explanation validation checks:
- version
- dataset and ensemble identity
- observation index
- candidate/rank domain
- probability and score ranges
- entropy diagnostics
- model attribution integrity
- deterministic explanation identity

Report validation checks:
- version
- lineage
- non-empty explanations
- every explanation validation result
- deterministic report identity

## 9. Dedicated Regression

Created:
tests/test_sequence_explainability.py

Coverage includes:
- version
- latest/explicit/negative observation handling
- Top-K
- score preservation
- rank percentile
- rank gaps
- cumulative probability
- entropy diagnostics
- effective candidate count
- base explanation boundary
- model attribution
- attribution lineage validation
- deterministic identities
- report construction
- report validation
- zero-candidate handling
- summary output

Dedicated result:
38 passed, 0 warnings.

## 10. Milestones

37.1 Phase Boundary Definition — COMPLETE
37.2 Phase 36 Ranking Input Contract — COMPLETE
37.3 Ensemble Lineage Contract — COMPLETE
37.4 Candidate Explanation Contract — COMPLETE
37.5 Rank Interpretation — COMPLETE
37.6 Probability Interpretation — COMPLETE
37.7 Score Interpretation — COMPLETE
37.8 Probability Gap Analysis — COMPLETE
37.9 Cumulative Probability Context — COMPLETE
37.10 Rank Percentile — COMPLETE
37.11 Entropy Diagnostics — COMPLETE
37.12 Normalized Entropy — COMPLETE
37.13 Effective Candidate Count — COMPLETE
37.14 Base Explainability Boundary — COMPLETE
37.15 Optional Model Attribution Contract — COMPLETE
37.16 Attribution Lineage Validation — COMPLETE
37.17 Deterministic Explanation Identity — COMPLETE
37.18 Explainability Report — COMPLETE
37.19 Explanation Validation — COMPLETE
37.20 Report Validation — COMPLETE
37.21 Dedicated Regression Coverage — COMPLETE
37.22 Integration Smoke Test — COMPLETE
37.23 Full Regression Verification — COMPLETE
37.24 Documentation / Blueprint Update — COMPLETE
37.25 Final Integrity Verification — COMPLETE

## 11. Production Outputs

- analytics/sequence_explainability.py
- tests/test_sequence_explainability.py
- docs/PHASE_37_EXPLAINABILITY.md

## 12. Architecture Boundary

Phase 37 is downstream-only:

Phase 35 ensemble
        ↓
Phase 36 candidate scoring / ranking
        ↓
Phase 37 explainability
        ↓
future UI / monitoring / actual-vs-ranked analysis

It does not:
- query SQL
- modify historical observations
- construct features
- retrain models
- calibrate probabilities
- select an ensemble
- change candidate scores
- change candidate ranks
- fabricate model contributions

## 13. Release State

Phase 37 is complete locally and warning-clean.

No third-party dependency was added.
No SQL schema was changed.
No model implementation was replaced.
No GitHub commit or push was performed.

Next roadmap phase:
Phase 38 — Ensemble expansion / downstream ensemble consumption.
