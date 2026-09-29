# NeuroLytics — Changelog

All notable NeuroLytics development milestones are recorded here.

The project follows a SQL-first, test-driven development workflow.

---

## 2026-09-30 — Phase 31: GRU

### Status

COMPLETE LOCALLY

### Added

- analytics/gru.py
- tests/test_gru.py
- docs/PHASE_31_GRU.md

### Capabilities

- deterministic NumPy GRU classifier
- GRU update, reset, and candidate/new-state gates
- one-hot digit sequence encoding for digits 0–9
- chronological dataset splitting
- backpropagation through time
- gradient clipping
- deterministic training
- training history and early stopping
- next-digit probability prediction
- Top-K next-digit prediction
- log-likelihood and evaluation metrics
- position-wise GRU models
- baseline log-loss comparison
- deterministic artifact identity
- model validation
- joblib persistence/loading
- artifact lineage validation
- reproducibility checks

### Verification

Phase 31 focused regression: 46 passed, 0 warnings.

Full project regression: 4849 passed in 59.77s, 0 failures, 0 errors, 0 warnings.

Previous baseline: 4803 passed.

Phase 31 increase: +46 tests.

GRU model version: 31.0.0.

Model kind: gru.

No new third-party dependency was added.

### Release

No GitHub commit or push was performed.

### Next

Phase 32 — Transformer

---

# [Unreleased]

## 2026-09-30 - Phase 30 LSTM

- Phase 30 is COMPLETE LOCALLY.
- Added `analytics/lstm.py` with version `30.0.0` and model kind `lstm`.
- Added `tests/test_lstm.py` with 46 dedicated regression tests.
- Implemented deterministic NumPy LSTM training with recurrent gates, backpropagation-through-time, gradient clipping, early stopping, best-state restore, sequence-window prediction, evaluation metrics, position-wise models, chronological splitting, artifact identity, validation, persistence/loading, lineage validation, and reproducibility.
- No new third-party dependency was required.
- Dedicated regression: 46 passed, 0 warnings.
- Full project regression: 4803 passed in 59.55s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4757 passed.
- Regression increase: +46 tests.
- Phase 31 is next on the roadmap.
- GitHub commit/push was not performed.

## 2026-09-30 - Phase 29 Hidden Markov Models (HMM)

- Phase 29 is COMPLETE LOCALLY.
- Added `analytics/hidden_markov_models.py` with model version `29.0.0`.
- Added `tests/test_hidden_markov_models.py` with 71 dedicated regression tests.
- Implemented deterministic discrete HMMs with configurable latent state count, 10 observed digit symbols, deterministic initialization, scaled forward/backward inference, posterior state probabilities, Viterbi decoding, Baum-Welch training, convergence tracking, next-observation probabilities, Top-K prediction, log-likelihood, accuracy/log-loss evaluation, position-wise models, baseline comparison, deterministic artifact identity, validation, persistence/loading, lineage validation, and reproducibility.
- Digit `0` remains a valid observed symbol.
- No new third-party dependency was required beyond the existing project environment.
- Dedicated regression: 71 passed, 0 warnings.
- Full project regression: 4757 passed in 68.65s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4686 passed.
- Regression increase: +71 tests.
- Phase 31 - GRU is next.
- GitHub commit/push was not performed.

## 2026-09-30 - Phase 28 Markov Models

- Phase 28 is COMPLETE LOCALLY.
- Added `analytics/markov_models.py` with model version `28.0.0`.
- Added `tests/test_markov_models.py` with 52 dedicated regression tests.
- Implemented configurable order-1 through order-10 categorical Markov chains over digits 0-9.
- Implemented transition counts, smoothed transition probabilities, explicit zero handling, next-state prediction, probability prediction, log-likelihood, accuracy/log-loss evaluation, position-wise models, baseline comparison, deterministic artifact identity, validation, persistence/loading, artifact lineage validation, reproducibility, and stationary-distribution propagation.
- No new third-party dependency was required.
- Dedicated regression: 52 passed, 0 warnings.
- Full project regression: 4686 passed in 67.21s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4634 passed.
- Regression increase: +52 tests.
- Phase 29 - Hidden Markov Models is next.
- GitHub commit/push was not performed.

## 2026-09-30 - Phase 27 CatBoost

