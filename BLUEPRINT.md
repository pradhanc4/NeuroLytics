## Phase 87 — Admin / Configuration Dashboard Architecture

Phase 87 adds a read-only administration projection above the existing Phase 70/71/73 security and rate-limit contracts, Phase 68/69 serving/inference contracts, and Phase 76 production service.

The dashboard exposes service state, security metadata, rate-limit policy, production startup policy, serving identity, dependencies, and authorization scopes. Secret material is excluded. All admin routes are GET-only and require admin:read by default. No runtime mutation protocol is introduced.

Next official phase: Phase 88 — Full Frontend Integration.

# NeuroLytics — Master Project Blueprint

Audit date: 2026-10-01
Current official roadmap phase: Phase 47 — Performance Monitoring Framework — COMPLETE LOCALLY
Authoritative roadmap: docs/ROADMAP_1_100.md
Latest verified full regression: 7,074 passed in 177.91s, 0 failures, 0 errors, 0 warnings

## Phase 40 — Learning-to-Rank Dataset

### Purpose

Create the authoritative ranking judgment-list dataset consumed by Phase 41, while reusing existing candidate scoring, consensus, walk-forward, and point-in-time infrastructure.

### Contract

`Historical target observation → ranking group → ten digit candidates → candidate features + relevance label → temporal split → deterministic dataset identity`

### Ranking-group rules

- one group represents one target observation
- exactly ten candidates: digits 0–9
- digit 0 is valid and preserved
- candidate identity is position-scoped
- the observed target digit receives relevance label 1
- all other candidates receive relevance label 0
- panel/Jodi family metadata is preserved when available
- relationship key is deterministic

### Temporal safety

- feature availability date must be strictly before target date
- train groups occur before validation boundary
- validation groups occur between validation and test boundaries
- test groups occur on/after test boundary
- complete groups remain in one split
- candidate rows cannot cross split boundaries

### Lineage

- source dataset identity is required
- feature schema identity is required
- dataset identity is deterministic SHA-256
- validation checks row/group alignment, candidate identity, labels, split isolation, finite features, and temporal leakage

### Production files

- `analytics/learning_to_rank_dataset.py`
- `tests/test_learning_to_rank_dataset.py`
- `docs/PHASE_40_LEARNING_TO_RANK_DATASET.md`

### Reuse boundary

Phase 40 does not implement another scorer, ensemble, consensus engine, or walk-forward evaluator. It consumes the established Phase 36–39 architecture and prepares the training judgment-list contract for Phase 41.

## Phase 41 — Learning-to-Rank Model

### Purpose

Implement the first ranking model consuming the Phase 40 judgment-list dataset.

### Model

- pairwise logistic Learning-to-Rank
- positive-vs-negative candidate comparisons within each ranking group
- training-only feature standardization
- L2 regularization
- deterministic optimization
- validation monitoring and best-state restoration
- early stopping

### Outputs

- candidate scores
- ten-class softmax probabilities
- deterministic ranks
- Top-K candidates
- train/validation/test metrics
- accuracy
- Top-K accuracy
- MRR
- NDCG
- log loss

### Lineage / Integrity

- Phase 40 dataset identity preserved
- feature-schema identity preserved
- deterministic model identity
- model validation
- report validation
- Joblib persistence
- persistence reproducibility
- digit 0 preserved

### Production files

- analytics/learning_to_rank_model.py
- tests/test_learning_to_rank_model.py
- docs/PHASE_41_LEARNING_TO_RANK_MODEL.md

### Verification

- focused regression: 47 passed, 0 warnings
- full regression: 5240 passed, 0 failures, 0 errors, 0 warnings
- compileall: PASS
- production import: PASS
- no new dependency

### Reuse boundary

Phase 41 consumes Phase 40 and does not duplicate candidate scoring, advanced consensus, or walk-forward evaluation.

## Phase 42 — Panel Ranking

### Purpose

Convert three position-wise Phase 41 Learning-to-Rank probability predictions into a deterministic ranking of explicit three-digit Panel/Panna candidates.

### Contract

For Panel abc: P(panel) = P(position_1=a) × P(position_2=b) × P(position_3=c).

Raw candidate masses are normalized across the supplied candidate universe.

Candidate score = normalized probability × 100.

Ties are resolved by Panel value.

### Outputs

- ranked Panel candidates
- normalized Panel probabilities
- 0–100 Panel scores
- deterministic ranks
- probability margin
- optional actual Panel
- Panel/Jodi family metadata
- deterministic ranking identity
- deterministic report identity
- strict validation
- report summary

### Integrity rules

- Panel is a three-character digit string.
- Leading zeros are preserved.
- Digit 0 is valid.
- Each position prediction contains exactly digits 0–9.
- Each position probability vector must be finite, non-negative, and normalized.
- Exactly three position predictions are required.
- Candidate-universe normalization is explicit; candidates are not silently invented.
- No training, feature engineering, consensus, or walk-forward engine is duplicated.

### Production files

- analytics/panel_ranking.py
- tests/test_panel_ranking.py
- docs/PHASE_42_PANEL_RANKING.md

### Verification

- focused regression: 43 passed, 0 warnings
- production import: PASS
- compileall: PASS
- full regression: 5283 passed, 0 failures, 0 errors, 0 warnings
- no new dependency

### Downstream boundary

Phase 42 feeds Phase 43 Jodi Ranking and Phase 44 Top-K Framework.

## Phase 46 — Performance Over Time

### Purpose

Analyze temporal changes in realized ranking performance produced by Phase 45 without changing Phase 44/45 semantics.

### Contract

Phase 45 ActualVsRankedReport → chronological observations → configurable periods → period metrics → descriptive temporal trends.

### Outputs

- period-level observation and actual-availability counts
- missed-observation counts and miss rate
- mean actual rank
- Hit@K rates
- mean reciprocal rank
- mean top probability
- mean cumulative probability
- per-day linear trend slope
- trend direction and first-to-last change
- deterministic report identity
- strict validation
- summary API

### Integrity

- Phase 45 source is validated before analysis.
- Period construction is deterministic and anchored to the first observation.
- Rank, Hit@K, reciprocal-rank, probability, and actual-value semantics are preserved.
- Missing actuals remain unavailable.
- No model training, reranking, rescoring, or probability generation occurs.

### Production files

- `analytics/performance_over_time.py`
- `tests/test_performance_over_time.py`
- `docs/PHASE_46_PERFORMANCE_OVER_TIME.md`

### Verification

- dedicated regression: 64 passed, 0 warnings
- production import: PASS
- compileall: PASS
- full regression: 5,505 passed, 0 failures, 0 errors, 0 warnings
- no new dependency

### Downstream boundary

Phase 46 provides the temporal performance layer for future monitoring, degradation, drift, and lifecycle controls.

## Phase 45 — Actual-vs-Ranked Analysis

### Purpose

Analyze realized actual values against the ranking outcomes established by Phase 44 without changing ranking or Top-K semantics.

### Contract

Phase 44 Top-K Evaluation Report → observation-level actual-vs-ranked records → rank distribution/buckets → descriptive rank metrics → Phase 46 Performance Over Time.

### Outputs

- actual-vs-ranked observations
- actual rank and reciprocal rank
- Hit@K carry-forward
- rank buckets
- rank distribution
- rank-bucket counts
- actual availability and missed counts
- mean and median actual rank
- mean reciprocal rank
- mean top probability
- mean cumulative probability
- deterministic report identity
- strict validation

### Integrity

- Phase 44 source report is validated before analysis.
- Group IDs remain unique.
- Missing actuals remain unavailable.
- Rank buckets are derived deterministically from actual rank.
- Digit 0 and leading zeros are preserved.
- No model training or reranking occurs.

### Production files

- analytics/actual_vs_ranked.py
- tests/test_actual_vs_ranked.py
- docs/PHASE_45_ACTUAL_VS_RANKED.md

### Verification

- dedicated regression: 48 passed, 0 warnings
- production import: PASS
- compileall: PASS
- full regression: pending
- no new dependency

### Downstream boundary

Phase 45 provides the canonical observation-level input for Phase 46 Performance Over Time.

## Phase 44 — Top-K Framework

### Purpose

Provide one reusable Top-K selection and evaluation boundary over the existing Panel and Jodi ranking artifacts.

### Contract

Existing ranking → Top-K selection → actual rank / Hit@K / MRR / cumulative probability → deterministic evaluation report → Phase 45 Actual-vs-Ranked Analysis.

### Supported sources

- Phase 42 PanelRankingObservation
- Phase 43 JodiRankingObservation

### Outputs

- deterministic TopKSelection
- TopKCandidate records
- TopKEvaluationRow records
- TopKEvaluationReport
- Hit@K rates
- actual rank
- reciprocal rank
- mean reciprocal rank
- cumulative probability
- strict validation
- deterministic SHA-256 identities

### Integrity

- K must be a positive integer.
- K values are unique and deterministically sorted.
- K greater than available candidates is safely clamped.
- Panel and Jodi observations cannot be mixed in one report.
- Ranking group identities must be unique within a report.
- Missing actuals are represented as unavailable, never fabricated.
- Digit 0 and leading zeros are preserved.
- Upstream ranking probability, score, rank, family metadata, and identity lineage are preserved.
- No training state or second ranking engine is introduced.

### Production files

- analytics/top_k_framework.py
- tests/test_top_k_framework.py
- docs/PHASE_44_TOP_K_FRAMEWORK.md

### Verification

- dedicated regression: 63 passed, 0 warnings
- production import: PASS
- compileall: PASS
- full regression: 5393 passed, 0 failures, 0 errors, 0 warnings
- no new dependency

### Downstream boundary

Phase 44 provides the canonical Top-K semantics consumed by Phase 45 Actual-vs-Ranked Analysis.

## Phase 43 — Jodi Ranking

### Purpose

Convert two position-wise Phase 41 Learning-to-Rank probability predictions into a deterministic ranking of explicit two-digit Jodi candidates.

### Contract

For Jodi AB: P(AB) = P(position_1=A) × P(position_2=B). Raw candidate masses are normalized over the supplied Jodi candidate universe. Candidate score = normalized probability × 100.

### Integrity

- Jodi is a two-character digit string.
- Leading zeros are preserved.
- Digit 0 is valid.
- Exactly two position predictions are required.
- Probability vectors must contain digits 0–9 and sum to one.
- Candidate universe is explicit.
- Family metadata and lineage are preserved.

### Production files

- analytics/jodi_ranking.py
- tests/test_jodi_ranking.py
- docs/PHASE_43_JODI_RANKING.md

### Verification

- focused regression: 47 passed, 0 warnings
- production import: PASS
- compileall: PASS
- no new dependency

### Downstream boundary

Phase 43 feeds Phase 44 Top-K Framework.

## 1. Project Vision

NeuroLytics is a local-first, SQL-driven historical data analytics, statistical analysis, machine-learning, sequence-analysis, ranking, backtesting, monitoring, and prediction platform.

Original result: 123 45 678 → Open/Panna + Jodi + Close/Panel → col1..col8.

## 2. Golden Data Rules

- SQL is the production source of truth.
- CSV is not the production source of truth.
- Leading zeros are preserved.
- Digit 0 is valid.
- 0 and NULL are distinct.
- Missing dates are not fabricated.
- Duplicate market/date observations are rejected.
- For target date T, only result_date < T may be used for historical features.
- Target-date and future leakage are forbidden.
- Reference mappings are authoritative; inactive/unmapped values stay inactive/unmapped.
- Existing infrastructure must be reused.
- Feature names must be globally unique.
- Artifacts must be reproducible and integrity-checkable.

## 3. System Blueprint

`	ext
USER / RAW HISTORICAL DATA
        ↓
Historical Input + Parser + Validation
        ↓
SQL / SQLite / SQLAlchemy
        ↓
Reference + Classification + Data Quality
        ↓
Historical Data Loader
        ↓
Point-in-Time Features
        ↓
Unified Feature Dataset
        ↓
Schema → Validation → Leakage Detection
        ↓
Feature/Dataset Versioning
        ↓
Feature Artifact + Integrity
        ↓
Sequence / ML Dataset Contracts
        ↓
Statistical + Classical ML + Markov/HMM + LSTM/GRU/Transformer
        ↓
Evaluation → Calibration → Comparison → Explainability
        ↓
Ensemble → Candidate Scoring → Ranking
        ↓
Walk-Forward / Backtesting → Monitoring → API/UI
`

## 4. Current SQL ER Diagram

`mermaid
erDiagram
    MARKETS ||--o{ HISTORICAL_RESULTS : contains
    HISTORICAL_RESULTS ||--o{ HISTORICAL_CLASSIFICATIONS : classified_as
    HISTORICAL_RESULTS ||--o{ HISTORICAL_DATA_QUALITY : quality_checked
    JODI_FAMILIES ||--o{ JODI_FAMILY_MEMBERS : contains
    PANEL_FAMILIES ||--o{ PANEL_FAMILY_MEMBERS : contains
    MARKETS { int id PK; string name UK; bool is_active }
    HISTORICAL_RESULTS { int id PK; int market_id FK; date result_date; string open_result; string jodi_result; string close_result; int col1; int col2; int col3; int col4; int col5; int col6; int col7; int col8 }
    PANNA_REFERENCE { int id PK; string panna UK; int digit_1; int digit_2; int digit_3; string panna_type; bool is_active }
    JODI_FAMILIES { int id PK; string family_name UK; string description; bool is_active }
    JODI_FAMILY_MEMBERS { int id PK; int family_id FK; string jodi; int digit_1; int digit_2; bool is_active }
    PANEL_FAMILIES { int id PK; string family_name UK; string description; bool is_active }
    PANEL_FAMILY_MEMBERS { int id PK; int family_id FK; string panel; int digit_1; int digit_2; int digit_3; bool is_active }
    HISTORICAL_CLASSIFICATIONS { int id PK; int historical_result_id FK; string classification_version; string open_class; string jodi_class; string close_class; string overall_class; datetime created_at }
    HISTORICAL_DATA_QUALITY { int id PK; int historical_result_id FK; string validation_version; string status; int issue_count; string issue_summary; datetime checked_at }
`

## 5. SQL Connection Table

| Parent | Child | FK | Cardinality | Purpose |
|---|---|---|---|---|
| markets | historical_results | market_id | 1:N | historical observations |
| historical_results | historical_classifications | historical_result_id | 1:N | versioned classifications |
| historical_results | historical_data_quality | historical_result_id | 1:N | versioned quality results |
| jodi_families | jodi_family_members | family_id | 1:N | Jodi family membership |
| panel_families | panel_family_members | family_id | 1:N | Panel family membership |

