# NeuroLytics — Changelog

All notable NeuroLytics development milestones are recorded here.

The project follows a SQL-first, test-driven development workflow.

---

# [Unreleased]

## Current Development State

NeuroLytics has completed Phase 14 of the currently implemented feature-engineering roadmap.

Phases 1–9 are complete.

Phase 9.3 is complete/paused at milestone 9.3.75.

Phases 10–12 contain related accumulated analytics functionality but are not independently closed.

Phase 13 — Leakage-Safe Feature Framework is COMPLETE.

Phase 14 — Time / Frequency / Recency Feature Expansion is COMPLETE.

Latest Phase 14 focused regression:

358 passed in 1.39s

Latest full project regression:

3206 passed in 41.58s

No known regression failures remain.

GitHub release work is pending repository review and explicit release confirmation.

---

# Phase 14 — Time / Frequency / Recency Feature Expansion

## Status

COMPLETE

## Summary

Phase 14 expanded the Phase 13 point-in-time feature framework with deterministic time, cyclical time, historical interval, observation density, frequency, frequency change, concentration/diversity, recency, recency distribution, recency bucket, and change/trend features.

The phase extends the existing feature architecture.

No parallel feature pipeline was introduced.

No model training, prediction, ranking, or UI functionality was added.

All historical feature calculations preserve the Phase 13 point-in-time rule:

result_date < target_date

Target-date and future observations are excluded.

---

# Phase 14.1 — Foundation / Configuration

## Status

COMPLETE

Expanded:

features/feature_config.py

Added configuration support for:

- time features
- cyclical time features
- historical interval features
- observation density
- observation density windows
- frequency windows
- frequency comparison windows
- frequency diversity/concentration
- recency lookbacks
- recency calendar behavior
- recency distribution
- recency buckets
- recency bucket boundaries
- change features
- trend features
- trend windows

Configuration validation was extended while preserving existing Phase 13 validation contracts.

Existing Phase 13 tests remained compatible.

---

# Phase 14.2 — Time Features

## Status

COMPLETE

Added:

features/time_features.py

Implemented deterministic calendar features:

- day of week
- day of week number
- day of month
- day of year
- ISO week
- month
- month name
- quarter
- year

Time features are derived from the target date.

---

# Phase 14.3 — Cyclical Time Features

## Status

COMPLETE

Extended:

features/time_features.py

Implemented cyclical representations using sine/cosine transformations for:

- day of week
- day of month
- day of year
- ISO week
- month
- quarter

Day-of-year calculations preserve leap-year behavior.

Cyclical feature names are deterministic.

---

# Phase 14.4 — Historical Interval Features

## Status

COMPLETE

Added:

features/historical_interval_features.py

Implemented:

- historical_interval_days_since_last
- historical_interval_days_since_first
- historical_interval_span_days
- historical_interval_mean_days
- historical_interval_min_days
- historical_interval_max_days
- historical_interval_std_days

Only unique historical dates before the target date are considered.

No-history and single-observation cases are handled explicitly.

---

# Phase 14.5 — Observation Density Features

## Status

COMPLETE

Added:

features/observation_density_features.py

Default calendar windows:

- 7
- 14
- 30
- 60
- 90 days

Implemented:

- observation count per window
- observation rate per window
- total historical observation count
- historical span
- overall observation rate
- average historical interval
- historical interval standard deviation

Target-date and future observations are excluded.

Duplicate historical dates are handled as unique dates for density calculations.

---

# Phase 14.6 — Historical Frequency Expansion

## Status

COMPLETE

Added:

features/historical_frequency_features.py

Expanded historical frequency analysis for configured observation-count windows.

For every configured position and digit 0–9:

- frequency count
- frequency percentage

Deterministic feature naming was introduced.

Example:

position_frequency_count_window_digit

position_frequency_percentage_window_digit

The existing Phase 9 statistical frequency engine is reused through an explicit observation adapter.

---

# Phase 14.7 — Rolling Frequency

## Status

COMPLETE

Added:

features/rolling_frequency_features.py

Implemented trailing observation-count frequency percentages for digits 0–9 across configured positions and windows.

Feature values use percentage units:

0–100

Only historical observations before the target date are included.

---

# Phase 14.8 — Frequency Change

## Status

COMPLETE

Added:

features/frequency_change_features.py

Implemented comparison between recent and older historical frequency windows.

Definition:

recent frequency percentage - older frequency percentage

