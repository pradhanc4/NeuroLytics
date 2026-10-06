# Phase 53 — Ranking Drift Monitoring

Version: 53.0.0
Status: COMPLETE

## Purpose

Phase 53 monitors whether the distribution and placement of observed actual ranks changes
over time.

The validated Phase 45 ActualVsRankedReport is the source of truth. Phase 53 is distinct
from:

- Phase 48 Performance Degradation Detection, which evaluates adverse performance changes.
- Phase 49 Model Drift Detection, which evaluates model probability-output distribution drift.
- Phase 51 Prediction Distribution Monitoring, which descriptively records prediction-output
  distributions.
- Phase 52 Calibration Drift Monitoring, which evaluates probability calibration.

Phase 53 focuses on ranking structure.

## Ranking Signals

Each populated period records:

- Top-1 rate
- Top-3 rate
- Top-5 rate
- Top-10 rate
- Mean actual rank
- Mean reciprocal rank
- Exact rank distribution
- Rank probability distribution
- Rank-bucket distribution

Rank buckets are:

- TOP_1
- TOP_3
- TOP_5
- TOP_10
- OUTSIDE_TOP_10
- UNAVAILABLE is represented by the period missed-observation count rather than a rank
  distribution bucket.

## Rank Distribution

The configured rank_max defaults to 20.

Ranks above rank_max are deterministically accumulated into the rank_max bucket for the
numeric distribution while remaining represented as OUTSIDE_TOP_10 in the bucket view.

The numeric distribution always contains exactly rank_max entries, including zero-count
ranks.

This preserves a stable distribution shape for drift comparison.

## Drift Metrics

Default metrics:

- top_1_rate
- top_3_rate
- top_5_rate
- top_10_rate
- mean_actual_rank
- mean_reciprocal_rank
- rank_distribution_psi

Default threshold: 0.05.

For scalar ranking metrics, drift is detected when:

abs(comparison_value - baseline_value) >= threshold

For rank_distribution_psi, PSI is calculated between the baseline and comparison numeric rank
distributions using a small epsilon for zero-frequency safety.

The earliest populated period is the baseline. Every later populated period is compared
against that baseline.

## Periods

Default period size: 7 days.

The earliest populated target date is the temporal anchor.

Only populated periods are emitted. Empty calendar periods are never fabricated.

At least two populated periods are required for drift comparison.

## Missing Actuals

If actual_rank is None:

- it is excluded from rank rates and rank-distribution calculations
- it increments missed_observations
- it remains part of observation_count

No missing result is converted into a fabricated rank.

## Panel / Jodi Compatibility

The source_type is preserved and validated as either panel or jodi.

No separate ranking-drift implementation is created for either source.

## Public APIs

- build_ranking_drift_report()
- ranking_drift_summary()
- ranking_drift_periods()
- ranking_drift_observations()
- validate_ranking_drift_report()

Core classes:

- RankingDistribution
- RankingPeriod
- RankingDriftRule
- RankingDriftObservation
- RankingDriftReport
- RankingDriftValidationResult

## Determinism

Report identity uses SHA-256 over canonical JSON containing:

- source identity
- source type
- period configuration
- rank configuration
- rules
- period distributions
- period metrics
- drift observations

Identical source/configuration produces the same report identity.

## Validation

Strict validation covers:

- report type and version
- source type and identity
- period/rank configuration
- rule uniqueness and thresholds
- chronological unique periods
- period lengths
- observation reconciliation
- actual/missed reconciliation
- rank distribution cardinality
- rank distribution count reconciliation
- probability normalization
- bucket cardinality
- metric bounds
- finite numerical values
- observation cardinality
- comparison ordering
- drift flag consistency
- drifted metric consistency
- drifted period consistency
- overall drift consistency
- report identity

## Explicit Non-Goals

Phase 53 does not:

- generate predictions
- modify predictions
- rerank candidates
- rescore candidates
- retrain models
- select or promote models
- rollback models
- generate operational alerts
- mutate historical source data
- detect feature/data drift
- detect probability-output drift
- perform probability calibration
- perform concept-drift detection

## Milestones