Unique constraints currently include market name, market/date, classification result/version, quality result/version, Jodi family name, family/Jodi, Panel family name, and family/Panel.

## 6. Historical Data Flow

`	ext
123 45 678 → database/parser.py → database/services.py → historical_results
                                   ↓
                         historical_data_loader.py
                                   ↓
                           point_in_time.py
                                   ↓
                      feature / sequence engines
`

## 7. Feature Architecture

`	ext
historical_data_loader → point_in_time → feature engines
feature engines → unified_dataset → schema → validator → leakage detector
validator/leakage → feature_versioning + dataset_versioning
versioning → feature_dataset_contract → feature_artifact → artifact_integrity → versioned_artifact
`

Feature families: time, cyclical time, interval, density, lag, rolling, recency, position, frequency, frequency change, concentration/diversity, family, family frequency, family recency, family transitions, position transitions, transition frequency/stability, relationship trend, sequence and cross-position.

## 8. Sequence Dataset Blueprint

`	ext
historical_data_loader
   ↓
sequence_windows → sequence_targets
   ↓
sequence_dataset_validator + sequence_leakage_validator + sequence_temporal_split
   ↓
sequence_dataset
   ├→ sequence_dataset_integration
   ├→ sequence_dataset_artifact
   └→ sequence_dataset_reproducibility
`

## 9. Analytics Blueprint

`	ext
statistical_foundation → frequency_analysis → position_frequency → position_distribution
position_distribution → change / trend / metrics / stability / volatility
distribution_regime_detection → transition / stability / summary / overview
cross_position_relationship_matrix → change_detection / stability / summary / overview
`

Analytics describes historical behavior; the feature layer converts it into point-in-time ML inputs.

## 10. Model Blueprint

| Phase | Model | File | Version |
|---|---|---|---|
| 18 | Statistical Baseline | analytics/statistical_baseline_*.py | baseline |
| 19 | Bayesian | analytics/bayesian_models.py | 19.x |
| 20 | Logistic Regression | analytics/logistic_regression.py | 20.x |
| 21 | Decision Tree | analytics/decision_tree.py | 21.x |
| 22 | Random Forest | analytics/random_forest.py | 22.x |
| 23 | Extra Trees | analytics/extra_trees.py | 23.x |
| 24 | Gradient Boosting | analytics/gradient_boosting.py | 24.x |
| 25 | XGBoost | analytics/xgboost.py | 25.0.0 |
| 26 | LightGBM | analytics/lightgbm.py | 26.0.0 |
| 27 | CatBoost | analytics/catboost.py | 27.0.0 |
| 28 | Markov | analytics/markov_models.py | 28.0.0 |
| 29 | HMM | analytics/hidden_markov_models.py | 29.0.0 |
| 30 | LSTM | analytics/lstm.py | 30.0.0 |
| 31 | GRU | analytics/gru.py | 31.0.0 |
| 32 | Transformer | analytics/transformer.py | 32.0.0 |
| 33 | Advanced Sequence Framework | analytics/sequence_framework.py | 33.0.0 |
| 34 | Advanced Sequence Evaluation & Calibration | analytics/sequence_evaluation.py | 34.0.0 |
| 35 | Formal Model Comparison / Ensemble | analytics/sequence_ensemble.py | 35.0.0 |
| 36 | Candidate Scoring / Ranking | analytics/candidate_scoring.py | 36.0.0 |
| 37 | Explainability / Downstream Ranking Interpretation | analytics/sequence_explainability.py | 37.0.0 |
| 38 | Advanced Ensemble Expansion / Consensus | analytics/advanced_ensemble.py | 38.0.0 |

## 11. Sequence Neural Model Architecture

`	ext
Sequence Dataset → digit embedding + positional encoding → Transformer self-attention
→ residual/layer normalization + feed-forward encoder → softmax
→ 10-digit probabilities → Top-K/evaluation → artifact/lineage/persistence/reproducibility

Recurrent path: one-hot digits → LSTM/GRU → BPTT → softmax.
`

Phase 30/31/32 use NumPy only. Transformer adds embedding, sinusoidal positional encoding, multi-head self-attention, residual normalization, feed-forward encoding, and softmax next-digit prediction.

Phase 33 adds a common registry/adapter layer across Markov, HMM, LSTM, GRU, and Transformer without replacing their model-specific contracts. The framework preserves dataset identity, target name, model version, artifact identity, evaluation metrics, position-wise orchestration, and deterministic model ordering. Future framework-backed models should preserve the surrounding contracts.

## 12. User Intended Prediction Platform

`	ext
Historical observations → position analysis → frequency/recency/transitions
→ family/cross-position relationships → leakage-safe features → multiple models
→ probabilities → evaluation → calibration → comparison → ensemble
→ candidate scoring → ranking/Top-K → walk-forward/backtesting
→ performance → drift/degradation → retraining/lifecycle → API/UI
`

## 13. Phase History

See PROJECT_STATUS.md for the authoritative detailed phase record. Current roadmap position:
- Phases 1–9: COMPLETE (Phase 9.3 paused at 9.3.75)
- Phases 10–12: related implementations exist but are not independently closed
- Phases 13–31: COMPLETE
- Phase 32: TRANSFORMER — COMPLETE
- Phase 33: ADVANCED SEQUENCE FRAMEWORK — COMPLETE LOCALLY
- Phase 34: ADVANCED SEQUENCE EVALUATION & CALIBRATION — COMPLETE LOCALLY
- Phase 35: FORMAL MODEL COMPARISON / ENSEMBLE — COMPLETE LOCALLY
- Phase 36: CANDIDATE SCORING / RANKING — COMPLETE LOCALLY
- Phase 37: EXPLAINABILITY — COMPLETE LOCALLY
- Phase 38: ADVANCED ENSEMBLE EXPANSION / CONSENSUS — COMPLETE LOCALLY
- Phase 46: PERFORMANCE OVER TIME — COMPLETE LOCALLY
- Phases 35–76: FUTURE

## 14. Phase 32 Boundary

Phase 32 reused the historical loader, point-in-time rules, sequence dataset contract, temporal split, versioning, artifact/lineage infrastructure and testing pattern. It introduced no parallel historical-data or sequence-data pipeline.

Phase 33 continued the same contract-first sequence architecture and extended model interoperability rather than duplicate historical or sequence ingestion.

Phase 34 continued the same boundary and added standardized probability evaluation and calibration above SequenceModelRun. It did not alter historical ingestion, feature engineering, sequence construction, or model mathematics.

Phase 35 adds deterministic formal comparison and ensemble blending above Phase 34 evaluation outputs. It requires identical evaluation sample universes before probability blending and does not duplicate historical or sequence ingestion.

Phase 36 adds deterministic candidate scoring and ranking directly above the selected Phase 35 ensemble. Candidate score is a transparent 0–100 rescaling of ensemble probability; ranking uses probability descending with lower-digit tie-breaking. It preserves ensemble and dataset lineage and does not introduce new predictive signal.

## Phase 86 — Prediction Interface Architecture

Phase 86 is the user-facing prediction entry point over existing production inference.

Authoritative sources:
- Phase 68 Production Serving
- Phase 69 Production Inference API
- Phase 76 Production Service

The frontend does not implement prediction mathematics. It:
- loads serving identity/version/artifact and readiness
- validates request structure for usability
- submits POST /v1/inference
- displays the authoritative response
- preserves existing lineage, readiness, security, rate-limit, and deterministic contracts

Interface fields:
- request ID
- read-only model identity
- read-only model version
- read-only artifact identity
- numeric features JSON

Phase 86 regression:
- dedicated: 55 passed
- Phase 76–86 integration: 457 passed
- full project: 7,615 passed
- failures/errors: 0/0

Next official phase: Phase 87 — Admin / Configuration Dashboard.

## Phase 85 — Model Health Dashboard Architecture

Phase 85 adds a dedicated read-only presentation boundary above the authoritative Phase 57 Model Health Scorecard.

Authoritative source:
- Phase 57 Model Health Scorecard

Composition:
- analytics/model_health_dashboard.py
- ModelHealthDashboardService

Production:
- model-health:read scope
- six GET-only routes
- shared Phase 76 rate limiting/security

Frontend:
- Model Health navigation
- health KPIs
- scorecard
- thresholds
- component evidence
- source lineage
- validation

Architectural rule:
Phase 85 must not recalculate health or mutate model state. Missing health reports are represented as UNAVAILABLE / REPORT_NOT_ATTACHED rather than fabricated health.

Phase 85 regression:
- dedicated: 55 passed
- Phase 76–85 integration: 402 passed
- full project: 7,560 passed
- failures/errors: 0/0

Next official phase: Phase 86 — Prediction Interface.

## Phase 84 — Drift / Monitoring Dashboard Architecture

Phase 84 adds a read-only composition boundary above the existing drift engines.

Authoritative source layers:
- Phase 49 Model Drift
- Phase 50 Data Drift
- Phase 52 Calibration Drift
- Phase 53 Ranking Drift
- Phase 54 Feature Drift
- Phase 55 Concept Drift

Composition layer:
- analytics/drift_dashboard.py
- DriftMonitoringDashboardService

Production exposure:
- Phase 76 production service
- configurable drift:read authorization scope
- shared rate limiting
- GET-only dashboard routes

Frontend exposure:
- Drift / Monitoring navigation
- unified drift KPIs
- six source-domain panels
- observation inspection

Architectural rule:
Phase 84 must not duplicate drift calculations or mutate monitoring/model state. Source reports remain authoritative. Missing source reports are represented as UNAVAILABLE / REPORT_NOT_ATTACHED rather than fabricated no-drift results.

Phase 84 regression:
- dedicated: 50 passed
- Phase 76–84 integration: 347 passed
- full project: 7,505 passed
- failures/errors: 0/0

Next official phase: Phase 85 — Model Health Dashboard.

## 15. Architecture Health

| Area | State |
|---|---|
| SQL source of truth | established |
| historical input | established |
| reference systems | established |
| classification | established |
| data quality | established |
| descriptive analytics | established |
| point-in-time features | established |
| leakage detection | established |
| feature/dataset versioning | established |
| sequence datasets | established |
| classical ML | established |
| Markov/HMM/LSTM/GRU/Transformer | established |
| Transformer | established |
| sequence evaluation/calibration | established |
| formal model comparison | established |
| ensemble | established |
| candidate scoring/ranking | established |
| ranking/backtesting | future |
| monitoring/lifecycle | future |
| backend/frontend | future formal phases |

## 16. Audit Notes

Live SQLite audit: 9 tables, 5 explicit FK relationships. Current Python production concentration: database/, features/, analytics/. Top-level backend/frontend/ml/ranking/backtesting/models/reports/scripts directories exist for current/future architecture but did not contain current Python production modules in this audit.

Older continuation documents are historical context. For current decisions prioritize actual source files, live schema, PROJECT_STATUS.md, CHANGELOG.md and latest regression.

## 17. Permanent Architecture Rule

Before every major phase: read BLUEPRINT.md, identify the correct architectural layer, reuse existing modules/contracts, add tests, run focused and full regression, update PROJECT_STATUS.md and CHANGELOG.md, and update BLUEPRINT.md when architecture changes.

## 18. Phase 34 Evaluation / Calibration Architecture

SequenceModelRun
   ↓
Probability Extraction
   ├─ Markov predict_proba
   ├─ HMM predict_next_proba
   ├─ LSTM predict_proba
   ├─ GRU predict_proba
   └─ Transformer predict_proba
   ↓
Standardized Evaluation
   ├─ Log Loss
   ├─ Accuracy
   ├─ Top-K Accuracy
   ├─ Brier Score
   ├─ Expected Calibration Error
   └─ Predictive Entropy
   ↓
Deterministic Temperature Calibration
   ↓
Evaluation / Calibration Report
   ↓
Future Formal Model Comparison

Phase 34 consumes Phase 33 runs and preserves dataset/model lineage. No historical or sequence ingestion is duplicated.

## 18. Machine-Generated File Inventory


### database/ (27 files)
- database/__init__.py
- database/classification_rules.py
- database/classification_service.py
- database/classification_validator.py
- database/config.py
- database/data_quality_rules.py
- database/data_quality_service.py
- database/engine.py
- database/historical_input_service.py
- database/historical_quality_checker.py
- database/init_db.py
- database/jodi_family_relationship.py
- database/jodi_relationship.py
- database/jodi_service.py
- database/jodi_validator.py
- database/models.py
- database/neurolytics.db
- database/panel_family_relationship.py
- database/panel_relationship.py
- database/panel_service.py
- database/panel_validator.py
- database/panna_relationship.py
- database/panna_service.py
- database/panna_validator.py
- database/parser.py
- database/quality_report_service.py
- database/services.py

### features/ (62 files)
- features/__init__.py
- features/artifact_integrity.py
- features/change_trend_features.py
- features/cross_position_family_relationships.py
- features/cross_position_features.py
- features/cyclical_time_features.py
- features/dataset_versioning.py
- features/family_recency.py
- features/family_transitions.py
- features/feature_artifact.py
- features/feature_config.py
- features/feature_config_phase14_backup.py
- features/feature_dataset_contract.py
- features/feature_pipeline.py
- features/feature_schema.py
- features/feature_schema_builder.py
- features/feature_validator.py
- features/feature_versioning.py
- features/frequency_change_features.py
- features/frequency_concentration_features.py
- features/frequency_features.py
- features/historical_data_loader.py
- features/historical_family_frequency.py
- features/historical_frequency_features.py
- features/historical_interval_features.py
- features/jodi_family.py
- features/lag_features.py
- features/leakage_detector.py
- features/observation_density_features.py
- features/panna_panel_family.py
- features/point_in_time.py
- features/position_family.py
- features/position_features.py
- features/position_transitions.py
- features/recency_bucket_features.py
- features/recency_distribution_features.py
- features/recency_expansion_features.py
- features/recency_features.py
- features/relationship_change_trend.py
- features/rolling_features.py
- features/rolling_frequency_features.py
- features/sequence_dataset.py
- features/sequence_dataset_artifact.py
- features/sequence_dataset_integration.py
- features/sequence_dataset_reproducibility.py
- features/sequence_dataset_validator.py
- features/sequence_features.py
- features/sequence_leakage_validator.py
- features/sequence_targets.py
- features/sequence_temporal_split.py
- features/sequence_windows.py
- features/time_features.py
- features/transition_frequency.py
- features/transition_stability.py
- features/unified_dataset.py
- features/version_comparison.py
- features/version_compatibility.py
- features/version_lineage.py
- features/version_reproducibility.py
- features/version_validation.py
- features/versioned_artifact.py
- features/versioning_contract.py