All digits 0–9 are represented.

Feature names include:

- comparison index
- older window
- recent window
- digit

Configured comparisons are deterministic and independently evaluated.

---

# Phase 14.9 — Frequency Concentration / Diversity

## Status

COMPLETE

Added:

features/frequency_concentration_features.py

Reused the existing Phase 9.3 distribution-regime implementation.

Implemented:

- dominant digit
- dominant digit percentage
- entropy
- normalized entropy
- concentration level
- diversity level

Normalized entropy:

entropy / log2(10)

Existing regime categories remain authoritative:

- CONCENTRATED
- BALANCED
- DIVERSE
- INSUFFICIENT_DATA

Dominant-digit ties use deterministic lower-digit tie resolution.

---

# Phase 14.10 — Recency Expansion

## Status

COMPLETE

Added:

features/recency_expansion_features.py

For each configured position, digit, and lookback:

- occurrence count
- occurrence rate
- observations since last seen
- seen within lookback

Latest matching historical observation has distance 0.

Unseen digits remain explicitly unavailable.

---

# Phase 14.11 — Recency Distribution

## Status

COMPLETE

Added:

features/recency_distribution_features.py

For each configured position, digit, and lookback:

- count
- rate
- mean distance
- minimum distance
- maximum distance
- standard deviation
- distance span

Population standard deviation is used.

No matching observations produce explicit unavailable statistical values rather than fabricated values.

---

# Phase 14.12 — Recency Buckets

## Status

COMPLETE

Added:

features/recency_bucket_features.py

Default bucket boundaries:

3
7
14

Default labels:

- RECENT_0_3
- RECENT_4_7
- RECENT_8_14
- STALE_15_PLUS
- UNSEEN

Implemented:

- bucket label
- bucket index
- recent indicators
- stale indicator
- unseen indicator

UNSEEN uses a distinct index from normal recency buckets.

During comprehensive testing, the implementation was reviewed for bucket-index correctness.

Unused internal code was removed without changing expected behavior.

Focused tests:

25 passed

---

# Phase 14.13 — Change & Trend

## Status

COMPLETE

Added:

features/change_trend_features.py

Implemented position-level change features:

- change
- absolute change
- change direction
- changed state

Implemented configurable trend-window features:

- mean
- minimum
- maximum
- range
- standard deviation
- change
- slope

Trend slope uses least-squares calculation over chronological observation indexes.

Target-date and future observations are excluded.

Zero remains a valid observed value.

Focused tests:

33 passed

---

# Phase 14.14 — Unified Integration

## Status

COMPLETE

Integrated Phase 14 feature families into:

features/unified_dataset.py

Integrated feature types:

- time
- historical_interval
- observation_density
- historical_frequency
- rolling_frequency
- frequency_change
- frequency_concentration
- recency_expansion
- recency_distribution
- recency_bucket
- change_trend

The unified dataset continues to provide:

- feature names
- feature values
- feature types
- sources
- deterministic ordering
- global duplicate-name validation

Unified dataset tests:

40 passed

---

# Phase 14.15 — Schema / Validation / Leakage Integration

## Status

COMPLETE

Extended:

features/feature_schema.py

features/feature_schema_builder.py

Phase 14 feature types are now represented by the feature schema system.

Schema Builder supports applicable Phase 14 window metadata.

Existing validation infrastructure continues to enforce:

- feature names
- duplicate names
- feature/schema counts
- name alignment
- schema versions
- schema definitions
- supported value types
- metadata
- deterministic ordering

Leakage detection continues to enforce:

- future-row exclusion
- target-date exclusion
- duplicate-date detection
- chronological ordering

Verification:

Schema Builder: 33 passed

Feature Validator: 36 passed

Leakage Detector: 34 passed

Feature Pipeline: 31 passed

Feature Dataset Contract: 38 passed

Unified Dataset: 40 passed

Feature Artifact: 37 passed

Artifact Integrity: 29 passed

Full regression after Phase 14.15:

3206 passed

---

# Phase 14.16 — Comprehensive Testing

## Status

COMPLETE

Executed the complete Phase 14 focused test suite covering:

- feature configuration
- time features
- cyclical time features
- historical interval features
- observation density
- historical frequency expansion
- rolling frequency
- frequency change
- frequency concentration/diversity
- recency expansion
- recency distribution
- recency buckets
- change/trend
- unified dataset integration

Phase 14 focused result:

