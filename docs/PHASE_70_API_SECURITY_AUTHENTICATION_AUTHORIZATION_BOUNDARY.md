# NeuroLytics — Phase 70 API Security / Authentication / Authorization Boundary

## Status

Phase 70 — API Security / Authentication / Authorization Boundary is COMPLETE LOCALLY.

Version: 70.0.0

## Purpose

Phase 70 adds an explicit security boundary around the Phase 69 API.

The implementation uses standard-library cryptographic hashing and constant-time comparison, so no new third-party dependency is required.

## Security Flow

HTTP request
    ↓
Credential header
    ↓
Credential hash lookup
    ↓
Authentication
    ↓
Revocation check
    ↓
Scope authorization
    ↓
Phase 69 API
    ↓
Phase 68 inference
    ↓
Response

## Core Security Types

- ApiSecurityPolicy
- ApiCredential
- ApiCredentialStore
- AuthorizationContext
- SecurityDecision

## Authentication

API keys are supplied through a configurable header.

Default header:

X-API-Key

Raw API keys are not stored in ApiCredential. The credential store stores SHA-256 hashes.

Credential verification uses hmac.compare_digest for constant-time hash comparison.

## Authorization

Default inference scope:

inference:read

Default readiness scope:

inference:read

A credential must authenticate successfully and contain the required scope.

Roles are represented in the authorization context but authorization decisions are scope-based, preventing role names from silently becoming permissions.

## Revocation

Credentials can be revoked without exposing the raw API key.

A revoked credential authenticates to the credential identity but is denied authorization.

## HTTP Boundary

GET /health remains public.

GET /ready requires authentication and the readiness scope when security is enabled.

POST /v1/inference requires authentication and the inference scope when security is enabled.

Security failures are returned before inference payload processing.

## HTTP Security Errors

401 — missing or invalid credential.

403 — revoked credential or insufficient scope.

Existing Phase 69 errors remain responsible for malformed JSON, unsupported content type, inference rejection, route errors, and other API-level conditions.

## Compatibility

create_inference_app() remains backward-compatible with Phase 69 by allowing security to be disabled explicitly/default for legacy callers.

create_secure_inference_app() is the explicit production security entry point and requires an enabled security policy.

## Security Non-Goals

Phase 70 does not implement:

- TLS termination
- password authentication
- OAuth/OIDC
- JWT
- external identity provider integration
- persistent credential database
- automatic secret rotation
- rate limiting
- network firewall configuration
- deployment orchestration
- audit-log persistence

These remain explicit future boundaries.

## Sensitive Data Rules

The API does not echo the supplied API key.

Security summaries expose credential IDs, roles/scopes, and counts, but not raw keys or credential secrets.

## Testing

Dedicated Phase 70 regression:

70 passed, 0 failures, 0 errors, 0 warnings.

Full project regression: 6,924 passed in 177.06s, 0 failures, 0 errors, 0 warnings.

Production import: PASS. Compileall: PASS. git diff --check: PASS.

## Milestones

70.1 Security Boundary Definition — COMPLETE
70.2 Phase 69 Integration Contract — COMPLETE
70.3 Security Version Contract — COMPLETE
70.4 Security Boundary Identity — COMPLETE
70.5 Security Policy — COMPLETE
70.6 Policy Type Validation — COMPLETE
70.7 Policy Boolean Validation — COMPLETE
70.8 Credential Header Validation — COMPLETE
70.9 Scope Policy Validation — COMPLETE
70.10 Credential Model — COMPLETE
70.11 Credential Store — COMPLETE
70.12 Credential Type Validation — COMPLETE
70.13 Credential ID Validation — COMPLETE
70.14 Role Validation — COMPLETE
70.15 Scope Validation — COMPLETE
70.16 Duplicate Scope Normalization — COMPLETE
70.17 SHA-256 Credential Hashing — COMPLETE
70.18 Deterministic Hashing — COMPLETE
70.19 UTF-8 Hashing — COMPLETE
70.20 Raw-Key Non-Persistence Contract — COMPLETE
70.21 Credential Identity Contract — COMPLETE
70.22 Credential Listing — COMPLETE
70.23 Credential Lookup — COMPLETE
70.24 Credential Issuance — COMPLETE
70.25 Credential Revocation — COMPLETE
70.26 Missing Credential Detection — COMPLETE
70.27 Invalid Credential Detection — COMPLETE
70.28 Constant-Time Credential Comparison — COMPLETE
70.29 Authentication Context — COMPLETE
70.30 Role Context — COMPLETE
70.31 Scope Context — COMPLETE
70.32 Authentication Decision — COMPLETE
70.33 Scope Authorization — COMPLETE
70.34 Insufficient Scope Denial — COMPLETE
70.35 Revoked Credential Denial — COMPLETE
70.36 Security Summary — COMPLETE
70.37 Raw Secret Exclusion — COMPLETE
70.38 Secure App Factory — COMPLETE
70.39 Configurable Security Policy — COMPLETE
70.40 Configurable Credential Header — COMPLETE
70.41 Public Health Boundary — COMPLETE
70.42 Protected Readiness Boundary — COMPLETE
70.43 Protected Inference Boundary — COMPLETE
70.44 HTTP 401 Mapping — COMPLETE
70.45 HTTP 403 Mapping — COMPLETE
70.46 Structured Security Error Contract — COMPLETE
70.47 Authentication Before Payload Processing — COMPLETE
70.48 Authorization Before Inference — COMPLETE
70.49 Phase 68 Delegation Preservation — COMPLETE
70.50 Phase 69 Response Preservation — COMPLETE
70.51 Invalid Credential Regression — COMPLETE
70.52 Missing Credential Regression — COMPLETE
70.53 Revoked Credential Regression — COMPLETE
70.54 Insufficient Scope Regression — COMPLETE
70.55 Valid Credential Regression — COMPLETE
70.56 Custom Header Regression — COMPLETE
70.57 Custom Scope Regression — COMPLETE
70.58 Public Health Regression — COMPLETE
70.59 Protected Readiness Regression — COMPLETE
70.60 Protected Inference Regression — COMPLETE
70.61 Dedicated Regression Coverage — COMPLETE
70.62 Production Import / Compile / Integrity Verification — COMPLETE
70.63 Documentation / Blueprint / Changelog — COMPLETE
70.64 Full Regression Verification — COMPLETE

## Architecture Result

Phase 70 establishes:

Phase 69 API
    ↓
Phase 70 authentication
    ↓
Phase 70 authorization
    ↓
Phase 68 model-bound inference

The security layer is explicit and deterministic. It does not modify model lifecycle, serving state, model weights, SQL history, or production traffic.

## Next Phase

Phase 71 — API Rate Limiting / Abuse Protection Boundary.
