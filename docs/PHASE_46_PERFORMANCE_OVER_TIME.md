# NeuroLytics — Phase 46: Performance Over Time

## Status

COMPLETE LOCALLY

## Purpose

Phase 46 analyzes how Phase 45 actual-vs-ranked performance changes over time. It is a descriptive temporal layer only.

## Architecture boundary

Phase 45 ActualVsRankedReport
→ chronological observations
→ configurable fixed calendar-relative periods
→ period-level performance metrics
→ deterministic metric trends
→ validated PerformanceOverTimeReport

Phase 46 does not retrain models, generate new probabilities, recompute ranks, rerank candidates, or replace Phase 44/45 semantics.

## Production outputs

- `analytics/performance_over_time.py`
- `tests/test_performance_over_time.py`
- `docs/PHASE_46_PERFORMANCE_OVER_TIME.md`

## Core capabilities

- validated Phase 45 source consumption
- configurable period length, default 7 days
- chronological period construction anchored to the first observation
- observation and actual-availability counts
- missed-observation and miss-rate tracking
- mean actual rank by period
- Hit@K rates by period
- mean reciprocal rank by period
- mean top probability by period
- mean cumulative probability by period
- deterministic per-day linear trend slopes
- trend direction classification: IMPROVING / DECLINING / STABLE
- first-to-last metric change
- Panel and Jodi source compatibility
- zero and leading-zero preservation through Phase 45 lineage
- deterministic SHA-256 report identity
- strict report validation
- summary API

## Metric interpretation

- Lower mean actual rank is descriptively better because a smaller rank means the realized value appeared earlier in the ranking. The module reports the metric and its direction without making a product-level decision.
- Higher Hit@K and reciprocal rank indicate stronger realized ranking placement.
- Miss rate measures the fraction of observations for which no actual rank was available.
- Probability summaries are carried from Phase 45 observations and are not regenerated.

## Trend contract

For each metric, the report calculates ordinary least-squares slope against period start date, expressed per day.

- positive slope → IMPROVING
- negative slope → DECLINING
- zero/tolerance-level slope → STABLE

This is a descriptive trend signal, not a forecast.

## Validation

The validator checks:

- version and source type
- source lineage
- positive period length
- chronological unique periods
- exact period boundaries
- non-empty periods
- period/global count reconciliation
- rank and probability bounds
- Hit@K bounds
- valid trend directions
- finite trend values
- trend-change consistency
- deterministic report identity prefix

## Milestones

46.1 Phase Boundary Definition — COMPLETE
46.2 Phase 45 Source Contract — COMPLETE
46.3 Phase 45 Source Validation — COMPLETE
46.4 Chronological Observation Ordering — COMPLETE
46.5 Configurable Period Contract — COMPLETE
46.6 Seven-Day Default Period — COMPLETE
46.7 Custom Period Length — COMPLETE
46.8 Deterministic Period Boundaries — COMPLETE
46.9 Period Observation Count — COMPLETE
46.10 Period Actual Availability Count — COMPLETE
46.11 Period Missed Count — COMPLETE
46.12 Period Miss Rate — COMPLETE
46.13 Period Mean Actual Rank — COMPLETE
46.14 Period Hit@K Metrics — COMPLETE
46.15 Period Mean Reciprocal Rank — COMPLETE
46.16 Period Mean Top Probability — COMPLETE
46.17 Period Mean Cumulative Probability — COMPLETE
46.18 Multi-Period Time Series — COMPLETE
46.19 Mean-Rank Trend — COMPLETE
46.20 MRR Trend — COMPLETE
46.21 Hit@K Trend — COMPLETE
46.22 Miss-Rate Trend — COMPLETE
46.23 Probability Trend Diagnostics — COMPLETE
46.24 Per-Day Trend Slope — COMPLETE
46.25 Trend Direction Classification — COMPLETE
46.26 First-to-Last Change — COMPLETE
46.27 Panel Source Compatibility — COMPLETE
46.28 Jodi Source Compatibility — COMPLETE
46.29 Zero-Digit Lineage Preservation — COMPLETE
46.30 Leading-Zero Lineage Preservation — COMPLETE
46.31 Source Report Lineage — COMPLETE
46.32 Deterministic Report Identity — COMPLETE
46.33 Report Validation — COMPLETE
46.34 Summary API — COMPLETE
46.35 Invalid Input Regression — COMPLETE
46.36 Bounds / Count Regression — COMPLETE
46.37 Determinism Regression — COMPLETE
46.38 Analysis-Only Boundary — COMPLETE
46.39 Dedicated Regression Coverage — COMPLETE
46.40 Production Import Verification — COMPLETE
46.41 Compile / Integrity Verification — COMPLETE
46.42 Documentation / Blueprint / Changelog — COMPLETE
46.43 Final Phase Integrity Verification — COMPLETE

## Verification

- Dedicated regression: 64 passed, 0 failures, 0 errors, 0 warnings
- Production import: PASS
- compileall: PASS
- git diff --check: PASS
- Full project regression: 5,505 passed in 57.92s, 0 failures, 0 errors, 0 warnings
- New third-party dependency: none

## Downstream boundary

Phase 46 establishes the temporal performance-monitoring input for future monitoring, degradation, drift, and lifecycle phases.

## Release

GitHub commit/push was not performed.
