# Phase 43 — Jodi Ranking

## Status

COMPLETE LOCALLY

## Purpose

Phase 43 converts two position-wise Phase 41 Learning-to-Rank probability distributions into a deterministic ranking of explicit two-digit Jodi candidates.

The phase follows Phase 42 Panel Ranking and does not train another model.

## Contract

For Jodi AB:

P(AB) = P(position_1=A) × P(position_2=B)

Raw candidate masses are normalized over the supplied Jodi candidate universe.

Candidate score = normalized probability × 100.

Ranking is descending by normalized probability, with the Jodi string as deterministic tie-break.

Leading-zero Jodis such as 00 and 05 remain valid two-digit identifiers.

## Architecture

Phase 40 Learning-to-Rank Dataset
→ Phase 41 Learning-to-Rank Model
→ two position-wise probability predictions
→ Phase 43 Jodi Ranking
→ Phase 44 Top-K Framework

## Production

Added:

- analytics/jodi_ranking.py
- tests/test_jodi_ranking.py
- docs/PHASE_43_JODI_RANKING.md

Version:

JODI_RANKING_VERSION = "43.0.0"

Core entities:

- JodiCandidateInput
- JodiRankedCandidate
- JodiRankingObservation
- JodiRankingReport
- JodiRankingValidationResult

Core functions:

- rank_jodis
- rank_jodis_from_predictions
- build_jodi_ranking_report
- validate_jodi_ranking
- validate_jodi_ranking_report
- jodi_values
- top_jodi
- jodi_ranking_summary

## Candidate semantics

A Jodi is represented as a two-character digit string.

Candidate identity is string-based so leading zeros are preserved.

Optional jodi_family_id and panel_family_id metadata are carried through ranking.

The implementation accepts an explicit candidate universe rather than silently inventing or expanding one.

## Probability integrity

Each source prediction must contain exactly ten digits 0 through 9.

Each probability vector must be finite, non-negative, contain ten values, and sum to one within tolerance.

Exactly two position predictions are required.

The product score is normalized only across the supplied Jodi candidates.

## Determinism and lineage

Jodi ordering is deterministic.

Ties use the Jodi string as the stable tie-break.

Ranking identity is SHA-256 based on phase version, group identity, target date, target position, ranked candidates, and source prediction group identities.

Report identity is SHA-256 based on phase version, source model identities, observation identities, and Top-K configuration.

No random state is introduced.

## Validation

Validation covers:

- object type
- group identity
- target date
- candidate existence
- contiguous ranks
- unique Jodis
- two-digit Jodi format
- probability ranges
- score ranges
- top probability
- probability margin
- optional actual Jodi
- ranking identity
- report version
- source model identity count
- observation uniqueness
- report identity
- observation-level validation

## Milestones

### 43.1 Phase Boundary Definition — COMPLETE
Defined Jodi Ranking as the two-digit ranking layer downstream of Phase 41.

### 43.2 Phase 41 Integration Contract — COMPLETE
Consumes two position-wise LearningToRankPrediction probability vectors.

### 43.3 Jodi Candidate Contract — COMPLETE
Introduced explicit two-digit Jodi candidates with family metadata.

### 43.4 Leading-Zero Preservation — COMPLETE
Preserves values such as 00 and 05 as strings.

### 43.5 Two-Position Probability Extraction — COMPLETE
Validates and extracts digit probabilities for both positions.

### 43.6 Jodi Probability Construction — COMPLETE
Computes multiplicative candidate mass across both positions.

### 43.7 Candidate-Universe Normalization — COMPLETE
Normalizes probability mass across the supplied Jodi universe.

### 43.8 Deterministic Jodi Ranking — COMPLETE
Ranks candidates by descending normalized probability.

### 43.9 Deterministic Tie-Break — COMPLETE
Uses Jodi value as stable tie-break.

### 43.10 Score Conversion — COMPLETE
Converts probability to the 0–100 candidate score scale.

### 43.11 Top-K Jodi Selection — COMPLETE
Supports bounded Top-K output.

### 43.12 Jodi Family Metadata — COMPLETE
Preserves Jodi family references.

### 43.13 Panel Family Metadata — COMPLETE
Preserves optional Panel family references.

### 43.14 Actual Jodi Support — COMPLETE
Supports an optional observed Jodi for downstream evaluation.

### 43.15 Observation Contract — COMPLETE
Defines immutable ranking observations.

### 43.16 Report Contract — COMPLETE
Defines deterministic multi-observation Jodi ranking reports.

### 43.17 Ranking Validation — COMPLETE
Adds strict observation validation.

### 43.18 Report Validation — COMPLETE
Adds strict report-level validation.

### 43.19 Ranking Identity — COMPLETE
Adds deterministic SHA-256 ranking identity.

### 43.20 Report Identity — COMPLETE
Adds deterministic SHA-256 report identity.

### 43.21 Prediction Adapter — COMPLETE
Adds a two-prediction convenience adapter.

### 43.22 Summary API — COMPLETE
Adds structured report summaries.

### 43.23 Zero-Digit Regression — COMPLETE
Dedicated coverage verifies 0 is valid in Jodi values.

### 43.24 Input Integrity Regression — COMPLETE
Malformed probability vectors and Jodi values fail safely.

### 43.25 Determinism Regression — COMPLETE
Repeated identical inputs produce identical identities and rankings.

### 43.26 Metadata Regression — COMPLETE
Jodi and Panel family metadata survive ranking.

### 43.27 Validation Regression — COMPLETE
Valid and intentionally corrupted contracts are detected.

### 43.28 Dedicated Regression Coverage — COMPLETE
47 dedicated tests pass with zero warnings.

### 43.29 Production Import Verification — COMPLETE
Production module imports successfully.

### 43.30 Compile / Integrity Verification — COMPLETE
compileall passes for the Phase 43 production module.

### 43.31 Documentation / Blueprint / Changelog — COMPLETE
Phase documentation and project architecture records are updated.

### 43.32 Final Phase Integrity Verification — COMPLETE
Focused tests, import, compilation, and full regression are required for closure.

## Design boundaries

Phase 43 does not:

- train a new ML model
- create another feature pipeline
- duplicate Phase 36 candidate scoring
- duplicate Phase 38 consensus
- duplicate Phase 39 walk-forward evaluation
- replace Phase 42 Panel Ranking
- silently invent a Jodi candidate universe
- claim real-world predictive accuracy

The explicit candidate-universe boundary keeps the ranking deterministic and auditable.

## Verification target

- dedicated regression: 47 passed
- failures: 0
- errors: 0
- warnings: 0
- production import: PASS
- compileall: PASS
- full project regression: 5330 passed, 0 failures, 0 errors, 0 warnings
- no new third-party dependency
- GitHub push is not part of phase completion

## Output

Phase 43 produces a validated deterministic Jodi ranking artifact for downstream Phase 44 Top-K Framework consumption.
