# NeuroLytics — Phase 58: Model Comparison Over Time

## Status

COMPLETE LOCALLY — DEDICATED REGRESSION CLEAN

## Purpose

Phase 58 provides a deterministic temporal comparison layer for Model Health Scorecard outputs.

It compares model-health snapshots between two explicitly named periods and reports:

- models common to both periods
- models appearing only in the baseline period
- models appearing only in the comparison period
- health-score changes for common models
- absolute changes
- relative changes when a non-zero baseline exists
- improved, declined, and unchanged model sets

The phase is descriptive. It does not select a champion or challenger and does not promote, demote, retrain, rollback, or modify models.

## Version

MODEL_COMPARISON_VERSION = 58.0.0

## Source Contract

The primary source is the validated Phase 57 ModelHealthReport.

Each report can be converted to a ModelHealthSnapshot containing:

- period_label
- model_identity
- health_score
- health_status
- component_scores
- source_report_identity

Snapshots preserve the original Phase 57 report identity for lineage.

## Comparison Contract

A comparison contains:

- comparison_id
- baseline_period
- comparison_period
- snapshots
- metric comparisons
- improved models
- declined models
- unchanged models
- common models
- baseline-only models
- comparison-only models

Both periods must contain at least one snapshot.

A model can be compared only when it exists in both periods.

## Health Score Comparison

Phase 58 currently compares:

- health_score

For each common model:

absolute_change = comparison_score - baseline_score

relative_change = absolute_change / abs(baseline_score)

When the baseline score is effectively zero, relative_change is represented as None rather than fabricating an infinite percentage.

## Model Set Accounting

The comparison partitions model identities into:

- common_models
- baseline_only_models
- comparison_only_models

These sets are deterministic and collectively account for every model identity present in either period.

## Change Classification

Using a small numerical epsilon:

- positive change → improved
- negative change → declined
- effectively zero change → unchanged

This classification is descriptive only.

It is not a ranking, recommendation, champion decision, or promotion decision.

## Core Classes

- ModelHealthSnapshot
- ModelMetricComparison
- ModelComparisonReport
- ModelComparisonValidationResult

## Public APIs

- build_model_health_snapshot()
- build_model_comparison_report()
- model_comparison_summary()
- model_comparison_metrics()
- model_comparison_snapshots()
- validate_model_comparison_report()

## Deterministic Identity

Report identity is generated using SHA-256 over:

- phase version
- comparison ID
- baseline period
- comparison period
- requested metrics
- snapshots
- source report identities
- metric comparison values

Identical inputs produce identical report identities.

Meaningful input changes produce different identities.

## Strict Validation

Validation covers:

- report type
- version
- comparison ID
- period labels
- period distinction
- snapshot presence
- snapshot period membership
- model identity
- score bounds
- status validity
- component uniqueness
- component score bounds
- source lineage
- model-set reconciliation
- metric validity
- common-model restriction
- finite comparison values
- absolute-change consistency
- relative-change consistency
- improved-model collection
- declined-model collection
- unchanged-model collection
- deterministic identity prefix

## Operational Boundary

Phase 58 does not:

- select a champion
- select a challenger
- promote a model
- demote a model
- retrain a model
- rollback a model
- change predictions
- rerank candidates
- mutate historical data
- modify ModelHealthReport outputs

Those responsibilities belong to later roadmap phases.

## Dedicated Regression

- 65 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes:

- snapshot construction
- source lineage
- period separation
- common model detection
- baseline-only model detection
- comparison-only model detection
- improved model classification
- declined model classification
- unchanged model classification
- absolute changes
- relative changes
- zero-baseline behavior
- score validation
- status validation
- component validation
- deterministic identities
- strict report validation
- no-promotion boundary

## Production Outputs

- analytics/model_comparison.py
- tests/test_model_comparison.py
- docs/PHASE_58_MODEL_COMPARISON_OVER_TIME.md

## Next Phase

Phase 59 — Model Champion / Challenger Framework
