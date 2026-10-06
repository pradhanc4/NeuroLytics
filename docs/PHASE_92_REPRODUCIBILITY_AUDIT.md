# NeuroLytics — Phase 92 Reproducibility Audit

## Status

**COMPLETE**

Version: **92.0.0**

Boundary: **REPRODUCIBILITY_AUDIT**

Phase 92 establishes a deterministic, local-first audit contract for reproducing NeuroLytics analytical outputs. It does not introduce MLOps, CI/CD, Docker, Kubernetes, cloud deployment, distributed execution, or external infrastructure.

## 92.1 Deterministic execution contract

Implemented in `analytics/reproducibility_audit.py`.

Outputs:
- fixed audit seed: `9200`
- Python random seeding
- NumPy seeding when NumPy is installed
- explicit model random-state policy
- deterministic single-worker audit replay policy
- stable key ordering and chronological data ordering

The audit does not claim that every third-party parallel algorithm is mathematically identical across every machine. It records the execution policy needed for a controlled local replay.

## 92.2 Dataset fingerprinting

The audit fingerprints ordered historical results using:
- result ID
- market ID
- result date
- Open
- Jodi
- Close
- col1 through col8

The fingerprint is SHA-256 based and stable for the same ordered dataset.

## 92.3 Database schema fingerprinting

The audit fingerprints registered SQLAlchemy tables, columns, nullability, primary-key flags, and constraint representations.

It also checks that the live database contains every registered NeuroLytics table.

## 92.4 Source fingerprinting

The audit fingerprints the core prediction/backtesting/sequential/feature-pipeline source files used by the Phase 90–92 execution boundary.

Each source entry contains its SHA-256 digest and byte size before the aggregate identity is calculated.

## 92.5 Environment fingerprinting

The audit captures non-volatile environment information:
- Python version
- implementation
- operating platform
- machine architecture
- installed versions for the primary ML/application dependencies

No network lookup is required.

## 92.6 Configuration fingerprinting

The audit fingerprints the reproducibility configuration, including:
- seed
- PYTHONHASHSEED policy
- random algorithm
- NumPy seeding policy
- model random-state policy
- audit parallelism policy
- ordering policy

## 92.7 Artifact fingerprinting

Existing files under `models/` are hashed recursively.

Generated audit JSON files are excluded from the artifact list to avoid self-referential fingerprints.

If no trained artifacts exist, artifact count is correctly reported as zero; the audit does not invent a model artifact.

## 92.8 Replay validation

The audit runs deterministic replay checks for:
1. dataset fingerprint
2. reproducibility configuration
3. environment snapshot

Each replay records first and second identities and a boolean reproducibility result.

## 92.9 Report identity

A final immutable-style report identity is derived from:
- audit version
- dataset identity
- schema identity
- source identity
- environment identity
- configuration identity
- artifact identities
- replay results
- issue list

## 92.10 Production admin endpoint

Added:

`GET /v1/admin/reproducibility`

The endpoint:
- uses the existing admin authorization boundary
- uses the existing rate limiter
- executes the same audit contract
- returns the reproducibility summary and report identity

## 92.11 Repeatable local runner

Added:

`scripts/run_reproducibility_audit.py`

Run from Windows CMD:

`cd /d D:\NeuroLytics`
`venv\Scripts\python.exe scripts\run_reproducibility_audit.py`

The runner writes:

`reports\reproducibility_audit.json`

## 92.12 Validation and tests

Dedicated test file:

`tests/test_phase92_reproducibility_audit.py`

Validated:
- version contract
- stable identity
- seed configuration
- environment identity
- dataset fingerprint
- complete audit
- summary fields
- report identity
- report writing
- admin endpoint success
- admin authorization protection

Dedicated Phase 92 result:

**12 passed**

Additional regression executed with the sequential prediction and frontend data-entry tests:

**25 passed**

## 92.13 Actual audit execution

The local audit runner completed successfully with:

- Status: **VALID**
- Artifact count: **0**
- Replay checks: **3**
- Report written to `reports/reproducibility_audit.json`

The zero-artifact result is expected when no trained model artifact is present. It is preferable to a fabricated artifact identity.

## Phase 92 completion criteria

| Milestone | Result |
|---|---|
| 92.1 Deterministic execution contract | COMPLETE |
| 92.2 Dataset fingerprint | COMPLETE |
| 92.3 Schema fingerprint | COMPLETE |
| 92.4 Source fingerprint | COMPLETE |
| 92.5 Environment fingerprint | COMPLETE |
| 92.6 Configuration fingerprint | COMPLETE |
| 92.7 Artifact fingerprint | COMPLETE |
| 92.8 Replay validation | COMPLETE |
| 92.9 Report identity | COMPLETE |
| 92.10 Admin API boundary | COMPLETE |
| 92.11 Repeatable runner | COMPLETE |
| 92.12 Automated tests | COMPLETE |
| 92.13 Real local audit execution | COMPLETE |

## Scope boundary

Phase 92 verifies reproducibility metadata and deterministic replay. It does **not** certify model correctness, future prediction accuracy, or perfect prediction. Those remain empirical questions evaluated by the existing validation, backtesting, feedback, and monitoring systems.

## Next official phase

**Phase 93 — Data Integrity Audit**
