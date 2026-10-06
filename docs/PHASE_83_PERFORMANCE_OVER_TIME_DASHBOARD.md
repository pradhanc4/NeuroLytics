# NeuroLytics — Phase 83 Performance-over-Time Dashboard

## Status

Phase 83 — Performance-over-Time Dashboard is COMPLETE LOCALLY.

Version: 83.0.0

Boundary: PERFORMANCE_OVER_TIME_DASHBOARD_BOUNDARY

Architecture: local-first, SQL-first, read-only dashboard projection.

No MLOps, CI/CD, cloud, Docker, Kubernetes, OAuth/OIDC, or distributed infrastructure was introduced.

## Scope

Phase 83 exposes the authoritative Phase 46 Performance Over Time report through a dedicated dashboard service, production API boundary, and frontend view.

The dashboard does not recalculate performance trends, retrain models, mutate reports, or fabricate metrics.

## Milestones

83.1 Dashboard foundation — COMPLETE
83.2 Phase 46 engine reuse — COMPLETE
83.3 Report attachment / empty-state contract — COMPLETE
83.4 Summary projection — COMPLETE
83.5 Period-level performance projection — COMPLETE
83.6 Actual rank projection — COMPLETE
83.7 Hit-rate-over-time projection — COMPLETE
83.8 Mean reciprocal rank projection — COMPLETE
83.9 Top-probability projection — COMPLETE
83.10 Cumulative-probability projection — COMPLETE
83.11 Miss-rate projection — COMPLETE
83.12 Deterministic trend projection — COMPLETE
83.13 Aggregate coverage metrics — COMPLETE
83.14 Dashboard composition contract — COMPLETE
83.15 Production API integration — COMPLETE
83.16 Authorization / rate-limit boundary — COMPLETE
83.17 Frontend navigation — COMPLETE
83.18 Frontend KPI cards — COMPLETE
83.19 Frontend period view — COMPLETE
83.20 Frontend hit-rate view — COMPLETE
83.21 Frontend trend view — COMPLETE
83.22 Frontend aggregate metrics view — COMPLETE
83.23 Refresh integration — COMPLETE
83.24 Dedicated regression suite — COMPLETE
83.25 Full regression verification — COMPLETE
83.26 Documentation / roadmap update — COMPLETE

## Core implementation

Created:

- analytics/performance_dashboard.py
- tests/test_phase83_performance_dashboard.py
- docs/PHASE_83_PERFORMANCE_OVER_TIME_DASHBOARD.md

Main service:

- PerformanceOverTimeDashboardService

Projection methods:

- summary()
- periods()
- trends()
- hit_rates()
- metrics()
- dashboard()

## Source of truth

Phase 46 remains authoritative:

- PerformanceOverTimeReport
- PerformancePeriod
- PerformanceTrend
- performance_over_time_summary()
- validate_performance_over_time_report()

Phase 83 is presentation and API composition only.

## Dashboard data

The dashboard exposes:

- report status
- report identity
- source type
- period length
- period count
- observation count
- actual available observations
- missed observations
- actual coverage
- miss rate
- mean actual rank
- hit rate for each configured K
- mean reciprocal rank
- mean top probability
- mean cumulative probability
- deterministic slope per day
- trend direction
- first value
- last value
- change

Trend directions are inherited from Phase 46:

- IMPROVING
- DECLINING
- STABLE

## Production API

Added read-only routes:

- GET /v1/performance/summary
- GET /v1/performance/periods
- GET /v1/performance/trends
- GET /v1/performance/hit-rates
- GET /v1/performance/metrics

New scope:

- performance:read

All routes use the existing shared authorization and rate-limit boundary.

## Frontend

Added:

- Performance navigation item
- Performance-over-Time Dashboard page
- report status KPI
- period count KPI
- coverage KPI
- miss-rate KPI
- performance-period view
- hit-rates-over-time view
- deterministic trend view
- aggregate metrics panel
- refresh control

## Empty state

When no PerformanceOverTimeReport is attached:

UNAVAILABLE / REPORT_NOT_ATTACHED

No synthetic performance observations or trends are generated.

The current production service intentionally creates the dashboard without attaching a persisted report, so report-specific production endpoints expose the truthful unavailable state.

## Integrity rules

Phase 83 is strictly read-only.

It does not:

- train models
- retrain models
- promote models
- rollback models
- change ranking results
- change Phase 46 calculations
- write historical data
- mutate reports
- bypass authorization
- bypass rate limiting
- fabricate performance metrics

## Verification

Dedicated Phase 83 regression:

54 passed, 0 failures, 0 errors.

Full project regression is recorded in PROJECT_STATUS.md after final verification.

compileall and git diff --check are required closure checks.

## Next phase

Phase 84 — Drift / Monitoring Dashboard.
