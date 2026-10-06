# Phase 71 — API Rate Limiting / Abuse Protection Boundary

## Status

COMPLETE LOCALLY

Phase 71 adds a deterministic, dependency-free rate-limiting and abuse-protection boundary above Phase 70 authentication/authorization and below Phase 69 request payload processing.

Version: 71.0.0
Boundary: API_RATE_LIMIT_BOUNDARY

## Purpose

Phase 71 protects the HTTP API from request bursts, sustained excessive request volume, and repeated authentication failures.

The phase does not change model inference, feature construction, model lifecycle, historical SQL, or Phase 68 serving behavior.

## Architecture

HTTP Request
    ↓
Phase 70 Authentication / Authorization
    ↓
Phase 71 Rate Limiting / Abuse Protection
    ↓
Content-Type / JSON Validation
    ↓
Phase 69 API
    ↓
Phase 68 Inference
    ↓
Activated Model

Authentication failures are rate-limited using the request IP identity.

Authenticated requests are rate-limited using the credential identity.

Health remains public and is intentionally outside the Phase 71 limiter.

## Implementation

Added:

- analytics/api_rate_limit.py
- tests/test_api_rate_limit.py
- docs/PHASE_71_API_RATE_LIMITING_ABUSE_PROTECTION_BOUNDARY.md

Updated:

- analytics/production_api.py
- PROJECT_STATUS.md
- CHANGELOG.md
- BLUEPRINT.md

No new third-party dependency was added.

## Policy

ApiRateLimitPolicy defines enabled, requests_per_window, window_seconds, burst_limit, and burst_window_seconds.

Default policy:

- 60 requests per 60 seconds
- burst limit 10 requests per 1 second
- enabled by default for the explicit secure application factory

The legacy create_inference_app() remains rate-limit-disabled by default for Phase 69 compatibility.

create_secure_inference_app() enables rate limiting by default.

## Rate Limiter

ApiRateLimiter uses Python's monotonic clock and in-memory deques.

The limiter maintains:

- sustained request events for the configured window
- short-window burst events

Expired events are removed deterministically.

The implementation is dependency-free and process-local.

## Decision Contract

RateLimitDecision exposes:

- status
- identity
- limit
- remaining
- retry_after
- window_seconds
- allowed property

Allowed status: RATE_LIMIT_ALLOWED

Blocked status: RATE_LIMITED

HTTP denial code: RATE_LIMIT_DENIED

## HTTP Contract

When the request exceeds its limit:

- HTTP status: 429
- structured error response
- Retry-After header
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Window

Rate limiting is applied before JSON body parsing and before Phase 68 inference.

## Authentication Abuse Protection

Missing, invalid, revoked, and insufficient-scope credentials consume an IP-based rate-limit bucket.

The raw API key is never used as the rate-limit identity.

Successful authenticated requests use credential:<credential_id>.

Unauthenticated failures use ip:<remote_addr>.

The API key itself is never returned in rate-limit responses.

## Endpoint Boundary

### /health

- public
- not rate limited
- unchanged from Phase 69/70

### /ready

- Phase 70 authentication/authorization applies when security is enabled
- Phase 71 rate limiting applies after successful authorization
- failed authentication attempts are IP-limited

### /v1/inference

- Phase 70 authentication/authorization applies when security is enabled
- Phase 71 rate limiting applies before content-type and JSON processing
- Phase 68 remains the inference authority

## Determinism

The limiter accepts an injectable clock for deterministic testing.

Production uses time.monotonic().

The rate-limit decision does not depend on wall-clock date changes.

Retry-After is calculated from the earliest event responsible for the active limit.

## Safety Boundaries

Phase 71 does not:

- modify model weights
- retrain models
- modify feature artifacts
- modify historical SQL
- change model versions
- activate or roll back models
- mutate Phase 61 lifecycle state
- bypass Phase 70 authorization
- expose API keys
- persist credentials
- open network ports
- start a server automatically
- introduce distributed shared rate limiting

## Compatibility

Existing Phase 69 callers can continue using create_inference_app() without rate limiting.

The secure production entry point create_secure_inference_app() enables Phase 71 by default.

A custom ApiRateLimitPolicy or ApiRateLimiter can be supplied explicitly.

A supplied limiter must use the same policy as the application factory.

## Test Coverage

Dedicated Phase 71 regression:

70 passed
0 failures
0 errors
0 warnings

Coverage includes:

