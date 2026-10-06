# NeuroLytics — Phase 95 Performance / Scalability Testing

Version: 95.0.0

## Objective

Phase 95 measures the performance characteristics of the existing local NeuroLytics architecture without introducing MLOps, CI/CD, Docker, Kubernetes, cloud deployment, or distributed infrastructure.

The phase establishes repeatable measurements and baseline thresholds for:

- SQLite query access
- historical result fetching
- prediction primitives
- panel ranking
- Jodi ranking
- feature-vector scaling
- candidate sorting
- memory behavior
- runtime environment

## Milestones

### 95.1 Benchmark contract — COMPLETE

Added explicit measurement and scalability dataclasses with deterministic report identity.

### 95.2 Database performance — COMPLETE

Measures:
- historical row count query
- fetch of up to 1,000 chronological historical rows

### 95.3 Prediction performance — COMPLETE

Measures 1,000 prediction operations through the existing Phase 90 prediction primitive.

### 95.4 Ranking performance — COMPLETE

Measures:
- 1,000 panel candidates
- 100 Jodi candidates

### 95.5 Feature scalability — COMPLETE

Runs deterministic feature-vector materialization at 100, 1,000, 5,000, and 10,000 items.

### 95.6 Candidate scalability — COMPLETE

Measures candidate sorting at 100, 500, and 1,000 candidates.

### 95.7 Memory probe — COMPLETE

Runs a controlled allocation/release probe and records process memory information where supported by the operating system.

### 95.8 Threshold framework — COMPLETE

Default thresholds are intentionally conservative local-development gates and are recorded in the report.

A WARNING means the measured operation exceeded its baseline threshold. It is a performance finding, not a correctness failure.

### 95.9 Admin API — COMPLETE

Added:

GET /v1/admin/performance-scalability

The endpoint follows the existing admin authorization and rate-limiting boundary.

### 95.10 Repeatable runner — COMPLETE

Windows CMD:

    cd /d D:\NeuroLytics
    venv\Scripts\python.exe scripts\run_performance_scalability_audit.py

Output:

    reports\performance_scalability_audit.json

### 95.11 Automated tests — COMPLETE

Added:

tests\test_phase95_performance_scalability.py

### 95.12 Documentation / roadmap — COMPLETE

Phase 95 is marked COMPLETE and Phase 96 becomes the next planned phase.

## Default thresholds

- database count: 250 ms per operation
- database fetch up to 1,000 rows: 1,000 ms
- prediction primitive: 5,000 ms per 1,000 iterations
- panel ranking: 5,000 ms per benchmark invocation
- Jodi ranking: 2,500 ms per benchmark invocation
- memory growth probe: 256 MB

These are baseline engineering gates, not production SLAs.

## Output artifacts

- analytics/performance_scalability_audit.py
- scripts/run_performance_scalability_audit.py
- tests/test_phase95_performance_scalability.py
- reports/performance_scalability_audit.json
- GET /v1/admin/performance-scalability
- docs/PHASE_95_PERFORMANCE_SCALABILITY_TESTING.md
