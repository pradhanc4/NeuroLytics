from pathlib import Path
from analytics.production_release import (
    run_production_release_audit,
    production_release_summary,
    write_production_release_report,
    release_gate,
)

def main():
    report = run_production_release_audit()
    write_production_release_report(report)
    summary = production_release_summary(report)
    gate = release_gate(report)
    print(f"PHASE100_STATUS={summary['status']}")
    print(f"PHASE100_VERSION={summary['version']}")
    print(f"PHASE100_RELEASE_STATE={summary['release_state']}")
    print(f"PHASE100_CHECKS={summary['counts']['total']}")
    print(f"PHASE100_VALID={summary['counts']['valid']}")
    print(f"PHASE100_WARNINGS={summary['counts']['warnings']}")
    print(f"PHASE100_INVALID={summary['counts']['invalid']}")
    print(f"PHASE100_OPERATIONAL_RELEASE={summary['operational_prediction_release']}")
    print(f"PHASE100_RELEASE_IDENTITY={summary['release_identity']}")
    print(f"PHASE100_RELEASE_ALLOWED={gate['release_allowed']}")
    print(f"PHASE100_OPERATIONAL_ALLOWED={gate['operational_prediction_release_allowed']}")
    print(f"PHASE100_REPORT={Path('reports/production_release.json')}")

if __name__ == "__main__":
    main()
