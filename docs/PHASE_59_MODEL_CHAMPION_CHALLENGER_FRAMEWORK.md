# NeuroLytics — Phase 59: Model Champion / Challenger Framework

## Status

COMPLETE LOCALLY — DEDICATED REGRESSION CLEAN

## Purpose

Phase 59 establishes an explicit Champion / Challenger role framework on top of the Phase 58 Model Comparison report.

The framework represents model roles and attaches comparison evidence to those roles.

It does not execute promotion, demotion, rollback, retraining, or production traffic changes.

## Version

CHAMPION_CHALLENGER_VERSION = 59.0.0

## Role Model

Two active roles are supported:

- CHAMPION
- CHALLENGER

A champion represents the explicitly assigned incumbent role.

A challenger represents an explicitly assigned comparison candidate.

Role assignment is explicit input to the framework. The framework does not infer a champion from health scores.

## Assignment Contract

Each ModelRoleAssignment contains:

- model_identity
- role
- state
- assignment_reason
- source_identity

Supported states:

- ACTIVE
- INACTIVE

The report requires:

- exactly one active champion
- at least one active challenger
- unique model identities across champion and challengers

## Eligibility Boundary

Champion and challenger models must exist in the Phase 58 comparison report's common-model set.

This ensures that role assignments have comparable baseline/comparison evidence.

Models that exist only in one comparison period cannot be assigned to an active Champion / Challenger role by this phase.

## Evidence Contract

Each challenger receives explicit evidence against the champion:

- challenger health score
- champion health score
- absolute change versus champion
- relative change versus champion
- Phase 58 comparison report identity

Absolute change:

challenger_health_score - champion_health_score

Relative change:

absolute_change / abs(champion_health_score)

When the champion score is effectively zero, relative change is represented as None.

## Important Decision Boundary

Phase 59 intentionally does NOT:

- select the champion automatically
- select the challenger automatically
- rank challengers
- declare a winner
- calculate a promotion score
- promote a challenger
- demote a champion
- change traffic allocation
- retrain models
- rollback models
- alter predictions

The champion and challenger roles are explicit assignments.

This keeps role representation separate from future model-selection and promotion policy.

## Model Accounting

The report exposes:

- eligible_models
- inactive_models

Eligible models are the assigned champion plus assigned challengers.

Inactive common models remain represented separately.

## Core Classes

- ModelRoleAssignment
- ChampionChallengerEvidence
- ChampionChallengerReport
- ChampionChallengerValidationResult

## Public APIs

- build_champion_challenger_report()
- champion_challenger_summary()
- champion_challenger_evidence()
- champion_challenger_models()
- validate_champion_challenger_report()

## Source Lineage

The Phase 58 ModelComparisonReport identity is preserved as:

comparison_source_identity

Every evidence record also preserves the same comparison source identity.

This provides deterministic lineage from:

Phase 59 role framework
        ↓
Phase 58 temporal comparison
        ↓
Phase 57 model health
        ↓
Monitoring layers

## Deterministic Identity

Report identity is a SHA-256 digest of:

- Phase 59 version
- framework ID
- comparison source identity
- baseline period
- comparison period
- champion assignment
- challenger assignments
- evidence values
- eligible models
- inactive models

Identical inputs produce identical identities.

Changes to role assignment or evidence inputs change the report identity.

## Strict Validation

Validation covers:

- report type
- version
- framework identity
- comparison source identity
- periods
- champion assignment
- champion role
- champion active state
- challenger presence
- challenger roles
- challenger active states
- duplicate role models
- evidence/challenger reconciliation
- evidence champion identity
- evidence score bounds
- evidence absolute change
- evidence relative change
- evidence source lineage
- eligible-model collection
- inactive-model uniqueness
- deterministic identity prefix

## Dedicated Regression

- 70 passed
- 0 failures
- 0 errors
- 0 warnings

Coverage includes:

- champion assignment
- challenger assignment
- active-state validation
- role validation
- model eligibility
- source lineage
- score evidence
- absolute/relative evidence
- zero champion-score behavior
- deterministic identity
- strict validation
- invalid-input regression
- no-promotion boundary
- no-selection-score boundary
- immutable report contracts

## Production Outputs

- analytics/champion_challenger.py
- tests/test_champion_challenger.py
- docs/PHASE_59_MODEL_CHAMPION_CHALLENGER_FRAMEWORK.md

## Next Phase

Phase 60 — Model Selection / Promotion Framework
