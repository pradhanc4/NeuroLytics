NeuroLytics — Changelog

All notable NeuroLytics development milestones are recorded here.

The project follows a SQL-first, test-driven development workflow.

[Unreleased]

Current Development State

NeuroLytics has completed Phases 1 through 13 of the approved roadmap.

Latest full regression:

2880 passed in 11.09s

No known regression failures remain.

GitHub release work is pending repository review.

Phase 13 — Leakage-Safe Feature Framework

Status

COMPLETE

Summary

Phase 13 established the feature-engineering foundation required to convert SQL historical data into point-in-time-correct, validated, reproducible feature datasets.

Implemented:

historical data loading

point-in-time correctness

feature configuration

lag features

rolling features

recency features

position features

frequency features

sequence features

cross-position features

unified feature datasets

feature schemas

schema building

feature validation

leakage detection

feature versioning

pipeline orchestration

dataset contracts

feature artifacts

artifact integrity

No model training or ranking functionality was added as part of Phase 13.

Historical Data Loader

Added:

features/historical_data_loader.py

Implemented SQL historical-result loading, historical observation conversion, market validation, historical-result validation, position validation, and chronological ordering.

Point-in-Time History

Added:

features/point_in_time.py

For target date T, only:

result_date < T

is included.

Target-date and future observations are excluded.

Duplicate historical dates are rejected.

Feature Configuration

Added:

features/feature_config.py

Supports feature version, positions, lag windows, rolling windows, frequency settings, recency settings, and position-feature settings.

Lag Features

Added:

features/lag_features.py

Supports configurable historical lag features such as:

col1_lag_1
col1_lag_2
col1_lag_3

Rolling Features

Added:

features/rolling_features.py

Supports mean, minimum, and maximum over configurable point-in-time windows.

Recency Features

Added:

features/recency_features.py

Supports observations-since-last-seen and seen-within-lookback for digits 0–9.

Position Features

Added:

features/position_features.py

Supports latest value, parity, zero state, high state, historical mean, minimum, and maximum.

Frequency Features

Added:

features/frequency_features.py

Supports digit counts and percentages using the existing statistical frequency engine.

Sequence Features

Added:

features/sequence_features.py

Supports previous value, latest value, transition, transition distance, changed state, latest transition count, and latest transition percentage.

Sequence features were namespaced to prevent collision with position features.

Example:

col1_sequence_latest_value
col1_sequence_transition

Unified Feature Dataset

Added:

features/unified_dataset.py

Provides feature records, names, values, types, sources, feature count, and global duplicate-name validation.

Feature Schema

Added:

features/feature_schema.py

Metadata includes feature name, version, type, source, position, window, lag, description, availability rule, and data type.

Feature Schema Builder

Added:

features/feature_schema_builder.py

Provides schema generation, validation, deterministic ordering, and duplicate detection.

Feature Validator

Added:

features/feature_validator.py

Validates feature names, types, sources, schemas, duplicate names, metadata, and structure.

Focused tests:

36 passed

Leakage Detector

Added:

features/leakage_detector.py

Leakage categories:

FUTURE_ROW
TARGET_DATE_INCLUDED
DUPLICATE_DATE
TEMPORAL_ORDER

Statuses:

CLEAN
LEAKAGE

Focused tests:

34 passed

Feature Versioning

Added:

features/feature_versioning.py

Uses deterministic SHA-256 identity.

Focused tests:

39 passed

Feature Pipeline

Added:

features/feature_pipeline.py

Pipeline:

SQL
 ↓
Historical Loader
 ↓
Point-in-Time History
 ↓
Unified Features
 ↓
Schemas
 ↓
Validation
 ↓
Leakage Detection
 ↓
Version Identity

Focused tests:

31 passed

Feature Dataset Contract

Added:

features/feature_dataset_contract.py

Validates target date, feature version, feature count, schema count, feature names, schema alignment, validation status, leakage status, and version identity.

A valid contract requires:

validation = VALID
leakage = CLEAN

Focused tests:

38 passed

Feature Artifact

Added:

features/feature_artifact.py

Provides an immutable reproducible feature representation containing target date, feature version, feature names, feature values, schemas, version identity, validation status, and leakage status.

Focused tests:

37 passed

Artifact Integrity

Added:

features/artifact_integrity.py

Uses SHA-256 for deterministic artifact integrity.

Focused tests:

29 passed

Phase 13 — Corrections

Sequence / Position Feature Name Collision

Position and Sequence Features initially generated duplicate names such as:

col1_latest_value

The duplicate validator was not weakened.

Sequence features were namespaced:

col1_sequence_latest_value

This preserves global feature-name uniqueness.

Frequency Feature Integration

The initial frequency feature implementation passed HistoricalFeatureObservation directly into the existing statistical frequency engine.