- Phase 27 is COMPLETE LOCALLY.
- Added `analytics/catboost.py` with model version `27.0.0` and runtime version `1.2.10`.
- Added `tests/test_catboost.py` with 46 dedicated regression tests.
- Added pinned dependency `catboost==1.2.10`.
- Implemented CatBoost configuration, dataset contract, validation, sequence adapter, chronological splitting, binary/multiclass objectives, training, early stopping, probability prediction, evaluation, feature importance, position models, baseline comparison, deterministic artifact identity, persistence, version-reference validation, and reproducibility.
- Dedicated regression: 46 passed, 0 warnings.
- Full project regression: 4634 passed in 149.50s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4588 passed.
- Regression increase: +46 tests.
- Phase 28 is next.
- GitHub commit/push was not performed.


## 2026-09-30 - Phase 26 LightGBM

- Phase 26 is COMPLETE LOCALLY.
- Added `analytics/lightgbm.py` with version `26.0.0`.
- Added `tests/test_lightgbm.py` with 44 dedicated regression tests.
- Added pinned dependency `lightgbm==4.6.0`.
- Implemented LightGBM configuration, dataset contract, validation, sequence adapter, chronological splitting, binary/multiclass objectives, training, early stopping, probability prediction, evaluation, feature importance, position models, baseline comparison, deterministic artifact identity, persistence, version-reference validation, and reproducibility.
- Dedicated regression: 44 passed, 0 warnings.
- Full project regression: 4588 passed in 74.00s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4544 passed.
- Regression increase: +44 tests.
- Phase 27 - CatBoost is next.
- GitHub commit/push was not performed.


## 2026-09-30 ? Phase 24 Warning Cleanup

- Resolved the remaining 24 project regression warnings from the Phase 24 validation baseline.
- Updated Logistic Regression construction to preserve the NeuroLytics penalty configuration contract while using sklearn 1.9.1's non-deprecated `l1_ratio` / `C` representation.
- Preserved L2, L1, Elastic Net, and no-penalty configuration behavior.
- Updated Random Forest and Extra Trees fractional `max_samples` regression fixtures to use sufficiently sized datasets, preserving fractional bootstrap coverage without sklearn low-sample warnings.
- Focused regression: 95 passed, 0 warnings.
- Full project regression: 4506 passed in 71.58s, 0 warnings, 0 failures, 0 errors.
- Phase 25 ? XGBoost is next.
- GitHub commit/push was not performed.

## 2026-09-30 - Phase 25 XGBoost

- Phase 25 is COMPLETE LOCALLY.
- Added `analytics/xgboost.py` with version `25.0.0`.
- Added `tests/test_xgboost.py` with 38 dedicated regression tests.
- Added pinned dependency `xgboost==3.0.5`.
- Implemented XGBoost configuration, dataset contract, validation, sequence adapter, chronological splitting, binary/multiclass objectives, training, early stopping, probability prediction, evaluation, feature importance, position models, baseline comparison, artifact identity, persistence, version-reference validation, and reproducibility.
- Dedicated regression: 38 passed, 0 warnings.
- Full project regression: 4544 passed in 75.27s, 0 failures, 0 errors, 0 warnings.
- Previous baseline: 4506 passed.
- Regression increase: +38 tests.
- Phase 26 - LightGBM is next.
- GitHub commit/push was not performed.

## Current Development State

NeuroLytics has completed Phase 26 of the currently implemented ML model roadmap.

Phases 1–9 are complete.

Phase 9.3 is complete/paused at milestone 9.3.75.

Phases 10–12 contain related accumulated analytics functionality but are not independently closed.

Phase 13 — Leakage-Safe Feature Framework is COMPLETE.

Phase 14 — Time / Frequency / Recency Feature Expansion is COMPLETE.

Phase 15 — Family / Relationship / Transition Features is COMPLETE.

Phase 16 — Sequence Dataset Builder is COMPLETE.

Phase 17 — Feature / Dataset Versioning is COMPLETE.

Phase 18 — Statistical Baseline is COMPLETE.

Phase 19 — Bayesian Models is COMPLETE.

Phase 20 — Logistic Regression is COMPLETE.

Phase 21 — Decision Tree is COMPLETE locally.

Phase 22 — Random Forest is COMPLETE locally.

Phase 22 dedicated regression: 31 passed, 1 warning in 1.36s.

Phase 22 full project regression: 4437 passed in 71.47s, 0 failures, 0 errors, 23 warnings.

Phase 22 dedicated regression: 31 passed, 1 warning in 1.36s.

Phase 22 adds deterministic Random Forest classification, chronological dataset splitting, binary/multiclass support, position-wise forests, bootstrap/OOB controls, feature importance, probability generation, evaluation, baseline comparison, validation, artifact/version integration, persistence/loading, and reproducibility.