### analytics/ (105 files)
- analytics/__init__.py
- analytics/bayesian_models.py
- analytics/catboost.py
- analytics/cross_position_relationship_change_detection.py
- analytics/cross_position_relationship_matrix.py
- analytics/cross_position_relationship_overview.py
- analytics/cross_position_relationship_stability.py
- analytics/cross_position_relationship_summary.py
- analytics/decision_tree.py
- analytics/distribution_regime_detection.py
- analytics/distribution_regime_overview.py
- analytics/distribution_regime_stability.py
- analytics/distribution_regime_summary.py
- analytics/distribution_regime_transition_analysis.py
- analytics/extra_trees.py
- analytics/frequency_analysis.py
- analytics/gradient_boosting.py
- analytics/gru.py
- analytics/hidden_markov_models.py
- analytics/lightgbm.py
- analytics/logistic_regression.py
- analytics/lstm.py
- analytics/markov_models.py
- analytics/position_analytics_comparison.py
- analytics/position_analytics_consolidation.py
- analytics/position_analytics_quality_report.py
- analytics/position_analytics_quality_summary.py
- analytics/position_analytics_summary.py
- analytics/position_behavior_profile.py
- analytics/position_behavior_profile_comparison.py
- analytics/position_behavior_profile_distribution.py
- analytics/position_behavior_profile_ranking.py
- analytics/position_behavior_profile_summary.py
- analytics/position_distribution.py
- analytics/position_distribution_change.py
- analytics/position_distribution_change_classification.py
- analytics/position_distribution_change_magnitude.py
- analytics/position_distribution_change_magnitude_summary.py
- analytics/position_distribution_change_summary.py
- analytics/position_distribution_change_trend.py
- analytics/position_distribution_metrics.py
- analytics/position_distribution_stability.py
- analytics/position_distribution_stability_comparison.py
- analytics/position_distribution_stability_comparison_summary.py
- analytics/position_distribution_stability_detail.py
- analytics/position_distribution_stability_overview.py
- analytics/position_distribution_stability_summary.py
- analytics/position_distribution_stability_trend.py
- analytics/position_distribution_stability_trend_comparison.py
- analytics/position_distribution_stability_trend_detail.py
- analytics/position_distribution_stability_trend_overview.py
- analytics/position_distribution_stability_trend_summary.py
- analytics/position_distribution_stability_trend_transition_comparison.py
- analytics/position_distribution_stability_trend_transition_comparison_detail.py
- analytics/position_distribution_stability_trend_transition_comparison_overview.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_detail.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail.py
- analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_summary.py
- analytics/position_distribution_stability_trend_transition_comparison_summary.py
- analytics/position_distribution_stability_trend_transition_overview.py
- analytics/position_distribution_stability_trend_transition_summary.py
- analytics/position_distribution_trend_consistency.py
- analytics/position_distribution_trend_persistence.py
- analytics/position_distribution_trend_strength.py
- analytics/position_distribution_trend_strength_summary.py
- analytics/position_distribution_volatility.py
- analytics/position_distribution_volatility_summary.py
- analytics/position_frequency.py
- analytics/position_frequency_summary.py
- analytics/random_forest.py
- analytics/statistical_baseline_comparison.py
- analytics/statistical_baseline_contract.py
- analytics/statistical_baseline_dataset.py
- analytics/statistical_baseline_reproducibility.py
- analytics/statistical_baseline_validation.py
- analytics/statistical_baseline_version_integration.py
- analytics/statistical_central_tendency_dispersion.py
- analytics/statistical_conditional_probability.py
- analytics/statistical_descriptive.py
- analytics/statistical_distribution_baseline.py
- analytics/statistical_foundation.py
- analytics/statistical_frequency_baseline.py
- analytics/statistical_independence_baseline.py
- analytics/statistical_position_baseline.py
- analytics/statistical_probability_baseline.py
- analytics/statistical_significance_baseline.py
- analytics/temporal_position_analysis.py
- analytics/temporal_position_change_classification.py
- analytics/temporal_position_change_detection.py
- analytics/temporal_position_change_summary.py
- analytics/temporal_position_summary.py
- analytics/xgboost.py
- analytics/transformer.py
- analytics/sequence_framework.py
- analytics/sequence_evaluation.py
- analytics/sequence_ensemble.py
- analytics/candidate_scoring.py

### tests/ (192 files)
- tests/conftest.py
- tests/test_artifact_integrity.py
- tests/test_bayesian_models.py
- tests/test_catboost.py
- tests/test_change_trend_features.py
- tests/test_classification_queries.py
- tests/test_classification_rules.py
- tests/test_classification_service.py
- tests/test_classification_validator.py
- tests/test_cross_position_family_relationships.py
- tests/test_cross_position_features.py
- tests/test_cross_position_relationship_change_detection.py
- tests/test_cross_position_relationship_matrix.py
- tests/test_cross_position_relationship_overview.py
- tests/test_cross_position_relationship_stability.py
- tests/test_cross_position_relationship_summary.py
- tests/test_cyclical_time_features.py
- tests/test_data_quality_rules.py
- tests/test_data_quality_service.py
- tests/test_dataset_versioning.py
- tests/test_decision_tree.py
- tests/test_distribution_regime_detection.py
- tests/test_distribution_regime_overview.py
- tests/test_distribution_regime_stability.py
- tests/test_distribution_regime_summary.py
- tests/test_distribution_regime_transition_analysis.py
- tests/test_extra_trees.py
- tests/test_family_recency.py
- tests/test_family_transitions.py
- tests/test_feature_artifact.py
- tests/test_feature_config.py
- tests/test_feature_dataset_contract.py
- tests/test_feature_pipeline.py
- tests/test_feature_schema.py
- tests/test_feature_schema_builder.py
- tests/test_feature_validator.py
- tests/test_feature_version_identity_validation.py
- tests/test_feature_versioning.py
- tests/test_frequency_analysis.py
- tests/test_frequency_change_features.py
- tests/test_frequency_concentration_features.py
- tests/test_frequency_features.py
- tests/test_gradient_boosting.py
- tests/test_gru.py
- tests/test_hidden_markov_models.py
- tests/test_historical_data_loader.py
- tests/test_historical_family_frequency.py
- tests/test_historical_frequency_features.py
- tests/test_historical_input_service.py
- tests/test_historical_interval_features.py
- tests/test_historical_quality_checker.py
- tests/test_jodi_family.py
- tests/test_jodi_family_relationship.py
- tests/test_jodi_relationship.py
- tests/test_jodi_service.py
- tests/test_jodi_validator.py
- tests/test_lag_features.py
- tests/test_leakage_detector.py
- tests/test_lightgbm.py
- tests/test_logistic_regression.py
- tests/test_lstm.py
- tests/test_markov_models.py
- tests/test_observation_density_features.py
- tests/test_panel_family_relationship.py
- tests/test_panel_relationship.py
- tests/test_panel_service.py
- tests/test_panel_validator.py
- tests/test_panna_integration.py
- tests/test_panna_panel_family.py
- tests/test_panna_relationship.py
- tests/test_panna_service.py
- tests/test_panna_validator.py
- tests/test_parser.py
- tests/test_phase1.py
- tests/test_phase16_comprehensive.py
- tests/test_phase8_integration.py
- tests/test_point_in_time.py
- tests/test_position_analytics_comparison.py
- tests/test_position_analytics_consolidation.py
- tests/test_position_analytics_quality_report.py
- tests/test_position_analytics_quality_summary.py
- tests/test_position_analytics_summary.py
- tests/test_position_behavior_profile.py
- tests/test_position_behavior_profile_comparison.py
- tests/test_position_behavior_profile_distribution.py
- tests/test_position_behavior_profile_ranking.py
- tests/test_position_behavior_profile_summary.py
- tests/test_position_distribution.py
- tests/test_position_distribution_change.py
- tests/test_position_distribution_change_classification.py
- tests/test_position_distribution_change_magnitude.py
- tests/test_position_distribution_change_magnitude_summary.py
- tests/test_position_distribution_change_summary.py
- tests/test_position_distribution_change_trend.py
- tests/test_position_distribution_metrics.py
- tests/test_position_distribution_stability.py
- tests/test_position_distribution_stability_comparison.py
- tests/test_position_distribution_stability_comparison_summary.py
- tests/test_position_distribution_stability_detail.py
- tests/test_position_distribution_stability_overview.py
- tests/test_position_distribution_stability_summary.py
- tests/test_position_distribution_stability_trend.py
- tests/test_position_distribution_stability_trend_comparison.py
- tests/test_position_distribution_stability_trend_detail.py
- tests/test_position_distribution_stability_trend_overview.py
- tests/test_position_distribution_stability_trend_summary.py
- tests/test_position_distribution_stability_trend_transition_comparison.py
- tests/test_position_distribution_stability_trend_transition_comparison_detail.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_detail.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail.py
- tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_summary.py
- tests/test_position_distribution_stability_trend_transition_comparison_summary.py
- tests/test_position_distribution_stability_trend_transition_overview.py
- tests/test_position_distribution_stability_trend_transition_summary.py
- tests/test_position_distribution_trend_consistency.py
- tests/test_position_distribution_trend_persistence.py
- tests/test_position_distribution_trend_strength.py
- tests/test_position_distribution_trend_strength_summary.py
- tests/test_position_distribution_volatility.py
- tests/test_position_distribution_volatility_summary.py
- tests/test_position_family.py
- tests/test_position_features.py
- tests/test_position_frequency.py
- tests/test_position_frequency_summary.py
- tests/test_position_transitions.py
- tests/test_quality_report_service.py
- tests/test_random_forest.py
- tests/test_recency_bucket_features.py
- tests/test_recency_distribution_features.py
- tests/test_recency_expansion_features.py
- tests/test_recency_features.py
- tests/test_relationship_change_trend.py
- tests/test_rolling_features.py
- tests/test_rolling_frequency_features.py
- tests/test_sequence_dataset.py
- tests/test_sequence_dataset_artifact.py
- tests/test_sequence_dataset_integration.py
- tests/test_sequence_dataset_reproducibility.py
- tests/test_sequence_dataset_validator.py
- tests/test_sequence_features.py
- tests/test_sequence_leakage_validator.py
- tests/test_sequence_targets.py
- tests/test_sequence_temporal_split.py
- tests/test_sequence_windows.py
- tests/test_services.py
- tests/test_statistical_baseline_comparison.py
- tests/test_statistical_baseline_contract.py
- tests/test_statistical_baseline_dataset.py
- tests/test_statistical_baseline_reproducibility.py
- tests/test_statistical_baseline_validation.py
- tests/test_statistical_baseline_version_integration.py
- tests/test_statistical_central_tendency_dispersion.py
- tests/test_statistical_conditional_probability.py
- tests/test_statistical_descriptive.py
- tests/test_statistical_distribution_baseline.py
- tests/test_statistical_foundation.py
- tests/test_statistical_frequency_baseline.py
- tests/test_statistical_independence_baseline.py
- tests/test_statistical_position_baseline.py
- tests/test_statistical_probability_baseline.py
- tests/test_statistical_significance_baseline.py
- tests/test_temporal_position_analysis.py
- tests/test_temporal_position_change_classification.py
- tests/test_temporal_position_change_detection.py
- tests/test_temporal_position_change_summary.py
- tests/test_temporal_position_summary.py
- tests/test_time_features.py
- tests/test_transition_frequency.py
- tests/test_transition_stability.py
- tests/test_unified_dataset.py
- tests/test_version_comparison.py
- tests/test_version_compatibility.py
- tests/test_version_lineage.py
- tests/test_version_reproducibility.py
- tests/test_version_validation.py
- tests/test_versioned_artifact.py
- tests/test_versioning_contract.py
- tests/test_xgboost.py
- tests/test_sequence_evaluation.py
- tests/test_sequence_ensemble.py
- tests/test_candidate_scoring.py

### docs/ (13 files)
- docs/PHASE_18_STATISTICAL_BASELINE.md
- docs/PHASE_19_BAYESIAN_MODELS.md
- docs/PHASE_20_LOGISTIC_REGRESSION.md
- docs/PHASE_21_DECISION_TREE.md
- docs/PHASE_22_RANDOM_FOREST.md
- docs/PHASE_23_EXTRA_TREES.md
- docs/PHASE_24_GRADIENT_BOOSTING.md
- docs/PHASE_31_GRU.md
- docs/PHASE_32_TRANSFORMER.md
- docs/PHASE_33_ADVANCED_SEQUENCE_FRAMEWORK.md
- docs/PHASE_34_SEQUENCE_EVALUATION_CALIBRATION.md
- docs/PHASE_35_FORMAL_MODEL_COMPARISON_ENSEMBLE.md
- docs/PHASE_36_CANDIDATE_SCORING_RANKING.md

## 19. Internal Python Import Graph

