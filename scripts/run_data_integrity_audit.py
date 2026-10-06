from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.engine import SessionLocal
from analytics.data_integrity_audit import (
    data_integrity_summary,
    run_data_integrity_audit,
    validate_data_integrity_audit,
    write_data_integrity_report,
)


def main() -> int:
    db = SessionLocal()
    try:
        report = run_data_integrity_audit(db)
        summary = data_integrity_summary(report)
        path = write_data_integrity_report(report)
    finally:
        db.close()

    status, issues = validate_data_integrity_audit(report)
    print(f"Phase 93 status: {status}")
    print(f"Report identity: {report.report_identity}")
    print(f"Checked tables: {len(report.checked_tables)}")
    print(f"Rows: {summary['row_counts']}")
    print(f"Invalid issues: {summary['invalid_issue_count']}")
    print(f"Warnings: {summary['warning_count']}")
    print(f"Report path: {path}")
    if issues:
        print("Validation issues:")
        for issue in issues:
            print(f" - {issue}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
