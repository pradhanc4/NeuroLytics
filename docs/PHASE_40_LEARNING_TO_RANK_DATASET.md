# NeuroLytics — Phase 40: Learning-to-Rank Dataset

Date: 2026-09-30
Status: COMPLETE LOCALLY
Version: 40.0.0

## Scope

Phase 40 establishes the authoritative Learning-to-Rank dataset contract for NeuroLytics.

The phase converts historical target observations into ranking groups. Each group contains exactly ten digit candidates, candidate feature vectors, relevance labels, candidate identity, optional panel/Jodi family relationship metadata, and a chronological train/validation/test split.

Phase 40 is a dataset phase only. It does not train a ranking model.

## Existing Architecture Reused

SQL / historical data
↓
Point-in-time feature framework
↓
Feature schema / validation / leakage controls
↓
Phase 34 evaluation + calibration
↓
Phase 35 comparison + first-order ensemble
↓
Phase 36 candidate scoring / ranking
↓
Phase 38 advanced consensus
↓
Phase 39 walk-forward / backtesting
↓
Phase 40 Learning-to-Rank Dataset
↓
Phase 41 Learning-to-Rank Model

No duplicate candidate scorer, ensemble, consensus engine, or walk-forward engine was introduced.

## Production Output

Production module:
analytics/learning_to_rank_dataset.py

Version:
LEARNING_TO_RANK_DATASET_VERSION = "40.0.0"

Dedicated regression:
tests/test_learning_to_rank_dataset.py

Documentation:
docs/PHASE_40_LEARNING_TO_RANK_DATASET.md

## Core Contracts

### Configuration

LearningToRankDatasetConfig defines:

- feature names
- validation start date
- test start date
- candidate digit universe
- target position
- label policy

The candidate universe is fixed to digits 0–9.

### Candidate Input

LearningToRankCandidateInput contains:

- candidate digit
- feature vector
- feature availability date
- optional panel family ID
- optional Jodi family ID

### Historical Observation Input

LearningToRankObservationInput contains:

- ranking group ID
- target date
- target position
- actual target digit
- ten candidate inputs
- optional source observation identity

### Dataset Row

LearningToRankRow represents one candidate inside one ranking group.

Fields include:

- group ID
- target date
- target position
- candidate ID
- candidate digit
- relevance label
- feature names
- feature values
- feature availability date
- panel family ID
- Jodi family ID
- relationship key
- temporal split

### Ranking Group

LearningToRankGroup represents one historical target observation.

Each group stores:

- group identity
- target date
- target position
- candidate IDs
- row range
- split
- actual digit

Exactly ten candidate rows belong to every group.

## Candidate and Label Contract

For every group:

- candidate digits are exactly 0,1,2,3,4,5,6,7,8,9
- digit 0 is a valid candidate
- candidate IDs are deterministic and position-scoped
- the observed actual digit receives relevance label 1
- every other candidate receives relevance label 0
- every group has exactly one positive relevance label

Current label policy:
binary_actual_digit

A future graded-label policy must be introduced as an explicit contract change.

## Panel / Jodi Relationship Contract

Panel family and Jodi family identifiers are carried as candidate metadata when available.

The deterministic relationship key is:
panel=<panel_id>|jodi=<jodi_id>

Missing relationship values are represented explicitly as NONE.

Phase 40 does not invent or infer family membership. Authoritative family mappings remain owned by the existing database/reference architecture.

## Point-in-Time Contract

Every candidate feature vector includes a feature availability date.

Required rule:

feature_available_date < target_date

A feature available on the target date is rejected.

A feature available after the target date is rejected.

This preserves the existing NeuroLytics point-in-time rule and prevents candidate-level look-ahead leakage.

## Temporal Split Contract

Splitting is performed at the ranking-group level.

Given validation_start_date and test_start_date:

- target_date < validation_start_date → TRAIN
- validation_start_date <= target_date < test_start_date → VALIDATION
- target_date >= test_start_date → TEST

All ten candidate rows from a group remain in the same split.

Random row-level splitting is not used.

## Dataset Identity

Dataset identity is deterministic SHA-256 over:

- Phase 40 version
- source dataset identity
- feature schema identity
- configuration
- generated rows
- generated groups

Identity prefix:
learning-to-rank-dataset-

This supports reproducibility and downstream artifact lineage.

## Validation

