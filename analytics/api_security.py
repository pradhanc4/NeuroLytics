from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Iterable, Mapping

API_SECURITY_VERSION = "70.0.0"
SECURITY_BOUNDARY = "API_SECURITY_BOUNDARY"
AUTHENTICATED = "AUTHENTICATED"
UNAUTHENTICATED = "UNAUTHENTICATED"
AUTHORIZED = "AUTHORIZED"
FORBIDDEN = "FORBIDDEN"
REVOKED = "REVOKED"
MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
INVALID_CREDENTIAL = "INVALID_CREDENTIAL"
INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"

@dataclass(frozen=True)
class ApiSecurityPolicy:
    enabled: bool = True
    credential_header: str = "X-API-Key"
    required_inference_scope: str = "inference:read"
    required_ready_scope: str = "inference:read"
    allow_public_health: bool = True

@dataclass(frozen=True)
class ApiCredential:
    credential_id: str
    key_hash: str
    role: str
    scopes: tuple[str, ...]
    revoked: bool = False

@dataclass(frozen=True)
class AuthorizationContext:
    credential_id: str
    role: str
    scopes: tuple[str, ...]

@dataclass(frozen=True)
class SecurityDecision:
    status: str
    code: str
    message: str
    context: AuthorizationContext | None = None

class ApiCredentialStore:
    def __init__(self, credentials: Iterable[ApiCredential] = ()) -> None:
        self._credentials: dict[str, ApiCredential] = {}
        for credential in credentials:
            self.add_credential(credential)

    @staticmethod
    def hash_key(raw_key: str) -> str:
        if not isinstance(raw_key, str) or not raw_key:
            raise ValueError("raw_key must be a non-empty string")
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def add_credential(self, credential: ApiCredential) -> None:
        if not isinstance(credential, ApiCredential):
            raise TypeError("credential must be ApiCredential")
        if not credential.credential_id:
            raise ValueError("credential_id must be non-empty")
        if not credential.key_hash:
            raise ValueError("key_hash must be non-empty")
        if not credential.role:
            raise ValueError("role must be non-empty")
        if len(set(credential.scopes)) != len(credential.scopes):
            raise ValueError("credential scopes must be unique")
        self._credentials[credential.credential_id] = credential

    def issue_key(self, credential_id: str, role: str, scopes: Iterable[str], raw_key: str) -> ApiCredential:
        if not isinstance(credential_id, str) or not credential_id:
            raise ValueError("credential_id must be non-empty")
        if not isinstance(role, str) or not role:
            raise ValueError("role must be non-empty")
        scope_tuple = tuple(sorted(set(scopes)))
        if not all(isinstance(scope, str) and scope for scope in scope_tuple):
            raise ValueError("scopes must contain non-empty strings")
        credential = ApiCredential(
            credential_id=credential_id,
            key_hash=self.hash_key(raw_key),
            role=role,
            scopes=scope_tuple,
        )
        self.add_credential(credential)
        return credential

    def revoke(self, credential_id: str) -> ApiCredential:
        credential = self.get(credential_id)
        revoked = ApiCredential(
            credential.credential_id,
            credential.key_hash,
            credential.role,
            credential.scopes,
            True,
        )
        self._credentials[credential_id] = revoked
        return revoked

    def get(self, credential_id: str) -> ApiCredential:
        try:
            return self._credentials[credential_id]
        except KeyError as exc:
            raise KeyError(f"unknown credential_id: {credential_id}") from exc

    def credentials(self) -> tuple[ApiCredential, ...]:
        return tuple(self._credentials[key] for key in sorted(self._credentials))

    def verify(self, raw_key: str) -> SecurityDecision:
        if not isinstance(raw_key, str) or not raw_key:
            return SecurityDecision(UNAUTHENTICATED, MISSING_CREDENTIAL, "API credential is required.")
        supplied_hash = self.hash_key(raw_key)
        matched: ApiCredential | None = None
        for credential in self._credentials.values():
            if hmac.compare_digest(supplied_hash, credential.key_hash):
                matched = credential
                break
        if matched is None:
            return SecurityDecision(UNAUTHENTICATED, INVALID_CREDENTIAL, "API credential is invalid.")
        context = AuthorizationContext(matched.credential_id, matched.role, matched.scopes)
        if matched.revoked:
            return SecurityDecision(FORBIDDEN, REVOKED, "API credential is revoked.", context)
        return SecurityDecision(AUTHENTICATED, AUTHENTICATED, "API credential is valid.", context)

def validate_security_policy(policy: ApiSecurityPolicy) -> None:
    if not isinstance(policy, ApiSecurityPolicy):
        raise TypeError("policy must be ApiSecurityPolicy")
    if not isinstance(policy.enabled, bool) or not isinstance(policy.allow_public_health, bool):
        raise ValueError("security policy boolean fields must be boolean")
    if not isinstance(policy.credential_header, str) or not policy.credential_header:
        raise ValueError("credential_header must be non-empty")
    if not isinstance(policy.required_inference_scope, str) or not policy.required_inference_scope:
        raise ValueError("required_inference_scope must be non-empty")
    if not isinstance(policy.required_ready_scope, str) or not policy.required_ready_scope:
        raise ValueError("required_ready_scope must be non-empty")

def authorize(
    decision: SecurityDecision,
    required_scope: str,
) -> SecurityDecision:
    if decision.status != AUTHENTICATED or decision.context is None:
        return decision
    if required_scope not in decision.context.scopes:
        return SecurityDecision(
            FORBIDDEN,
            INSUFFICIENT_SCOPE,
            "API credential does not have the required scope.",
            decision.context,
        )
    return SecurityDecision(AUTHORIZED, AUTHORIZED, "API credential is authorized.", decision.context)

def security_summary(policy: ApiSecurityPolicy, store: ApiCredentialStore) -> Mapping[str, object]:
    return {
        "security_version": API_SECURITY_VERSION,
        "boundary": SECURITY_BOUNDARY,
        "enabled": policy.enabled,
        "credential_header": policy.credential_header,
        "credential_count": len(store.credentials()),
        "credential_ids": tuple(c.credential_id for c in store.credentials()),
        "raw_keys_exposed": False,
    }

__all__ = [
    "API_SECURITY_VERSION",
    "SECURITY_BOUNDARY",
    "AUTHENTICATED",
    "UNAUTHENTICATED",
    "AUTHORIZED",
    "FORBIDDEN",
    "REVOKED",
    "MISSING_CREDENTIAL",
    "INVALID_CREDENTIAL",
    "INSUFFICIENT_SCOPE",
    "ApiSecurityPolicy",
    "ApiCredential",
    "AuthorizationContext",
    "SecurityDecision",
    "ApiCredentialStore",
    "validate_security_policy",
    "authorize",
    "security_summary",
]
