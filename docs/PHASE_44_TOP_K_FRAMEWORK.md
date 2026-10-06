# Phase 44 — Top-K Framework

## Status

COMPLETE LOCALLY

## Purpose

Phase 44 provides one reusable Top-K selection and evaluation layer for the existing Phase 42 Panel Ranking and Phase 43 Jodi Ranking artifacts.

It does not retrain models, create new probabilities, or duplicate ranking logic.

## Production contract

Existing ranking
→ Top-K selection
→ Hit@K / actual rank / MRR
→ cumulative probability
→ deterministic evaluation report
→ Phase 45 Actual-vs-Ranked Analysis

## Version

- Top-K framework: 44.0.0
- Selection identity prefix: top-k-selection-
- Evaluation report identity prefix: top-k-evaluation-report-

## Core entities

- TopKCandidate
- TopKSelection
- TopKEvaluationRow
- TopKEvaluationReport
- TopKValidationResult

## Supported ranking sources

### Panel

Consumes PanelRankingObservation from Phase 42.

The three-digit Panel string remains unchanged, including leading zeros such as 000, 005, and 045.

### Jodi

Consumes JodiRankingObservation from Phase 43.

The two-digit Jodi string remains unchanged, including leading-zero values such as 00 and 05.

## Selection capabilities

- configurable integer K
- deterministic first-K extraction from an existing ranking
- K larger than the available candidate count is safely clamped
- candidate probability preservation
- score preservation
- rank preservation
- Panel/Jodi family metadata preservation
- source ranking identity lineage
- cumulative probability
- deterministic SHA-256 selection identity

## Evaluation capabilities

For configured K values:

- Hit@K
- actual rank
- reciprocal rank
- mean reciprocal rank (MRR)
- top probability
- cumulative probability at maximum configured K
- observation counts
- actual-value availability counts
- Hit@K aggregate rates
- deterministic SHA-256 report identity

## Integrity rules

- K must be a positive integer.
- K values must be unique.
- K values are normalized into deterministic ascending order.
- Ranking source must be Panel or Jodi.
- Mixed Panel/Jodi observations are rejected within one evaluation report.
- Ranking groups must be unique within an evaluation report.
- Actual values are optional; missing actuals produce unavailable rank and zero reciprocal rank.
- Actual values outside the visible upstream ranking remain unavailable rather than being fabricated.
- Hit@K is derived from actual rank; it is never independently guessed.
- Probability and score values must remain finite and bounded.
- Digit 0 is valid.
- Leading zeros are preserved.
- No model weights or training state are introduced.

## Public APIs

- normalize_top_k_values
- top_k_selection
- top_k_values
- cumulative_probability
- actual_rank
- hit_at_k
- reciprocal_rank
- build_top_k_evaluation_row
- build_top_k_evaluation_report
- validate_top_k_selection
- validate_top_k_evaluation_report
- top_k_summary

## Architecture boundary

Phase 44 consumes ranked candidate artifacts only.

It does not:

- retrain Phase 41
- recompute Panel probability
- recompute Jodi probability
- replace Phase 36 candidate scoring
- replace Phase 38 consensus
- replace Phase 39 walk-forward/backtesting
- create a second ranking engine

## Downstream contract

Phase 45 can consume TopKEvaluationReport.rows to perform actual-vs-ranked analysis without reimplementing Top-K semantics.

## Verification

Dedicated Phase 44 regression:

- 63 passed
- 0 failures
- 0 errors
- 0 warnings
- full project regression: 5393 passed in 81.19s

Production import: PASS.

Compileall: PASS.

No new third-party dependency was added.

GitHub commit/push: not performed.

## Milestones

44.1 Phase Boundary Definition — COMPLETE
44.2 Phase 42 Panel Integration Contract — COMPLETE
44.3 Phase 43 Jodi Integration Contract — COMPLETE
44.4 Common Ranking Observation Adapter — COMPLETE
44.5 Top-K Integer Contract — COMPLETE
44.6 Top-K Configuration Normalization — COMPLETE
44.7 Deterministic Top-K Selection — COMPLETE
44.8 K-Above-Available Handling — COMPLETE
44.9 Candidate Probability Preservation — COMPLETE
44.10 Candidate Score Preservation — COMPLETE
44.11 Candidate Rank Preservation — COMPLETE
44.12 Panel Metadata Preservation — COMPLETE
44.13 Jodi Metadata Preservation — COMPLETE
44.14 Leading-Zero Preservation — COMPLETE
44.15 Digit-Zero Regression — COMPLETE
44.16 Cumulative Probability — COMPLETE
44.17 Actual-Value Extraction — COMPLETE
44.18 Actual-Rank Detection — COMPLETE
44.19 Hit@K Metric — COMPLETE
44.20 Reciprocal-Rank Metric — COMPLETE
44.21 Top-K Evaluation Row Contract — COMPLETE
44.22 Multi-K Evaluation Report — COMPLETE
44.23 Hit@K Aggregate Rates — COMPLETE
44.24 MRR Aggregate — COMPLETE
44.25 Missing-Actual Handling — COMPLETE
44.26 Mixed-Source Rejection — COMPLETE
44.27 Group-Identity Uniqueness — COMPLETE
44.28 Selection Identity — COMPLETE
44.29 Evaluation Report Identity — COMPLETE
44.30 Selection Validation — COMPLETE
44.31 Evaluation Report Validation — COMPLETE
44.32 Summary API — COMPLETE
44.33 Determinism Regression — COMPLETE
44.34 Metadata Regression — COMPLETE
44.35 Input Integrity Regression — COMPLETE
44.36 Dedicated Regression Coverage — COMPLETE
44.37 Production Import Verification — COMPLETE
44.38 Compile / Integrity Verification — COMPLETE
44.39 Documentation / Blueprint / Changelog — COMPLETE
44.40 Final Phase Integrity Verification — COMPLETE
## Phase 45 readiness

The Phase 44 report is intentionally shaped for the next actual-vs-ranked layer:

- group_id identifies the observation.
- target_date provides temporal context.
- actual_value identifies the realized Panel/Jodi value when available.
- actual_rank records where that value appears in the upstream visible ranking.
- hit_at_k provides normalized K-specific outcomes.
- reciprocal_rank provides rank-sensitive evaluation.
- source_type separates Panel and Jodi analysis.
- source_report_identity preserves upstream report lineage.

This prevents Phase 45 from rebuilding ranking semantics or silently changing the definition of a Top-K hit.
