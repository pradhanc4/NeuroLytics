# Phase 45 — Actual-vs-Ranked Analysis

## Status

COMPLETE LOCALLY

## Purpose

Phase 45 analyzes the realized actual value against the ranked candidate outcome produced by Phase 44.

It is an analysis layer only. It does not train a model, alter probabilities, rerank candidates, or redefine Top-K semantics.

## Production contract

Phase 44 Top-K Evaluation Report
→ observation-level actual-vs-ranked records
→ rank distribution and buckets
→ Hit@K carry-forward
→ rank-sensitive metrics
→ deterministic Phase 45 report
→ Phase 46 Performance Over Time

## Version

- Actual-vs-Ranked version: 45.0.0
- Report identity prefix: actual-vs-ranked-report-

## Core entities

- ActualVsRankedObservation
- ActualVsRankedReport
- ActualVsRankedValidationResult

## Source contract

The only production input is Phase 44 TopKEvaluationReport.

The Phase 44 report is validated before Phase 45 analysis begins.

Panel and Jodi source types remain separated by the inherited source_type field.

## Observation-level outputs

Each observation preserves:

- source type
- group ID
- target date
- actual value
- actual rank
- reciprocal rank
- Hit@K outcomes
- deterministic rank bucket
- top candidate probability
- cumulative probability at the maximum configured K

## Rank buckets

- TOP_1
- TOP_3
- TOP_5
- TOP_10
- OUTSIDE_TOP_10
- UNAVAILABLE

An unavailable actual rank means the actual value was not present in the visible upstream ranking; Phase 45 does not fabricate a rank.

## Aggregate outputs

The report provides:

- actual-value availability count
- missed/unavailable count
- rank distribution
- rank-bucket counts
- Hit@K rates inherited from Phase 44
- mean actual rank
- median actual rank
- mean reciprocal rank
- mean top-candidate probability
- mean cumulative probability at maximum K
- deterministic report identity

## Metric semantics

### Actual rank

The rank is inherited directly from Phase 44.

### Hit@K

Hit@K is carried directly from Phase 44 rather than recomputed with a second definition.

### Mean actual rank

Calculated only across observations with an available actual rank.

Lower numeric rank represents an earlier position in the existing ranking; this metric is descriptive and is not a model-selection score.

### Median actual rank

Calculated only across observations with an available actual rank.

### Mean reciprocal rank

Calculated across observations with an available actual rank using the reciprocal rank already established by Phase 44.

### Probability summaries

Top probability and cumulative probability are descriptive summaries of the upstream ranking artifact.

## Integrity rules

- Input must be a Phase 44 TopKEvaluationReport.
- The Phase 44 report must pass its own validation contract.
- Observations must have unique group IDs.
- Source type must be Panel or Jodi.
- Actual rank must be positive when available.
- Missing actuals remain UNAVAILABLE.
- Rank buckets must agree with actual rank.
- Probabilities must be finite and bounded.
- Report identity is deterministic SHA-256 lineage.
- Digit 0 remains valid.
- Leading zeros remain unchanged.

## Architecture boundary

Phase 45 does not:

- retrain Phase 41
- change Phase 42 Panel ranking
- change Phase 43 Jodi ranking
- replace Phase 44 Top-K evaluation
- generate new probabilities
- create another candidate scorer
- create another consensus engine
- create another walk-forward evaluator
- introduce training state

## Public APIs

- build_actual_vs_ranked_report
- actual_vs_ranked_summary
- validate_actual_vs_ranked_report

## Downstream readiness

Phase 46 can consume the Phase 45 observation records using target_date as the temporal axis without rebuilding:

- actual-rank semantics
- Hit@K semantics
- reciprocal-rank semantics
- missing-actual semantics
- rank buckets

This keeps future performance-over-time analysis consistent with the Phase 44 evaluation contract.

## Production files

- analytics/actual_vs_ranked.py
- tests/test_actual_vs_ranked.py
- docs/PHASE_45_ACTUAL_VS_RANKED.md

## Verification

### Dedicated regression

- 48 passed
- 0 failures
- 0 errors
- 0 warnings

### Production verification

- production import: PASS
- compileall: PASS
- git diff --check: PASS

### Full regression

Final full project verification:

- 5,441 passed in 72.06s
- 0 failures
- 0 errors
- 0 warnings

Previous verified baseline:

- 5,393 passed

Regression increase: +48 tests.

### Dependencies

No new third-party dependency.

### Release

GitHub commit/push not performed.

## Milestones

45.1 Phase Boundary Definition — COMPLETE
45.2 Phase 44 Source Contract — COMPLETE
45.3 Phase 44 Source Validation — COMPLETE
45.4 Observation Adapter — COMPLETE
45.5 Actual Value Preservation — COMPLETE
45.6 Actual Rank Preservation — COMPLETE
45.7 Reciprocal Rank Preservation — COMPLETE
45.8 Hit@K Preservation — COMPLETE
45.9 Rank Bucket Contract — COMPLETE
45.10 Top-1 Bucket — COMPLETE
45.11 Top-3 Bucket — COMPLETE
45.12 Top-5 Bucket — COMPLETE
45.13 Top-10 Bucket — COMPLETE
45.14 Outside-Top-10 Bucket — COMPLETE
45.15 Unavailable Actual Bucket — COMPLETE
45.16 Rank Distribution — COMPLETE
45.17 Rank Bucket Counts — COMPLETE
45.18 Actual Availability Count — COMPLETE
45.19 Missed Observation Count — COMPLETE
45.20 Mean Actual Rank — COMPLETE
45.21 Median Actual Rank — COMPLETE
45.22 Mean Reciprocal Rank — COMPLETE
45.23 Mean Top Probability — COMPLETE
45.24 Mean Cumulative Probability — COMPLETE
45.25 Panel Source Compatibility — COMPLETE
45.26 Jodi Source Compatibility — COMPLETE
45.27 Zero-Digit Preservation — COMPLETE
45.28 Leading-Zero Preservation — COMPLETE
45.29 Observation Identity Preservation — COMPLETE
45.30 Source Report Lineage — COMPLETE
45.31 Deterministic Report Identity — COMPLETE
45.32 Report Validation — COMPLETE
45.33 Invalid Version Regression — COMPLETE
45.34 Duplicate Group Regression — COMPLETE
45.35 Rank-Bucket Integrity Regression — COMPLETE
45.36 Metric-Bounds Regression — COMPLETE
45.37 Missing-Actual Regression — COMPLETE
45.38 Determinism Regression — COMPLETE
45.39 Summary API — COMPLETE
45.40 Analysis-Only Boundary — COMPLETE
45.41 Dedicated Regression Coverage — COMPLETE
45.42 Production Import Verification — COMPLETE
45.43 Compile / Integrity Verification — COMPLETE
45.44 Documentation / Blueprint / Changelog — COMPLETE
45.45 Final Phase Integrity Verification — COMPLETE

## Phase 46 boundary

Phase 46 — Performance Over Time should consume Phase 45 observations and analyze temporal changes in rank, Hit@K, reciprocal rank, and related descriptive metrics.

Phase 46 should not recreate the Phase 44 or Phase 45 definitions.
