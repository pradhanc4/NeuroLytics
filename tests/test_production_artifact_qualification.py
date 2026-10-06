from analytics.production_artifact_qualification import (
    VALID, WARNING, run_production_artifact_qualification, summary,
)


def test_version_and_boundary():
    report = run_production_artifact_qualification()
    assert report.version == "101.0.0"
    assert report.status == WARNING
    assert report.activation_ready is False


def test_all_artifacts_are_validated():
    report = run_production_artifact_qualification()
    assert len(report.artifact_identities) == 5
    assert all(len(value) == 64 for value in report.artifact_identities.values())


def test_activation_authorization_is_explicitly_gated():
    report = run_production_artifact_qualification()
    checks = {check.name: check for check in report.checks}
    assert checks["explicit_activation_authorization"].status == WARNING


def test_summary_shape():
    report = run_production_artifact_qualification()
    payload = summary(report)
    assert payload["boundary"] == "PRODUCTION_ARTIFACT_QUALIFICATION"
    assert payload["counts"]["invalid"] == 0
