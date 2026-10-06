from __future__ import annotations

from analytics.api_rate_limit import ApiRateLimitPolicy
from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy
from analytics.api_validation import ApiValidationPolicy
from analytics.security_audit import (
    SECURITY_AUDIT_VERSION,
    SECURITY_HEADERS,
    VALID,
    audit_security_contract,
    scan_for_secrets,
    scan_sensitive_root_files,
    security_header_contract,
)


def test_phase97_version():
    assert SECURITY_AUDIT_VERSION == "97.0.0"


def test_security_headers_contract():
    headers = security_header_contract()
    assert headers == SECURITY_HEADERS
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_security_policies_are_secure():
    assert ApiSecurityPolicy(enabled=True).enabled is True
    assert ApiRateLimitPolicy(enabled=True).enabled is True
    assert ApiValidationPolicy().require_object_body is True


def test_credential_store_does_not_retain_raw_key():
    store = ApiCredentialStore()
    credential = store.issue_key("audit", "audit", ("audit:read",), "audit-secret")
    assert len(credential.key_hash) == 64
    assert not hasattr(credential, "raw_key")


def test_credential_verification_uses_expected_results():
    store = ApiCredentialStore()
    store.issue_key("audit", "audit", ("audit:read",), "audit-secret")
    assert store.verify("audit-secret").status == "AUTHENTICATED"
    assert store.verify("wrong").code == "INVALID_CREDENTIAL"


def test_secret_scan_clean_for_safe_fixture(tmp_path):
    source = tmp_path / "safe.py"
    source.write_text("API_VERSION = '97.0.0'\n", encoding="utf-8")
    assert scan_for_secrets([source]) == ()


def test_secret_scan_detects_private_key_pattern(tmp_path):
    source = tmp_path / "unsafe.py"
    source.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    assert scan_for_secrets([source]) == (str(source),)


def test_sensitive_root_scan(tmp_path):
    assert scan_sensitive_root_files(tmp_path) == ()
    (tmp_path / ".env").write_text("X=1", encoding="utf-8")
    assert str(tmp_path / ".env") in scan_sensitive_root_files(tmp_path)


def test_phase97_full_audit_is_valid():
    report = audit_security_contract(".")
    assert report.status == VALID
    assert len(report.checks) >= 10
    assert report.report_identity.startswith("security-audit-")


def test_phase97_audit_has_no_invalid_checks():
    report = audit_security_contract(".")
    assert all(check.status == VALID for check in report.checks)


def test_production_security_headers_are_emitted():
    from tests.test_phase76_production_service_integration import service
    from analytics.production_service import create_production_app

    app = create_production_app(service())
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_v1_responses_are_not_cached():
    from tests.test_phase76_production_service_integration import service
    from analytics.production_service import create_production_app

    app = create_production_app(service())
    response = app.test_client().get("/v1/monitoring/summary")
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"
