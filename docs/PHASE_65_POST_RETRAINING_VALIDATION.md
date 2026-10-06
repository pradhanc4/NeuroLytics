# NeuroLytics — Phase 65 Post-Retraining Validation

## Status

Phase 65 — Post-Retraining Validation is COMPLETE LOCALLY.

Version: 65.0.0

## Purpose

Phase 65 independently validates the candidate produced by Phase 64 before any later lifecycle or production action.

The validation layer consumes:

- Phase 64 AutomatedRetrainingReport
- Phase 63 RetrainingDatasetReport
- optionally a persisted Phase 64 model artifact
- optionally a supplied fitted model object

It does not train, promote, activate, register, deploy, rollback, or mutate production state.

## Validation Areas

### Lineage

Validates:

- dataset identity
- decision identity
- feature version
- feature names and order
- model identity
- artifact identity
- model version

### Dataset / Split Integrity

Validates that reported TRAIN, VALIDATION, and TEST row counts agree with the Phase 63 dataset partitions and that required evaluation splits are present when configured.

### Model Contract

Validates that the artifact records at least two target classes and that supplied/persisted model metadata agrees with the retraining artifact lineage.

### Metric Integrity

Validates:

- accuracy bounds [0,1]
- weighted F1 bounds [0,1]
- non-negative log loss
- finite metric values
- optional minimum accuracy threshold
- optional minimum F1 threshold
- optional maximum log-loss threshold

Thresholds are validation criteria only; they do not trigger promotion.

### Persistence

Persistence is optional by default. If required, the configured artifact path must exist and load as a RandomForestClassifier. Persisted model classes must match the retraining artifact.

## Important Phase 64 Boundary

Phase 64 reports can exist without model persistence. Phase 65 therefore does not pretend that model bytes are embedded in an `AutomatedRetrainingReport`. A persisted path or supplied fitted model is only required when the validation configuration explicitly needs direct model inspection.

## Output

`PostRetrainingValidationReport` records:

- validation identity
- source lineage
- individual validation checks
- passed checks
- failed checks
- TRAIN/VALIDATION/TEST metrics
- deterministic report identity

Overall status is VALID only when all structural checks pass.

## Public API

- `validate_post_retraining_validation_config()`
- `build_post_retraining_validation_report()`
- `validate_post_retraining_validation_report()`
- `post_retraining_validation_summary()`
- `post_retraining_validation_checks()`
- `post_retraining_validation_failures()`

## Safety Boundary

Phase 65 does not:

- train a model
- change model weights
- change model predictions
- select a champion
- promote a challenger
- mutate lifecycle state
- register a model
- deploy a model
- change production traffic
- rollback a model
- modify SQL data
- modify FeatureArtifacts

## Milestones

65.1 Phase Boundary Definition — COMPLETE
65.2 Phase 64 Source Contract — COMPLETE
65.3 Phase 63 Dataset Source Contract — COMPLETE
65.4 Retraining Report Validation Gate — COMPLETE
65.5 Dataset Report Validation Gate — COMPLETE
65.6 Dataset Identity Reconciliation — COMPLETE
65.7 Decision Identity Reconciliation — COMPLETE
65.8 Feature Version Lineage — COMPLETE
65.9 Feature Name / Order Lineage — COMPLETE
65.10 Model Identity Lineage — COMPLETE
65.11 Artifact Identity Contract — COMPLETE
65.12 Model Version Contract — COMPLETE
65.13 TRAIN Row Reconciliation — COMPLETE
65.14 VALIDATION Row Reconciliation — COMPLETE
65.15 TEST Row Reconciliation — COMPLETE
65.16 Validation Split Requirement — COMPLETE
65.17 Test Split Requirement — COMPLETE
65.18 Target-Class Contract — COMPLETE
65.19 Metric Finiteness — COMPLETE
65.20 Accuracy Bounds — COMPLETE
65.21 F1 Bounds — COMPLETE
65.22 Log-Loss Bounds — COMPLETE
65.23 Minimum Accuracy Policy — COMPLETE
65.24 Minimum F1 Policy — COMPLETE
65.25 Maximum Log-Loss Policy — COMPLETE
65.26 Optional Persistence Contract — COMPLETE
65.27 Required Persistence Contract — COMPLETE
65.28 Persisted Artifact Existence — COMPLETE
65.29 Persisted Model Type Validation — COMPLETE
65.30 Persisted Model Class Validation — COMPLETE
65.31 Supplied Model Contract — COMPLETE
65.32 Supplied Model Class Validation — COMPLETE
65.33 Validation Check Contract — COMPLETE
65.34 PASS / FAIL Classification — COMPLETE
65.35 Passed Check Collection — COMPLETE
65.36 Failed Check Collection — COMPLETE
65.37 Overall VALID / INVALID Status — COMPLETE
65.38 Summary API — COMPLETE
65.39 Check Accessor — COMPLETE
65.40 Failure Accessor — COMPLETE
65.41 Deterministic Validation Identity — COMPLETE
65.42 Strict Report Validation — COMPLETE
65.43 Version Validation — COMPLETE
65.44 Status Validation — COMPLETE
65.45 Check Identity Validation — COMPLETE
65.46 Check Status Validation — COMPLETE
65.47 Check Reconciliation — COMPLETE
65.48 Metric Validation — COMPLETE
65.49 Optional Metric Validation — COMPLETE
65.50 Invalid Input Regression — COMPLETE
65.51 Threshold Regression — COMPLETE
65.52 Persistence Boundary Regression — COMPLETE
65.53 Lineage Regression — COMPLETE
65.54 Determinism Regression — COMPLETE
65.55 Dedicated Regression Coverage — COMPLETE
65.56 Production Import / Compile / Integrity Verification — COMPLETE
65.57 Documentation / Blueprint / Changelog — COMPLETE
65.58 Full Regression Verification — COMPLETE
65.59 Final Phase Integrity Verification — COMPLETE

## Verification

Dedicated Phase 65 regression: 70 passed, 0 failures, 0 errors, 0 warnings.

No new third-party dependency was introduced.

No GitHub commit/push was performed.

## Next Phase

Phase 66 — Model Rollout / Controlled Activation Boundary.

Phase 66 should define controlled activation mechanics only after the candidate has passed independent validation, while preserving explicit approval and rollback boundaries.
