from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.final_system_integration import (
    run_final_system_integration,
    final_system_integration_summary,
    write_final_system_integration_report,
)

report = run_final_system_integration(ROOT)
write_final_system_integration_report(report, ROOT / "reports" / "final_system_integration.json")
summary = final_system_integration_summary(report)

print(f"PHASE99_STATUS={summary['status']}")
print(f"PHASE99_VERSION={summary['version']}")
print(f"PHASE99_CHECKS={summary['counts']['total']}")
print(f"PHASE99_VALID={summary['counts']['valid']}")
print(f"PHASE99_WARNINGS={summary['counts']['warnings']}")
print(f"PHASE99_INVALID={summary['counts']['invalid']}")
print(f"PHASE99_REPORT_IDENTITY={summary['report_identity']}")
print("PHASE99_REPORT=reports\\final_system_integration.json")

raise SystemExit(0 if summary["status"] != "INVALID" else 1)
