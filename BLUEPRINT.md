# NeuroLytics — Master Project Blueprint

Audit date: 2026-09-30
Current official phase: Phase 31 — GRU — COMPLETE LOCALLY
Latest full regression: 4849 passed, 0 failures, 0 errors, 0 warnings

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
Statistical + Classical ML + Markov/HMM + LSTM/GRU
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

## 11. LSTM / GRU Architecture

`	ext
Sequence Dataset → one-hot digits 0–9 → recurrent model → BPTT/gradient clipping
→ softmax → 10-digit probabilities → Top-K/evaluation → artifact/lineage/persistence/reproducibility
`

Phase 30/31 use NumPy only. Future framework-backed models should preserve the surrounding contracts.

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
- Phase 32: TRANSFORMER — NEXT
- Phases 33–76: FUTURE

## 14. Phase 32 Boundary

Phase 32 must reuse the historical loader, point-in-time rules, sequence dataset contract, temporal split, versioning, artifact/lineage infrastructure and testing pattern. It must not create a parallel historical-data or sequence-data pipeline.

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
| Markov/HMM/LSTM/GRU | established |
| Transformer | not started |
| evaluation/calibration/comparison | future formal phases |
| ensemble/ranking/backtesting | future |
| monitoring/lifecycle | future |
| backend/frontend | future formal phases |

## 16. Audit Notes

Live SQLite audit: 9 tables, 5 explicit FK relationships. Current Python production concentration: database/, features/, analytics/. Top-level backend/frontend/ml/ranking/backtesting/models/reports/scripts directories exist for current/future architecture but did not contain current Python production modules in this audit.

Older continuation documents are historical context. For current decisions prioritize actual source files, live schema, PROJECT_STATUS.md, CHANGELOG.md and latest regression.

## 17. Permanent Architecture Rule

Before every major phase: read BLUEPRINT.md, identify the correct architectural layer, reuse existing modules/contracts, add tests, run focused and full regression, update PROJECT_STATUS.md and CHANGELOG.md, and update BLUEPRINT.md when architecture changes.

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

### analytics/ (100 files)
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

### tests/ (187 files)
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

### docs/ (8 files)
- docs/PHASE_18_STATISTICAL_BASELINE.md
- docs/PHASE_19_BAYESIAN_MODELS.md
- docs/PHASE_20_LOGISTIC_REGRESSION.md
- docs/PHASE_21_DECISION_TREE.md
- docs/PHASE_22_RANDOM_FOREST.md
- docs/PHASE_23_EXTRA_TREES.md
- docs/PHASE_24_GRADIENT_BOOSTING.md
- docs/PHASE_31_GRU.md

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
| 32 | Transformer | next sequence architecture |

## 22. Current End-to-End Contract

The current intended dependency direction is:

SQL → Historical Services → Reference/Analytics → Point-in-Time Features → Dataset Contracts → Versioning/Artifacts → Models → Evaluation → Calibration → Comparison → Ensemble → Ranking → Backtesting → Monitoring → API/UI.

A future phase should not bypass an authoritative earlier layer merely to simplify implementation.

