# NeuroLytics — Phase 62 Retraining Decision Framework

## Status

Phase 62 — Retraining Decision Framework is COMPLETE LOCALLY.

Version: 62.0.0

## Purpose

Phase 62 establishes a deterministic decision layer that consumes normalized evidence from the monitoring stack and determines whether the evidence meets configured retraining criteria.

The framework does not train a model. It does not select a model, promote a model, mutate production state, alter traffic, rollback a version, or change predictions.

Actual retraining execution remains a later roadmap concern, beginning with Phase 63 dataset preparation and Phase 64 automated retraining.

## Monitoring Inputs

The framework accepts normalized evidence from these monitoring families:

- Phase 47 — performance monitoring
- Phase 48 — performance degradation detection
- Phase 49 — model drift detection
- Phase 50 — data drift detection
- Phase 51 — prediction distribution monitoring
- Phase 52 — calibration drift monitoring
- Phase 53 — ranking drift monitoring
- Phase 54 — feature drift monitoring
- Phase 55 — concept drift detection

The normalized contract preserves source type, metric, baseline value, latest value, threshold, trigger state, consecutive-period evidence, source identity, period label, and optional details.

## Core Contract

### RetrainingEvidence

Represents one normalized monitoring observation.

Required fields:

- source_type
- metric
- baseline_value
- latest_value
- threshold
- triggered
- consecutive_periods
- source_identity

Optional fields:

- period_label
- details

### RetrainingRule

Represents an explicit retraining threshold policy for a source/metric pair.

Fields:

- source_type
- metric
- threshold
- min_consecutive_periods
- enabled

Rules are unique by `(source_type, metric)`.

### RetrainingDecision

Contains the deterministic decision:

- RETRAIN
- HOLD

It also contains triggered evidence, supporting evidence, reasons, and source identities.

### RetrainingDecisionReport

The immutable report contains:

- framework version
- decision ID
- model identity
- evaluation date
- rules
- evidence
- decision
- deterministic report identity

## Decision Logic

For each evidence item:

1. The evidence must be valid and finite.
2. Its source type must belong to the supported monitoring families.
3. A configured enabled rule may impose a minimum consecutive-period requirement.
4. A configured enabled rule may impose an absolute change threshold.
5. The evidence must be explicitly marked triggered.
6. When all applicable requirements are satisfied, the evidence becomes a retraining trigger.
7. At least one retraining trigger produces RETRAIN.
8. No qualifying trigger produces HOLD.

Threshold equality is inclusive and protected against floating-point representation noise with a small numerical tolerance.

Disabled rules remain valid policy records but do not suppress explicitly triggered evidence.

## Safety Boundaries

Phase 62 does not:

- train models
- build retraining datasets
- modify feature artifacts
- modify SQL historical data
- select or promote a model
- mutate lifecycle state
- modify production traffic
- deploy artifacts
- rollback models
- generate predictions
- rerank candidates
- send notifications
- execute remediation

The output is a decision report for later controlled phases.

## Determinism and Lineage

Report identity is SHA-256 based and includes the version, decision ID, model identity, evaluation date, rules, evidence, and decision.

Source identities are preserved in the decision output. Repeating identical inputs produces the same report identity. Changing decision inputs changes the report identity.

## Validation

Strict validation checks:

- report type and version
- decision/model/evaluation identity
- rule structure and uniqueness
- supported source types
- finite numeric values
- positive consecutive-period requirements
- evidence structure and uniqueness
- trigger reconciliation
- supporting-evidence reconciliation
- source-identity reconciliation
- decision consistency
- reason consistency
- report identity prefix

## Public API

- build_retraining_decision_report()
- retraining_decision_summary()
- retraining_decision_evidence()
- retraining_decision_triggers()
- validate_retraining_decision_report()

## Production Outputs

- analytics/retraining_decision.py
- tests/test_retraining_decision.py
- docs/PHASE_62_RETRAINING_DECISION_FRAMEWORK.md

## Verification

Dedicated Phase 62 regression: 76 passed, 0 failures, 0 errors, 0 warnings.

No new third-party dependency is required.

GitHub commit/push is not performed as part of the phase.

## Next Phase

Phase 63 — Retraining Dataset Pipeline.

Phase 63 should prepare a reproducible, leakage-safe dataset from approved retraining evidence and preserve model/feature/data lineage without performing automated model training.