analytics/bayesian_models.py → analytics.statistical_baseline_dataset, features.versioning_contract
analytics/catboost.py → features.sequence_dataset, features.versioning_contract
analytics/cross_position_relationship_overview.py → analytics.cross_position_relationship_change_detection, analytics.cross_position_relationship_matrix, analytics.cross_position_relationship_stability, analytics.cross_position_relationship_summary
analytics/cross_position_relationship_summary.py → analytics.cross_position_relationship_matrix
analytics/decision_tree.py → features.sequence_dataset, features.sequence_temporal_split, features.versioning_contract
analytics/distribution_regime_overview.py → analytics.distribution_regime_detection, analytics.distribution_regime_stability, analytics.distribution_regime_summary, analytics.distribution_regime_transition_analysis
analytics/distribution_regime_stability.py → analytics.distribution_regime_detection, analytics.distribution_regime_transition_analysis
analytics/distribution_regime_summary.py → analytics.distribution_regime_detection, analytics.distribution_regime_transition_analysis
analytics/distribution_regime_transition_analysis.py → analytics.distribution_regime_detection
analytics/extra_trees.py → features.sequence_dataset, features.versioning_contract
analytics/frequency_analysis.py → analytics.statistical_foundation
analytics/gradient_boosting.py → features.sequence_dataset, features.versioning_contract
analytics/lightgbm.py → features.sequence_dataset, features.versioning_contract
analytics/logistic_regression.py → features.sequence_dataset, features.sequence_temporal_split, features.versioning_contract
analytics/position_analytics_quality_summary.py → analytics.position_analytics_quality_report
analytics/position_behavior_profile_comparison.py → analytics.position_behavior_profile
analytics/position_behavior_profile_distribution.py → analytics.position_behavior_profile
analytics/position_behavior_profile_ranking.py → analytics.position_behavior_profile
analytics/position_behavior_profile_summary.py → analytics.position_behavior_profile
analytics/position_distribution.py → analytics.frequency_analysis, analytics.position_frequency
analytics/position_distribution_change.py → analytics.position_distribution
analytics/position_distribution_change_classification.py → analytics.position_distribution_change
analytics/position_distribution_change_magnitude_summary.py → analytics.position_distribution_change_magnitude
analytics/position_distribution_change_summary.py → analytics.position_distribution_change, analytics.position_distribution_change_classification
analytics/position_distribution_change_trend.py → analytics.position_distribution
analytics/position_distribution_metrics.py → analytics.position_distribution
analytics/position_distribution_stability.py → analytics.position_distribution, analytics.position_distribution_metrics
analytics/position_distribution_stability_comparison.py → analytics.position_distribution_stability_summary
analytics/position_distribution_stability_comparison_summary.py → analytics.position_distribution_stability_comparison
analytics/position_distribution_stability_detail.py → analytics.position_distribution_volatility
analytics/position_distribution_stability_overview.py → analytics.position_distribution_stability_comparison_summary
analytics/position_distribution_stability_summary.py → analytics.position_distribution_volatility
analytics/position_distribution_stability_trend.py → analytics.position_distribution_stability_overview
analytics/position_distribution_stability_trend_comparison.py → analytics.position_distribution_stability_trend, analytics.position_distribution_stability_trend_overview
analytics/position_distribution_stability_trend_detail.py → analytics.position_distribution_stability_trend, analytics.position_distribution_stability_trend_overview
analytics/position_distribution_stability_trend_overview.py → analytics.position_distribution_stability_trend, analytics.position_distribution_stability_trend_summary
analytics/position_distribution_stability_trend_summary.py → analytics.position_distribution_stability_trend
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview
analytics/position_distribution_stability_trend_transition_comparison_overview_comparison_summary.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail
analytics/position_distribution_stability_trend_transition_overview.py → analytics.position_distribution_stability_trend_transition_summary
analytics/position_distribution_stability_trend_transition_summary.py → analytics.position_distribution_stability_trend_detail
analytics/position_distribution_trend_consistency.py → analytics.position_distribution
analytics/position_distribution_trend_persistence.py → analytics.position_distribution
analytics/position_distribution_trend_strength.py → analytics.position_distribution
analytics/position_distribution_trend_strength_summary.py → analytics.position_distribution_trend_strength
analytics/position_distribution_volatility.py → analytics.position_distribution
analytics/position_distribution_volatility_summary.py → analytics.position_distribution_volatility
analytics/position_frequency.py → analytics.frequency_analysis, analytics.statistical_foundation
analytics/position_frequency_summary.py → analytics.frequency_analysis, analytics.position_frequency
analytics/random_forest.py → features.sequence_dataset, features.versioning_contract
analytics/statistical_baseline_comparison.py → analytics.statistical_probability_baseline
analytics/statistical_baseline_contract.py → analytics.statistical_foundation
analytics/statistical_baseline_dataset.py → analytics.statistical_baseline_contract, analytics.statistical_foundation
analytics/statistical_baseline_reproducibility.py → analytics.statistical_baseline_dataset, analytics.statistical_baseline_validation, analytics.statistical_central_tendency_dispersion, analytics.statistical_conditional_probability, analytics.statistical_distribution_baseline, analytics.statistical_independence_baseline, analytics.statistical_probability_baseline, analytics.statistical_significance_baseline
analytics/statistical_baseline_validation.py → analytics.statistical_baseline_dataset, analytics.statistical_central_tendency_dispersion, analytics.statistical_conditional_probability, analytics.statistical_distribution_baseline, analytics.statistical_independence_baseline, analytics.statistical_probability_baseline, analytics.statistical_significance_baseline
analytics/statistical_baseline_version_integration.py → analytics.statistical_baseline_dataset, analytics.statistical_baseline_validation, features.version_compatibility, features.versioning_contract
analytics/statistical_central_tendency_dispersion.py → analytics.statistical_baseline_dataset, analytics.statistical_descriptive
analytics/statistical_conditional_probability.py → analytics.statistical_baseline_dataset, analytics.statistical_foundation
analytics/statistical_descriptive.py → analytics.statistical_baseline_dataset, analytics.statistical_foundation
analytics/statistical_distribution_baseline.py → analytics.position_distribution, analytics.position_frequency, analytics.statistical_baseline_dataset, analytics.statistical_foundation
analytics/statistical_frequency_baseline.py → analytics.frequency_analysis, analytics.statistical_baseline_dataset, analytics.statistical_foundation
analytics/statistical_independence_baseline.py → analytics.statistical_baseline_dataset
analytics/statistical_position_baseline.py → analytics.statistical_baseline_dataset, analytics.statistical_descriptive, analytics.statistical_foundation
analytics/statistical_probability_baseline.py → analytics.statistical_baseline_dataset, analytics.statistical_distribution_baseline
analytics/statistical_significance_baseline.py → analytics.statistical_baseline_dataset
analytics/temporal_position_analysis.py → analytics.statistical_foundation
analytics/temporal_position_change_classification.py → analytics.temporal_position_change_detection
analytics/temporal_position_change_summary.py → analytics.temporal_position_change_classification
analytics/temporal_position_summary.py → analytics.temporal_position_analysis
analytics/xgboost.py → features.sequence_dataset, features.versioning_contract
database/__init__.py → database.engine
database/classification_rules.py → database.parser
database/classification_service.py → database.classification_rules, database.models
database/classification_validator.py → database.classification_rules, database.parser
database/data_quality_service.py → database.data_quality_rules, database.models
database/engine.py → database.config
database/historical_input_service.py → database.models, database.services
database/historical_quality_checker.py → database.data_quality_service, database.models
database/init_db.py → database.engine
database/jodi_family_relationship.py → database.jodi_relationship, database.jodi_service, database.models
database/jodi_relationship.py → database.jodi_validator
database/jodi_service.py → database.jodi_validator, database.models
database/models.py → database.engine
database/panel_family_relationship.py → database.models, database.panel_relationship, database.panel_service
database/panel_relationship.py → database.panel_validator
database/panel_service.py → database.models, database.panel_validator
database/panna_service.py → database.models, database.panna_validator
database/quality_report_service.py → database.historical_quality_checker
database/services.py → database.models, database.parser
features/artifact_integrity.py → features.feature_artifact
features/change_trend_features.py → features.feature_config, features.historical_data_loader
features/cross_position_family_relationships.py → features.feature_config, features.point_in_time, features.position_family
features/cross_position_features.py → features.feature_config, features.point_in_time
features/dataset_versioning.py → features.feature_versioning, features.unified_dataset, features.versioning_contract
features/family_recency.py → database.models, features.feature_config, features.jodi_family, features.panna_panel_family, features.point_in_time
features/family_transitions.py → features.feature_config, features.jodi_family, features.panna_panel_family, features.point_in_time
features/feature_artifact.py → features.feature_dataset_contract, features.feature_schema, features.feature_validator, features.feature_versioning
features/feature_dataset_contract.py → features.feature_pipeline, features.feature_schema, features.feature_validator, features.feature_versioning, features.unified_dataset
features/feature_pipeline.py → database.models, database.services, features.feature_config, features.feature_schema, features.feature_schema_builder, features.feature_validator, features.feature_versioning, features.historical_data_loader, features.leakage_detector, features.point_in_time, features.unified_dataset
features/feature_schema_builder.py → features.feature_schema, features.unified_dataset
features/feature_validator.py → features.feature_schema, features.feature_schema_builder, features.unified_dataset
features/feature_versioning.py → features.feature_config, features.feature_schema, features.unified_dataset, features.versioning_contract
features/frequency_change_features.py → analytics.frequency_analysis, analytics.statistical_foundation, features.feature_config, features.historical_data_loader
features/frequency_concentration_features.py → analytics.distribution_regime_detection, features.feature_config, features.historical_data_loader
features/frequency_features.py → analytics.frequency_analysis, analytics.statistical_foundation, features.feature_config, features.point_in_time
features/historical_data_loader.py → database.models, database.services
features/historical_family_frequency.py → database.models, features.feature_config, features.historical_data_loader, features.jodi_family, features.panna_panel_family
features/historical_frequency_features.py → analytics.frequency_analysis, analytics.statistical_foundation, features.feature_config, features.point_in_time
features/historical_interval_features.py → features.feature_config, features.historical_data_loader
features/jodi_family.py → database.jodi_validator, database.models
features/lag_features.py → features.feature_config, features.point_in_time
features/leakage_detector.py → features.historical_data_loader, features.point_in_time
features/observation_density_features.py → features.feature_config, features.historical_data_loader
features/panna_panel_family.py → database.models, database.panel_validator, database.panna_validator
features/point_in_time.py → features.historical_data_loader
features/position_family.py → features.feature_config, features.jodi_family, features.panna_panel_family, features.point_in_time
features/position_features.py → features.feature_config, features.point_in_time
features/position_transitions.py → features.feature_config, features.point_in_time
features/recency_bucket_features.py → features.feature_config, features.historical_data_loader
features/recency_distribution_features.py → features.feature_config, features.point_in_time
features/recency_expansion_features.py → features.feature_config, features.point_in_time
features/recency_features.py → features.feature_config, features.point_in_time
features/relationship_change_trend.py → analytics.cross_position_relationship_change_detection, analytics.cross_position_relationship_stability, features.feature_config, features.point_in_time
features/rolling_features.py → features.feature_config, features.point_in_time
features/rolling_frequency_features.py → analytics.frequency_analysis, analytics.statistical_foundation, features.feature_config, features.historical_data_loader
features/sequence_dataset.py → features.historical_data_loader
features/sequence_dataset_artifact.py → features.feature_schema, features.feature_versioning, features.sequence_dataset, features.sequence_dataset_integration
features/sequence_dataset_integration.py → features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_validator, features.sequence_leakage_validator, features.sequence_targets, features.sequence_temporal_split, features.sequence_windows
features/sequence_dataset_reproducibility.py → features.sequence_dataset_integration
features/sequence_dataset_validator.py → features.sequence_dataset, features.sequence_targets, features.sequence_windows
features/sequence_features.py → features.feature_config, features.point_in_time
features/sequence_leakage_validator.py → features.historical_data_loader, features.leakage_detector, features.sequence_dataset, features.sequence_targets, features.sequence_windows
features/sequence_targets.py → features.historical_data_loader, features.sequence_dataset, features.sequence_windows
features/sequence_temporal_split.py → features.sequence_dataset
features/sequence_windows.py → features.historical_data_loader, features.sequence_dataset
features/transition_frequency.py → features.feature_config, features.point_in_time
features/transition_stability.py → features.feature_config, features.point_in_time
features/unified_dataset.py → features.change_trend_features, features.cross_position_features, features.family_recency, features.feature_config, features.frequency_change_features, features.frequency_concentration_features, features.frequency_features, features.historical_family_frequency, features.historical_frequency_features, features.historical_interval_features, features.lag_features, features.observation_density_features, features.point_in_time, features.position_features, features.recency_bucket_features, features.recency_distribution_features, features.recency_expansion_features, features.recency_features, features.rolling_features, features.rolling_frequency_features, features.sequence_features, features.time_features
features/version_comparison.py → features.versioning_contract
features/version_compatibility.py → features.versioning_contract
features/version_lineage.py → features.dataset_versioning, features.feature_versioning, features.versioning_contract
features/version_reproducibility.py → features.artifact_integrity, features.dataset_versioning, features.feature_versioning, features.versioned_artifact, features.versioning_contract
features/version_validation.py → features.artifact_integrity, features.dataset_versioning, features.feature_versioning, features.version_compatibility, features.versioned_artifact, features.versioning_contract
features/versioned_artifact.py → features.artifact_integrity, features.feature_artifact, features.feature_versioning, features.version_compatibility, features.versioning_contract
tests/conftest.py → database.engine, database.models
tests/test_artifact_integrity.py → database.services, features.artifact_integrity, features.feature_artifact, features.feature_config, features.feature_dataset_contract, features.feature_pipeline, features.feature_schema
tests/test_bayesian_models.py → analytics.bayesian_models, analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation, features.versioning_contract
tests/test_catboost.py → analytics.catboost
tests/test_change_trend_features.py → features.change_trend_features, features.feature_config, features.historical_data_loader
tests/test_classification_queries.py → database.classification_service, database.historical_input_service, database.models
tests/test_classification_rules.py → database.classification_rules
tests/test_classification_service.py → database.classification_service, database.models
tests/test_classification_validator.py → database.classification_rules, database.classification_validator, database.models
tests/test_cross_position_family_relationships.py → database.models, features.cross_position_family_relationships, features.feature_config, features.historical_data_loader, features.point_in_time
tests/test_cross_position_features.py → features.cross_position_features, features.feature_config, features.historical_data_loader, features.point_in_time
tests/test_cross_position_relationship_change_detection.py → analytics.cross_position_relationship_change_detection
tests/test_cross_position_relationship_matrix.py → analytics.cross_position_relationship_matrix
tests/test_cross_position_relationship_overview.py → analytics.cross_position_relationship_change_detection, analytics.cross_position_relationship_matrix, analytics.cross_position_relationship_overview, analytics.cross_position_relationship_stability, analytics.cross_position_relationship_summary
tests/test_cross_position_relationship_stability.py → analytics.cross_position_relationship_stability
tests/test_cross_position_relationship_summary.py → analytics.cross_position_relationship_matrix, analytics.cross_position_relationship_summary
tests/test_cyclical_time_features.py → features.cyclical_time_features
tests/test_data_quality_rules.py → database.data_quality_rules
tests/test_data_quality_service.py → database.data_quality_service, database.models
tests/test_dataset_versioning.py → features.dataset_versioning, features.feature_config, features.feature_schema, features.feature_versioning, features.unified_dataset, features.versioning_contract
tests/test_decision_tree.py → analytics.decision_tree
tests/test_distribution_regime_detection.py → analytics.distribution_regime_detection
tests/test_distribution_regime_overview.py → analytics.distribution_regime_detection, analytics.distribution_regime_overview, analytics.distribution_regime_transition_analysis
tests/test_distribution_regime_stability.py → analytics.distribution_regime_detection, analytics.distribution_regime_stability, analytics.distribution_regime_transition_analysis
tests/test_distribution_regime_summary.py → analytics.distribution_regime_detection, analytics.distribution_regime_summary, analytics.distribution_regime_transition_analysis
tests/test_distribution_regime_transition_analysis.py → analytics.distribution_regime_detection, analytics.distribution_regime_transition_analysis
tests/test_extra_trees.py → analytics.extra_trees
tests/test_family_recency.py → database.jodi_service, database.models, database.panel_service, features.family_recency, features.feature_config, features.point_in_time
tests/test_family_transitions.py → database.jodi_service, database.models, database.panel_service, features.family_transitions, features.feature_config, features.historical_data_loader, features.point_in_time
tests/test_feature_artifact.py → database.services, features.feature_artifact, features.feature_config, features.feature_dataset_contract, features.feature_pipeline
tests/test_feature_config.py → features.feature_config
tests/test_feature_dataset_contract.py → database.services, features.feature_config, features.feature_dataset_contract, features.feature_pipeline, features.feature_schema, features.feature_versioning
tests/test_feature_pipeline.py → database.models, database.services, features.feature_config, features.feature_pipeline
tests/test_feature_schema.py → features.feature_schema
tests/test_feature_schema_builder.py → features.feature_schema, features.feature_schema_builder, features.unified_dataset
tests/test_feature_validator.py → features.feature_schema, features.feature_validator, features.unified_dataset
tests/test_feature_version_identity_validation.py → features.feature_config, features.feature_schema, features.feature_versioning, features.versioning_contract
tests/test_feature_versioning.py → features.feature_config, features.feature_schema, features.feature_versioning, features.unified_dataset
tests/test_frequency_analysis.py → analytics.frequency_analysis, analytics.statistical_foundation
tests/test_frequency_change_features.py → features.feature_config, features.frequency_change_features, features.historical_data_loader
tests/test_frequency_concentration_features.py → features.feature_config, features.frequency_concentration_features, features.historical_data_loader
tests/test_frequency_features.py → features.feature_config, features.frequency_features, features.historical_data_loader, features.point_in_time
tests/test_gradient_boosting.py → analytics.gradient_boosting
tests/test_gru.py → analytics.gru
tests/test_hidden_markov_models.py → analytics.hidden_markov_models
tests/test_historical_data_loader.py → database.models, database.services, features.historical_data_loader
tests/test_historical_family_frequency.py → database.models, features.feature_config, features.historical_data_loader, features.historical_family_frequency
tests/test_historical_frequency_features.py → features.feature_config, features.historical_frequency_features, features.point_in_time
tests/test_historical_input_service.py → database.historical_input_service, database.models
tests/test_historical_interval_features.py → features.feature_config, features.historical_data_loader, features.historical_interval_features
tests/test_historical_quality_checker.py → database.historical_quality_checker, database.models
tests/test_jodi_family.py → database.models, features.jodi_family
tests/test_jodi_family_relationship.py → database.jodi_family_relationship, database.jodi_service
tests/test_jodi_relationship.py → database.jodi_relationship
tests/test_jodi_service.py → database.jodi_service, database.models
tests/test_jodi_validator.py → database.jodi_validator
tests/test_lag_features.py → features.feature_config, features.historical_data_loader, features.lag_features, features.point_in_time
tests/test_leakage_detector.py → features.historical_data_loader, features.leakage_detector, features.point_in_time
tests/test_lightgbm.py → analytics.lightgbm
tests/test_logistic_regression.py → analytics.logistic_regression
tests/test_lstm.py → analytics.lstm
tests/test_markov_models.py → analytics.markov_models
tests/test_observation_density_features.py → features.feature_config, features.historical_data_loader, features.observation_density_features
tests/test_panel_family_relationship.py → database.models, database.panel_family_relationship, database.panel_service
tests/test_panel_relationship.py → database.panel_relationship
tests/test_panel_service.py → database.models, database.panel_service
tests/test_panel_validator.py → database.panel_validator
tests/test_panna_integration.py → database.models, database.panna_relationship, database.panna_service, database.panna_validator
tests/test_panna_panel_family.py → database.models, features.panna_panel_family
tests/test_panna_relationship.py → database.panna_relationship
tests/test_panna_service.py → database.models, database.panna_service
tests/test_panna_validator.py → database.panna_validator
tests/test_parser.py → database.parser
tests/test_phase16_comprehensive.py → features.feature_schema, features.feature_versioning, features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_artifact, features.sequence_dataset_integration, features.sequence_dataset_validator, features.sequence_leakage_validator, features.sequence_targets, features.sequence_temporal_split, features.sequence_windows
tests/test_phase8_integration.py → database.data_quality_rules, database.data_quality_service, database.historical_quality_checker, database.models, database.quality_report_service
tests/test_point_in_time.py → features.historical_data_loader, features.point_in_time
tests/test_position_analytics_comparison.py → analytics.position_analytics_comparison
tests/test_position_analytics_consolidation.py → analytics.position_analytics_consolidation
tests/test_position_analytics_quality_report.py → analytics.position_analytics_quality_report
tests/test_position_analytics_quality_summary.py → analytics.position_analytics_quality_report, analytics.position_analytics_quality_summary
tests/test_position_analytics_summary.py → analytics.position_analytics_summary
tests/test_position_behavior_profile.py → analytics.position_behavior_profile
tests/test_position_behavior_profile_comparison.py → analytics.position_behavior_profile, analytics.position_behavior_profile_comparison
tests/test_position_behavior_profile_distribution.py → analytics.position_behavior_profile, analytics.position_behavior_profile_distribution
tests/test_position_behavior_profile_ranking.py → analytics.position_behavior_profile, analytics.position_behavior_profile_ranking
tests/test_position_behavior_profile_summary.py → analytics.position_behavior_profile, analytics.position_behavior_profile_summary
tests/test_position_distribution.py → analytics.position_distribution, analytics.position_frequency, analytics.statistical_foundation
tests/test_position_distribution_change.py → analytics.position_distribution, analytics.position_distribution_change
tests/test_position_distribution_change_classification.py → analytics.position_distribution_change, analytics.position_distribution_change_classification
tests/test_position_distribution_change_magnitude.py → analytics.position_distribution_change_magnitude
tests/test_position_distribution_change_magnitude_summary.py → analytics.position_distribution_change_magnitude_summary
tests/test_position_distribution_change_summary.py → analytics.position_distribution_change, analytics.position_distribution_change_summary
tests/test_position_distribution_change_trend.py → analytics.position_distribution, analytics.position_distribution_change_trend
tests/test_position_distribution_metrics.py → analytics.position_distribution, analytics.position_distribution_stability
tests/test_position_distribution_stability.py → analytics.position_distribution, analytics.position_distribution_stability
tests/test_position_distribution_stability_comparison.py → analytics.position_distribution_stability_comparison, analytics.position_distribution_stability_summary, analytics.position_distribution_volatility
tests/test_position_distribution_stability_comparison_summary.py → analytics.position_distribution_stability_comparison, analytics.position_distribution_stability_comparison_summary
tests/test_position_distribution_stability_detail.py → analytics.position_distribution_stability_detail, analytics.position_distribution_volatility
tests/test_position_distribution_stability_overview.py → analytics.position_distribution_stability_comparison_summary, analytics.position_distribution_stability_overview
tests/test_position_distribution_stability_summary.py → analytics.position_distribution_stability_summary, analytics.position_distribution_volatility
tests/test_position_distribution_stability_trend.py → analytics.position_distribution_stability_overview, analytics.position_distribution_stability_trend
tests/test_position_distribution_stability_trend_comparison.py → analytics.position_distribution_stability_trend_comparison, analytics.position_distribution_stability_trend_overview
tests/test_position_distribution_stability_trend_detail.py → analytics.position_distribution_stability_trend_detail, analytics.position_distribution_stability_trend_overview
tests/test_position_distribution_stability_trend_overview.py → analytics.position_distribution_stability_trend, analytics.position_distribution_stability_trend_overview, analytics.position_distribution_stability_trend_summary
tests/test_position_distribution_stability_trend_summary.py → analytics.position_distribution_stability_trend, analytics.position_distribution_stability_trend_summary
tests/test_position_distribution_stability_trend_transition_comparison.py → analytics.position_distribution_stability_trend_transition_comparison, analytics.position_distribution_stability_trend_transition_overview
tests/test_position_distribution_stability_trend_transition_comparison_detail.py → analytics.position_distribution_stability_trend_transition_comparison_detail, analytics.position_distribution_stability_trend_transition_overview
tests/test_position_distribution_stability_trend_transition_comparison_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_summary
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_detail, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail
tests/test_position_distribution_stability_trend_transition_comparison_overview_comparison_summary.py → analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_detail, analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_summary
tests/test_position_distribution_stability_trend_transition_comparison_summary.py → analytics.position_distribution_stability_trend_transition_comparison_detail, analytics.position_distribution_stability_trend_transition_comparison_summary
tests/test_position_distribution_stability_trend_transition_overview.py → analytics.position_distribution_stability_trend_transition_overview, analytics.position_distribution_stability_trend_transition_summary
tests/test_position_distribution_stability_trend_transition_summary.py → analytics.position_distribution_stability_trend_detail, analytics.position_distribution_stability_trend_transition_summary
tests/test_position_distribution_trend_consistency.py → analytics.position_distribution, analytics.position_distribution_trend_consistency
tests/test_position_distribution_trend_persistence.py → analytics.position_distribution, analytics.position_distribution_trend_persistence
tests/test_position_distribution_trend_strength.py → analytics.position_distribution, analytics.position_distribution_trend_strength
tests/test_position_distribution_trend_strength_summary.py → analytics.position_distribution_trend_strength, analytics.position_distribution_trend_strength_summary
tests/test_position_distribution_volatility.py → analytics.position_distribution, analytics.position_distribution_volatility
tests/test_position_distribution_volatility_summary.py → analytics.position_distribution_volatility, analytics.position_distribution_volatility_summary
tests/test_position_family.py → database.models, features.feature_config, features.historical_data_loader, features.jodi_family, features.panna_panel_family, features.point_in_time, features.position_family
tests/test_position_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.position_features
tests/test_position_frequency.py → analytics.position_frequency, analytics.statistical_foundation
tests/test_position_frequency_summary.py → analytics.position_frequency, analytics.position_frequency_summary, analytics.statistical_foundation
tests/test_position_transitions.py → features.feature_config, features.point_in_time, features.position_transitions
tests/test_quality_report_service.py → database.models, database.quality_report_service
tests/test_random_forest.py → analytics.random_forest
tests/test_recency_bucket_features.py → features.feature_config, features.historical_data_loader, features.recency_bucket_features
tests/test_recency_distribution_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.recency_distribution_features
tests/test_recency_expansion_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.recency_expansion_features
tests/test_recency_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.recency_features
tests/test_relationship_change_trend.py → features.feature_config, features.point_in_time, features.relationship_change_trend
tests/test_rolling_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.rolling_features
tests/test_rolling_frequency_features.py → features.feature_config, features.historical_data_loader, features.rolling_frequency_features
tests/test_sequence_dataset.py → features.sequence_dataset
tests/test_sequence_dataset_artifact.py → features.feature_schema, features.feature_versioning, features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_artifact, features.sequence_dataset_integration, features.sequence_temporal_split
tests/test_sequence_dataset_integration.py → features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_integration, features.sequence_leakage_validator, features.sequence_temporal_split
tests/test_sequence_dataset_reproducibility.py → features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_integration, features.sequence_dataset_reproducibility, features.sequence_temporal_split
tests/test_sequence_dataset_validator.py → features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_validator, features.sequence_targets, features.sequence_windows
tests/test_sequence_features.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.sequence_features
tests/test_sequence_leakage_validator.py → features.historical_data_loader, features.sequence_dataset, features.sequence_dataset_validator, features.sequence_leakage_validator, features.sequence_targets, features.sequence_windows
tests/test_sequence_targets.py → features.historical_data_loader, features.sequence_dataset, features.sequence_targets, features.sequence_windows
tests/test_sequence_temporal_split.py → features.sequence_dataset, features.sequence_temporal_split
tests/test_sequence_windows.py → features.historical_data_loader, features.sequence_dataset, features.sequence_windows
tests/test_services.py → database.engine, database.models, database.services
tests/test_statistical_baseline_comparison.py → analytics.statistical_baseline_comparison, analytics.statistical_probability_baseline
tests/test_statistical_baseline_contract.py → analytics.statistical_baseline_contract, analytics.statistical_foundation
tests/test_statistical_baseline_dataset.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation
tests/test_statistical_baseline_reproducibility.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_baseline_reproducibility, analytics.statistical_foundation
tests/test_statistical_baseline_validation.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_baseline_validation, analytics.statistical_foundation
tests/test_statistical_baseline_version_integration.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_baseline_version_integration, analytics.statistical_foundation, features.versioning_contract
tests/test_statistical_central_tendency_dispersion.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_central_tendency_dispersion, analytics.statistical_foundation
tests/test_statistical_conditional_probability.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_conditional_probability, analytics.statistical_foundation
tests/test_statistical_descriptive.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_descriptive, analytics.statistical_foundation
tests/test_statistical_distribution_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_distribution_baseline, analytics.statistical_foundation
tests/test_statistical_foundation.py → analytics.statistical_foundation
tests/test_statistical_frequency_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation, analytics.statistical_frequency_baseline
tests/test_statistical_independence_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation, analytics.statistical_independence_baseline
tests/test_statistical_position_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_descriptive, analytics.statistical_foundation, analytics.statistical_position_baseline
tests/test_statistical_probability_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation, analytics.statistical_probability_baseline
tests/test_statistical_significance_baseline.py → analytics.statistical_baseline_contract, analytics.statistical_baseline_dataset, analytics.statistical_foundation, analytics.statistical_significance_baseline
tests/test_temporal_position_analysis.py → analytics.temporal_position_analysis
tests/test_temporal_position_change_classification.py → analytics.temporal_position_change_classification, analytics.temporal_position_change_detection
tests/test_temporal_position_change_detection.py → analytics.temporal_position_change_detection
tests/test_temporal_position_change_summary.py → analytics.temporal_position_change_classification, analytics.temporal_position_change_detection, analytics.temporal_position_change_summary
tests/test_temporal_position_summary.py → analytics.temporal_position_analysis, analytics.temporal_position_summary
tests/test_time_features.py → features.time_features
tests/test_transition_frequency.py → features.feature_config, features.point_in_time, features.transition_frequency
tests/test_transition_stability.py → features.feature_config, features.point_in_time, features.transition_stability
tests/test_unified_dataset.py → features.feature_config, features.historical_data_loader, features.point_in_time, features.unified_dataset
tests/test_version_comparison.py → features.version_comparison, features.versioning_contract
tests/test_version_compatibility.py → features.dataset_versioning, features.feature_config, features.feature_schema, features.feature_versioning, features.unified_dataset, features.version_compatibility, features.versioning_contract
tests/test_version_lineage.py → features.dataset_versioning, features.feature_config, features.feature_schema, features.feature_versioning, features.unified_dataset, features.version_lineage, features.versioning_contract
tests/test_version_reproducibility.py → database.models, database.services, features.artifact_integrity, features.dataset_versioning, features.feature_artifact, features.feature_config, features.feature_dataset_contract, features.feature_pipeline, features.feature_versioning, features.unified_dataset, features.version_reproducibility, features.versioned_artifact
tests/test_version_validation.py → database.models, database.services, features.artifact_integrity, features.dataset_versioning, features.feature_artifact, features.feature_config, features.feature_dataset_contract, features.feature_pipeline, features.feature_versioning, features.version_compatibility, features.version_validation, features.versioned_artifact
tests/test_versioned_artifact.py → database.services, features.artifact_integrity, features.dataset_versioning, features.feature_artifact, features.feature_config, features.feature_dataset_contract, features.feature_pipeline, features.feature_versioning, features.versioned_artifact
tests/test_versioning_contract.py → features.versioning_contract
tests/test_xgboost.py → analytics.xgboost, features.versioning_contract

