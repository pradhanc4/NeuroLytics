# Phase 52 — Calibration Drift Monitoring

Version: 52.0.0
Status: COMPLETE

## Purpose

Phase 52 monitors whether top-prediction probabilities remain calibrated against observed
Top-1 outcomes over time.

The current Phase 45 source contract exposes top_probability and actual_rank. Therefore the
calibration target is explicitly defined as:

- predicted probability = top_probability
- observed binary outcome = 1 when actual_rank == 1
- observed binary outcome = 0 when actual_rank > 1
- observations with actual_rank == None are excluded from calibration calculations

This is a calibration-drift layer, not a prediction-generation or retraining layer.

## Metrics

Each populated period records:

- mean_predicted_probability
- empirical_hit_rate
- calibration_gap = mean_predicted_probability - empirical_hit_rate
- brier_score
- expected_calibration_error (ECE)
- fixed-width calibration bins

ECE is the weighted mean absolute gap between each populated probability bin's mean
prediction and empirical Top-1 hit rate.

Brier score is the mean squared error between top_probability and the binary Top-1 outcome.

Calibration gap is signed and preserves whether predictions are systematically above or below
the observed Top-1 rate.

## Periods

Default period size: 7 days.

The earliest populated source target date is the anchor. Later observations are assigned to
deterministic fixed-width periods.

Empty calendar periods are not fabricated.

At least two populated periods are required for drift comparison.

## Calibration Bins

Default bin count: 10.

Bins cover [0, 1] with deterministic equal-width intervals:

0.00-0.10 through 0.90-1.00.

Probability 0 and probability 1 are valid inputs.

Each period preserves:

- bin label
- observation count
- mean predicted probability
- empirical hit rate
- absolute calibration gap

## Drift Detection

Default rules:

- expected_calibration_error: threshold 0.05
- brier_score: threshold 0.05
- calibration_gap: threshold 0.05

Optional rules can monitor:

- mean_predicted_probability
- empirical_hit_rate

For every configured metric, the earliest populated period is the baseline. Each later
populated period is compared against that baseline.

Absolute change is:

abs(comparison_value - baseline_value)

A metric is marked drifted when absolute change >= its configured threshold.

The report collects drifted metrics and metric/period pairs.

## Source Boundary

Input must be a validated Phase 45 ActualVsRankedReport.

No candidate identity is fabricated.

No source data is modified.

## Public APIs

- build_calibration_drift_report()
- calibration_drift_summary()
- calibration_drift_periods()
- calibration_drift_observations()
- validate_calibration_drift_report()

Core classes:

- CalibrationBin
- CalibrationPeriod
- CalibrationDriftRule
- CalibrationDriftObservation
- CalibrationDriftReport
- CalibrationDriftValidationResult

Constants:

- CALIBRATION_DRIFT_VERSION = "52.0.0"
- DEFAULT_PERIOD_DAYS = 7
- DEFAULT_BINS = 10
- DEFAULT_THRESHOLD = 0.05

## Validation

Strict validation covers:

- report type and version
- source type and source identity
- period and bin configuration
- rule uniqueness and thresholds
- chronological unique periods
- period lengths
- observation counts
- calibration counts
- bin cardinality and reconciliation
- probability/hit-rate bounds
- Brier score bounds
- ECE bounds
- calibration-gap bounds
- finite metrics
- comparison cardinality
- baseline/comparison ordering
- drift flag consistency
- drifted metric consistency
- drifted period consistency
- deterministic identity prefix

## Determinism

The report identity is a SHA-256 hash over canonical JSON containing the source identity,
configuration, rules, period metrics, bins, and drift observations.

Identical source/configuration produces an identical report identity.

## Explicit Non-Goals

Phase 52 does not:

- generate predictions
- modify predictions
- rerank candidates
- rescore candidates
- retrain models
- select models
- promote models
- rollback models
- generate operational alerts
- mutate historical source data
- detect feature/data drift
- detect model-output PSI drift
- perform concept-drift detection

## Milestones

52.1 Phase Boundary Definition — COMPLETE
52.2 Phase 45 Source Contract — COMPLETE
52.3 Top-Probability Calibration Target — COMPLETE
52.4 Top-1 Outcome Definition — COMPLETE
52.5 Missing-Actual Exclusion — COMPLETE
52.6 Source Validation — COMPLETE
52.7 Source Lineage Preservation — COMPLETE
52.8 Period Configuration — COMPLETE
52.9 Chronological Period Grouping — COMPLETE
52.10 Empty-Period Non-Fabrication — COMPLETE
52.11 Minimum Two-Period Requirement — COMPLETE
52.12 Calibration Bin Configuration — COMPLETE
52.13 Equal-Width Probability Bins — COMPLETE
52.14 Probability-Zero Compatibility — COMPLETE
52.15 Probability-One Compatibility — COMPLETE
52.16 Mean Predicted Probability — COMPLETE
52.17 Empirical Top-1 Hit Rate — COMPLETE
52.18 Signed Calibration Gap — COMPLETE
52.19 Brier Score — COMPLETE
52.20 Expected Calibration Error — COMPLETE
52.21 Calibration Bin Statistics — COMPLETE
52.22 Default Drift Rules — COMPLETE
52.23 Custom Drift Rules — COMPLETE
52.24 Rule Uniqueness Validation — COMPLETE
52.25 Threshold Validation — COMPLETE
52.26 Baseline Period Selection — COMPLETE
52.27 Comparison Period Selection — COMPLETE
52.28 Absolute Change Calculation — COMPLETE
52.29 Drift Threshold Decision — COMPLETE
52.30 Drifted Metric Collection — COMPLETE
52.31 Drifted Period Collection — COMPLETE
52.32 Overall Drift Decision — COMPLETE
52.33 Panel Compatibility — COMPLETE
52.34 Jodi Compatibility — COMPLETE
52.35 Configurable Period Size — COMPLETE
52.36 Configurable Bin Count — COMPLETE
52.37 Deterministic Report Identity — COMPLETE
52.38 Period Accessor — COMPLETE
52.39 Observation Accessor — COMPLETE
52.40 Summary API — COMPLETE
52.41 Strict Report Validation — COMPLETE
52.42 Invalid Input Regression — COMPLETE
52.43 Calibration Math Regression — COMPLETE
52.44 Brier Regression — COMPLETE
52.45 ECE Regression — COMPLETE
52.46 Drift Threshold Regression — COMPLETE
52.47 Multi-Metric Regression — COMPLETE
52.48 Multi-Period Regression — COMPLETE
52.49 Determinism Regression — COMPLETE
52.50 No-Action Boundary Regression — COMPLETE
52.51 Dedicated Regression Coverage — COMPLETE
52.52 Production Import / Compile / Integrity Verification — COMPLETE
52.53 Documentation / Blueprint / Changelog — COMPLETE
52.54 Full Regression Verification — COMPLETE
52.55 Final Phase Integrity Verification — COMPLETE

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

Phase 52 complements Phase 51. Phase 51 records probability distributions descriptively;
Phase 52 evaluates probability calibration against observed Top-1 outcomes.

Next roadmap phase: Phase 53 — Ranking Drift Monitoring.
