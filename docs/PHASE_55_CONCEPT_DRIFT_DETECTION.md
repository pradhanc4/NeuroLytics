# NeuroLytics — Phase 55: Concept Drift Detection

## Status

COMPLETE LOCALLY — WARNING CLEAN

## Purpose

Phase 55 detects changes in the relationship between engineered feature values and observed outcomes over time.

This is concept drift monitoring: it asks whether P(Y | X) has changed, rather than only whether X changed, Y changed, model performance changed, or probabilities became miscalibrated.

## Architectural Boundary

Phase 55 consumes two established contracts:
- validated, leakage-clean FeatureArtifact history
- validated Phase 45 ActualVsRankedReport outcomes

The feature and outcome histories must align exactly by target date.

The layer does not:
- create or mutate features
- generate predictions
- retrain models
- rerank or rescore candidates
- alter probabilities
- trigger alerts
- select or promote models
- perform automated remediation

## Distinction From Earlier Monitoring Phases

- Phase 48: adverse performance changes.
- Phase 49: model-output distribution drift.
- Phase 50: input data distribution drift.
- Phase 51: prediction distribution monitoring.
- Phase 52: probability calibration drift.
- Phase 53: ranking-structure drift.
- Phase 54: engineered feature distribution/statistics drift.
- Phase 55: the feature-to-outcome relationship itself.

A feature can have a stable distribution while its relationship with the outcome changes; Phase 55 is designed to detect that case.

## Version

CONCEPT_DRIFT_VERSION = 55.0.0

Defaults:
- period: 7 days
- conditional bins: 5
- drift threshold: 0.10

## Outcome Contract

The observed outcome is derived from Phase 45 ActualVsRankedObservation:
- actual_rank == 1 → positive outcome 1
- actual_rank > 1 → outcome 0
- unavailable actual rank → excluded from paired concept-drift calculations

Both Panel and Jodi source types are supported.

## Conditional Relationship Method

For each monitored numeric feature:
1. Sort artifacts chronologically.
2. Use the earliest populated period as the baseline.
3. Build equal-width feature bins from baseline numeric values.
4. Compute baseline outcome rate within each feature bin.
5. Apply the same baseline bin edges to each later populated period.
6. Compute comparison outcome rates within those same bins.
7. Calculate a comparison-size-weighted mean absolute conditional-rate change.
8. Mark concept drift when the change is greater than or equal to the configured threshold.

The method is conditional: it measures how outcome behavior changes at comparable feature-value levels.

## Numeric Feature Contract

Default rules monitor schemas declared as:
- int
- integer
- float
- number
- numeric
- double

None is excluded from paired calculations.

Boolean, nonnumeric, and non-finite feature values are rejected when encountered in a monitored feature.

A populated period must contain at least one paired numeric feature/outcome observation.

## Temporal Contract

Requirements:
- at least two FeatureArtifact records
- unique feature target dates
- identical feature version
- identical feature names and order
- valid and leakage-clean artifacts
- valid Phase 45 outcome report
- unique outcome dates
- exact feature/outcome date alignment
- at least two populated periods

Only populated periods are emitted. Missing calendar dates are never fabricated.

## Report Contract

ConceptDriftObservation records:
- feature
- baseline period
- comparison period
- baseline paired observation count
- comparison paired observation count
- baseline outcome rate
- comparison outcome rate
- conditional rate change
- threshold
- drift flag

ConceptDriftReport records:
- version
- source type
- feature version
- feature artifact count
- outcome report identity
- period configuration
- bin configuration
- rules
- observations
- drifted features
- drifted periods
- overall drift
- deterministic SHA-256 identity

## Determinism

Report identity hashes normalized source lineage, configuration, observations, and drift decisions.

Identical inputs produce identical report identities.

## Validation

Strict validation covers:
- version and source type
- feature lineage
- outcome lineage
- period/bin configuration
- rule uniqueness and thresholds
- observation cardinality
- duplicate observations
- chronological ordering
- sample counts
- finite rates
- rate bounds
- conditional-change bounds
- drift-flag consistency
- drifted feature/period consistency
- overall drift consistency
- report identity prefix

## Public API

- build_concept_drift_report()
- concept_drift_summary()
- concept_drift_feature_names()
- concept_drift_observations()
- validate_concept_drift_report()

## Regression Coverage

Dedicated Phase 55 regression:
- 58 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes:
- stable relationship
- relationship shift
- threshold behavior
- determinism
- Panel/Jodi compatibility
- source alignment
- feature lineage
- leakage validation
- missing outcomes
- zero values
- constant features
- invalid numeric values
- temporal ordering
- non-fabricated periods
- multi-feature monitoring
- strict report validation
- identity preservation

## Production Outputs

- analytics/concept_drift.py
- tests/test_concept_drift.py
- docs/PHASE_55_CONCEPT_DRIFT_DETECTION.md

## Next Phase

Phase 56 — Alert / Threshold Framework