## 20. Root File Inventory

- .env.example — environment template
- .gitignore — repository exclusions
- README.md — project entry documentation
- overview.txt — continuation/project context
- ull project discription.txt — historical master project description
- PROJECT_STATUS.md — authoritative current phase/status history
- CHANGELOG.md — milestone change history
- 
equirements.txt — runtime/test dependencies
- 
un.py — current application entry foundation
- 
eurolytics.pdf — project reference artifact
- project activate VM keys.txt — local project reference file; not part of production runtime

## 21. Phase-to-Architecture Connection Map

| Phase | Main architectural contribution | Connects forward to |
|---|---|---|
| 1 | project/environment foundation | all layers |
| 2 | SQLAlchemy/SQLite database | parser, services, references |
| 3 | historical parser/input | historical_results |
| 4 | Panna/Panel reference | family features |
| 5 | Jodi family reference | Jodi/family features |
| 6 | Panel family reference | Panel/family features |
| 7 | historical classification | descriptive analytics/quality |
| 8 | data quality engine | feature safety |
| 9 | frequency/statistical/position analytics | feature engineering |
| 10 | trend/correlation/anomaly related infrastructure | feature/analytics layers; not independently closed |
| 11 | relationship/cross-position related infrastructure | family/relationship features; not independently closed |
| 12 | sequence/transition related infrastructure | sequence dataset/features; not independently closed |
| 13 | leakage-safe feature framework | all later ML datasets |
| 14 | time/frequency/recency expansion | unified feature dataset |
| 15 | family/relationship/transition features | richer ML inputs |
| 16 | formal sequence dataset builder | Markov/HMM/LSTM/GRU/Transformer |
| 17 | feature/dataset versioning | artifact/lineage/model governance |
| 18 | statistical baseline | model comparison/evaluation |
| 19 | Bayesian models | probability/evaluation |
| 20 | Logistic Regression | supervised model family |
| 21 | Decision Tree | supervised model family |
| 22 | Random Forest | supervised model family |
| 23 | Extra Trees | supervised model family |
| 24 | Gradient Boosting | boosting model family |
| 25 | XGBoost | boosting model family |
| 26 | LightGBM | boosting model family |
| 27 | CatBoost | boosting model family |
| 28 | Markov sequence model | sequential comparison |
| 29 | Hidden Markov Model | sequential comparison |
| 30 | NumPy LSTM | recurrent sequence layer |
| 31 | NumPy GRU | recurrent sequence layer |
| 32 | Transformer | multi-head sequence architecture; next-digit probability model |
| 33 | Advanced Sequence Framework | interoperable sequence-model registry and orchestration |

