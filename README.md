# AI Master Planner + Data Analytics + Machine Learning Platform

## Project Overview

This project is a local SQL-first data analytics and machine learning platform.

The system is designed to:

- collect historical results directly into SQL
- validate and classify historical data
- maintain reference datasets
- perform statistical and data analysis
- engineer leakage-safe features
- train multiple machine learning and sequence models
- evaluate models using time-aware validation
- generate candidate scores and rankings
- perform walk-forward backtesting
- monitor model performance
- detect performance degradation
- retrain challenger models
- compare challenger and active models
- maintain model and experiment history
- provide analytics and ranking dashboards

## Core Architecture

User Input
→ SQL Database
→ Data Validation
→ Classification
→ Analytics
→ Feature Engineering
→ Model Training
→ Calibration
→ Ensemble
→ Candidate Scoring
→ Learning-to-Rank
→ Top-K Ranking
→ Walk-Forward Backtesting
→ Model Monitoring
→ Retraining
→ Dashboard

## Data Source

SQL is the single source of truth.

CSV is not part of the production architecture.

## Historical Input

Users will enter results in grouped form:

`Open | Jodi | Close`

Example:

`123 | 45 | 678`

The application will automatically derive:

- Open result
- Jodi result
- Close result
- Col1 through Col8

## Planned Model Families

- Statistical baseline
- Bayesian probability model
- Logistic Regression
- Decision Tree
- Random Forest
- Extra Trees
- Gradient Boosting
- XGBoost
- LightGBM
- CatBoost
- Markov / Transition Model
- Hidden Markov Model
- LSTM
- GRU
- Transformer / advanced sequence models
- Learning-to-Rank

## Evaluation

The project will use:

- chronological validation
- walk-forward backtesting
- Top-K evaluation
- probability calibration
- model comparison
- model monitoring
- data drift monitoring
- retraining evaluation

No future information may be used when generating a historical prediction.

## Project Status

Phase 1 - Project Foundation