# NeuroLytics — Phase 54: Feature Drift Monitoring

## Status

COMPLETE LOCALLY — WARNING CLEAN

## Purpose

Phase 54 adds a deterministic monitoring layer for engineered feature behavior over time.

The layer consumes validated, leakage-clean FeatureArtifact history and compares an earliest populated baseline period with later populated periods. It monitors numeric feature distribution drift using PSI and records supporting feature statistics.

## Architectural Boundary

Phase 54 is intentionally downstream-only.

It:
- consumes FeatureArtifact objects
- preserves feature version and feature-name lineage
- validates temporal uniqueness and feature-schema alignment
- groups observations into populated calendar periods
- computes missing rate, mean, standard deviation, and PSI
- compares every later populated period to the baseline
- exposes strict validation, accessors, summary, and deterministic identity

It does not:
- mutate feature artifacts
- create new features
- retrain models
- rerank or rescore predictions
- change prediction probabilities
- detect concept drift
- trigger alerts or retraining
- replace Phase 50 Data Drift Detection

## Phase 50 vs Phase 54

Phase 50 provides a general model-input data-drift contract.

Phase 54 establishes a feature-specific monitoring contract around engineered FeatureArtifact values, with explicit feature statistics and missingness alongside the PSI distribution measure. The two layers remain independent and can be used together.

## Version

FEATURE_DRIFT_VERSION = 54.0.0

Defaults:
- period: 7 days
- PSI threshold: 0.20
- bins: 10

## Core Contracts

### FeatureDriftRule

Defines:
- feature_name
- positive finite threshold

### FeatureDriftObservation

Records:
- feature name
- baseline/comparison period starts
- numeric sample counts
- baseline/comparison missing rates
- baseline/comparison means
- baseline/comparison standard deviations
- PSI
- threshold
- drift decision

### FeatureDriftReport

Contains:
- version
- feature version
- source artifact count
- source feature names
- period configuration
- rules
- bin count
- observations
- drifted features
- drifted periods
- overall drift flag
- deterministic report identity

### FeatureDriftValidationResult

Provides:
- VALID or INVALID
- deterministic issue codes
- is_valid convenience property

## Temporal Contract

Artifacts are sorted by target_date.

Requirements:
- at least two artifacts
- unique target dates
- same feature version
- identical feature names and order
- valid artifact status
- leakage status CLEAN

Periods are anchored at the earliest target date.

Only populated periods are emitted. Missing calendar dates do not create synthetic observations or empty periods.

The earliest populated period is the baseline. Every later populated period is compared with that baseline.

## Numeric Feature Contract

Default rules select features whose declared schema data type is one of:
- int
- integer
- float
- number
- numeric
- double

None is treated as missing.

Boolean values are rejected as numeric measurements.

Non-finite values (NaN, inf, -inf) are rejected.

A period must contain at least one numeric observation for every monitored feature.

## Feature Statistics

For every baseline/comparison pair the report records:
- numeric observation count
- missing rate across all period artifacts
- arithmetic mean
- population standard deviation
- PSI

Missingness is therefore visible even though missing values are excluded from the numeric distribution.

## PSI Contract

PSI uses equal-width bins over the combined baseline/comparison numeric range.

Zero-frequency bins use epsilon 1e-12 for numerical stability.

If all values share the same numeric value, PSI is exactly 0.0.

Drift is detected when:

PSI >= threshold

The threshold comparison is inclusive.

## Determinism

Report identity is a SHA-256 hash of the complete normalized configuration and observation payload.

The identity includes:
- version
- feature version
- source feature names
- period configuration
- rules
- bin count
- observations
- drift decisions

Repeated execution over identical input produces the same report identity.

## Validation

Strict validation covers:
- report type and version
- feature/source metadata
- period and bin configuration
- rule uniqueness
- threshold validity
- observation cardinality
- duplicate observations
- declared-feature alignment
- chronological comparison order
- sample counts
- finite statistics
- missing-rate bounds
- standard-deviation bounds
- PSI bounds
- drift-flag consistency
- drifted-feature consistency
- drifted-period consistency
- overall drift consistency
- report-identity prefix

## Public API

- build_feature_drift_report()
- feature_drift_summary()
- feature_drift_feature_names()
- feature_drift_observations()
- validate_feature_drift_report()

## Regression Coverage

Dedicated Phase 54 suite:
- tests/test_feature_drift.py
- 54 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes:
- defaults and version
- determinism
- stable and shifted distributions
- custom thresholds
- accessors and summary
- invalid rules/configuration
- source lineage validation
- invalid artifacts
- nonnumeric and boolean values
- NaN rejection
- missing-value handling
- zero-value handling
- zero standard deviation
- multiple features
- multi-feature drift isolation
- identity changes
- inclusive threshold behavior
- strict report validation
- chronological ordering
- empty-period non-fabrication
- invalid report handling

## Production Outputs

- analytics/feature_drift.py
- tests/test_feature_drift.py
- docs/PHASE_54_FEATURE_DRIFT_MONITORING.md

## Verification Requirements

Before phase closure:
1. dedicated regression passes
2. production import passes
3. compileall passes
4. git diff --check passes
5. full project regression passes
6. status/changelog/blueprint are updated
7. no new third-party dependency is introduced

## Next Phase

Phase 55 — Concept Drift Detection