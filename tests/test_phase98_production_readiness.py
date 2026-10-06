from pathlib import Path

from analytics.production_readiness_audit import (
    INVALID,
    PRODUCTION_READINESS_BOUNDARY,
    PRODUCTION_READINESS_VERSION,
    VALID,
    WARNING,
    REQUIRED_ROUTES,
    run_production_readiness_audit,
    production_readiness_summary,
)

ROOT = Path(__file__).resolve().parents[1]

def test_version_and_boundary():
    assert PRODUCTION_READINESS_VERSION == "98.0.0"
    assert PRODUCTION_READINESS_BOUNDARY == "PRODUCTION_READINESS_AUDIT"

def test_required_routes_are_declared():
    assert "/health" in REQUIRED_ROUTES
    assert "/v1/inference" in REQUIRED_ROUTES
    assert "/v1/admin/security-audit" in REQUIRED_ROUTES
    assert "/v1/admin/production-readiness" in REQUIRED_ROUTES

def test_audit_returns_structured_report():
    report = run_production_readiness_audit(ROOT)
    assert report.version == PRODUCTION_READINESS_VERSION
    assert report.checks

def test_summary_contains_counts():
    summary = production_readiness_summary(run_production_readiness_audit(ROOT))
    assert summary["counts"]["total"] == len(summary["checks"])
    assert summary["counts"]["valid"] + summary["counts"]["warnings"] + summary["counts"]["invalid"] == summary["counts"]["total"]

def test_core_modules_are_ready():
    report = run_production_readiness_audit(ROOT)
    check = next(item for item in report.checks if item.name == "core_module_imports")
    assert check.status == VALID

def test_production_route_inventory_is_ready():
    report = run_production_readiness_audit(ROOT)
    check = next(item for item in report.checks if item.name == "production_route_inventory")
    assert check.status == VALID

def test_hardening_reports_are_present_and_valid():
    report = run_production_readiness_audit(ROOT)
    check = next(item for item in report.checks if item.name == "hardening_audit_status")
    assert check.status == VALID

def test_missing_model_or_data_is_not_fabricated_as_ready():
    report = run_production_readiness_audit(ROOT)
    model = next(item for item in report.checks if item.name == "model_artifact_readiness")
    data = next(item for item in report.checks if item.name == "historical_data_readiness")
    assert model.status in {VALID, WARNING}
    assert data.status in {VALID, WARNING}
    assert model.status != INVALID
    assert data.status != INVALID