validate_learning_to_rank_dataset() validates:

- dataset type
- configuration
- version
- source identity
- feature schema identity
- non-empty rows/groups
- ten rows per group
- unique groups
- digits 0–9
- one positive label per group
- feature schema alignment
- feature vector length
- feature finiteness
- feature temporal availability
- candidate identity
- relationship key
- row/group alignment
- split consistency
- chronological boundaries
- split isolation
- dataset identity prefix

Invalid datasets return a structured validation result.

## Retrieval APIs

The module provides:

- get_learning_to_rank_split_rows()
- get_learning_to_rank_group()
- learning_to_rank_group_sizes()
- learning_to_rank_summary()

These are read-only contract helpers.

## Determinism

The builder:

1. validates all input observations
2. orders groups by target date and group ID
3. orders candidates by digit
4. assigns deterministic candidate IDs
5. assigns deterministic temporal splits
6. computes deterministic relationship keys
7. hashes the complete dataset contract

Equivalent input produces equivalent dataset identity.

## Leakage Boundary

Phase 40 does not regenerate historical features.

It expects feature values and their availability metadata from upstream point-in-time-safe infrastructure.

The separation is:

Feature generation responsibility
↓
Phase 40 dataset assembly responsibility
↓
Phase 41 model-training responsibility

## Milestones

40.1 Phase Boundary Definition — COMPLETE
40.2 Learning-to-Rank Configuration Contract — COMPLETE
40.3 Feature Schema Contract — COMPLETE
40.4 Source Dataset Identity Contract — COMPLETE
40.5 Historical Observation Input Contract — COMPLETE
40.6 Candidate Input Contract — COMPLETE
40.7 Ten-Candidate Contract — COMPLETE
40.8 Digit Zero Preservation — COMPLETE
40.9 Candidate Identity Contract — COMPLETE
40.10 Candidate Feature Vector Contract — COMPLETE
40.11 Feature Availability Date Contract — COMPLETE
40.12 Point-in-Time Feature Availability Validation — COMPLETE
40.13 Ranking Group Contract — COMPLETE
40.14 Ranking Group Cardinality — COMPLETE
40.15 Candidate Label Contract — COMPLETE
40.16 Binary Actual-Digit Relevance Label — COMPLETE
40.17 Panel Family Relationship Metadata — COMPLETE
40.18 Jodi Family Relationship Metadata — COMPLETE
40.19 Panel/Jodi Relationship Key — COMPLETE
40.20 Chronological Group Ordering — COMPLETE
40.21 Train Boundary Contract — COMPLETE
40.22 Validation Boundary Contract — COMPLETE
40.23 Test Boundary Contract — COMPLETE
40.24 Group-Preserving Temporal Split — COMPLETE
40.25 Split Isolation Validation — COMPLETE
40.26 Row/Group Alignment — COMPLETE
40.27 Deterministic Dataset Identity — COMPLETE
40.28 Dataset Validation Contract — COMPLETE
40.29 Split Retrieval API — COMPLETE
40.30 Ranking Group Retrieval API — COMPLETE
40.31 Dataset Summary API — COMPLETE
40.32 Deterministic Reproducibility — COMPLETE
40.33 Dedicated Regression Coverage — COMPLETE
40.34 Compile / Integrity Verification — COMPLETE
40.35 Documentation / Blueprint / Changelog Update — COMPLETE
40.36 Final Phase Integrity Verification — COMPLETE

## Regression

Focused Phase 40 regression:
45 passed, 0 failures, 0 errors, 0 warnings

Full project regression:
5193 passed in 84.76s, 0 failures, 0 errors, 0 warnings

Previous full-project baseline:
5148 passed

Regression increase:
+45 tests

Compile verification:
PASS

No new third-party dependency was added.

## Phase Boundary to Phase 41

Phase 41 may consume:

- ranking groups
- candidate rows
- feature vectors
- relevance labels
- candidate identities
- panel/Jodi metadata
- train/validation/test group assignments
- dataset identity
- feature schema identity
- source dataset identity

Phase 41 must not weaken:

- the point-in-time feature rule
- group-preserving temporal splits
- digit 0 support
- deterministic lineage
- authoritative family mappings

## Release State

Phase 40 is complete locally.

GitHub commit/push was intentionally not performed.

Next implementation boundary:
Phase 41 — Learning-to-Rank Model