358 passed in 1.39s

A complete project-wide regression was then executed.

Final full regression:

3206 passed in 41.58s

Result:

0 failed

0 errors

---

# Phase 14.17 — Documentation / Release

## Status

COMPLETE

Updated project documentation to reflect the completion of Phase 14.

Documentation coverage includes:

- Phase 14 scope
- Phase 14 architecture
- Phase 14 feature families
- Phase 14 configuration
- unified feature integration
- schema integration
- validation integration
- leakage integration
- comprehensive testing
- final regression
- roadmap status
- release status

Final verification:

Phase 14 focused suite:

358 passed in 1.39s

Full project regression:

3206 passed in 41.58s

GitHub commit/push remains pending explicit release confirmation.

---

# Phase 14 — Final Architecture

SQL HistoricalResult
        ↓
Historical Data Loader
        ↓
Point-in-Time History
        ↓
Phase 13 Feature Engines
        ├── Lag
        ├── Rolling
        ├── Recency
        ├── Position
        ├── Frequency
        ├── Sequence
        └── Cross-Position
        ↓
Phase 14 Feature Engines
        ├── Time
        ├── Cyclical Time
        ├── Historical Interval
        ├── Observation Density
        ├── Historical Frequency
        ├── Rolling Frequency
        ├── Frequency Change
        ├── Frequency Concentration / Diversity
        ├── Recency Expansion
        ├── Recency Distribution
        ├── Recency Buckets
        └── Change / Trend
        ↓
Unified Feature Dataset
        ↓
Feature Schema
        ↓
Feature Validation
        ↓
Leakage Detection
        ↓
Feature Versioning
        ↓
Feature Pipeline
        ↓
Feature Dataset Contract
        ↓
Feature Artifact
        ↓
Artifact Integrity
        ↓
Future ML / Evaluation / Ranking Layers

---

# Phase 14 — Implemented Modules

features/feature_config.py

features/time_features.py

features/historical_interval_features.py

features/observation_density_features.py

features/historical_frequency_features.py

features/rolling_frequency_features.py

features/frequency_change_features.py

features/frequency_concentration_features.py

features/recency_expansion_features.py

features/recency_distribution_features.py

features/recency_bucket_features.py

features/change_trend_features.py

Updated integration:

features/unified_dataset.py

features/feature_schema.py

features/feature_schema_builder.py

Existing validation/integrity infrastructure:

features/feature_validator.py

features/leakage_detector.py

features/feature_pipeline.py

features/feature_dataset_contract.py

features/feature_artifact.py

features/artifact_integrity.py

---

# Phase 14 — Engineering Decisions

## SQL Source of Truth

SQL remains the production source of truth.

Phase 14 does not introduce CSV as a production source.

## Point-in-Time Safety

For target date T:

result_date < T

Only observations strictly before the target date contribute to historical features.

## No Fabricated Historical Data

Phase 14 was engineered and tested using controlled fixtures and the existing historical data structures.

No fabricated real-world historical observations are used as evidence of predictive performance.

Real historical data can be loaded later through the existing SQL historical input system.

## Zero Handling

Digit 0 is a valid observed value.

Zero is never converted into missing data.

## NULL Handling

NULL remains distinct from zero.

## Missing History

Insufficient historical information is represented explicitly.

Features do not invent observations to fill missing history.

## Analytics Reuse

Existing Phase 9 statistical and distribution engines are reused where appropriate.

Duplicate analytics implementations are avoided.

## Deterministic Naming

Phase 14 feature names are deterministic and globally validated.

## Versioning

Phase 14 participates in the existing feature versioning and artifact integrity architecture.

---

# Phase 13 — Leakage-Safe Feature Framework

## Status

COMPLETE

Phase 13 established the feature-engineering foundation required to convert SQL historical data into point-in-time-correct, validated, reproducible feature datasets.

Implemented:

- historical data loading
- point-in-time correctness
- feature configuration
- lag features
- rolling features
- recency features
- position features
- frequency features
- sequence features
- cross-position features
- unified feature datasets
- feature schemas
- schema building
- feature validation
- leakage detection
- feature versioning
- pipeline orchestration
- dataset contracts
- feature artifacts
- artifact integrity

No model training or ranking functionality was added as part of Phase 13.

Final Phase 13 regression:

2880 passed in 11.09s

---

# Phase 9 — Frequency / Statistical Analysis

## Phase 9.1

