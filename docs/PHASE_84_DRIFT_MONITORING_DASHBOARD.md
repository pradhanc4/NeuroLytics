# NeuroLytics — Phase 84: Drift / Monitoring Dashboard

## Status
COMPLETE LOCALLY — REGRESSION CLEAN

## Purpose
Phase 84 provides a unified, read-only frontend/dashboard projection of the existing NeuroLytics drift and monitoring reports.

The dashboard consumes the authoritative contracts already implemented by:
- Phase 49 — Model Drift Detection
- Phase 50 — Data Drift Detection
- Phase 52 — Calibration Drift Monitoring
- Phase 53 — Ranking Drift Monitoring
- Phase 54 — Feature Drift Monitoring
- Phase 55 — Concept Drift Detection

Phase 84 does not create a second drift engine. It exposes the existing reports through one stable dashboard boundary.

## Architectural Boundary
Phase 84 is presentation and read-only API composition.

It:
- preserves source report identity
- preserves source report version
- preserves source configuration and thresholds through existing summaries
- exposes drift decisions without recomputing them
- exposes observation-level evidence
- reports unavailable sections explicitly when no report is attached
- provides a unified local frontend navigation surface
- uses the existing Phase 76 production service security/rate-limit boundary

It does not:
- calculate new drift metrics
- modify drift reports
- create predictions
- retrain models
- promote or activate models
- rollback models
- generate automated remediation
- mutate historical data
- add cloud infrastructure
- add MLOps, CI/CD, Docker, Kubernetes, OAuth/OIDC, or distributed infrastructure

## Version
DRIFT_DASHBOARD_VERSION = 84.0.0
Boundary: DRIFT_MONITORING_DASHBOARD_BOUNDARY
Default API authorization scope: drift:read

## Unified Report Families
| Section | Source Phase | Meaning |
|---|---:|---|
| data | 50 | Model-input data distribution drift |
| model | 49 | Model-output distribution drift |
| calibration | 52 | Probability calibration drift |
| ranking | 53 | Ranking-structure drift |
| feature | 54 | Engineered-feature distribution/statistics drift |
| concept | 55 | Feature-to-outcome relationship drift |

The dashboard keeps these meanings separate. A single drift_detected summary flag means at least one attached source report has its authoritative drifted decision set to true; it does not replace the source-domain decision.

## Core Service
File: analytics/drift_dashboard.py

Main class: DriftMonitoringDashboardService

Constructor accepts optional authoritative reports:
- data_report
- model_report
- calibration_report
- ranking_report
- feature_report
- concept_report

No report is fabricated when a source report is absent.

## Dashboard Contract
The dashboard contract is read-only and exposes:
- version
- boundary
- section names
- route definitions
- available report count
- drifted section list
- attached-report drift state
- source summaries
- source validation status
- source observations

The dashboard uses explicit states:
- VALID
- INVALID
- AVAILABLE
- UNAVAILABLE

Missing reports return status = UNAVAILABLE and reason = REPORT_NOT_ATTACHED. This prevents an empty local environment from being represented as a false no-drift result.

## Summary API
drift_dashboard_summary() returns the unified dashboard summary.

Summary includes:
- dashboard version
- dashboard boundary
- read-only flag
- section count
- available section count
- drifted section names
- unified drift-detected flag
- per-domain source summaries

## Overview API
drift_dashboard_overview() returns the compact cross-domain view used by the frontend.

Each domain preserves:
- source report status
- source report identity
- source report version
- source drift decision
- source-specific summary fields
- explicit unavailable state when detached

## Section API
drift_dashboard_section(service, name) returns:
- source summary
- source validation result
- observation projection

Supported names:
- data
- model
- calibration
- ranking
- feature
- concept

Unknown names are rejected deterministically.

## Observation API
drift_dashboard_observations(service, name) exposes source observation records without changing their meaning.

Date and datetime values are normalized to ISO strings for JSON transport. Observation count and returned-observation count are both exposed. A configurable maximum is bounded to prevent unbounded dashboard responses.

## Production API Routes
The Phase 76 production service now exposes:
- GET /v1/drift/summary
- GET /v1/drift/overview
- GET /v1/drift/<name>
- GET /v1/drift/<name>/observations

All four routes are read-only GET routes.

They reuse:
- Phase 76 production authorization
- Phase 76 rate limiting
- existing Flask production boundary
- configurable drift_scope, defaulting to drift:read

Invalid section names return a deterministic 400 response. POST requests are rejected with the existing 405 contract.

## Frontend
Phase 84 adds a new Drift / Monitoring Dashboard and navigation entry Drift / Monitoring.

Frontend capabilities:
- available-section KPI
- unified drift-detected state
- drifted-section count
- Phase 84 version display
- cross-domain overview
- Data Drift panel
- Model Drift panel
- Calibration Drift panel
- Ranking Drift panel
- Feature Drift panel
- Concept Drift panel
- observation-detail selector
- observation refresh control
- explicit unavailable/error display

The frontend calls the new Phase 84 API routes only; drift calculations remain server-side in their authoritative source modules.

