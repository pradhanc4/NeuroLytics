# NeuroLytics Standalone System Architecture

## Objective

NeuroLytics is being consolidated behind one local application boundary so the
database, data validation, feature engineering, analytics, ML, sequential
prediction, ranking, feedback, retraining, monitoring, and audit layers use a
shared system contract.

This does not introduce cloud deployment, MLOps, CI/CD, Docker, Kubernetes, or
distributed infrastructure.

## Canonical flow

Data Entry
-> SQLite / SQLAlchemy
-> Validation
-> Feature Engineering
-> Statistical Analytics
-> Classical ML / Boosting
-> Sequence Models
-> Ensemble / Calibration
-> Sequential Prediction
-> Ranking / Top-K
-> Actual-vs-Ranked / Performance
-> Feedback
-> Controlled Retraining
-> Model Health / Drift / Safety Audits

## Single source of truth

'database/neurolytics.db' is the local persistence boundary.

The application-level workflow boundary is:

'analytics/system_orchestrator.py'

Version: '101.0.0'

Boundary: 'STANDALONE_SYSTEM_ORCHESTRATION_BOUNDARY'

## Stage 1 / Stage 2 transaction guarantee

Stage 1 creates or updates exactly one pending row identified by:

'market_id + result_date'

Stage 2 receives the exact 'stage_id' whenever available.

Completion is atomic:

1. load Stage 1
2. verify the market
3. verify no completed historical row already exists
4. derive Jodi from Stage 1 first digit + Stage 2 second digit
5. validate and derive col1-col8
6. create 'historical_results'
7. mark Stage 1 'COMPLETED'
8. commit once

If any step fails, the transaction rolls back.

This prevents a completed historical row from being created while the Stage 1
row remains pending, or the reverse.

## System inspection routes

- 'GET /v1/system/status'
- 'GET /v1/system/pipeline'
- 'GET /v1/system/database'

The routes expose system state and lineage; they do not fabricate model readiness.

## Important operational rule

Not every model is trained after every row. The orchestrator exposes all model
and analytics frames as one architecture, while existing training, validation,
ranking, and production gates remain authoritative.

Insufficient data must produce an explicit 'NOT_READY' or
'INSUFFICIENT_DATA' state rather than synthetic artifacts.

## Current database state at implementation

The current local database was verified to contain:

- 2 markets
- 1 completed historical result
- 1 Stage 1 row marked 'COMPLETED'
- 4 prediction feedback rows

The completed result was verified as:

- date: '2021-04-01'
- market: 'PHASE92_SEQUENCE'
- Open: '459'
- Jodi: '80'
- Close: '280'
- columns: '4,5,9,8,0,2,8,0'

## Scope

This architecture is an integration layer over the existing 1-100 roadmap.
Existing ML and analytics implementations remain the authoritative engines.
