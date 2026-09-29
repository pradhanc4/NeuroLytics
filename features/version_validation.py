from __future__ import annotations

from dataclasses import dataclass

from features.artifact_integrity import (
    ArtifactIntegrity,
    validate_artifact_integrity,
)

from features.dataset_versioning import (
    DatasetVersionIdentity,
    validate_dataset_version_identity,
    validate_dataset_version_reference_against_identity,
)

from features.feature_versioning import (
    FeatureVersionIdentity,
    validate_feature_version_identity,
    validate_feature_version_reference_against_identity,
)

from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)


from features.version_compatibility import (
    check_feature_version_compatibility,
)

from features.versioned_artifact import (
    VersionedFeatureArtifact,
    validate_versioned_feature_artifact,
)


VALID = "VALID"
INVALID = "INVALID"


FEATURE_IDENTITY_INVALID = (
    "FEATURE_IDENTITY_INVALID"
)

DATASET_IDENTITY_INVALID = (
    "DATASET_IDENTITY_INVALID"
)

FEATURE_REFERENCE_INVALID = (
    "FEATURE_REFERENCE_INVALID"
)

DATASET_REFERENCE_INVALID = (
    "DATASET_REFERENCE_INVALID"
)

FEATURE_REFERENCE_MISMATCH = (
    "FEATURE_REFERENCE_MISMATCH"
)

DATASET_REFERENCE_MISMATCH = (
    "DATASET_REFERENCE_MISMATCH"
)

VERSION_COMPATIBILITY_INVALID = (
    "VERSION_COMPATIBILITY_INVALID"
)

ARTIFACT_INTEGRITY_INVALID = (
    "ARTIFACT_INTEGRITY_INVALID"
)

VERSIONED_ARTIFACT_INVALID = (
    "VERSIONED_ARTIFACT_INVALID"
)


@dataclass(frozen=True)
class VersionValidationIssue:
    """
    One version-validation failure.
    """

    code: str
    message: str


@dataclass(frozen=True)
class VersionValidationResult:
    """
    Complete validation result for a versioned object graph.
    """

    status: str
    issues: tuple[
        VersionValidationIssue,
        ...
    ]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def is_invalid(self) -> bool:
        return self.status == INVALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
) -> VersionValidationIssue:
    return VersionValidationIssue(
        code=code,
        message=message,
    )


def _validate_identity_safely(
    identity,
    validator,
    code: str,
    label: str,
) -> list[VersionValidationIssue]:
    try:
        validator(identity)
    except (
        TypeError,
        ValueError,
    ) as exc:
        return [
            _build_issue(
                code=code,
                message=(
                    f"{label} validation failed: "
                    f"{exc}"
                ),
            )
        ]

    return []


def _validate_reference_safely(
    reference,
    validator,
    code: str,
    label: str,
) -> list[VersionValidationIssue]:
    try:
        validator(reference)
    except (
        TypeError,
        ValueError,
    ) as exc:
        return [
            _build_issue(
                code=code,
                message=(
                    f"{label} validation failed: "
                    f"{exc}"
                ),
            )
        ]

    return []


