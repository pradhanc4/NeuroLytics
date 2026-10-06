# NeuroLytics — Phase 56: Alert / Threshold Framework

## Status
COMPLETE LOCALLY — WARNING CLEAN

## Purpose
Phase 56 establishes the shared threshold-evaluation layer for monitoring outputs. It converts normalized metric values and configured alert rules into deterministic alert observations and severity buckets.

## Architectural Boundary
Phase 56 is an evaluation and reporting layer only. It does not send notifications, retrain models, promote models, rollback models, rerank candidates, alter predictions, mutate source data, or automatically remediate a condition.

Inputs are generic metric/value pairs plus explicit AlertRule definitions. This keeps Phase 56 reusable across performance, model drift, data drift, feature drift, calibration drift, ranking drift, and concept drift.

## Version
ALERT_THRESHOLD_VERSION = 56.0.0

## Rule Contract
Each AlertRule contains:
- alert_id
- metric
- threshold
- severity
- operator
- enabled

Supported operators:
- gte
- gt
- lte
- lt
- eq

Supported severities:
- INFO
- WARNING
- CRITICAL

Rule IDs are unique. Multiple rules may intentionally target the same metric.

## Evaluation Contract
For every enabled rule, the framework:
1. locates the supplied metric value
2. validates finiteness
3. evaluates the configured operator
4. creates an AlertObservation
5. records the source identity and evaluation date
6. classifies active alerts by severity
7. builds a deterministic report identity

Disabled rules remain in the report configuration but are not evaluated and do not require an observed metric value.

Threshold comparisons are deterministic. gte/lte are inclusive; gt/lt are strict; eq uses a small absolute tolerance.

## Report Contract
AlertThresholdReport contains:
- version
- source_type
- source_identity
- normalized rules
- observations
- active_alerts
- critical_alerts
- warning_alerts
- alert_count
- deterministic SHA-256 report identity

An alert is active when its configured operator evaluates true. A clear state is represented by zero active alerts; no external notification is emitted by this phase.

## Validation
Strict validation covers:
- report type and version
- source identity
- rule uniqueness
- rule severity/operator/threshold validity
- observation uniqueness
- observed-value finiteness
- source lineage preservation
- operator consistency
- severity consistency
- rule/observation consistency
- active-alert collection consistency
- severity collection consistency
- alert count consistency
- report identity prefix

## Determinism
Report identity includes source identity, normalized rule configuration, evaluated observations, and evaluation date. Identical inputs produce identical report identities.

## Integration Boundary
Phase 56 can evaluate metrics produced by earlier monitoring layers, including:
- Phase 47 performance monitoring
- Phase 48 performance degradation
- Phase 49 model drift
- Phase 50 data drift
- Phase 51 prediction distribution monitoring
- Phase 52 calibration drift
- Phase 53 ranking drift
- Phase 54 feature drift
- Phase 55 concept drift

The integration remains explicit: Phase 56 does not silently infer thresholds or change the semantics of upstream reports.

## Regression Coverage
Dedicated Phase 56 regression:
- 63 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes:
- threshold operators
- inclusive/exclusive boundaries
- severity routing
- disabled rules
- missing metric handling
- duplicate rule IDs
- invalid severity/operator
- non-finite values
- duplicate metric values
- source identity preservation
- evaluation date preservation
- deterministic identity
- active-only accessor
- strict validation
- multiple rules on one metric
- clear-state behavior
- no-action boundary

## Production Outputs
- analytics/alert_threshold.py
- tests/test_alert_threshold.py
- docs/PHASE_56_ALERT_THRESHOLD_FRAMEWORK.md

## Next Phase
Phase 57 — Model Health Scorecard