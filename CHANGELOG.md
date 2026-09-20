# Changelog

All important project changes will be documented here.

## [0.1.0] - Phase 1

### Added

- Fresh project architecture
- SQL-first project direction
- Initial Python environment
- Initial project folder structure
- Initial documentation
- Initial Git configuration

## Phase 3 — Historical Input / Parser

### Completed

- Added historical input application service.
- Added explicit validation for market name and result date.
- Added validation for Open, Jodi, and Close inputs.
- Integrated the existing result parser with the historical input workflow.
- Verified automatic Col1-Col8 derivation.
- Verified preservation of leading zeros.
- Verified SQL persistence and retrieval.
- Verified duplicate market/date protection.
- Added error-handling tests for invalid and duplicate input.
- Completed full Phase 3 regression testing.

### Verification

- Test suite: 36 passed
- SQL persistence: verified
- Parser integration: verified
- Leading-zero handling: verified
- Duplicate protection: verified
- Error handling: verified