## Milestones
84.1 Phase Boundary Definition — COMPLETE
84.2 Phase 49 Model Drift Source Contract — COMPLETE
84.3 Phase 50 Data Drift Source Contract — COMPLETE
84.4 Phase 52 Calibration Drift Source Contract — COMPLETE
84.5 Phase 53 Ranking Drift Source Contract — COMPLETE
84.6 Phase 54 Feature Drift Source Contract — COMPLETE
84.7 Phase 55 Concept Drift Source Contract — COMPLETE
84.8 Six-Domain Report Registry — COMPLETE
84.9 Report Attachment State — COMPLETE
84.10 Explicit UNAVAILABLE State — COMPLETE
84.11 Source Identity Preservation — COMPLETE
84.12 Source Version Preservation — COMPLETE
84.13 Source Summary Preservation — COMPLETE
84.14 Source Validation Projection — COMPLETE
84.15 Observation Projection — COMPLETE
84.16 Date Normalization — COMPLETE
84.17 Observation Response Limit — COMPLETE
84.18 Unified Summary Contract — COMPLETE
84.19 Unified Overview Contract — COMPLETE
84.20 Domain Section Contract — COMPLETE
84.21 Invalid Section Validation — COMPLETE
84.22 Dashboard Composition Contract — COMPLETE
84.23 Read-Only Boundary — COMPLETE
84.24 No-Calculation Boundary — COMPLETE
84.25 No-Remediation Boundary — COMPLETE
84.26 Production Import — COMPLETE
84.27 Configurable Drift Authorization Scope — COMPLETE
84.28 Shared Rate-Limit Integration — COMPLETE
84.29 Summary Route — COMPLETE
84.30 Overview Route — COMPLETE
84.31 Section Route — COMPLETE
84.32 Observation Route — COMPLETE
84.33 GET-Only Route Contract — COMPLETE
84.34 Invalid Route Input Contract — COMPLETE
84.35 Frontend Navigation — COMPLETE
84.36 Frontend KPI Surface — COMPLETE
84.37 Frontend Domain Panels — COMPLETE
84.38 Frontend Observation Surface — COMPLETE
84.39 Frontend Refresh Controls — COMPLETE
84.40 Dedicated Regression — COMPLETE
84.41 Phase 76–84 Integration Regression — COMPLETE
84.42 Compileall Verification — COMPLETE
84.43 git diff --check Verification — COMPLETE
84.44 Full Project Regression — COMPLETE
84.45 Documentation / Roadmap / Status Update — COMPLETE

## Dedicated Regression
File: tests/test_phase84_drift_monitoring_dashboard.py
Result:
- 50 passed
- 0 failures
- 0 errors

Coverage includes version/boundary, read-only contract, all six report families, empty/unavailable behavior, attachment state, report identity, observation shape, dashboard composition, no-mutation boundary, observation limits, invalid section handling, production routes, GET-only behavior, frontend route contracts, frontend navigation, frontend panels, frontend JavaScript API usage, configurable authorization scope, and stable route/section contracts.

## Integration Regression
Phase 76–84 dashboard/production integration:
- 347 passed
- 0 failures
- 0 errors

## Full Project Regression
Previous authoritative baseline after Phase 83:
- 7,455 passed

Phase 84 full project result:
- 7,505 passed
- 0 failures
- 0 errors
- 156.37 seconds

Regression increase:
- +50 tests

## Static / Integrity Verification
- Python compileall: PASS
- git diff --check: PASS
- no new third-party dependency
- no cloud/MLOps/CI/CD infrastructure introduced
- GitHub commit/push: NOT PERFORMED

## Empty Environment Behavior
When production creates DriftMonitoringDashboardService() without attached persisted reports:
- available sections = 0
- drifted sections = empty
- source sections = UNAVAILABLE
- reason = REPORT_NOT_ATTACHED

This is intentional and consistent with the Phase 80–83 dashboard pattern.

## Error / Fix Record
### Test command selection issue
An initial integration command referenced a nonexistent historical filename for the Phase 76A test suite. The repository was searched and the integration command was corrected to the actual Phase 76–84 dashboard test files. No production-code change was required.

### Frontend function-boundary verification
While integrating the Phase 84 JavaScript navigation, the existing switchView function boundary was made explicit before DOMContentLoaded registration. The resulting frontend source was included in Phase 84 contract checks.

## Files Added
- analytics/drift_dashboard.py
- tests/test_phase84_drift_monitoring_dashboard.py
- docs/PHASE_84_DRIFT_MONITORING_DASHBOARD.md

## Files Updated
- analytics/production_service.py
- frontend/templates/index.html
- frontend/static/js/app.js
- PROJECT_STATUS.md
- CHANGELOG.md
- BLUEPRINT.md
- docs/ROADMAP_1_100.md

## Architecture Outcome
Phase 84 creates the frontend monitoring layer above the existing drift engines:

Phase 49 Model Drift
Phase 50 Data Drift
Phase 52 Calibration Drift
Phase 53 Ranking Drift
Phase 54 Feature Drift
Phase 55 Concept Drift
        ↓
DriftMonitoringDashboardService
        ↓
Phase 76 Production Service
        ↓
Phase 84 Drift / Monitoring API
        ↓
Phase 84 Frontend Dashboard

The source engines remain authoritative. Phase 84 is a composition and presentation boundary only.

## Next Official Phase
Phase 85 — Model Health Dashboard