Phase 23 — Extra Trees is COMPLETE locally.

Phase 23 dedicated regression: 33 passed, 1 warning in 1.36s.

Phase 23 full project regression: 4470 passed in 74.31s, 0 failures, 0 errors, 24 warnings.

Phase 23 dedicated regression: 33 passed, 1 warning in 1.36s.

Phase 23 adds deterministic Extra Trees classification, chronological dataset splitting, binary/multiclass support, position-wise Extra Trees models, randomized tree/feature controls, bootstrap/OOB controls, feature importance, probability generation, evaluation, Random Forest baseline comparison, validation, artifact/version integration, persistence/loading, and reproducibility.

Phase 21 dedicated regression: 26 passed.

Phase 21 full project regression: 4406 passed in 71.03s.

Phase 21 completed with 0 failures and 0 errors. The existing 22 scikit-learn warnings remain from Phase 20 Logistic Regression deprecation behavior.

Phase 21 adds deterministic Decision Tree classification, chronological splitting, binary/multiclass support, position-wise models, probability generation, evaluation, baseline comparison, validation, artifact/version integration, persistence/loading, and reproducibility.

GitHub release remains pending explicit user confirmation.

Latest Phase 20 focused regression:

31 passed

Latest full project regression:

4380 passed in 71.25s

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


## Phase 16 — Sequence Dataset Builder

### Phase 16.1 — Sequence Dataset Contract / Foundation
Status: COMPLETE

Established the immutable sequence dataset contract.

Implemented:
- `SequenceDatasetConfig`
- `SequenceSample`
- `SequenceDataset`
- sequence length and position contracts
- strict target-date boundary rules
- sequence feature-shape validation

---

### Phase 16.2 — Sequence Window Construction
Status: COMPLETE

Implemented chronological sequence-window construction.

Implemented:
- `SequenceWindow`
- `SequenceWindowDataset`
- deterministic chronological windows
- configurable sequence length
- incomplete-sequence handling
- observation/result/market identity preservation
- duplicate-date and chronological validation

Verification:
- 40 focused tests passed

---

### Phase 16.3 — Target Construction
Status: COMPLETE

Implemented target construction from the observation immediately following each sequence window.

Implemented:
- `SequenceTarget`
- `SequenceTargetDataset`
- target-date alignment
- target position handling
- result/market identity preservation
- strict temporal separation between sequence and target

Verification:
- 42 focused tests passed

---

### Phase 16.4 — Sequence Dataset Validation
Status: COMPLETE

Integrated sequence windows and targets into the validated sequence dataset.

Implemented:
- window/target alignment validation
- sequence sample construction
- complete dataset validation
- sequence length validation
- target-date validation
- target exclusion from input sequence

Verification:
- 41 focused tests passed

---

### Phase 16.5 — Point-in-Time / Leakage Validation
Status: COMPLETE

Implemented sequence-specific point-in-time and leakage validation.

Implemented:
- sequence target boundary validation
- target-in-sequence detection
- future-row detection
- temporal ordering validation
- missing target-date validation
- terminal-window handling
- component-level leakage validation
- dataset-level leakage validation

Verification:
- 27 focused tests passed

---

### Phase 16.6 — Train / Validation Temporal Splitting
Status: COMPLETE

Implemented chronological sequence dataset splitting.

Rules:
- training targets are on or before the configured split date
- validation targets are strictly after the split date
- samples cannot exist in both partitions
- sample ordering remains deterministic

Verification:
- 21 focused tests passed

---

### Phase 16.7 — Sequence Dataset Integration
Status: COMPLETE

Integrated the Phase 16 sequence components without duplicating existing logic.

Integrated:
- sequence windows
- sequence targets
- validated sequence dataset
- point-in-time validation
- temporal splitting

Verification:
- 28 focused tests passed

---

### Phase 16.8 — Dataset Determinism / Reproducibility
Status: COMPLETE

Verified deterministic and reproducible sequence dataset behavior through the Phase 16 comprehensive test suite.

Verified:
- deterministic sequence construction
- deterministic target construction
- deterministic integrated dataset output
- reproducible schema/version information
- reproducible artifact serialization
- reproducible artifact integrity

No random behavior was introduced into the sequence dataset pipeline.

---

### Phase 16.9 — Schema / Artifact Integration
Status: COMPLETE

Integrated the sequence dataset with the existing schema, version identity, artifact serialization, and integrity architecture.