The existing engine expects StatisticalObservation with a column_name.

An explicit adapter was added in the feature layer.

The existing analytics engine was reused rather than duplicated.

Final frequency feature tests:

19 passed

Feature Validator Correction

Duplicate-name/schema errors were changed to structured validation failures instead of escaping as exceptions.

Final validator tests:

36 passed

Phase 13 — Final Verification

Final project-wide regression:

2880 passed in 11.09s

Result:

0 failed
0 errors

Phase 9 — Frequency / Statistical Analysis

Phase 9.1

Implemented statistical observation contracts, analysis-column validation, observation extraction, result structures, type validation, zero handling, and NULL handling.

Focused tests:

17 passed

Full regression:

395 passed

Phase 9.2

Implemented digit frequency analysis, all-position frequency analysis, frequency lookup, explicit digits 0–9, zero handling, and missing-value handling.

Focused tests:

11 passed

Full regression:

406 passed

Phase 9.3

Expanded statistical analysis into position-wise analytics including frequency, summaries, distributions, distribution comparison, comparison metrics/matrices/summaries, stability analysis/summaries/comparison, temporal position analysis, change detection/classification/summaries, distribution regime detection/transitions/overview, consolidation, quality reporting, and quality summaries.

Final milestone:

9.3.75

Final recorded Phase 9.3 regression:

2342 passed

Phase 9.3 was intentionally paused without inventing additional milestones.

Phase 8 — Data Validation & Quality

Implemented historical quality model, rules, service, checker, reports, NULL detection, zero validation, duplicate dates, missing calendar dates, structural validation, and VALID/WARNING/INVALID states.

Final regression:

378 passed

Phase 7 — Historical Classification

Implemented versioned structural classification, zero presence, digit sum, parity, order, Jodi structure, Open/Close relationship, digit overlap, lookup, date-range lookup, validation, and leading-zero preservation.

Focused tests:

73 passed

Full regression:

292 passed

Phase 6 — Panel Family Reference

Implemented Panel Family/member models and services, search/filtering, duplicate protection, leading-zero preservation, relationship analysis, reverse relationships, same-position relationships, digit-sum relationships, and summaries.

Panel-specific tests:

85 passed

Full regression:

219 passed

Phase 5 — Jodi Family Reference

Implemented SQL-backed Jodi Family infrastructure including family/member models, lookup, search, filtering, duplicate protection, structural analysis, relationships, summaries, and validation.

Phase 4 — Panna / Panel Reference

Implemented Panna SQL storage, validation, normalization, leading-zero preservation, active/inactive status, lookup, search, filtering, and structural digit analysis.

Verification:

73 passed

Phase 3 — Historical Input / Parser

Implemented historical input service, validation, parser, Open/Jodi/Close handling, SQL persistence, automatic col1–col8 derivation, leading-zero preservation, duplicate market/date protection, retrieval, and error handling.

Verification:

36 passed

Phase 2 — SQL Database Foundation

Implemented SQLAlchemy/SQLite foundation, database engine, sessions, models, initialization, services, parser integration, uniqueness protection, and leading-zero preservation.

Phase 1 — Project Architecture & Environment

Established project structure, Python environment, dependency management, .gitignore, .env.example, README, test foundation, database foundation, analytics foundation, ML foundation, feature foundation, ranking foundation, backtesting foundation, frontend foundation, and documentation foundation.

Architecture:

SQL-first, local development

Current Roadmap Status

Phase 1   COMPLETE
Phase 2   COMPLETE
Phase 3   COMPLETE
Phase 4   COMPLETE
Phase 5   COMPLETE
Phase 6   COMPLETE
Phase 7   COMPLETE
Phase 8   COMPLETE
Phase 9   COMPLETE
Phase 10  NOT INDEPENDENTLY CLOSED
Phase 11  NOT INDEPENDENTLY CLOSED
Phase 12  NOT INDEPENDENTLY CLOSED
Phase 13  COMPLETE
Phase 14+ NOT STARTED

Current Engineering Rules

SQL is the source of truth.

Do not fabricate missing data.

0 is a valid digit.

NULL is distinct from zero.

Future observations cannot be used for historical features.

Duplicate dates are rejected where required.

Feature names must be globally unique.

Feature definitions are versioned.

Feature artifacts are reproducible.

Artifact integrity is deterministic.

Existing analytics should be reused instead of duplicated.

Phase completion requires explicit scope verification.

GitHub Release Status

Before GitHub release:

review all changed files

review README

review PROJECT_STATUS.md

review CHANGELOG.md

review Phase 9 documentation

review Phase 13 documentation

run full regression

inspect Git status

review staged changes

commit

push only after explicit release confirmation

Latest verified regression:

2880 passed in 11.09s