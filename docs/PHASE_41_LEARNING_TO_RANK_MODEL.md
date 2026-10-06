# NeuroLytics — Phase 41: Learning-to-Rank Model

Date: 2026-09-30
Status: COMPLETE LOCALLY
Version: 41.0.0
Model kind: pairwise_logistic_ltr

## Scope

Phase 41 implements the first Learning-to-Rank model above the Phase 40 ranking judgment-list dataset.

The model uses pairwise logistic ranking: within each ten-candidate ranking group, the observed candidate is compared against each of the nine non-observed candidates. A linear scoring function is optimized over these pairwise differences.

The resulting candidate scores are converted to a ten-class softmax distribution for ranking, Top-K analysis, MRR, NDCG, and log-loss evaluation.

## Architecture

Historical SQL / point-in-time features
↓
Phase 40 Learning-to-Rank Dataset
↓
Phase 41 Pairwise Logistic Ranking Model
↓
Candidate Scores
↓
Ten-Class Softmax Probabilities
↓
Ranking / Top-K / MRR / NDCG
↓
Phase 42 Panel Ranking and downstream ranking analysis

Phase 41 does not rebuild Phase 36 candidate scoring, Phase 38 consensus, or Phase 39 walk-forward evaluation.

## Production Output

Production module: analytics/learning_to_rank_model.py

Version: LEARNING_TO_RANK_MODEL_VERSION = 41.0.0

Model kind: pairwise_logistic_ltr

Dedicated tests: tests/test_learning_to_rank_model.py

## Model Contract

### Configuration

LearningToRankModelConfig controls:
- learning rate
- epochs
- L2 regularization
- deterministic random seed
- Top-K size
- early-stopping patience
- minimum validation improvement

### Model

LearningToRankModel stores:
- model version
- model kind
- source dataset identity
- feature-schema identity
- feature names
- target position
- learned weights
- bias
- training configuration
- training history
- deterministic model identity

The trained artifact also retains the deterministic feature standardization parameters used during training.

### Training

Training uses:
1. Phase 40 dataset validation
2. training-group extraction
3. feature standardization using training groups only
4. deterministic weight initialization
5. pairwise positive-vs-negative comparisons
6. logistic pairwise loss
7. L2 regularization
8. gradient updates
9. validation-set monitoring
10. best-state restoration
11. deterministic model identity

Each group contributes nine pairwise comparisons.

## Pairwise Objective

For positive feature vector x+ and negative feature vector x-:

margin = w · (x+ - x-)

The optimization minimizes logistic pairwise loss while applying L2 regularization.

The pairwise formulation uses ranking relationships directly rather than treating candidate rows as independent classification samples.

## Prediction Contract

predict_learning_to_rank_group() returns:
- group ID
- target date
- candidate digits
- candidate scores
- candidate probabilities
- candidate ranks
- actual digit
- top candidate
- Top-K candidates

Scores are converted to probabilities with a stable ten-class softmax.

Exactly ten candidates are required.

Ranks are deterministic: higher score first; lower candidate digit breaks exact ties.

## Evaluation Contract

evaluate_learning_to_rank_model() evaluates all three temporal splits:
- train
- validation
- test

Metrics:
- accuracy
- Top-K accuracy
- Mean Reciprocal Rank (MRR)
- NDCG
- log loss

MRR uses the reciprocal rank of the actual observed candidate.
NDCG uses the rank of the single relevance-positive candidate.
Log loss uses the model's ten-class softmax probability for the actual candidate.

## Temporal Safety

Phase 41 consumes the Phase 40 train/validation/test groups.

It does not reshuffle or recreate temporal boundaries.

Feature standardization statistics are learned from training groups only.

Validation data is used for early stopping/model selection.

Test data remains the final evaluation boundary.

## Digit Zero

Digit 0 remains a valid candidate throughout training, pairwise construction, scoring, probability generation, ranking, Top-K, and evaluation.

