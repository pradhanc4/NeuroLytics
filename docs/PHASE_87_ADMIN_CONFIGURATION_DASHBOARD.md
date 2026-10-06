# NeuroLytics — Phase 87: Admin / Configuration Dashboard

## Status
COMPLETE LOCALLY — DEDICATED REGRESSION CLEAN

## Objective
Phase 87 provides a read-only administration and configuration dashboard over the existing production-service contracts.

The phase does not introduce runtime mutation of credentials, rate limits, model state, serving state, or production policies.

## Version / Boundary
- Version: 87.0.0
- Boundary: ADMIN_CONFIGURATION_DASHBOARD_BOUNDARY
- Authorization scope: admin:read
- Read-only: true

## Authoritative Sources
Phase 87 composes existing contracts from:
- Phase 70/73 API Security
- Phase 71 shared Rate Limiter
- Phase 68/69 serving and inference
- Phase 76 Production Service
- Phase 77 Frontend Foundation

No duplicate security, rate-limit, serving, or inference engine was introduced.

## Dashboard Sections

### 1. Service State
Exposes:
- production service lifecycle state
- startup issues
- production service version
- production service boundary

### 2. Security Configuration
Exposes:
- security version
- security boundary
- enabled state
- credential count
- credential IDs
- role
- scopes
- revoked state

Never exposes:
- raw API keys
- key hashes

### 3. Rate-Limit Configuration
Exposes:
- enabled state
- requests per window
- window seconds
- burst limit
- burst window
- tracked identity count

### 4. Production Policy
Exposes existing startup requirements:
- require inference ready
- require monitoring healthy
- require shared security
- require shared rate limiter

### 5. Serving Configuration
Exposes:
- serving state
- model identity
- model version
- artifact identity

### 6. Dependencies
Exposes existing production dependency names, status, and detail.

### 7. API Scopes
Exposes the configured authorization scope mapping used by the production app.

## API Routes

All routes are GET-only:
- GET /v1/admin/summary
- GET /v1/admin/service
- GET /v1/admin/security
- GET /v1/admin/rate-limit
- GET /v1/admin/policy
- GET /v1/admin/serving
- GET /v1/admin/dependencies
- GET /v1/admin/scopes

All admin routes use the configurable admin:read authorization scope by default and reuse the existing Phase 76 security/rate-limit boundary.

No POST, PUT, PATCH, or DELETE administration routes were added.

## Frontend

Updated:
- frontend/templates/index.html
- frontend/static/js/app.js

Added:
- Admin / Configuration navigation
- service lifecycle KPI
- security KPI
- rate-limit KPI
- read-only KPI
- service configuration panel
- security configuration panel
- rate-limit configuration panel
- production policy panel
- serving panel
- dependency panel
- API scope table
- refresh control

## Security Boundary

The dashboard is intentionally metadata-only.

Credential records preserve:
- credential ID
- role
- scopes
- revoked status

Secret material is explicitly excluded.

## Mutation Boundary

Phase 87 does not:
- issue API keys
- revoke API keys
- change scopes
- change rate limits
- change production policy
- change model activation
- promote a model
- rollback a model
- retrain a model
- alter serving state

This preserves the existing runtime contracts and avoids introducing an unrequested administration mutation protocol.

## Milestones

87.1 Phase Boundary Definition — COMPLETE
87.2 Existing Security Contract Review — COMPLETE
87.3 Existing Rate-Limit Contract Review — COMPLETE
87.4 Existing Production Policy Review — COMPLETE
87.5 Existing Serving Contract Review — COMPLETE
87.6 Dedicated Admin Dashboard Service — COMPLETE
87.7 Version / Boundary Contract — COMPLETE
87.8 Read-Only Contract — COMPLETE
87.9 Secret Exposure Protection — COMPLETE
87.10 Credential Metadata Projection — COMPLETE
87.11 Security Summary Projection — COMPLETE
87.12 Rate-Limit Summary Projection — COMPLETE
87.13 Production Policy Projection — COMPLETE
87.14 Serving Projection — COMPLETE
87.15 Dependency Projection — COMPLETE
87.16 Authorization Scope Projection — COMPLETE
87.17 Dashboard Composition — COMPLETE
87.18 Configurable Admin Scope — COMPLETE
87.19 Summary Route — COMPLETE
87.20 Service Route — COMPLETE
87.21 Security Route — COMPLETE
87.22 Rate-Limit Route — COMPLETE
87.23 Policy Route — COMPLETE
87.24 Serving Route — COMPLETE
87.25 Dependency Route — COMPLETE
87.26 Scope Route — COMPLETE
87.27 Shared Security Integration — COMPLETE
87.28 Shared Rate-Limit Integration — COMPLETE
87.29 GET-Only Route Contract — COMPLETE
87.30 Frontend Navigation — COMPLETE
87.31 Frontend KPI Surface — COMPLETE
87.32 Frontend Service Panel — COMPLETE
87.33 Frontend Security Panel — COMPLETE
87.34 Frontend Rate-Limit Panel — COMPLETE
87.35 Frontend Policy Panel — COMPLETE
87.36 Frontend Serving Panel — COMPLETE
87.37 Frontend Dependency Panel — COMPLETE
87.38 Frontend Scope Table — COMPLETE
87.39 Frontend Refresh Control — COMPLETE
87.40 Dedicated Regression — COMPLETE
87.41 Phase 76–87 Integration Regression — PENDING FULL RERUN
87.42 Compileall Verification — COMPLETE
87.43 git diff --check Verification — COMPLETE
87.44 Full Project Regression — PENDING FULL RERUN
87.45 Documentation / Roadmap / Status Update — COMPLETE

## Dedicated Regression

File:
tests/test_phase87_admin_configuration_dashboard.py

Result:
- 55 passed
- 0 failures
- 0 errors
- 23.39 seconds

Coverage includes:
- dashboard version/boundary
- read-only contract
- security metadata
- secret protection
- rate-limit configuration
- production policy
- serving configuration
- dependency projection
- scope projection
- dashboard composition
- all eight API routes
- GET-only enforcement
- frontend route configuration
- frontend navigation
- frontend panels
- frontend JavaScript API usage
- refresh wiring
- preservation of the existing inference route

## Verification Boundary

The dedicated Phase 87 regression is authoritative and green. A full-project rerun was started, reached 36% without a test failure, but was terminated because the remote runner was progressing abnormally slowly. No full-project pass is claimed for this phase run. The previous authoritative Phase 86 baseline remains 7,615 passed.

## Static Verification
- compileall: PASS
- git diff --check: PASS
- no new third-party dependency
- no GitHub commit/push

## Scope Rule

Phase 87 remains local-first.

It does not introduce:
- MLOps
- CI/CD
- Docker
- Kubernetes
- cloud deployment
- distributed infrastructure
- OAuth/OIDC
- a new authentication system

## Next Official Phase

Phase 88 — Full Frontend Integration
