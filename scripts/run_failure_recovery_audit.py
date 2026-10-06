from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.failure_recovery import (
    run_failure_recovery_audit,
    write_failure_recovery_report,
    failure_recovery_summary,
)


def main() -> int:
    report = run_failure_recovery_audit()
    path = write_failure_recovery_report(report)
    summary = failure_recovery_summary(report)
    print(f"PHASE96_STATUS={summary['status']}")
    print(f"PHASE96_VERSION={summary['version']}")
    print(f"PHASE96_CHECKS={len(summary['checks'])}")
    print(f"PHASE96_EVENTS={len(summary['events'])}")
    print(f"PHASE96_REPORT_IDENTITY={summary['report_identity']}")
    print(f"PHASE96_REPORT={path}")
    return 0 if report.status == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
