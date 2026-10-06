# Phase 33 — Advanced Sequence Framework

## Status

COMPLETE LOCALLY — WARNING CLEAN

## Scope

Phase 33 adds a contract-first interoperability layer across the existing NeuroLytics sequence-model families.

It does not create a second historical loader, SQL path, feature pipeline, or sequence dataset pipeline.

The framework coordinates the existing:
- Markov model
- Hidden Markov Model
- LSTM
- GRU
- Transformer

## Production Module

analytics/sequence_framework.py

Version:

33.0.0

## Architecture

```
Existing SQL / Historical Architecture
        ↓
Existing Point-in-Time / Sequence Dataset Contracts
        ↓
SequenceFrameworkDataset
        ↓
SequenceModelRegistry
        ↓
Model Adapter / Dataset Adapter
        ├── Markov
        ├── HMM
        ├── LSTM
        ├── GRU
        └── Transformer
        ↓
Common SequenceModelRun
        ↓
Evaluation Metrics / Artifact Identity
        ↓
SequenceFrameworkReport
        ↓
Future Calibration / Comparison / Ensemble / Ranking
```
## Framework Dataset Contract

SequenceFrameworkDataset is a lightweight orchestration envelope.

Rules preserved:
- SQL remains the production source of truth.
- Existing sequence dataset infrastructure remains authoritative.
- digit 0 is valid.
- digits must remain in 0–9.
- empty sequences are rejected.
- target name and dataset identity are preserved.
- model-specific datasets are created through existing model builders.
- no future or target-date data is introduced by this layer.

## Registry

SequenceModelRegistry provides:
- deterministic model-kind registration
- duplicate registration protection
- explicit supported model families
- model version metadata
- model class metadata
- model-specific dataset builders
- model-specific artifact builders

Default registry kinds are deterministic:
- gru
- hidden_markov
- lstm
- markov
- transformer

## Common Lifecycle

The framework exposes a common lifecycle:

1. build_sequence_framework_dataset()
2. validate_sequence_framework_dataset()
3. prepare_model_dataset()
4. build_sequence_model()
5. train_sequence_model()
6. train_sequence_models()
7. compare_sequence_model_runs()
8. build_sequence_framework_report()
9. validate_sequence_model_run()
10. validate_sequence_framework_report()
11. predict_next_sequence_model()

The existing model implementations remain responsible for their own:
- model mathematics
- training
- model validation
- persistence
- artifact generation
- model-specific lineage

## Multi-Model Training

train_sequence_models() accepts a deterministic model-kind list and returns sorted model runs.

This allows the same validated sequence envelope to be evaluated through multiple model families without duplicating ingestion logic.
## Position-Wise Integration

build_position_sequence_models() provides the same position-wise architecture used by the individual model phases.

Models are returned in sorted position order.

This keeps col1–col8 style position modeling compatible with the existing NeuroLytics architecture.

## Comparison

SequenceModelComparison exposes:
- model kind
- model version
- log loss
- accuracy
- observation count
- optional log-loss delta against a supplied baseline
- optional accuracy delta against a supplied baseline

The framework does not claim model superiority. Formal calibration and model-comparison phases remain downstream.

## Framework Report

SequenceFrameworkReport records:
- framework version
- dataset identity
- target name
- model runs
- comparable metrics
- deterministic framework identity

Framework identity is derived from the framework version, dataset identity, target, model versions, and artifact identities.
## Compatibility

The framework adapts the existing model-specific configuration contracts rather than changing them.

Supported configuration objects:
- MarkovConfig
- HMMConfig
- LSTMConfig
- GRUConfig
- TransformerConfig

Mapping-based configuration is also accepted and converted through the registered config class.

No existing Phase 28–32 model API was replaced.

## Leakage Boundary

Phase 33 does not perform feature engineering or historical selection.

The dependency remains:

SQL
→ Historical Services
→ Point-in-Time Features
→ Sequence Dataset
→ Sequence Framework
→ Sequence Model
→ Evaluation

Therefore the framework cannot bypass the established temporal boundary by design.
## Tests

Dedicated test module:

tests/test_sequence_framework.py

Dedicated regression:

39 passed, 0 warnings

Coverage includes:
- framework version
- supported model registry
- dataset contract
- zero handling
- invalid sequence handling
- registry lookup
- duplicate registration
- version mapping
- model construction
- model dataset preparation
- Markov training
- HMM training
- LSTM training
- GRU training
- Transformer training
- deterministic multi-model ordering
- model comparison
- framework report
- report lineage checks
- run validation
- prediction adapter
- position-wise models
- baseline validation
- NumPy integer windows
## Full Regression

Previous baseline:

4912 passed

Phase 33 result:

4951 passed in 60.08s

Result:
- 0 failures
- 0 errors
- 0 warnings
- +39 tests

## Milestones

33.1 Framework Foundation — COMPLETE
33.2 Framework Dataset Contract — COMPLETE
33.3 Sequence Model Registry — COMPLETE
33.4 Model Version Metadata — COMPLETE
33.5 Model Configuration Adapter — COMPLETE
33.6 Existing Dataset Adapter — COMPLETE
33.7 Markov Integration — COMPLETE
33.8 HMM Integration — COMPLETE
33.9 LSTM Integration — COMPLETE
33.10 GRU Integration — COMPLETE
33.11 Transformer Integration — COMPLETE
33.12 Common Training Run — COMPLETE
33.13 Common Evaluation Contract — COMPLETE
33.14 Multi-Model Training — COMPLETE
33.15 Model Comparison Envelope — COMPLETE
33.16 Framework Report — COMPLETE
33.17 Position-Wise Integration — COMPLETE
33.18 Prediction Adapter — COMPLETE
33.19 Validation / Lineage Checks — COMPLETE
33.20 Deterministic Framework Identity — COMPLETE
33.21 Dedicated Regression Coverage — COMPLETE
33.22 Full Regression Verification — COMPLETE
33.23 Documentation / Architecture Update — COMPLETE
33.24 Final Verification — COMPLETE
## Production Outputs

analytics/sequence_framework.py
tests/test_sequence_framework.py
docs/PHASE_33_ADVANCED_SEQUENCE_FRAMEWORK.md

## Architectural Connections

Phase 33 connects:
- Phase 16 sequence dataset infrastructure → framework dataset envelope
- Phase 17 versioning/artifact infrastructure → model-run artifacts
- Phase 28 Markov → registry
- Phase 29 HMM → registry
- Phase 30 LSTM → registry
- Phase 31 GRU → registry
- Phase 32 Transformer → registry

Forward connection:

Sequence Framework
→ Evaluation
→ Calibration
→ Formal Model Comparison
→ Ensemble
→ Candidate Scoring
→ Ranking
→ Backtesting
→ Monitoring
→ API/UI

## Release State

Phase 33 is complete locally and warning-clean.

GitHub commit/push was not performed.

Next roadmap phase:

Phase 34 — next advanced sequence/ML layer according to the project roadmap.