def validate_version_identities(
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> VersionValidationResult:
    """
    Validate both feature and dataset version identities.

    Existing identity validators remain authoritative.
    """

    issues: list[
        VersionValidationIssue
    ] = []

    issues.extend(
        _validate_identity_safely(
            feature_identity,
            validate_feature_version_identity,
            FEATURE_IDENTITY_INVALID,
            "Feature version identity",
        )
    )

    issues.extend(
        _validate_identity_safely(
            dataset_identity,
            validate_dataset_version_identity,
            DATASET_IDENTITY_INVALID,
            "Dataset version identity",
        )
    )

    return VersionValidationResult(
        status=(
            VALID
            if not issues
            else INVALID
        ),
        issues=tuple(issues),
    )


def validate_version_references(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> VersionValidationResult:
    """
    Validate feature/dataset references and verify that each
    reference belongs to its authoritative identity.
    """

    issues: list[
        VersionValidationIssue
    ] = []

    issues.extend(
        _validate_reference_safely(
            feature_reference,
            validate_feature_version_reference,
            FEATURE_REFERENCE_INVALID,
            "Feature version reference",
        )
    )

    issues.extend(
        _validate_reference_safely(
            dataset_reference,
            validate_dataset_version_reference,
            DATASET_REFERENCE_INVALID,
            "Dataset version reference",
        )
    )

    if not issues:
        try:
            validate_feature_version_reference_against_identity(
                feature_reference,
                feature_identity,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            issues.append(
                _build_issue(
                    FEATURE_REFERENCE_MISMATCH,
                    (
                        "Feature version reference does not "
                        "match its identity: "
                        f"{exc}"
                    ),
                )
            )

        try:
            validate_dataset_version_reference_against_identity(
                dataset_reference,
                dataset_identity,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            issues.append(
                _build_issue(
                    DATASET_REFERENCE_MISMATCH,
                    (
                        "Dataset version reference does not "
                        "match its identity: "
                        f"{exc}"
                    ),
                )
            )

    return VersionValidationResult(
        status=(
            VALID
            if not issues
            else INVALID
        ),
        issues=tuple(issues),
    )


def validate_version_compatibility(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> VersionValidationResult:
    """
    Validate feature/dataset version compatibility using the
    existing Phase 17.4 compatibility rules.
    """

    try:
        result = check_feature_version_compatibility(
            feature_reference,
            dataset_reference,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return VersionValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    VERSION_COMPATIBILITY_INVALID,
                    (
                        "Version compatibility validation "
                        f"failed: {exc}"
                    ),
                ),
            ),
        )

    if result.is_compatible:
        return VersionValidationResult(
            status=VALID,
            issues=(),
        )

    return VersionValidationResult(
        status=INVALID,
        issues=tuple(
            _build_issue(
                VERSION_COMPATIBILITY_INVALID,
                issue.message,
            )
            for issue in result.issues
        ),
    )


def validate_artifact_version_integrity(
    artifact,
    integrity: ArtifactIntegrity,
) -> VersionValidationResult:
    """
    Validate existing FeatureArtifact integrity.

    No new integrity algorithm is introduced here.
    """

    try:
        validate_artifact_integrity(
            artifact,
            integrity,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return VersionValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    ARTIFACT_INTEGRITY_INVALID,
                    (
                        "Artifact integrity validation "
                        f"failed: {exc}"
                    ),
                ),
            ),
        )

    return VersionValidationResult(
        status=VALID,
        issues=(),
    )


def validate_versioned_artifact(
    versioned_artifact: VersionedFeatureArtifact,
) -> VersionValidationResult:
    """
    Validate a complete VersionedFeatureArtifact using the
    existing versioned-artifact validation system.
    """

    try:
        validate_versioned_feature_artifact(
            versioned_artifact
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return VersionValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    VERSIONED_ARTIFACT_INVALID,
                    (
                        "Versioned feature artifact validation "
                        f"failed: {exc}"
                    ),
                ),
            ),
        )

    return VersionValidationResult(
        status=VALID,
        issues=(),
    )


