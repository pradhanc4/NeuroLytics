from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

FRONTEND_VERSION = "77.0.0"
VALID = "VALID"
INVALID = "INVALID"

@dataclass(frozen=True)
class FrontendApiContract:
    api_base: str = ""
    health_path: str = "/health"
    readiness_path: str = "/ready"
    inference_path: str = "/v1/inference"
    monitoring_summary_path: str = "/v1/monitoring/summary"
    monitoring_report_path: str = "/v1/monitoring/{name}"

@dataclass(frozen=True)
class FrontendState:
    service_status: str
    readiness: str
    model_identity: str | None
    model_version: str | None
    artifact_identity: str | None
    error: str | None = None

def validate_contract(contract: FrontendApiContract) -> tuple[str, ...]:
    issues = []
    if not isinstance(contract, FrontendApiContract):
        return ("INVALID_CONTRACT_TYPE",)
    for name in ("health_path","readiness_path","inference_path",
                 "monitoring_summary_path","monitoring_report_path"):
        value = getattr(contract, name)
        if not isinstance(value, str) or not value.startswith("/"):
            issues.append("INVALID_" + name.upper())
    if not isinstance(contract.api_base, str):
        issues.append("INVALID_API_BASE")
    return tuple(issues)

def contract_summary(contract: FrontendApiContract) -> Mapping[str, str]:
    issues = validate_contract(contract)
    return {
        "version": FRONTEND_VERSION,
        "status": VALID if not issues else INVALID,
        "api_base": contract.api_base,
        "health": contract.health_path,
        "ready": contract.readiness_path,
        "inference": contract.inference_path,
        "monitoring_summary": contract.monitoring_summary_path,
        "monitoring_report": contract.monitoring_report_path,
    }

__all__ = ["FRONTEND_VERSION","VALID","INVALID","FrontendApiContract",
           "FrontendState","validate_contract","contract_summary"]
