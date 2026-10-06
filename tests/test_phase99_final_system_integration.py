from pathlib import Path

from analytics.final_system_integration import (
    FINAL_SYSTEM_INTEGRATION_BOUNDARY,
    FINAL_SYSTEM_INTEGRATION_VERSION,
    VALID,
    WARNING,
    run_final_system_integration,
    final_system_integration_summary,
)

ROOT = Path(__file__).resolve().parents[1]

def test_version_and_boundary():
    assert FINAL_SYSTEM_INTEGRATION_VERSION == "99.0.0"
    assert FINAL_SYSTEM_INTEGRATION_BOUNDARY == "FINAL_SYSTEM_INTEGRATION"

def test_report_has_checks():
    report = run_final_system_integration(ROOT)
    assert report.checks
    assert report.version == "99.0.0"

def test_release_files_integrated():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "release_file_inventory")
    assert check.status == VALID

def test_critical_routes_integrated():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "critical_route_integration")
    assert check.status == VALID

def test_module_integration():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "module_integration")
    assert check.status == VALID

def test_readiness_gate_has_no_invalid_findings():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "production_readiness_gate")
    assert check.status == VALID

def test_sequential_prediction_boundary():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "sequential_prediction_boundary")
    assert check.status == VALID

def test_audit_chain_boundary():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "audit_chain_boundary")
    assert check.status == VALID

def test_operational_warning_is_explicit():
    report = run_final_system_integration(ROOT)
    check = next(c for c in report.checks if c.name == "conditional_operational_inputs")
    assert check.status in {VALID, WARNING}

def test_summary_counts():
    summary = final_system_integration_summary(run_final_system_integration(ROOT))
    counts = summary["counts"]
    assert counts["total"] == len(summary["checks"])
    assert counts["valid"] + counts["warnings"] + counts["invalid"] == counts["total"]