## 21A. Phase 32 Production Connections

- analytics/transformer.py consumes validated digit sequence windows through the Phase 16 sequence contract concept.
- It does not query SQL directly and does not create a second historical-data loader.
- tests/test_transformer.py provides dedicated deterministic regression coverage.
- docs/PHASE_32_TRANSFORMER.md records the implementation contract and milestone closure.
- The model connects forward to future evaluation, calibration, comparison, ensemble, candidate scoring, ranking, and backtesting phases.
- Model persistence uses the existing Joblib-based project runtime; artifact identity and lineage remain model-layer responsibilities.
- The Transformer is intentionally independent from future framework-backed implementations so the deterministic reference remains testable.

## 21B. Phase 33 Production Connections

- analytics/sequence_framework.py provides the common sequence-model orchestration boundary.
- It consumes the existing sequence dataset contract and does not query SQL directly.
- The registry covers Markov, HMM, LSTM, GRU, and Transformer model families.
- Model-specific dataset builders, config classes, evaluators, and artifact builders remain authoritative.
- tests/test_sequence_framework.py provides 39 dedicated deterministic regression tests.
- docs/PHASE_33_ADVANCED_SEQUENCE_FRAMEWORK.md records the framework contract and milestone closure.
- Framework identity is derived deterministically from framework version, dataset identity, target, model versions, and artifact identities.
- The framework connects forward to evaluation, calibration, formal comparison, ensemble, candidate scoring, ranking, backtesting, monitoring, and API/UI.

## 22. Current End-to-End Contract

The current intended dependency direction is:

SQL → Historical Services → Reference/Analytics → Point-in-Time Features → Dataset Contracts → Versioning/Artifacts → Models → Evaluation → Calibration → Comparison → Ensemble → Ranking → Backtesting → Monitoring → API/UI.

A future phase should not bypass an authoritative earlier layer merely to simplify implementation.



## Phase 37 Architecture Update - 2026-09-30

Phase 37 establishes downstream explainability above candidate ranking.

Architecture:

Phase 35 ensemble
        ↓
Phase 36 candidate scoring / ranking
        ↓
Phase 37 explainability
        ↓
future UI / monitoring / actual-vs-ranked analysis

Phase 37 is evidence-preserving. Base explanations use only ranking and ensemble fields already present in production contracts. Model-level candidate attribution is optional and requires aligned SequenceEvaluationResult inputs; ensemble weights alone are never treated as fabricated model contributions.

New production artifacts:
- analytics/sequence_explainability.py
- tests/test_sequence_explainability.py
- docs/PHASE_37_EXPLAINABILITY.md

Phase 37 dedicated regression: 38 passed, 0 warnings.
Phase 37 full project regression: 5079 passed, 0 failures, 0 errors, 0 warnings.

Phase 38 is the next active downstream expansion.
## 19. Phase 38 Advanced Ensemble Expansion / Consensus

Phase 38 consumes Phase 35 SequenceEnsembleResult outputs and adds a second-order consensus layer.

Architecture:

    Phase 34 Evaluation / Calibration
                ↓
    Phase 35 Formal Ensemble Methods
                ↓
    Phase 36 Candidate Scoring / Ranking
                ↓
    Phase 37 Explainability
                ↓
    Phase 38 Advanced Ensemble Consensus
                ↓
    Future Walk-Forward / Backtesting
                ↓
    Monitoring / Lifecycle / API / UI

Production module:

    analytics/advanced_ensemble.py

Version:

    38.0.0

Core objects:

    SequenceEnsembleAgreement
    SequenceConsensusWeights
    SequenceConsensusResult
    SequenceAdvancedEnsembleReport
    SequenceAdvancedEnsembleValidationResult
Phase 38 agreement analysis computes pairwise Jensen-Shannon divergence and total variation across supplied Phase 35 ensemble probability distributions.

Agreement diagnostics:

    mean_pairwise_js_divergence
    max_pairwise_js_divergence
    mean_pairwise_total_variation
    agreement_score

Consensus weighting supports:

    equal_weight
    inverse_disagreement

Consensus probabilities are ten-class digit distributions over 0–9.

Consensus ranking uses:

    probability descending
    lower digit first on ties

Consensus diagnostics preserve:

    probability margin
    entropy
    normalized entropy
    effective candidate count

The phase is descriptive and compositional. It does not introduce a new model-training path or replace the Phase 35 ensemble mathematics.
Phase 38 validation requires:

    shared dataset identity
    shared observation count
    shared target sequence
    valid ten-class probability rows
    unique ensemble identities
    finite normalized consensus weights
    deterministic lineage identities

The phase preserves the project golden rules:

    SQL remains source of truth.
    Digit 0 remains valid.
    NULL remains distinct from zero.
    No historical ingestion is duplicated.
    No future leakage path is introduced.

Phase 38 production connections:

    analytics.sequence_ensemble.SequenceEnsembleResult
        ↓
    analytics.advanced_ensemble
        ├── agreement analysis
        ├── consensus weighting
        ├── probability consensus
        ├── rank consensus
        └── consensus validation
        ↓
    downstream backtesting / monitoring
Phase 38 regression and release state:

    Dedicated tests: 42 passed
    Full regression: 5121 passed
    Failures: 0
    Errors: 0
    Warnings: 0
    compileall: PASS
    git diff --check: PASS
    GitHub push: NOT PERFORMED

Phase 38 is COMPLETE LOCALLY — WARNING CLEAN.

Next architecture target:

    downstream walk-forward / backtesting and consensus evaluation.


## Phase 39 — Walk-Forward / Backtesting & Consensus Evaluation

Status: COMPLETE LOCALLY — WARNING CLEAN
Version: 39.0.0

Phase 39 adds the temporal validation layer after Phase 38 consensus.

Architecture:

Phase 38 Advanced Ensemble Consensus
        ↓
Phase 39 Walk-Forward Fold Engine
        ↓
chronological test observations
        ↓
probability metrics / fold results
        ↓
aggregate backtest report
        ↓
Phase 39 Consensus Evaluation
        ↓
future monitoring / lifecycle controls

Production:
- analytics/walk_forward_backtesting.py
- tests/test_walk_forward_backtesting.py
- docs/PHASE_39_WALK_FORWARD_BACKTESTING.md

Core contracts:
- expanding training window
- chronological test window
- train_end == test_start
- non-overlapping test windows
- ten-class probabilities
- digit 0 preserved
- deterministic SHA-256 lineage
- Phase 38 consensus compatibility

Metrics:
- log loss
- accuracy
- Top-K accuracy
- multiclass Brier score
- probability margin
- consensus agreement score

Phase 39 milestones 39.1–39.29: COMPLETE.

Verification:
- dedicated regression: 27 passed, 0 warnings
- compileall: PASS
- full regression: 5148 passed, 0 failures, 0 errors, 0 warnings
- git diff --check: PASS
- no new third-party dependency
- GitHub commit/push: not performed

Roadmap note: the historical 76-phase roadmap requires reconciliation because the implemented Phase 34–39 sequence differs from the older roadmap labels. This reconciliation should occur before assigning the next numbered implementation phase.


## Roadmap Reconciliation — 2026-09-30

The historical 76-phase roadmap is retained for traceability but is no longer treated as a one-to-one implementation map.

### Historical scope retained without retroactive closure

- Phases 10–12 remain not independently closed.
- Phase 13 is complete at milestone 13.75; no 13.76+ defined milestone sequence exists in current project records.

### Actual sequence-model implementation mapping

- Phase 34 — Advanced Sequence Evaluation & Calibration — COMPLETE
- Phase 35 — Formal Model Comparison / Ensemble — COMPLETE
- Phase 36 — Candidate Scoring / Ranking — COMPLETE
- Phase 37 — Explainability / Downstream Ranking Interpretation — COMPLETE
- Phase 38 — Advanced Ensemble Expansion / Consensus — COMPLETE
- Phase 39 — Walk-Forward / Backtesting & Consensus Evaluation — COMPLETE

### Superseded historical labels

- Historical Phase 35 Calibration is absorbed into actual Phase 34.
- Historical Phase 36 Model Comparison is implemented as actual Phase 35.
- Historical Phase 39 Candidate Scoring is implemented as actual Phase 36.
- Historical Phase 45 Walk-Forward Evaluation is implemented as actual Phase 39.
- Historical Phase 49 Disagreement / Consensus is implemented across actual Phases 38–39.

No duplicate capability should be implemented for these historical labels.

### Next implementation boundary

**Phase 40 — Learning-to-Rank Dataset — COMPLETE
41 — Learning-to-Rank Model — COMPLETE.

Phase 41 — Learning-to-Rank Model is the next implementation boundary.

The Phase 40 definition must preserve the existing point-in-time, leakage-safe, deterministic lineage architecture and must not rebuild candidate scoring, consensus, or walk-forward infrastructure.


## Phase 47 Monitoring Architecture

Phase 47 introduces the formal performance monitoring layer above Phase 46.

Phase 46 PerformanceOverTimeReport
→ Phase 47 PerformanceMonitoringReport
→ Phase 48 Performance Degradation Detection

The Phase 47 report contains deterministic PerformanceMetricSnapshot records, source lineage, configurable monitored metrics, first-period baseline values, and latest-period values. It is observational only and does not perform alerting, degradation classification, drift detection, retraining, ranking changes, or prediction generation.

Monitoring metrics are derived exclusively from Phase 46 period metrics. The monitoring layer does not recompute historical outcomes or create new predictive signal.

## Phase 47 Boundary Rule

Future monitoring phases must consume the validated Phase 47 contract rather than bypassing it when implementing degradation, drift, alerting, model health, or lifecycle logic.


## Phase 48 — Performance Degradation Detection

Phase 48 consumes the validated Phase 47 PerformanceMonitoringReport and produces a deterministic PerformanceDegradationReport.

