from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy, validate_security_policy
from analytics.api_rate_limit import ApiRateLimitPolicy, ApiRateLimiter, validate_rate_limit_policy
from analytics.api_validation import ApiValidationPolicy, validate_api_validation_policy

SECURITY_AUDIT_VERSION = "97.0.0"
SECURITY_AUDIT_BOUNDARY = "SECURITY_AUDIT_BOUNDARY"
VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)aws_secret_access_key\s*="),
    re.compile(r"(?i)(?:password|passwd|secret_key|private_key)\s*=\s*['\"]"),
)

@dataclass(frozen=True)
class SecurityCheck:
    name: str
    status: str
    detail: str

@dataclass(frozen=True)
class SecurityAuditReport:
    version: str
    status: str
    checks: tuple[SecurityCheck, ...]
    report_identity: str

def _identity(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "security-audit-" + hashlib.sha256(raw).hexdigest()

def _check(name: str, ok: bool, detail: str, *, warning: bool = False) -> SecurityCheck:
    if ok:
        status = VALID
    else:
        status = WARNING if warning else INVALID
    return SecurityCheck(name, status, detail)

def security_header_contract() -> dict[str, str]:
    return dict(SECURITY_HEADERS)

def scan_for_secrets(paths: Iterable[str | Path]) -> tuple[str, ...]:
    findings: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(str(path))
                break
    return tuple(sorted(set(findings)))

def scan_sensitive_root_files(root: str | Path) -> tuple[str, ...]:
    root_path = Path(root)
    findings: list[str] = []
    if not root_path.exists():
        return ()
    for pattern in (".env", ".env.*", "*.pem", "*.key", "*.p12"):
        findings.extend(
            str(path) for path in root_path.glob(pattern)
            if path.is_file() and path.name not in {".env.example", ".env.template"}
        )
    return tuple(sorted(set(findings)))

def audit_security_contract(project_root: str | Path = ".") -> SecurityAuditReport:
    root = Path(project_root)
    checks: list[SecurityCheck] = []

    security_policy = ApiSecurityPolicy(enabled=True)
    validate_security_policy(security_policy)
    checks.append(_check(
        "authentication_policy",
        security_policy.enabled and security_policy.credential_header == "X-API-Key",
        "API authentication is explicitly enabled with a dedicated credential header.",
    ))

    rate_policy = ApiRateLimitPolicy(enabled=True)
    validate_rate_limit_policy(rate_policy)
    checks.append(_check(
        "rate_limit_policy",
        rate_policy.enabled and rate_policy.requests_per_window > 0 and rate_policy.burst_limit > 0,
        "Bounded request and burst limits are configured.",
    ))

    validation_policy = ApiValidationPolicy()
    validate_api_validation_policy(validation_policy)
    checks.append(_check(
        "request_validation_policy",
        validation_policy.require_object_body and validation_policy.max_json_bytes <= 1_048_576,
        "JSON object validation and a 1 MiB request ceiling are configured.",
    ))

    store = ApiCredentialStore()
    credential = store.issue_key("phase97-audit", "audit", ("audit:read",), "phase97-audit-secret")
    checks.append(_check(
        "credential_storage",
        len(credential.key_hash) == 64 and not hasattr(credential, "raw_key"),
        "Credentials retain a SHA-256 hash and do not retain raw API keys.",
    ))
    checks.append(_check(
        "credential_verification",
        store.verify("phase97-audit-secret").status == "AUTHENTICATED"
        and store.verify("wrong-secret").code == "INVALID_CREDENTIAL",
        "Valid credentials authenticate and invalid credentials are rejected.",
    ))

    limiter = ApiRateLimiter(rate_policy)
    first = limiter.check("phase97-audit")
    checks.append(_check(
        "rate_limit_runtime",
        first.allowed and first.remaining == rate_policy.requests_per_window - 1,
        "Rate limiter decrements remaining capacity for an identity.",
    ))

    source_paths = [
        root / "analytics" / "api_security.py",
        root / "analytics" / "api_rate_limit.py",
        root / "analytics" / "api_validation.py",
        root / "analytics" / "production_service.py",
        root / "analytics" / "production_api.py",
    ]
    secret_findings = scan_for_secrets(source_paths)
    checks.append(_check(
        "source_secret_scan",
        not secret_findings,
        "No high-risk secret/private-key patterns were found in production source files."
        if not secret_findings else f"Potential secret pattern found in: {secret_findings}",
    ))

    sensitive_root = scan_sensitive_root_files(root)
    checks.append(_check(
        "sensitive_root_files",
        not sensitive_root,
        "No root-level environment/key/certificate files were found."
        if not sensitive_root else f"Sensitive root files require review: {sensitive_root}",
        warning=True,
    ))

    production_source = root / "analytics" / "production_service.py"
    source_text = production_source.read_text(encoding="utf-8", errors="ignore") if production_source.exists() else ""
    checks.append(_check(
        "production_authorization_boundary",
        "_security_failure" in source_text and "authorize_request" in source_text,
        "Production routes use the shared authorization boundary.",
    ))
    checks.append(_check(
        "production_rate_limit_boundary",
        "rate_limit_headers" in source_text and "rate_limiter" in source_text,
        "Production routes retain the shared rate-limit boundary.",
    ))
    checks.append(_check(
        "safe_error_boundary",
        "INTERNAL_SERVER_ERROR_RECOVERABLE" in source_text,
        "Unexpected production exceptions use the safe error contract.",
    ))
    checks.append(_check(
        "security_headers_contract",
        all(value in source_text for value in (
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        )),
        "Production application emits the Phase 97 baseline security headers.",
    ))

    report_payload = {
        "version": SECURITY_AUDIT_VERSION,
        "checks": [(c.name, c.status, c.detail) for c in checks],
    }
    status = VALID if all(c.status == VALID for c in checks) else (
        WARNING if all(c.status != INVALID for c in checks) else INVALID
    )
    return SecurityAuditReport(
        SECURITY_AUDIT_VERSION,
        status,
        tuple(checks),
        _identity(report_payload),
    )

def security_audit_summary(report: SecurityAuditReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "version": report.version,
        "boundary": SECURITY_AUDIT_BOUNDARY,
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail}
            for c in report.checks
        ],
        "report_identity": report.report_identity,
    }

def write_security_audit_report(
    report: SecurityAuditReport,
    path: str | Path = "reports/security_audit.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(security_audit_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination

__all__ = [
    "SECURITY_AUDIT_VERSION", "SECURITY_AUDIT_BOUNDARY",
    "VALID", "WARNING", "INVALID", "SECURITY_HEADERS",
    "SecurityCheck", "SecurityAuditReport",
    "security_header_contract", "scan_for_secrets",
    "scan_sensitive_root_files", "audit_security_contract",
    "security_audit_summary", "write_security_audit_report",
]
