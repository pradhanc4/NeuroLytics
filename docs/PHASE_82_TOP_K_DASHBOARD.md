# NeuroLytics — Phase 82 Top-K Dashboard

## Status

Phase 82 — Top-K Dashboard is COMPLETE LOCALLY.

Implementation date: 2026-10-02

Version: 82.0.0

Boundary: TOP_K_DASHBOARD_BOUNDARY

Architecture: local-first, SQL-first, read-only dashboard projection.

No MLOps, CI/CD, cloud, Docker, Kubernetes, or distributed infrastructure was introduced.

## Scope

Phase 82 exposes the authoritative Phase 44 Top-K evaluation engine through a dedicated dashboard service, production API boundary, and frontend view.

The dashboard does not recalculate Top-K ranking, retrain models, promote models, mutate data, or fabricate evaluation results.

## Milestones

82.1 Top-K Dashboard Foundation — COMPLETE
82.2 Authoritative Phase 44 Engine Reuse — COMPLETE
82.3 Report Attachment / Empty State — COMPLETE
82.4 Summary Metrics — COMPLETE
82.5 Hit-Rate-by-K Projection — COMPLETE
82.6 Mean Reciprocal Rank Projection — COMPLETE
82.7 Actual-Rank Distribution — COMPLETE
82.8 Actual-Outcome Coverage — COMPLETE
82.9 Observation-Level Detail Projection — COMPLETE
82.10 Dashboard Contract — COMPLETE
82.11 Production API Integration — COMPLETE
82.12 Authorization / Rate-Limit Boundary — COMPLETE
82.13 Frontend Navigation — COMPLETE
82.14 Frontend KPI Cards — COMPLETE
82.15 Frontend Hit-Rate View — COMPLETE
82.16 Frontend Rank Distribution View — COMPLETE
82.17 Frontend Observation Table — COMPLETE
82.18 Refresh / Loading Integration — COMPLETE
82.19 Dedicated Regression Coverage — COMPLETE
82.20 Full Regression Verification — COMPLETE
82.21 Documentation / Roadmap Update — COMPLETE

## Core implementation

Created:

- analytics/top_k_dashboard.py
- tests/test_phase82_top_k_dashboard.py
- docs/PHASE_82_TOP_K_DASHBOARD.md

The dashboard service is TopKDashboardService.

## Exposed information

The dashboard projection provides:

- report attachment status
- source type
- configured K values
- evaluated observation count
- actual-value availability count
- hit rate for every configured K
- hit percentage for every configured K
- mean reciprocal rank
- actual rank distribution
- unranked observation count
- actual-outcome coverage
- observation-level Top-K details
- report identity
- framework/dashboard versions
- read-only contract

Observation detail preserves:

- source type
- group ID
- target date
- actual value
- actual rank
- reciprocal rank
- top probability
- cumulative probability at maximum K
- hit/miss state for every configured K

## Production API

Added six read-only endpoints:

- GET /v1/top-k/summary
- GET /v1/top-k/metrics
- GET /v1/top-k/rows
- GET /v1/top-k/hit-rate
- GET /v1/top-k/rank-distribution
- GET /v1/top-k/coverage

All endpoints use the shared production authorization and rate-limiting boundary.

New scope:

- top-k:read

Frontend configuration exposes all six routes.

## Frontend

Added a dedicated Top-K navigation entry and dashboard.

The UI contains:

- report state
- actual coverage
- MRR
- evaluated observations
- hit-rate-by-K display
- actual-rank distribution display
- detailed metrics JSON panel
- coverage panel
- observation-level table
- refresh control

The existing Ranking Dashboard remains unchanged in purpose. Phase 81 continues to provide the combined ranking view; Phase 82 provides a deeper Top-K-specific view.

## Empty-state contract

When no TopKEvaluationReport is attached, the service returns:

UNAVAILABLE / REPORT_NOT_ATTACHED

No synthetic ranking metrics are created.

The current production service constructs the dashboard without attaching persisted reports, so production report-specific Top-K endpoints intentionally expose the explicit unavailable state until an authoritative report is attached by the surrounding application flow.

## Safety / integrity rules

Phase 82 is strictly read-only.

It does not:

- train models
- retrain models
- change model versions
- promote or reject models
- change ranking results
- change Top-K K values in the underlying engine
- write historical data
- bypass authorization
- bypass rate limiting
- replace Phase 44 calculation logic
- fabricate metrics for empty datasets

Leading-zero values remain strings through the dashboard projection.

## Regression coverage

Dedicated Phase 82 tests cover:

- version and boundary
- contract
- empty state
- report availability
- Top-K metrics
- hit-rate series
- MRR
- rank distribution
- coverage
- observation details
- report identity
- read-only surface
- production routes
- GET-only enforcement
- frontend configuration
- frontend navigation
- frontend panels
- frontend API wiring
- truthful no-report behavior

Final test result is recorded in PROJECT_STATUS.md after verification.

## Next phase

Phase 83 — Performance-over-Time Dashboard.
