from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.production_readiness_audit import (
    run_production_readiness_audit,
    production_readiness_summary,
    write_production_readiness_report,
)

def main() -> int:
    report = run_production_readiness_audit(ROOT)
    write_production_readiness_report(report, ROOT / "reports" / "production_readiness_audit.json")
    summary = production_readiness_summary(report)
    print(f"PHASE98_STATUS={summary['status']}")
    print(f"PHASE98_VERSION={summary['version']}")
    print(f"PHASE98_CHECKS={summary['counts']['total']}")
    print(f"PHASE98_VALID={summary['counts']['valid']}")
    print(f"PHASE98_WARNINGS={summary['counts']['warnings']}")
    print(f"PHASE98_INVALID={summary['counts']['invalid']}")
    print(f"PHASE98_REPORT_IDENTITY={summary['report_identity']}")
    print("PHASE98_REPORT=reports\\production_readiness_audit.json")
    return 0 if summary["status"] != "INVALID" else 1

if __name__ == "__main__":
    raise SystemExit(main())
