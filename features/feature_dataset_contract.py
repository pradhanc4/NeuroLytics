from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_pipeline import FeaturePipelineResult
from features.feature_schema import FeatureSchema
from features.feature_validator import (
    INVALID,
    VALID,
)
from features.feature_versioning import FeatureVersionIdentity
from features.unified_dataset import UnifiedFeatureDataset


@dataclass(frozen=True)
class FeatureDatasetContract:
    """Structural contract for a completed Phase 13 dataset."""

    target_date: date
    feature_version: str
    feature_count: int
    schema_count: int
    feature_names: tuple[str, ...]
    schemas: tuple[FeatureSchema, ...]
    version_identity: FeatureVersionIdentity
    validation_status: str
    leakage_status: str


@dataclass(frozen=True)
class ContractValidationIssue:
    """One feature dataset contract issue."""

    code: str
    message: str


@dataclass(frozen=True)
class ContractValidationResult:
    """Result of feature dataset contract validation."""

    status: str
    issues: tuple[ContractValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
) -> ContractValidationIssue:
    return ContractValidationIssue(
        code=code,
        message=message,
    )


def build_feature_dataset_contract(
    result: FeaturePipelineResult,
) -> FeatureDatasetContract:
    """
    Build the immutable structural contract from a
    completed feature pipeline result.
    """

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return FeatureDatasetContract(
        target_date=result.target_date,
        feature_version=result.feature_version,
        feature_count=result.feature_count,
        schema_count=len(result.schemas),
        feature_names=result.dataset.feature_names,
        schemas=result.schemas,
        version_identity=result.version_identity,
        validation_status=result.validation.status,
        leakage_status=result.leakage.status,
    )


def _validate_target_date(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    if not isinstance(
        contract.target_date,
        date,
    ):
        issues.append(
            _build_issue(
                "INVALID_TARGET_DATE",
                "Contract target date must be a date.",
            )
        )

    return issues


def _validate_feature_version(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    if (
        not isinstance(
            contract.feature_version,
            str,
        )
        or not contract.feature_version.strip()
    ):
        issues.append(
            _build_issue(
                "INVALID_FEATURE_VERSION",
                "Feature version must be a non-empty string.",
            )
        )

    if (
        contract.version_identity.feature_version
        != contract.feature_version
    ):
        issues.append(
            _build_issue(
                "VERSION_IDENTITY_MISMATCH",
                (
                    "Version identity feature version does not "
                    "match the contract feature version."
                ),
            )
        )

    return issues


def _validate_feature_counts(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    if contract.feature_count < 0:
        issues.append(
            _build_issue(
                "INVALID_FEATURE_COUNT",
                "Feature count cannot be negative.",
            )
        )

    if contract.schema_count < 0:
        issues.append(
            _build_issue(
                "INVALID_SCHEMA_COUNT",
                "Schema count cannot be negative.",
            )
        )

    if contract.feature_count != len(
        contract.feature_names
    ):
        issues.append(
            _build_issue(
                "FEATURE_NAME_COUNT_MISMATCH",
                (
                    "Feature count does not match the number "
                    "of feature names."
                ),
            )
        )

    if contract.feature_count != contract.schema_count:
        issues.append(
            _build_issue(
                "FEATURE_SCHEMA_COUNT_MISMATCH",
                (
                    "Feature count does not match schema count."
                ),
            )
        )

    return issues


def _validate_feature_names(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    if len(
        contract.feature_names
    ) != len(
        set(contract.feature_names)
    ):
        issues.append(
            _build_issue(
                "DUPLICATE_FEATURE_NAMES",
                "Feature names must be globally unique.",
            )
        )

    for feature_name in contract.feature_names:
        if (
            not isinstance(
                feature_name,
                str,
            )
            or not feature_name
        ):
            issues.append(
                _build_issue(
                    "INVALID_FEATURE_NAME",
                    "Every feature name must be a non-empty string.",
                )
            )

    return issues


def _validate_schema_alignment(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    schema_names = tuple(
        schema.feature_name
        for schema in contract.schemas
    )

    if schema_names != contract.feature_names:
        issues.append(
            _build_issue(
                "SCHEMA_FEATURE_ORDER_MISMATCH",
                (
                    "Schema feature ordering must exactly match "
                    "feature ordering."
                ),
            )
        )

    for schema in contract.schemas:
        if schema.feature_version != (
            contract.feature_version
        ):
            issues.append(
                _build_issue(
                    "SCHEMA_VERSION_MISMATCH",
                    (
                        f"Schema version does not match contract "
                        f"version for {schema.feature_name}."
                    ),
                )
            )

    return issues


def _validate_statuses(
    contract: FeatureDatasetContract,
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []

    if contract.validation_status != VALID:
        issues.append(
            _build_issue(
                "DATASET_VALIDATION_FAILED",
                (
                    "Feature dataset validation status must be "
                    "VALID before the contract is accepted."
                ),
            )
        )

    if contract.leakage_status != "CLEAN":
        issues.append(
            _build_issue(
                "LEAKAGE_DETECTED",
                (
                    "Feature dataset leakage status must be "
                    "CLEAN before the contract is accepted."
                ),
            )
        )

    return issues


def validate_feature_dataset_contract(
    contract: FeatureDatasetContract,
) -> ContractValidationResult:
    """Validate the complete Phase 13 dataset contract."""

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    issues: list[ContractValidationIssue] = []

    issues.extend(
        _validate_target_date(contract)
    )

    issues.extend(
        _validate_feature_version(contract)
    )

    issues.extend(
        _validate_feature_counts(contract)
    )

    issues.extend(
        _validate_feature_names(contract)
    )

    issues.extend(
        _validate_schema_alignment(contract)
    )

    issues.extend(
        _validate_statuses(contract)
    )

    final_issues = tuple(
        issues
    )

    status = (
        INVALID
        if final_issues
        else VALID
    )

    return ContractValidationResult(
        status=status,
        issues=final_issues,
    )


def get_contract_feature_count(
    contract: FeatureDatasetContract,
) -> int:
    """Return feature count from the contract."""

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    return contract.feature_count


def get_contract_schema_count(
    contract: FeatureDatasetContract,
) -> int:
    """Return schema count from the contract."""

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    return contract.schema_count


def get_contract_feature_names(
    contract: FeatureDatasetContract,
) -> tuple[str, ...]:
    """Return feature names from the contract."""

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    return contract.feature_names


def get_contract_version_identity(
    contract: FeatureDatasetContract,
) -> FeatureVersionIdentity:
    """Return reproducibility identity from the contract."""

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    return contract.version_identity


def get_contract_validation_status(
    result: ContractValidationResult,
) -> str:
    """Return contract validation status."""

    if not isinstance(
        result,
        ContractValidationResult,
    ):
        raise TypeError(
            "result must be a ContractValidationResult instance."
        )

    return result.status


def get_contract_validation_issues(
    result: ContractValidationResult,
) -> tuple[ContractValidationIssue, ...]:
    """Return contract validation issues."""

    if not isinstance(
        result,
        ContractValidationResult,
    ):
        raise TypeError(
            "result must be a ContractValidationResult instance."
        )

    return result.issues


def is_feature_dataset_contract_valid(
    result: ContractValidationResult,
) -> bool:
    """Return whether the dataset contract is valid."""

    if not isinstance(
        result,
        ContractValidationResult,
    ):
        raise TypeError(
            "result must be a ContractValidationResult instance."
        )

    return result.is_valid