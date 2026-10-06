from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.engine import SessionLocal
from analytics.temporal_safety_audit import (
    run_temporal_safety_audit,
    temporal_safety_summary,
    write_temporal_safety_report,
)

db = SessionLocal()
try:
    report = run_temporal_safety_audit(db)
    summary = temporal_safety_summary(report)
finally:
    db.close()

path = write_temporal_safety_report(report)
print(f"PHASE94_STATUS={summary['status']}")
print(f"PHASE94_VERSION={summary['version']}")
print(f"PHASE94_ISSUES={summary['issue_count']}")
print(f"PHASE94_INVALID_ISSUES={summary['invalid_issue_count']}")
print(f"PHASE94_REPORT_IDENTITY={summary['report_identity']}")
print(f"PHASE94_REPORT_PATH={path}")
