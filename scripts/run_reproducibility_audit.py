from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.engine import SessionLocal
from analytics.reproducibility_audit import (
    run_reproducibility_audit,
    reproducibility_summary,
    validate_reproducibility_audit,
    write_reproducibility_report,
)


def main() -> int:
    db = SessionLocal()
    try:
        report = run_reproducibility_audit(db)
        summary = reproducibility_summary(report)
        path = write_reproducibility_report(report)
    finally:
        db.close()

    status, issues = validate_reproducibility_audit(report)
    print(f"Phase 92 status: {status}")
    print(f"Report identity: {report.report_identity}")
    print(f"Dataset identity: {report.dataset_identity}")
    print(f"Schema identity: {report.schema_identity}")
    print(f"Source identity: {report.source_identity}")
    print(f"Environment identity: {report.environment_identity}")
    print(f"Configuration identity: {report.configuration_identity}")
    print(f"Artifact count: {summary['artifact_count']}")
    print(f"Replay checks: {len(report.replay_checks)}")
    print(f"Report path: {path}")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f" - {issue}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
