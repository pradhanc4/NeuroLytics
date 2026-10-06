# NeuroLytics — Phase 80 Model Dashboard

## Status
COMPLETE

## Scope
Phase 80 adds a read-only Model Dashboard over the existing model lifecycle and
production-serving contracts. It does not create a second registry and does not
add model mutation, retraining, deployment, MLOps, CI/CD, cloud, Docker, or
Kubernetes functionality.

## Milestones

### 80.1 Dashboard service foundation
- Added `analytics/model_dashboard.py`.
- Version: `80.0.0`.
- Boundary: `MODEL_DASHBOARD_BOUNDARY`.
- Read-only service projection.

### 80.2 Current model identity
Exposes model identity, model version, artifact identity, serving ID,
activation ID, and source lineage from Phase 68 serving.

### 80.3 Serving state and checks
Exposes serving status, serving state, failed checks, and individual serving
checks without changing the serving plan.

### 80.4 Model health
Projects the existing Phase 57 health report when a report is attached.
If no report is attached, the API explicitly returns `UNAVAILABLE` with
`REPORT_NOT_ATTACHED`; no health value is fabricated.

### 80.5 Model comparison
Projects the existing Phase 58 comparison report when available, including
periods, common models, improved/declined/unchanged collections, and metric
comparisons.

### 80.6 Champion / challenger and selection
Projects existing Phase 59 and Phase 60 reports when available.

### 80.7 Version lifecycle and rollout
Projects existing Phase 61 lifecycle and Phase 66 rollout evidence when
available. The dashboard never executes activation, promotion, rollback, or
retraining.

### 80.8 Production API integration
Added read-only GET routes:
- `/v1/model/summary`
- `/v1/model/identity`
- `/v1/model/health`
- `/v1/model/comparison`
- `/v1/model/champion-challenger`
- `/v1/model/selection`
- `/v1/model/lifecycle`
- `/v1/model/rollout`

All routes reuse the existing analytics authorization and rate-limiting
boundary.

### 80.9 Frontend
The Model Status navigation item now opens the Model Dashboard with:
- current model KPIs
- identity and serving lineage
- serving checks
- health section
- champion/challenger section
- selection section
- lifecycle section
- rollout section
- refresh control

### 80.10 Empty and unavailable-state safety
Optional lifecycle reports are never synthesized. The dashboard explicitly
labels unavailable reports so an empty local environment remains truthful.

## Validation

Dedicated Phase 80 tests: 37 passed.

Required validation:
- `venv\\Scripts\\python.exe -m pytest tests/test_phase80_model_dashboard.py -q`
- `venv\\Scripts\\python.exe -m compileall -q analytics frontend tests`
- `git diff --check`

## Output

Phase 80 establishes the frontend/model integration boundary needed by later
dashboard phases while preserving all existing model lifecycle contracts.

Next official phase: **Phase 81 — Ranking Dashboard**.