Phase 47 Performance Monitoring
→ Phase 48 Performance Degradation Detection
→ Phase 49 Model Drift Detection

Degradation is rule-based and explicit. Each rule defines a monitored metric, an absolute threshold, an optional relative threshold, and a required number of consecutive adverse period transitions. A metric is degraded only when adverse direction, threshold breach, and consecutive evidence requirements are all satisfied.

Higher values are treated as adverse for mean_actual_rank and miss_rate. Lower values are treated as adverse for reciprocal rank, probability metrics, and hit_at_K metrics.

Phase 48 is detection-only. It does not send alerts, retrain models, select or promote models, rollback artifacts, change predictions, or modify ranking semantics.

Future alerting and lifecycle phases must consume this validated degradation contract rather than embedding independent degradation logic.


## Phase 49 Model Drift Detection Architecture

Phase 49 adds model-output distribution monitoring above the Phase 45 ActualVsRankedReport.

Phase 45 Actual-vs-Ranked Observations
   ↓
Temporal Period Grouping
   ↓
Baseline Prediction Distribution
   ↓
Comparison Prediction Distributions
   ↓
PSI Drift Detection
   ↓
Validated ModelDriftReport
   ↓
Phase 50 Data Drift Detection

The Phase 49 detector uses top_probability and cumulative_probability by default. It compares populated periods against the earliest populated baseline using deterministic equal-width probability bins and configurable PSI thresholds.

Architecture rules:
- Phase 45 remains the source of truth for model-output observations.
- Empty calendar periods are never fabricated.
- Source lineage is preserved.
- Digit 0 and leading-zero values remain untouched.
- Model drift does not imply data drift or concept drift.
- No retraining, reranking, rescoring, promotion, rollback, alerting, or SQL mutation occurs in Phase 49.
- No new third-party dependency is required.

## Phase 50 Data Drift Detection Architecture

Validated FeatureArtifact History
   ↓
Feature-Version / Schema Alignment
   ↓
Temporal Period Grouping
   ↓
Baseline Feature Distributions
   ↓
Comparison Feature Distributions
   ↓
PSI Drift Detection
   ↓
Validated DataDriftReport
   ↓
Phase 51 Prediction Distribution Monitoring

Phase 50 monitors numeric input-feature distributions. The earliest populated period is the baseline and later populated periods are compared independently. None values are excluded from numeric samples; a period with no remaining numeric sample for a monitored feature is rejected.

Architecture rules:
- FeatureArtifact remains the source contract.
- Feature version and feature ordering must remain consistent.
- Empty calendar periods are never fabricated.
- No feature values are modified.
- No SQL or historical source data is modified.
- Data drift is not model-output drift and is not concept drift.
- No retraining, reranking, rescoring, promotion, rollback, or alerting occurs in Phase 50.
- No new third-party dependency is required.
## Phase 51 Architecture Update — Prediction Distribution Monitoring

Phase 51 adds a monitoring-only temporal distribution layer above the validated Phase 45 ActualVsRankedReport.

Architecture:

Phase 45 ActualVsRankedReport
    ↓
Phase 46 Performance Over Time
    ↓
Phase 47 Performance Monitoring
    ↓
Phase 48 Performance Degradation Detection
    ↓
Phase 49 Model Drift Detection
    ↓
Phase 50 Data Drift Detection
    ↓
Phase 51 Prediction Distribution Monitoring
    ↓
Phase 52 Calibration Drift Monitoring

Phase 51 records period-level prediction-output distributions that are actually exposed by the Phase 45 contract:
- observed rank distribution
- rank-bucket distribution
- top-probability distribution
- top-probability mean
- cumulative-probability mean
- probability entropy
- observation and miss counts

Phase 51 deliberately does not invent predicted-candidate identity because Phase 45 does not expose that field.

Phase 51 is descriptive monitoring only. Drift classification remains a separate concern, with Phase 49 already providing model-output drift detection and later monitoring phases handling additional drift/calibration boundaries.

No historical ingestion, feature engineering, model training, ranking, prediction generation, or source mutation is duplicated by Phase 51.
## Phase 52 Architecture Update — Calibration Drift Monitoring

Phase 52 adds calibration monitoring after Phase 51 prediction-distribution monitoring.

Architecture:

Phase 45 ActualVsRankedReport
    ↓
Phase 46 Performance Over Time
    ↓
Phase 47 Performance Monitoring
    ↓
Phase 48 Performance Degradation Detection
    ↓
Phase 49 Model Drift Detection
    ↓
Phase 50 Data Drift Detection
    ↓
Phase 51 Prediction Distribution Monitoring
    ↓
Phase 52 Calibration Drift Monitoring
    ↓
Phase 53 Ranking Drift Monitoring

Phase 52 uses the current Phase 45 probability/outcome contract:
- top_probability is the predicted probability
- actual_rank == 1 is the observed Top-1 outcome
- actual_rank > 1 is the observed negative outcome
- actual_rank == None is excluded from calibration calculations

Phase 52 monitors mean predicted probability, empirical Top-1 hit rate, signed calibration gap, Brier score, expected calibration error, and calibration-bin statistics.

Phase 52 detects baseline-to-period calibration changes using configurable absolute thresholds. It does not generate predictions, rerank/rescore, retrain, promote, rollback, alert operationally, or mutate source data.

No candidate identity is fabricated because the Phase 45 source contract does not expose it.
## Phase 53 Architecture Update — Ranking Drift Monitoring

Phase 53 adds ranking-structure drift monitoring after calibration monitoring.

Architecture:

Phase 45 ActualVsRankedReport
    ↓
Phase 46 Performance Over Time
    ↓
Phase 47 Performance Monitoring
    ↓
Phase 48 Performance Degradation Detection
    ↓
Phase 49 Model Drift Detection
    ↓
Phase 50 Data Drift Detection
    ↓
Phase 51 Prediction Distribution Monitoring
    ↓
Phase 52 Calibration Drift Monitoring
    ↓
Phase 53 Ranking Drift Monitoring
    ↓
Phase 54 Feature Drift Monitoring

Phase 53 monitors:
- Top-1, Top-3, Top-5, and Top-10 rates
- mean actual rank
- mean reciprocal rank
- exact numeric rank distributions
- rank-bucket distributions
- rank-distribution PSI

Phase 53 compares each later populated period against the earliest populated baseline period.
It uses configurable absolute-change thresholds for scalar ranking metrics and PSI thresholds
for numeric rank-distribution drift.

Phase 53 is monitoring-only. It does not generate predictions, rerank/rescore candidates,
retrain models, promote/rollback models, generate operational alerts, or mutate source data.

Missing actual ranks are excluded from rank-distribution metrics and preserved as missed
observations. Leading-zero source values remain untouched.

The existing Phase 45 source contract is the sole source of truth for this phase.

## Phase 54 — Feature Drift Monitoring

Phase 54 establishes a feature-specific monitoring layer above the validated FeatureArtifact contract.

Architecture:

FeatureArtifact History
        ↓
Source / Lineage Validation
        ↓
Numeric Feature Rule Selection
        ↓
Chronological Populated Periods
        ↓
Earliest Period Baseline
        ↓
Feature Statistics
  ├─ Numeric Count
  ├─ Missing Rate
  ├─ Mean
  └─ Standard Deviation
        ↓
PSI Distribution Comparison
        ↓
FeatureDriftObservation
        ↓
FeatureDriftReport
        ├─ Drifted Features
        ├─ Drifted Periods
        ├─ Overall Drift
        └─ Deterministic Identity
        ↓
Strict Validation / Summary / Accessors
        ↓
Future Concept Drift / Alert / Lifecycle Layers

Phase 54 does not mutate FeatureArtifact history and does not create a parallel feature-generation pipeline.

The feature-drift layer requires:
- valid FeatureArtifact inputs
- leakage status CLEAN
- identical feature version
- identical feature names and order
- unique target dates
- at least two populated periods
- numeric values or None for monitored numeric features

The baseline is the earliest populated period. Later populated periods are compared to that baseline. Empty calendar periods are never fabricated.

PSI uses equal-width bins over the combined baseline/comparison range and epsilon 1e-12 for zero-frequency safety. Drift is detected when PSI is greater than or equal to the configured threshold.

Phase 54 is deliberately distinct from Phase 50 Data Drift Detection: Phase 50 provides the general model-input data-drift contract, while Phase 54 explicitly monitors engineered FeatureArtifact behavior with feature statistics and missingness.

Phase 54 does not implement concept drift detection, alerting, retraining, model promotion, rollback, prediction generation, or ranking changes.

Phase 54 version: 54.0.0.
Phase 54 dedicated regression: 54 passed before final full-suite verification.
Next architecture phase: Phase 55 — Concept Drift Detection.

## Phase 55 — Concept Drift Detection

Phase 55 establishes the first explicit feature-to-outcome relationship monitoring layer.

Architecture:

FeatureArtifact History
        ↓
Feature Source Validation
        ↓
Phase 45 ActualVsRankedReport
        ↓
Outcome Source Validation
        ↓
Exact Target-Date Alignment
        ↓
Chronological Populated Periods
        ↓
Earliest Period Baseline
        ↓
Baseline Feature Bins
        ↓
Conditional Outcome Rates P(Y | X-bin)
        ↓
Later-Period Conditional Outcome Rates
        ↓
Weighted Absolute Conditional Rate Change
        ↓
ConceptDriftObservation
        ↓
ConceptDriftReport
        ├─ Drifted Features
        ├─ Drifted Periods
        ├─ Overall Drift
        └─ Deterministic Identity
        ↓
Strict Validation / Summary / Accessors
        ↓
Future Alert / Threshold Layer

Phase 55 is intentionally different from Phase 54. Phase 54 asks whether feature distributions changed. Phase 55 asks whether the outcome relationship at comparable feature values changed.

Phase 55 also remains distinct from Phase 52 calibration drift: calibration drift evaluates predicted probabilities against outcomes, whereas concept drift evaluates the conditional relationship between engineered feature values and observed outcomes.

The outcome contract uses actual_rank == 1 as the positive outcome, actual_rank > 1 as negative, and unavailable actuals as excluded.

The same baseline feature bin edges are reused for every comparison period so that changes in conditional outcome rates are measured on a stable feature-value partition.

Phase 55 does not generate predictions, mutate features, retrain models, rerank candidates, alter probabilities, alert, promote, or rollback models.

Phase 55 version: 55.0.0.
Phase 55 dedicated regression: 58 passed.
Next architecture phase: Phase 56 — Alert / Threshold Framework.

## Phase 56 — Alert / Threshold Framework

Phase 56 establishes a reusable evaluation boundary above NeuroLytics monitoring reports.

Architecture:

Monitoring Metric Values
        ↓
Explicit AlertRule Configuration
        ↓
Rule Validation
        ↓
Operator Evaluation
        ↓
AlertObservation
        ├─ Active / Clear
        ├─ INFO / WARNING / CRITICAL
        └─ Source Lineage
        ↓
AlertThresholdReport
        ├─ Active Alerts
        ├─ Critical Alerts
        ├─ Warning Alerts
        ├─ Alert Count
        └─ Deterministic SHA-256 Identity
        ↓
Strict Validation / Summary / Accessors
        ↓
Future Model Health / Operational Layers

Supported operators are gte, gt, lte, lt, and eq. Multiple rules may target the same metric. Disabled rules remain configured but are not evaluated.

Phase 56 is intentionally action-free. It does not send notifications, retrain models, promote or rollback models, rerank candidates, change predictions, or mutate source data.

Phase 56 version: 56.0.0.
Dedicated regression: 63 passed.
Full regression: 5,907 passed, 0 failures, 0 errors, 0 warnings.
Next architecture phase: Phase 57 — Model Health Scorecard.

## Phase 57 — Model Health Scorecard

Phase 57 establishes a unified normalized health aggregation boundary.

Monitoring / Alert Components
        ↓
Normalized HealthComponent
        ├─ score [0,1]
        ├─ status
        ├─ weight
        └─ source identity
        ↓
Weighted Health Score
        ↓
HEALTHY / DEGRADED / CRITICAL
        ↓
ModelHealthReport
        ├─ critical components
        ├─ degraded components
        ├─ component count
        └─ deterministic SHA-256 identity
        ↓
Strict Validation / Summary / Accessors
        ↓
Future Model Comparison / Champion-Challenger / Promotion Layers

Default bands:
- HEALTHY >= 0.80
- DEGRADED >= 0.50 and < 0.80
- CRITICAL < 0.50

Phase 57 is intentionally action-free. It does not select, promote, rollback, retrain, modify, rerank, or change model behavior.

Phase 57 version: 57.0.0.
Dedicated regression: 80 passed.
Full regression: pending final verification.
Next architecture phase: Phase 58 — Model Comparison Over Time.

## Phase 58 — Model Comparison Over Time

Phase 57 Model Health Reports
        ↓
ModelHealthSnapshot
        ├─ period
        ├─ model identity
        ├─ health score
        ├─ health status
        ├─ component scores
        └─ source report identity
        ↓
Baseline / Comparison Periods
        ↓
Model Set Reconciliation
        ├─ common models
        ├─ baseline-only models
        └─ comparison-only models
        ↓
Health Score Delta
        ├─ absolute change
        └─ relative change
        ↓
Descriptive Change Classification
        ├─ improved
        ├─ declined
        └─ unchanged
        ↓
ModelComparisonReport
        ↓
Validation / Summary / Accessors
        ↓
Phase 59 Champion / Challenger Boundary

Phase 58 is descriptive only. Improved/declined classifications do not constitute a model recommendation, ranking, promotion, demotion, champion, or challenger decision.

Phase 58 version: 58.0.0.
Dedicated regression: 65 passed.
Full regression: pending final verification.
Next architecture phase: Phase 59 — Model Champion / Challenger Framework.

## Phase 59 — Model Champion / Challenger Framework

Phase 58 ModelComparisonReport
        ↓
Explicit Role Assignment
        ├── CHAMPION
        └── CHALLENGER × N
        ↓
Common-Model Eligibility
        ↓
Temporal Health Evidence
        ├── challenger score
        ├── champion score
        ├── absolute change
        └── relative change
        ↓
ChampionChallengerReport
        ├── eligible models
        ├── inactive models
        └── source lineage
        ↓
Strict Validation / Summary / Accessors
        ↓
Phase 60 Model Selection / Promotion Boundary

