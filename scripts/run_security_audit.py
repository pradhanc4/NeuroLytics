from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.security_audit import (
    audit_security_contract,
    security_audit_summary,
    write_security_audit_report,
)


def main() -> int:
    report = audit_security_contract(PROJECT_ROOT)
    path = write_security_audit_report(report)
    summary = security_audit_summary(report)
    print(f"PHASE97_STATUS={summary['status']}")
    print(f"PHASE97_VERSION={summary['version']}")
    print(f"PHASE97_CHECKS={len(summary['checks'])}")
    print(f"PHASE97_REPORT_IDENTITY={summary['report_identity']}")
    print(f"PHASE97_REPORT={path}")
    return 0 if report.status == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
