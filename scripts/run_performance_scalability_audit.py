from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.engine import SessionLocal
from analytics.performance_scalability_audit import (
    run_performance_scalability_audit,
    performance_scalability_summary,
    write_performance_scalability_report,
)

db = SessionLocal()
try:
    report = run_performance_scalability_audit(db)
    summary = performance_scalability_summary(report)
finally:
    db.close()

path = write_performance_scalability_report(report)
print(f"PHASE95_STATUS={summary['status']}")
print(f"PHASE95_VERSION={summary['version']}")
print(f"PHASE95_MEASUREMENTS={len(summary['measurements'])}")
print(f"PHASE95_SCALABILITY_MEASUREMENTS={len(summary['scalability'])}")
print(f"PHASE95_BOTTLENECKS={len(summary['bottlenecks'])}")
print(f"PHASE95_REPORT_IDENTITY={summary['report_identity']}")
print(f"PHASE95_REPORT_PATH={path}")