Implemented:
- `SequenceDatasetArtifact`
- sequence artifact integrity
- deterministic canonical serialization
- SHA-256 artifact fingerprinting
- feature schema validation reuse
- feature version identity validation reuse
- leakage-free artifact requirements
- artifact integrity validation

The implementation does not create a replacement for the existing feature artifact infrastructure.

Verification:
- 27 focused tests passed

---

### Phase 16.10 — Comprehensive Phase 16 Testing
Status: COMPLETE

Comprehensive Phase 16 testing covered:

- complete pipeline construction
- sequence contract validation
- window/target alignment
- point-in-time and leakage stress
- temporal split validation
- determinism and reproducibility
- schema/version integration
- artifact integrity
- boundary conditions
- immutability
- invalid input handling
- end-to-end sequence invariants

Verification:

```text
Phase 16.10 comprehensive:
58 passed in 0.26s

Combined Phase 16 regression:
320 passed in 0.77s

Phase 17 — Versioning, Compatibility & Lineage

- Added versioning contract foundation.
- Added feature version identity validation.
- Added dataset version identity.
- Added feature/dataset compatibility validation.
- Added version comparison and change detection.
- Added feature-to-dataset version lineage.
- Added versioned artifact integration.
- Added version reproducibility and determinism validation.
- Added centralized version validation and integrity checks.
- Added comprehensive Phase 17 test coverage.

Verification:
294 tests passed in 16.57s.

# Phase 18 — Statistical Baseline

## Status

COMPLETE

## Summary

Phase 18 established the deterministic statistical-baseline layer required before the Bayesian and machine-learning model phases.

The implementation reuses the existing statistical, frequency, distribution, and versioning architecture rather than creating parallel calculation or version systems.

## Completed Milestones

18.1 — Statistical Baseline Contract / Foundation — COMPLETE

18.2 — Baseline Dataset Preparation — COMPLETE

18.3 — Descriptive Statistics Engine — COMPLETE

18.4 — Frequency Baseline — COMPLETE

18.5 — Position-Wise Statistical Baseline — COMPLETE

18.6 — Distribution Baseline — COMPLETE

18.7 — Central Tendency & Dispersion — COMPLETE

18.8 — Probability Baseline — COMPLETE

18.9 — Conditional Probability Baseline — COMPLETE

18.10 — Independence / Dependence Baseline — COMPLETE

18.11 — Statistical Significance Baseline — COMPLETE

18.12 — Baseline Comparison & Change Detection — COMPLETE

18.13 — Statistical Baseline Validation — COMPLETE

18.14 — Statistical Baseline Artifact / Version Integration — COMPLETE

18.15 — Determinism / Reproducibility — COMPLETE

18.16 — Comprehensive Phase 18 Testing — COMPLETE

18.17 — Documentation / Release — COMPLETE locally

## Key Modules

analytics/statistical_baseline_contract.py

analytics/statistical_baseline_dataset.py

analytics/statistical_descriptive.py

analytics/statistical_frequency_baseline.py

analytics/statistical_position_baseline.py

analytics/statistical_distribution_baseline.py

analytics/statistical_central_tendency_dispersion.py

analytics/statistical_probability_baseline.py

analytics/statistical_conditional_probability.py

analytics/statistical_independence_baseline.py

analytics/statistical_significance_baseline.py

analytics/statistical_baseline_comparison.py

analytics/statistical_baseline_validation.py

analytics/statistical_baseline_version_integration.py

analytics/statistical_baseline_reproducibility.py

## Verification

Phase 18 comprehensive test family:

212 passed

Full NeuroLytics regression:

4331 passed in 52.52s

No failures or errors were reported.

## Release State

Phase 18 implementation and local documentation are complete.

No Git commit or push was performed.

GitHub release remains pending explicit release approval.

## Next Roadmap Phase

Phase 19 — Bayesian Models


# Phase 19 — Bayesian Models

## Status

COMPLETE

Phase 19 added a local deterministic Bayesian modeling layer over the Phase 18 Statistical Baseline.

Completed milestones:

19.1 Bayesian Modeling Contract / Foundation
19.2 Bayesian Dataset Preparation
19.3 Prior Distribution Framework
19.4 Likelihood Framework
19.5 Posterior Distribution Framework
19.6 Bayesian Parameter Estimation
19.7 Bayesian Digit Probability Model
19.8 Bayesian Position Model
19.9 Bayesian Conditional Model
19.10 Bayesian Updating Engine
19.11 Posterior Predictive Distribution
19.12 Bayesian Uncertainty / Credible Intervals
19.13 Bayesian Model Validation
19.14 Bayesian Baseline Comparison
19.15 Bayesian Artifact / Version Integration
19.16 Determinism / Reproducibility
19.17 Comprehensive Phase 19 Testing
19.18 Documentation / Local Release

Implemented module:

analytics/bayesian_models.py

The Bayesian layer reuses Phase 18 StatisticalBaselineDataset and Phase 17 dataset version references.

Engineering rules remain unchanged:

- SQL is the production source of truth.
- Digit 0 is a valid observed value.
- NULL remains distinct from zero.
- No fabricated historical observations are introduced.
- Bayesian artifacts are deterministic.
- Version compatibility is validated through the existing Phase 17 contract.
- Bayesian probabilities and uncertainty intervals are not guarantees of future outcomes.

Phase 19 focused regression:

18 passed

Documentation:

docs/PHASE_19_BAYESIAN_MODELS.md

GitHub commit/push remains pending explicit release confirmation.

Next roadmap phase: Phase 20 — Logistic Regression.


---

# Phase 20 — Logistic Regression

## Status

COMPLETE

## Summary

Implemented the Logistic Regression baseline as the next model layer after the Phase 18 Statistical Baseline and Phase 19 Bayesian Models.

The implementation reuses the existing sequence dataset and temporal-split contracts and validates Phase 17 version references rather than introducing a parallel versioning system.

## Production Files

analytics/logistic_regression.py

tests/test_logistic_regression.py

## Milestones

20.1 Contract / Foundation — COMPLETE
20.2 Dataset Preparation — COMPLETE
20.3 Target / Label Preparation — COMPLETE
20.4 Feature Matrix Preparation — COMPLETE
20.5 Train / Validation Split — COMPLETE
20.6 Training Engine — COMPLETE
20.7 Binary Classification — COMPLETE
20.8 Multiclass Classification — COMPLETE
20.9 Position-Wise Models — COMPLETE
20.10 Regularization — COMPLETE
20.11 Hyperparameters — COMPLETE
20.12 Probability / Scores — COMPLETE
20.13 Evaluation — COMPLETE
20.14 Baseline Comparison — COMPLETE
20.15 Validation — COMPLETE
20.16 Artifact / Version Integration — COMPLETE
20.17 Reproducibility — COMPLETE
20.18 Persistence / Loading — COMPLETE
20.19 Prediction Interface — COMPLETE
20.20 Comprehensive Testing — COMPLETE
20.21 Documentation / Local Release — COMPLETE

## Capabilities

- binary and multiclass Logistic Regression
- L1, L2, elasticnet, and no-penalty handling
- solver and penalty compatibility validation
- chronological model dataset splitting
- deterministic feature matrices
- position-wise models
- class predictions and probabilities
- accuracy, precision, recall, F1, log loss, and confusion matrix
- baseline log-loss comparison
- model validation
- deterministic artifact identity
- Phase 17 version-reference validation
- joblib model persistence
- reproducibility comparison

## Dependency

Added:

scikit-learn==1.9.1
joblib==1.6.0

## Testing

Focused Phase 20 suite:

31 passed

Full project regression:

4380 passed in 71.25s

0 failed

0 errors

## Release

Phase 20 is complete locally.

No GitHub commit or push was performed.

GitHub release remains pending explicit confirmation.

Next roadmap phase:

Phase 21 — Decision Tree


## 2026-09-29 — Phase 24: Gradient Boosting

### Status

COMPLETE LOCALLY

### Added

- analytics/gradient_boosting.py
- tests/test_gradient_boosting.py
- docs/PHASE_24_GRADIENT_BOOSTING.md

### Capabilities

- GradientBoostingClassifier training
- deterministic configuration
- binary and multiclass classification
- chronological dataset splitting
- prediction and probability generation
- evaluation metrics and confusion matrix
- feature importance
- position-wise models
- baseline log-loss comparison
- model validation
- artifact identity and reproducibility
- joblib persistence and type-safe loading
- learning-rate, tree-depth, subsampling, and early-stopping controls

### Verification

Phase 24 focused regression: 36 passed, 24 warnings in 1.30s.

Full project regression: 4506 passed, 0 failures, 0 errors, 48 warnings in 70.71s.

Phase 23 baseline: 4470 passed.

Phase 24 increase: +36 tests.

### Release

No GitHub commit or push was performed.

### Next

Phase 25 — XGBoost