## Determinism

The model is deterministic for identical Phase 40 dataset, feature schema, model configuration, and random seed.

Deterministic identity includes:
- model version
- model kind
- dataset identity
- feature schema identity
- feature names
- target position
- learned parameters
- configuration
- training history
- standardization parameters

Identity prefix: learning-to-rank-model-

## Persistence

Joblib persistence is supported through save_learning_to_rank_model() and load_learning_to_rank_model().

Loaded artifacts are checked for the expected model type. Prediction output remains identical after save/load.

## Validation

validate_learning_to_rank_model() checks model type, version, model kind, weight dimension, finite parameters, configuration, dataset identity, feature-schema identity, model identity, optional dataset compatibility, and target position.

validate_learning_to_rank_report() checks report type, version, group counts, metric ranges, log-loss validity, dataset identity, and report identity.

## Milestones

41.1 Phase Boundary Definition — COMPLETE
41.2 Phase 40 Dataset Integration — COMPLETE
41.3 Model Configuration Contract — COMPLETE
41.4 Pairwise Logistic Model Contract — COMPLETE
41.5 Training-Group Extraction — COMPLETE
41.6 Training-Only Feature Standardization — COMPLETE
41.7 Deterministic Parameter Initialization — COMPLETE
41.8 Positive Candidate Identification — COMPLETE
41.9 Pairwise Positive-vs-Negative Construction — COMPLETE
41.10 Pairwise Logistic Loss — COMPLETE
41.11 L2 Regularization — COMPLETE
41.12 Gradient Optimization — COMPLETE
41.13 Deterministic Training Loop — COMPLETE
41.14 Validation-Set Monitoring — COMPLETE
41.15 Best-State Restore — COMPLETE
41.16 Early Stopping — COMPLETE
41.17 Candidate Score Generation — COMPLETE
41.18 Ten-Class Softmax Probability Generation — COMPLETE
41.19 Deterministic Candidate Ranking — COMPLETE
41.20 Top-K Prediction — COMPLETE
41.21 Accuracy Evaluation — COMPLETE
41.22 Top-K Accuracy Evaluation — COMPLETE
41.23 MRR Evaluation — COMPLETE
41.24 NDCG Evaluation — COMPLETE
41.25 Log-Loss Evaluation — COMPLETE
41.26 Train / Validation / Test Evaluation — COMPLETE
41.27 Digit Zero Preservation — COMPLETE
41.28 Model Identity / Lineage — COMPLETE
41.29 Model Validation — COMPLETE
41.30 Report Contract — COMPLETE
41.31 Report Validation — COMPLETE
41.32 Joblib Persistence — COMPLETE
41.33 Persistence Reproducibility — COMPLETE
41.34 Deterministic Training Reproducibility — COMPLETE
41.35 Dedicated Regression Coverage — COMPLETE
41.36 Compile / Integrity Verification — COMPLETE
41.37 Documentation / Blueprint / Changelog Update — COMPLETE
41.38 Final Phase Integrity Verification — COMPLETE

## Regression

Focused Phase 41 regression: 47 passed, 0 failures, 0 errors, 0 warnings

Full project regression: 5240 passed in 82.32s, 0 failures, 0 errors, 0 warnings

Previous Phase 40 baseline: 5193 passed

Regression increase: +47 tests

Production import: PASS
Compile verification: PASS
No new third-party dependency was added.

## Integration Boundary

Phase 41 consumes the Phase 40 contract and produces model scores, probabilities, rankings, and evaluation reports.

Future phases may consume model identity, dataset identity, candidate scores, ten-class probabilities, candidate ranks, Top-K candidates, train/validation/test metrics, MRR, NDCG, and log loss.

Phase 42 may build Panel Ranking on top of these outputs.

## Release State

Phase 41 is complete locally.

GitHub commit/push was intentionally not performed.

Next implementation boundary: Phase 42 — Panel Ranking