# NeuroLytics — Phase 48 Performance Degradation Detection

## Status

Phase 48 — COMPLETE
Version: 48.0.0

## Purpose

Phase 48 converts the validated Phase 47 monitoring report into deterministic, configurable performance-degradation decisions. It identifies degradation only when an observed metric moves in its defined adverse direction, crosses a configured threshold, and satisfies the configured consecutive-period evidence requirement.

## Architecture

Phase 46 Performance Over Time
→ Phase 47 Performance Monitoring Framework
→ Phase 48 Performance Degradation Detection
→ Phase 49 Model Drift Detection

## Detection Contract

The detector accepts only a validated PerformanceMonitoringReport.

For every DegradationRule it evaluates:

1. baseline value from the first monitoring period
2. latest value from the last monitoring period
3. absolute change
4. optional relative change
5. adverse direction
6. absolute or relative threshold breach
7. consecutive adverse-period evidence

A metric is degraded only when all required conditions are satisfied.

## Direction Semantics

Higher-is-worse metrics:

- mean_actual_rank
- miss_rate

Lower-is-worse metrics:

- mean_reciprocal_rank
- mean_top_probability
- mean_cumulative_probability
- supported hit_at_K metrics

The direction is encoded as `WORSE_HIGHER` or `WORSE_LOWER`.

## Threshold Semantics

Each DegradationRule contains:

- metric
- absolute_threshold
- optional relative_threshold
- consecutive_periods

A threshold is breached when the configured absolute threshold OR configured relative threshold is reached.

Relative change is `(latest - baseline) / abs(baseline)` when the baseline is non-zero. Zero baselines produce `None` for relative change.

## Consecutive Evidence

The detector examines the most recent period-to-period transitions. Evidence continues while each recent transition moves in the adverse direction. A recovery or neutral transition breaks the consecutive evidence chain.

## Default Rules

- mean_actual_rank: absolute threshold 1.0
- mean_reciprocal_rank: absolute threshold 0.05
- miss_rate: absolute threshold 0.05
- mean_top_probability: absolute threshold 0.05
- mean_cumulative_probability: absolute threshold 0.05

All defaults require one consecutive adverse period.

## Outputs

`PerformanceDegradationObservation` contains:

- metric
- baseline value
- latest value
- absolute change
- relative change
- threshold
- direction
- degraded flag
- evidence-period count

`PerformanceDegradationReport` contains:

- source lineage
- monitoring-report lineage
- configured rules
- all metric observations
- degraded metric list
- overall degraded flag
- deterministic SHA-256 report identity

## Validation

The validator checks:

- report type and version
- source type
- source and monitoring lineage
- rule existence and uniqueness
- threshold validity
- consecutive-period validity
- observation/rule cardinality
- degraded metric consistency
- overall degraded flag consistency
- finite numeric values
- direction correctness
- report identity

## Explicit Non-Goals

Phase 48 does not:

- send alerts
- retrain models
- select models
- promote models
- rollback models
- change predictions
- change rankings
- change Top-K semantics
- detect data drift
- detect model drift
- modify historical source data

Those responsibilities remain isolated in later phases.

## Milestones

48.1 Phase Boundary Definition — COMPLETE
48.2 Phase 47 Source Contract — COMPLETE
48.3 Phase 47 Source Validation — COMPLETE
48.4 Source Lineage Preservation — COMPLETE
48.5 Monitoring Lineage Preservation — COMPLETE
48.6 Degradation Version Contract — COMPLETE
48.7 Degradation Rule Contract — COMPLETE
48.8 Default Rule Contract — COMPLETE
48.9 Custom Rule Selection — COMPLETE
48.10 Rule Metric Uniqueness — COMPLETE
48.11 Unknown Metric Rejection — COMPLETE
48.12 Absolute Threshold Validation — COMPLETE
48.13 Relative Threshold Validation — COMPLETE
48.14 Consecutive Period Validation — COMPLETE
48.15 Higher-Is-Worse Direction Contract — COMPLETE
48.16 Lower-Is-Worse Direction Contract — COMPLETE
48.17 Baseline Value Extraction — COMPLETE
48.18 Latest Value Extraction — COMPLETE
48.19 Absolute Change Calculation — COMPLETE
48.20 Relative Change Calculation — COMPLETE
48.21 Zero-Baseline Relative Change Handling — COMPLETE
48.22 Threshold Breach Evaluation — COMPLETE
48.23 Adverse Direction Evaluation — COMPLETE
48.24 Consecutive Evidence Evaluation — COMPLETE
48.25 Recovery Break Detection — COMPLETE
48.26 Metric-Level Degradation Decision — COMPLETE
48.27 Overall Degradation Decision — COMPLETE
48.28 Degraded Metric Collection — COMPLETE
48.29 Panel Compatibility — COMPLETE
48.30 Deterministic Report Identity — COMPLETE
48.31 Report Validation — COMPLETE
48.32 Summary API — COMPLETE
48.33 Invalid Input Regression — COMPLETE
48.34 Threshold Regression — COMPLETE
48.35 Consecutive Evidence Regression — COMPLETE
48.36 Determinism Regression — COMPLETE
48.37 Monitoring-Only / No-Retraining Boundary — COMPLETE
48.38 Dedicated Regression Coverage — COMPLETE
48.39 Production Import / Compile / Integrity Verification — COMPLETE
48.40 Documentation / Blueprint / Changelog — COMPLETE
48.41 Full Regression Verification — COMPLETE
48.42 Final Phase Integrity Verification — COMPLETE

## Tests

Dedicated Phase 48 regression: 47 passed in 0.21s.

No failures, errors, or warnings.

## Files

Created:

- analytics/performance_degradation.py
- tests/test_performance_degradation.py
- docs/PHASE_48_PERFORMANCE_DEGRADATION_DETECTION.md

Updated:

- PROJECT_STATUS.md
- CHANGELOG.md
- BLUEPRINT.md

## Dependency Policy

No new third-party dependency was introduced.

## Next Phase

Phase 49 — Model Drift Detection.