def validate_versioned_feature_artifact_integrity(
    versioned_artifact: VersionedFeatureArtifact,
    dataset_identity: DatasetVersionIdentity,
) -> VersionValidationResult:
    """
    Validate the complete versioned artifact.

    This is the main Phase 17.9 validation entry point.

    The authoritative DatasetVersionIdentity must be supplied
    explicitly. A DatasetVersionReference does not contain
    enough information to reconstruct the dataset identity.

    Validation covers:

    1. Feature version identity.
    2. Dataset version identity.
    3. Feature version reference.
    4. Dataset version reference.
    5. Reference-to-identity consistency.
    6. Feature/dataset compatibility.
    7. Existing artifact integrity.
    8. Existing VersionedFeatureArtifact contract.
    """

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        return VersionValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    VERSIONED_ARTIFACT_INVALID,
                    (
                        "versioned_artifact must be a "
                        "VersionedFeatureArtifact instance."
                    ),
                ),
            ),
        )

    if not isinstance(
        dataset_identity,
        DatasetVersionIdentity,
    ):
        return VersionValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    DATASET_IDENTITY_INVALID,
                    (
                        "dataset_identity must be a "
                        "DatasetVersionIdentity instance."
                    ),
                ),
            ),
        )

    issues: list[
        VersionValidationIssue
    ] = []

    artifact = (
        versioned_artifact.artifact
    )

    feature_identity = (
        artifact.version_identity
    )

    feature_reference = (
        versioned_artifact.feature_reference
    )

    dataset_reference = (
        versioned_artifact.dataset_reference
    )

    # --------------------------------------------------------------
    # 1. Validate feature and dataset identities.
    # --------------------------------------------------------------

    identity_result = (
        validate_version_identities(
            feature_identity,
            dataset_identity,
        )
    )

    issues.extend(
        identity_result.issues
    )

    # --------------------------------------------------------------
    # 2. Validate references against their authoritative identities.
    # --------------------------------------------------------------

    reference_result = (
        validate_version_references(
            feature_reference,
            dataset_reference,
            feature_identity,
            dataset_identity,
        )
    )

    issues.extend(
        reference_result.issues
    )

    # --------------------------------------------------------------
    # 3. Validate feature/dataset compatibility.
    # --------------------------------------------------------------

    compatibility_result = (
        validate_version_compatibility(
            feature_reference,
            dataset_reference,
        )
    )

    issues.extend(
        compatibility_result.issues
    )

    # --------------------------------------------------------------
    # 4. Validate existing artifact integrity.
    # --------------------------------------------------------------

    integrity_result = (
        validate_artifact_version_integrity(
            artifact,
            versioned_artifact.integrity,
        )
    )

    issues.extend(
        integrity_result.issues
    )

    # --------------------------------------------------------------
    # 5. Validate the complete existing
    #    VersionedFeatureArtifact contract.
    # --------------------------------------------------------------

    versioned_artifact_result = (
        validate_versioned_artifact(
            versioned_artifact
        )
    )

    issues.extend(
        versioned_artifact_result.issues
    )

    return VersionValidationResult(
        status=(
            VALID
            if not issues
            else INVALID
        ),
        issues=tuple(issues),
    )


def is_version_validation_valid(
    result: VersionValidationResult,
) -> bool:
    if not isinstance(
        result,
        VersionValidationResult,
    ):
        raise TypeError(
            "result must be a VersionValidationResult instance."
        )

    return result.is_valid


def get_version_validation_status(
    result: VersionValidationResult,
) -> str:
    if not isinstance(
        result,
        VersionValidationResult,
    ):
        raise TypeError(
            "result must be a VersionValidationResult instance."
        )

    return result.status


def get_version_validation_issues(
    result: VersionValidationResult,
) -> tuple[
    VersionValidationIssue,
    ...,
]:
    if not isinstance(
        result,
        VersionValidationResult,
    ):
        raise TypeError(
            "result must be a VersionValidationResult instance."
        )

    return result.issues


def get_version_validation_issue_count(
    result: VersionValidationResult,
) -> int:
    if not isinstance(
        result,
        VersionValidationResult,
    ):
        raise TypeError(
            "result must be a VersionValidationResult instance."
        )

    return result.issue_count


__all__ = [
    "VALID",
    "INVALID",
    "FEATURE_IDENTITY_INVALID",
    "DATASET_IDENTITY_INVALID",
    "FEATURE_REFERENCE_INVALID",
    "DATASET_REFERENCE_INVALID",
    "FEATURE_REFERENCE_MISMATCH",
    "DATASET_REFERENCE_MISMATCH",
    "VERSION_COMPATIBILITY_INVALID",
    "ARTIFACT_INTEGRITY_INVALID",
    "VERSIONED_ARTIFACT_INVALID",
    "VersionValidationIssue",
    "VersionValidationResult",
    "validate_version_identities",
    "validate_version_references",
    "validate_version_compatibility",
    "validate_artifact_version_integrity",
    "validate_versioned_artifact",
    "validate_versioned_feature_artifact_integrity",
    "is_version_validation_valid",
    "get_version_validation_status",
    "get_version_validation_issues",
    "get_version_validation_issue_count",
]