53.1 Phase Boundary Definition — COMPLETE
53.2 Phase 45 Source Contract — COMPLETE
53.3 Source Validation — COMPLETE
53.4 Source Lineage Preservation — COMPLETE
53.5 Ranking Observation Contract — COMPLETE
53.6 Target-Date Ordering — COMPLETE
53.7 Period Configuration — COMPLETE
53.8 Chronological Period Grouping — COMPLETE
53.9 Empty-Period Non-Fabrication — COMPLETE
53.10 Minimum Two-Period Requirement — COMPLETE
53.11 Actual Rank Extraction — COMPLETE
53.12 Missing-Actual Handling — COMPLETE
53.13 Top-1 Rate — COMPLETE
53.14 Top-3 Rate — COMPLETE
53.15 Top-5 Rate — COMPLETE
53.16 Top-10 Rate — COMPLETE
53.17 Mean Actual Rank — COMPLETE
53.18 Mean Reciprocal Rank — COMPLETE
53.19 Numeric Rank Distribution — COMPLETE
53.20 Stable Rank Cardinality — COMPLETE
53.21 Zero-Count Rank Preservation — COMPLETE
53.22 Rank Distribution Probabilities — COMPLETE
53.23 Rank Bucket Distribution — COMPLETE
53.24 OUTSIDE_TOP_10 Compatibility — COMPLETE
53.25 Configurable Rank Maximum — COMPLETE
53.26 Rank Distribution PSI — COMPLETE
53.27 Zero-Frequency PSI Safety — COMPLETE
53.28 Default Drift Metrics — COMPLETE
53.29 Custom Drift Metrics — COMPLETE
53.30 Rule Uniqueness Validation — COMPLETE
53.31 Threshold Validation — COMPLETE
53.32 Baseline Period Selection — COMPLETE
53.33 Comparison Period Selection — COMPLETE
53.34 Absolute Change Calculation — COMPLETE
53.35 Drift Threshold Decision — COMPLETE
53.36 Drifted Metric Collection — COMPLETE
53.37 Drifted Period Collection — COMPLETE
53.38 Overall Drift Decision — COMPLETE
53.39 Panel Compatibility — COMPLETE
53.40 Jodi Compatibility — COMPLETE
53.41 Deterministic Report Identity — COMPLETE
53.42 Period Accessor — COMPLETE
53.43 Observation Accessor — COMPLETE
53.44 Summary API — COMPLETE
53.45 Strict Report Validation — COMPLETE
53.46 Invalid Input Regression — COMPLETE
53.47 Ranking Rate Regression — COMPLETE
53.48 Mean Rank Regression — COMPLETE
53.49 MRR Regression — COMPLETE
53.50 Rank Distribution Regression — COMPLETE
53.51 PSI Drift Regression — COMPLETE
53.52 Threshold Regression — COMPLETE
53.53 Multi-Metric Regression — COMPLETE
53.54 Multi-Period Regression — COMPLETE
53.55 Determinism Regression — COMPLETE
53.56 No-Action Boundary Regression — COMPLETE
53.57 Dedicated Regression Coverage — COMPLETE
53.58 Production Import / Compile / Integrity Verification — COMPLETE
53.59 Documentation / Blueprint / Changelog — COMPLETE
53.60 Full Regression Verification — COMPLETE
53.61 Final Phase Integrity Verification — COMPLETE

## Architecture Position

Phase 45 ActualVsRankedReport
    ↓
Phase 46 Performance Over Time
    ↓
Phase 47 Performance Monitoring
    ↓
Phase 48 Performance Degradation Detection
    ↓
Phase 49 Model Drift Detection
    ↓
Phase 50 Data Drift Detection
    ↓
Phase 51 Prediction Distribution Monitoring
    ↓
Phase 52 Calibration Drift Monitoring
    ↓
Phase 53 Ranking Drift Monitoring
    ↓
Phase 54 Feature Drift Monitoring

Phase 53 is a ranking-structure monitoring layer and does not replace the performance,
probability-distribution, calibration, or feature-drift layers.

Next roadmap phase: Phase 54 — Feature Drift Monitoring.