Implemented statistical observation contracts, analysis-column validation, observation extraction, result structures, type validation, zero handling, and NULL handling.

Focused tests:

17 passed

Full regression:

395 passed

## Phase 9.2

Implemented digit frequency analysis, all-position frequency analysis, frequency lookup, explicit digits 0–9, zero handling, and missing-value handling.

Focused tests:

11 passed

Full regression:

406 passed

## Phase 9.3

Expanded statistical analysis into position-wise analytics including:

- frequency
- summaries
- distributions
- distribution comparison
- comparison metrics/matrices/summaries
- stability analysis
- temporal position analysis
- change detection
- distribution regime detection
- distribution transitions
- distribution overview
- position analytics consolidation
- quality reporting
- quality summaries

Final milestone:

9.3.75

Final recorded Phase 9.3 regression:

2342 passed

Phase 9.3 was intentionally paused without inventing additional milestones.

---

# Phase 8 — Data Validation & Quality

Implemented historical quality model, rules, service, checker, reports, NULL detection, zero validation, duplicate dates, missing calendar dates, structural validation, and VALID/WARNING/INVALID states.

Final regression:

378 passed

---

# Phase 7 — Historical Classification

Implemented versioned structural classification, zero presence, digit sum, parity, order, Jodi structure, Open/Close relationship, digit overlap, lookup, date-range lookup, validation, and leading-zero preservation.

Focused tests:

73 passed

Full regression:

292 passed

---

# Phase 6 — Panel Family Reference

Implemented Panel Family/member models and services, search/filtering, duplicate protection, leading-zero preservation, relationship analysis, reverse relationships, same-position relationships, digit-sum relationships, and summaries.

Panel-specific tests:

85 passed

Full regression:

219 passed

---

# Phase 5 — Jodi Family Reference

Implemented SQL-backed Jodi Family infrastructure including family/member models, lookup, search, filtering, duplicate protection, structural analysis, relationships, summaries, and validation.

---

# Phase 4 — Panna / Panel Reference

Implemented Panna SQL storage, validation, normalization, leading-zero preservation, active/inactive status, lookup, search, filtering, and structural digit analysis.

Verification:

73 passed

---

# Phase 3 — Historical Input / Parser

Implemented historical input service, validation, parser, Open/Jodi/Close handling, SQL persistence, automatic col1–col8 derivation, leading-zero preservation, duplicate market/date protection, retrieval, and error handling.

Verification:

36 passed

---

# Phase 2 — SQL Database Foundation

Implemented SQLAlchemy/SQLite foundation, database engine, sessions, models, initialization, services, parser integration, uniqueness protection, and leading-zero preservation.

---

# Phase 1 — Project Architecture & Environment

Established project structure, Python environment, dependency management, .gitignore, .env.example, README, test foundation, database foundation, analytics foundation, ML foundation, feature foundation, ranking foundation, backtesting foundation, frontend foundation, and documentation foundation.

Architecture:

SQL-first, local development

---

# Current Roadmap Status

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

Phase 14  COMPLETE

Phase 15–76  NOT STARTED

---

# Current Engineering Rules

SQL is the source of truth.

Do not fabricate missing data.

0 is a valid digit.

NULL is distinct from zero.

Future observations cannot be used for historical features.

Target-date observations cannot be used for historical features.

Duplicate dates are rejected where required.

Feature names must be globally unique.

Feature definitions are versioned.

Feature artifacts are reproducible.

Artifact integrity is deterministic.

Existing analytics should be reused instead of duplicated.

Phase completion requires explicit scope verification.

Phase 14 does not include model training, prediction, ranking, or UI.

Real historical data can be introduced later without redesigning the Phase 14 feature architecture.

---

# GitHub Release Status

Before GitHub release:

1. Review all changed files
2. Review README
3. Review PROJECT_STATUS.md
4. Review CHANGELOG.md
5. Review Phase 9 documentation
6. Review Phase 13 documentation
7. Review Phase 14 documentation
8. Run Phase 14 focused regression
9. Run full regression
10. Inspect Git status
11. Review staged changes
12. Confirm release contents
13. Commit only after explicit confirmation
14. Push only after explicit release confirmation

Current release state:

Phase 14 implementation: COMPLETE

Phase 14 testing: COMPLETE

Phase 14 documentation: COMPLETE

Git commit/push: PENDING EXPLICIT RELEASE CONFIRMATION

Latest verified full regression:

3206 passed in 41.58s