Phase 59 intentionally does not infer a winner, rank challengers, select a champion, calculate a promotion score, promote/demote models, alter traffic, retrain, or rollback.

Phase 59 version: 59.0.0.
Dedicated regression: 70 passed.
Full regression: pending final verification.
Next architecture phase: Phase 60 — Model Selection / Promotion Framework.


## Phase 60 — Model Selection / Promotion Framework

Phase 60 sits directly above Phase 59 Champion/Challenger evidence.

Phase 59 explicit roles/evidence
        ↓
Phase 60 promotion policy
        ↓
Challenger eligibility
        ↓
Deterministic candidate selection
        ↓
Promotion / Hold / Ineligible decision report
        ↓
Future Phase 61 model version lifecycle

Architecture boundary:
- Phase 60 does not infer the Phase 59 champion.
- Phase 60 does not mutate the active champion.
- Phase 60 does not change production traffic or prediction behavior.
- Phase 60 does not retrain or rollback models.
- Phase 60 records a deterministic decision artifact for later lifecycle handling.

Default selection policy:
- minimum health score = 0.80
- minimum improvement = 0.00
- healthy status required
- positive improvement required


## Phase 61 — Model Version Lifecycle

Phase 60 selection decision
        ↓
Model version identity
        ↓
CANDIDATE
   ┌────┴────┐
ACTIVE    REJECTED
   ↓
DEPRECATED
   ↓
RETIRED

Phase 61 records and validates lifecycle state and transitions. It does not itself mutate production state.

Lifecycle identity preserves model identity, version identity, artifact identity, Phase 60 source selection identity, optional parent version, transition reason, and transition source lineage.

## Phase 62 Retraining Decision Architecture — 2026-09-30

Monitoring Phases 47–55
        ↓
Normalized RetrainingEvidence
        ↓
RetrainingRule Evaluation
        ↓
Trigger / Supporting Evidence
        ↓
RETRAIN or HOLD Decision
        ↓
Phase 63 Retraining Dataset Pipeline
        ↓
Phase 64 Automated Retraining

Phase 62 is decision-only. It does not train, promote, rollback, deploy, mutate lifecycle state, or modify production traffic. Source identities and deterministic report identity are preserved.

## Phase 63 Retraining Dataset Architecture — 2026-09-30

Phase 62 Retraining Decision
        ↓
RETRAIN decision validation
        ↓
FeatureArtifact history
        ↓
VALID + CLEAN + same feature version
        ↓
Target-date alignment
        ↓
Chronological dataset assembly
        ↓
TRAIN / VALIDATION / TEST
        ↓
Lineage + deterministic dataset identity
        ↓
Phase 64 Automated Retraining

Phase 63 is dataset-preparation only. It does not train, promote, deploy, rollback, mutate lifecycle state, or modify production data.

## Phase 64 Automated Retraining Architecture — 2026-09-30

Phase 63 Validated Retraining Dataset
        ↓
Dataset Validation Gate
        ↓
Retraining Configuration
        ↓
Random Forest Training Engine
        ↓
TRAIN Evaluation
        ↓
VALIDATION Evaluation
        ↓
TEST Evaluation
        ↓
Model Identity + Artifact Identity
        ↓
Optional Explicit Persistence
        ↓
Phase 65 Post-Retraining Validation

Phase 64 trains a candidate artifact only. It does not promote, activate, register, deploy, rollback, or mutate production lifecycle state.

## Phase 65 Post-Retraining Validation Architecture — 2026-09-30

Phase 64 Automated Retraining Report
              ↓
Phase 63 Dataset Lineage Reconciliation
              ↓
Model / Artifact Identity Validation
              ↓
TRAIN / VALIDATION / TEST Reconciliation
              ↓
Metric Integrity + Threshold Validation
              ↓
Optional Persisted Artifact Validation
              ↓
Deterministic Validation Report
              ↓
Phase 66 Controlled Activation Boundary

Phase 65 is an independent validation gate. It does not train, promote, activate, register, deploy, rollback, or mutate production state.

## Phase 66 Controlled Activation Boundary — 2026-09-30

Phase 65 VALID validation
        ↓
Phase 61 CANDIDATE lifecycle state
        ↓
Phase 66 rollout checks
        ↓
READY / BLOCKED
        ↓
Explicit authorization
        ↓
AUTHORIZED rollout plan
        ↓
CANDIDATE→ACTIVE transition preview
        ↓
Phase 67 production activation executor

Phase 66 does not mutate lifecycle state, deploy services, change traffic, or execute production activation.

## Phase 67 — Production Activation / Rollout Executor Boundary

Phase 67 introduces the explicit executor boundary after Phase 66 authorization.

Architecture:

Phase 65 VALID validation
        ↓
Phase 61 CANDIDATE lifecycle
        ↓
Phase 66 READY rollout
        ↓
Phase 66 AUTHORIZED rollout
        ↓
Phase 67 activation plan
        ↓
Pre-execution revalidation
        ↓
CANDIDATE → ACTIVE transition representation
        ↓
Immutable activation receipt
        ↓
Future production serving / inference boundary

Key contract:
- analytics/production_activation.py
- authorization is mandatory by default
- current model state is revalidated immediately before execution
- model/artifact/version identities are reconciled
- activation is deterministic and auditable
- supplied ModelVersion is not mutated
- rollback is represented as preview metadata only
- external deployment and production traffic changes remain outside Phase 67

Phase 68 is the next architectural boundary: Production Serving / Inference Boundary.

## Phase 68 — Production Serving / Inference Boundary

Phase 68 introduces the serving/inference contract after Phase 67 activation.

Architecture:

Phase 67 activation receipt
        ↓
Phase 68 serving plan
        ↓
Serving validation
        ↓
Inference request normalization
        ↓
Model/version/artifact binding
        ↓
Predictor invocation
        ↓
Deterministic inference response
        ↓
Phase 69 production API / inference service

Key contract:
- analytics/production_serving.py
- activated receipt is required
- model/version/artifact identities are bound
- feature mappings are normalized and validated
- predictor errors are contained as structured rejections
- request and response identities are deterministic
- no SQL mutation
- no lifecycle mutation
- no network service deployment
- no production traffic changes

Phase 69 is the next architectural boundary: Production API / Inference Service Boundary.


## Phase 69 — Production API / Inference Service Boundary

Status: COMPLETE LOCALLY
Version: 69.0.0

Added:
- analytics/production_api.py
- tests/test_production_api.py
- docs/PHASE_69_PRODUCTION_API_INFERENCE_SERVICE_BOUNDARY.md

Phase 69 adds the Flask application-facing boundary above Phase 68. It provides /health, /ready, and /v1/inference, delegates model-bound validation to Phase 68, maps failures to structured HTTP responses, preserves deterministic response identity, and does not start a server automatically or mutate production state.

Dedicated regression: 70 passed, 0 failures, 0 errors, 0 warnings.

No new dependency. Flask was already installed.

Next: Phase 70 — API Security / Authentication / Authorization Boundary.


## Phase 70 — API Security / Authentication / Authorization Boundary

Status: COMPLETE LOCALLY
Version: 70.0.0

Added:
- analytics/api_security.py
- tests/test_api_security.py
- docs/PHASE_70_API_SECURITY_AUTHENTICATION_AUTHORIZATION_BOUNDARY.md

Architecture:
Phase 69 API
→ Phase 70 authentication
→ Phase 70 authorization
→ Phase 68 model-bound inference

Security uses hashed API keys, constant-time verification, configurable credential headers, scopes, roles, revocation, and structured 401/403 responses.

Health remains public. Readiness and inference require authorization when the security policy is enabled.

Dedicated Phase 70 regression: 70 passed, 0 failures, 0 errors, 0 warnings.

Next: Phase 71 — API Rate Limiting / Abuse Protection Boundary.


## Phase 71 — API Rate Limiting / Abuse Protection Boundary

Status: COMPLETE LOCALLY
Version: 71.0.0

Added:
- analytics/api_rate_limit.py
- tests/test_api_rate_limit.py
- docs/PHASE_71_API_RATE_LIMITING_ABUSE_PROTECTION_BOUNDARY.md

Updated:
- analytics/production_api.py

Architecture:
HTTP request
→ Phase 70 authentication / authorization
→ Phase 71 rate limiting / abuse protection
→ Phase 69 API validation
→ Phase 68 model-bound inference

Authenticated traffic is limited per credential identity. Authentication failures are limited per request IP. Health remains public and outside the limiter.

Default secure policy: 60 requests per 60 seconds with a 10-request burst window of 1 second.

HTTP 429 responses include Retry-After and X-RateLimit headers. Rate limiting occurs before payload parsing and before inference execution.

Dedicated Phase 71 regression: 70 passed, 0 failures, 0 errors, 0 warnings.

Adjacent Phase 68–71 regression: 280 passed, 0 failures, 0 errors, 0 warnings.

No new third-party dependency. GitHub commit/push was not performed.

Next: final full-project regression and Phase 72 boundary definition.


Phase 71 final regression update: 6994 passed in 130.26s, 0 failures, 0 errors, 0 warnings.

Next: Phase 72 boundary definition.


## Phase 72 — Performance / Monitoring API

Phase 72 adds the formal read-only API boundary over existing monitoring reports.

Architecture:

Phase 47–57 Monitoring / Health Reports
        ↓
Phase 72 Performance / Monitoring API
        ↓
Future Phase 77–88 Frontend / Dashboard Consumers

Implemented module:

analytics/performance_monitoring_api.py

Version:

72.0.0

Boundary:

PERFORMANCE_MONITORING_API_BOUNDARY

The service supports existing report families for performance, performance-over-time, performance degradation, model health, model drift, data drift, feature drift, calibration drift, ranking drift, concept drift, and prediction-distribution monitoring.

The API reuses authoritative report validators and summary functions. It does not recompute metrics from raw historical data and does not generate predictions.

Standalone endpoints:

GET /health
GET /v1/monitoring/summary
GET /v1/monitoring
GET /v1/monitoring/<report_type>

The service is intentionally read-only. It does not train models, mutate SQL, modify feature artifacts, activate models, rollback models, or mutate model lifecycle state.

Phase 70 authentication/authorization and Phase 71 rate limiting remain separate production boundaries. Phase 72 does not duplicate either implementation.

Phase 72 is the API contract consumed by later dashboard work; production service integration remains a later canonical roadmap boundary.

Dedicated Phase 72 regression: 48 passed, 0 failures, 0 errors, 0 warnings.

Next canonical roadmap phase: Phase 73 — Authentication / Authorization.


## Phase 72 Final Verification — 2026-10-01

Phase 72 is fully closed locally.

Dedicated regression: 48 passed, 0 failures, 0 errors, 0 warnings.

Adjacent Phase 68–72 regression: 328 passed in 22.53s, 0 failures, 0 errors, 0 warnings.

Full project regression: 7042 passed in 125.26s (2m 05s), 0 failures, 0 errors, 0 warnings.

Production import: PASS.
Compileall: PASS.
git diff --check: PASS.

Next canonical roadmap phase: Phase 73 — Authentication / Authorization.


## Phase 73 — Authentication / Authorization

Phase 73 formally integrates the existing Phase 70 API security primitives with the Phase 72 Performance / Monitoring API.

Architecture:

Phase 70 API Security
        ↓
Phase 73 Monitoring Authentication / Authorization
        ↓
Phase 72 Performance / Monitoring API
        ↓
Future monitoring consumers

Implemented module:

analytics/monitoring_api_authorization.py

Version: 73.0.0
Boundary: MONITORING_API_AUTHORIZATION_BOUNDARY

Default monitoring authorization scope: `monitoring:read`.

Protected route family: `/v1/monitoring*`.

`/health` remains public by default.

Phase 73 reuses Phase 70 `ApiCredentialStore`, `ApiSecurityPolicy`, `SecurityDecision`, credential hashing, revocation, and scope authorization. It does not create a second credential system.

Missing/invalid credentials map to HTTP 401. Revoked credentials and insufficient scope map to HTTP 403. Raw credentials are never returned.

Phase 71 rate limiting remains a separate boundary. Phase 72 remains the monitoring-report API owner.

Dedicated Phase 73 regression: 28 passed, 0 failures, 0 errors, 0 warnings.
Phase 72 + Phase 73 focused regression: 76 passed, 0 failures, 0 errors, 0 warnings.
Adjacent Phase 68–73 regression: 356 passed in 24.34s, 0 failures, 0 errors, 0 warnings.

Next canonical roadmap phase: Phase 74 — Production Monitoring Security Integration / Request Protection.


## Phase 73 Final Verification — 2026-10-01

Phase 73 is fully closed locally.

Dedicated regression: 28 passed, 0 failures, 0 errors, 0 warnings.
Phase 72 + Phase 73 focused regression: 76 passed, 0 failures, 0 errors, 0 warnings.
Adjacent Phase 68–73 regression: 356 passed in 24.34s, 0 failures, 0 errors, 0 warnings.
Full project regression: 7070 passed in 137.91s (2m 17s), 0 failures, 0 errors, 0 warnings.

Regression delta from Phase 72: +28 tests.
Production import: PASS.
Compileall: PASS.
git diff --check: PASS.

Next canonical roadmap phase: Phase 74 — Production Monitoring Security Integration / Request Protection.


## Roadmap Authority Update — 2026-10-01

The user-authoritative NeuroLytics implementation roadmap is now the exact 1–100 roadmap recorded in docs/ROADMAP_1_100.md.

Phase 47 is the current completed phase under that roadmap.

The next phase is Phase 48 — Performance Degradation Detection.

Older expanded roadmaps that inserted MLOps, CI/CD, Docker, Kubernetes, OAuth/OIDC, distributed infrastructure, or other unrequested production-infrastructure phases are not authoritative for phase numbering and must not be used to insert new phases.

Phase 47 monitoring remains observational and compositional. It consumes Phase 46 and provides the canonical monitoring contract for Phase 48 without performing degradation classification itself.


## Phase 48–74 Roadmap Reconciliation — 2026-10-01

Phases 48–73 are confirmed as existing complete local boundaries and remain authoritative in their existing production modules and tests.

Phase 74 adds the formal API request-validation/error-handling boundary above Phase 69 while preserving Phase 70 authentication and Phase 71 rate-limiting ordering.

Current official roadmap phase: Phase 74 — API Validation / Error Handling — COMPLETE LOCALLY.
Authoritative roadmap: docs/ROADMAP_1_100.md.
Next phase: Phase 75 — API Integration Testing.
