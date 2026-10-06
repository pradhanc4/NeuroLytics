from analytics.production_release import (
    CONDITIONAL_RELEASE, INVALID, RELEASE_READY, VALID,
    ProductionReleaseReport, ReleaseCheck,
    production_release_summary, release_gate,
    run_production_release_audit, validate_production_release,
    write_production_release_report,
)

def test_version():
    assert run_production_release_audit().version == "100.0.0"

def test_boundary():
    assert run_production_release_audit().boundary == "PRODUCTION_RELEASE"

def test_report_type():
    assert isinstance(run_production_release_audit(), ProductionReleaseReport)

def test_current_status_is_conditional_without_explicit_activation():
    report = run_production_release_audit()
    assert report.release_state == CONDITIONAL_RELEASE
    assert report.operational_prediction_release is False
    assert report.status == VALID
    gate_check = next(c for c in report.checks if c.name == "operational_activation_gate")
    assert gate_check.status == "WARNING"

def test_database_gate_is_visible():
    names = {c.name for c in run_production_release_audit().checks}
    assert "database_access" in names
    assert "historical_data_readiness" in names

def test_artifact_gate_is_visible():
    names = {c.name for c in run_production_release_audit().checks}
    assert "model_artifact_readiness" in names

def test_release_summary_shape():
    summary = production_release_summary(run_production_release_audit())
    assert summary["counts"]["total"] >= 10
    assert "release_identity" in summary

def test_gate_blocks_operational_prediction():
    gate = release_gate(run_production_release_audit())
    assert gate["release_allowed"] is True
    assert gate["operational_prediction_release_allowed"] is False

def test_report_validation():
    report = run_production_release_audit()
    assert validate_production_release(report) is report

def test_write_report(tmp_path):
    report = run_production_release_audit()
    path = write_production_release_report(report, tmp_path / "release.json")
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("{")

def test_identity_stable():
    a = run_production_release_audit()
    b = run_production_release_audit()
    assert a.release_identity == b.release_identity

def test_release_ready_contract():
    report = ProductionReleaseReport(
        "100.0.0", "PRODUCTION_RELEASE", VALID, RELEASE_READY, True,
        (ReleaseCheck("x", VALID, "ok"),), "production-release-test",
    )
    assert release_gate(report)["operational_prediction_release_allowed"] is True

def test_invalid_status_contract():
    report = ProductionReleaseReport(
        "100.0.0", "PRODUCTION_RELEASE", INVALID, CONDITIONAL_RELEASE, False,
        (ReleaseCheck("x", INVALID, "bad"),), "production-release-test",
    )
    assert validate_production_release(report) is report