- policy validation
- boolean/type validation
- request/window limits
- burst limits
- burst window
- deterministic clock
- expiration
- identity isolation
- limiter reset
- disabled mode
- decision contract
- response headers
- summary contract
- factory integration
- secure factory defaults
- 429 mapping
- Retry-After
- health exclusion
- readiness limiting
- inference limiting
- authentication-failure limiting
- rate limiting before payload parsing
- rate limiting before inference
- credential isolation
- IP isolation
- security regression
- deterministic response preservation

## Adjacent Regression

Phase 68 serving + Phase 69 API + Phase 70 security + Phase 71 rate limiting:

280 passed
0 failures
0 errors
0 warnings

## Final Verification

Authoritative full project regression: 6994 passed in 130.26s (0:02:10), 0 failures, 0 errors, 0 warnings.

Production import: PASS
Compileall: PASS
git diff --check: PASS

No new third-party dependency.

No GitHub commit or push was performed.

## Milestones

71.1 Phase Boundary Definition — COMPLETE
71.2 Phase 70 Source Contract — COMPLETE
71.3 Rate Limit Version Contract — COMPLETE
71.4 Boundary Identity Contract — COMPLETE
71.5 Policy Model — COMPLETE
71.6 Policy Type Validation — COMPLETE
71.7 Enabled Validation — COMPLETE
71.8 Sustained Request Limit Validation — COMPLETE
71.9 Sustained Window Validation — COMPLETE
71.10 Burst Limit Validation — COMPLETE
71.11 Burst Window Validation — COMPLETE
71.12 Limiter Model — COMPLETE
71.13 Monotonic Clock Contract — COMPLETE
71.14 Identity Contract — COMPLETE
71.15 Sustained Event Tracking — COMPLETE
71.16 Burst Event Tracking — COMPLETE
71.17 Event Expiration — COMPLETE
71.18 Burst Expiration — COMPLETE
71.19 Identity Isolation — COMPLETE
71.20 Reset Contract — COMPLETE
71.21 Disabled Limiter Contract — COMPLETE
71.22 Allowed Decision — COMPLETE
71.23 Limited Decision — COMPLETE
71.24 Remaining Count — COMPLETE
71.25 Retry-After Calculation — COMPLETE
71.26 Rate-Limit Headers — COMPLETE
71.27 Summary API — COMPLETE
71.28 Secret-Free Summary — COMPLETE
71.29 Production API Integration — COMPLETE
71.30 Security Integration Preservation — COMPLETE
71.31 Credential Identity Limiting — COMPLETE
71.32 IP Failure Limiting — COMPLETE
71.33 Health Exclusion — COMPLETE
71.34 Readiness Protection — COMPLETE
71.35 Inference Protection — COMPLETE
71.36 Pre-Payload Enforcement — COMPLETE
71.37 Pre-Inference Enforcement — COMPLETE
71.38 HTTP 429 Mapping — COMPLETE
71.39 Structured Error Contract — COMPLETE
71.40 Retry-After Contract — COMPLETE
71.41 Limit Header Contract — COMPLETE
71.42 Remaining Header Contract — COMPLETE
71.43 Window Header Contract — COMPLETE
71.44 Credential Isolation — COMPLETE
71.45 IP Isolation — COMPLETE
71.46 Missing Credential Protection — COMPLETE
71.47 Invalid Credential Protection — COMPLETE
71.48 Revoked Credential Protection — COMPLETE
71.49 Insufficient Scope Protection — COMPLETE
71.50 Raw-Key Exclusion — COMPLETE
71.51 Legacy API Compatibility — COMPLETE
71.52 Secure Factory Default — COMPLETE
71.53 Custom Policy Contract — COMPLETE
71.54 Custom Limiter Contract — COMPLETE
71.55 Limiter/Policy Reconciliation — COMPLETE
71.56 Deterministic Clock Regression — COMPLETE
71.57 Expiration Regression — COMPLETE
71.58 Burst Regression — COMPLETE
71.59 Sustained Limit Regression — COMPLETE
71.60 Security Regression — COMPLETE
71.61 Serving Regression — COMPLETE
71.62 Dedicated Regression Coverage — COMPLETE
71.63 Production Import / Compile / Integrity — COMPLETE
71.64 Documentation / Blueprint / Changelog — COMPLETE
71.65 Full Regression Verification — COMPLETE

## Next Boundary

Phase 72 should remain a separate boundary for persistent audit/security event handling or the next explicitly defined production-control concern. Phase 71 itself does not add persistent rate-limit state or distributed coordination.
