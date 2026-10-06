from pathlib import Path
from analytics.production_artifact_qualification import run_production_artifact_qualification, summary, write_report

report = run_production_artifact_qualification(Path(__file__).resolve().parents[1])
write_report(report)
payload = summary(report)
print(f"PHASE101_STATUS={payload['status']}")
print(f"PHASE101_ACTIVATION_READY={payload['activation_ready']}")
print(f"PHASE101_CHECKS={payload['counts']['total']}")
print(f"PHASE101_VALID={payload['counts']['valid']}")
print(f"PHASE101_WARNINGS={payload['counts']['warnings']}")
print(f"PHASE101_INVALID={payload['counts']['invalid']}")
print(f"PHASE101_REPORT_IDENTITY={payload['report_identity']}")
print("PHASE101_REPORT=reports\\production_artifact_qualification.json")
