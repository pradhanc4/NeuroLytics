from __future__ import annotations

from dataclasses import dataclass

from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)


COMPATIBLE = "COMPATIBLE"
INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True)
class VersionCompatibilityIssue:
    """One version compatibility issue."""

    code: str
    message: str


@dataclass(frozen=True)
class VersionCompatibilityResult:
    """Result of version compatibility validation."""

    status: str
    issues: tuple[VersionCompatibilityIssue, ...]

    @property
    def is_compatible(self) -> bool:
        """Return whether the versions are compatible."""

        return self.status == COMPATIBLE

    @property
    def issue_count(self) -> int:
        """Return the number of compatibility issues."""

        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
) -> VersionCompatibilityIssue:
    """Build one compatibility issue."""

    return VersionCompatibilityIssue(
        code=code,
        message=message,
    )


def _validate_feature_reference_type(
    reference: FeatureVersionReference,
) -> None:
    """Validate the feature reference."""

    validate_feature_version_reference(
        reference
    )


def _validate_dataset_reference_type(
    reference: DatasetVersionReference,
) -> None:
    """Validate the dataset reference."""

    validate_dataset_version_reference(
        reference
    )


def check_feature_version_compatibility(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> VersionCompatibilityResult:
    """
    Check compatibility between a feature version and a dataset version.

    A dataset is compatible with a feature version when:

    1. Both references are structurally valid.
    2. The dataset references the same feature version.
    3. The dataset references the same feature identity.

    Dataset identity itself is intentionally not recalculated here.
    """

    if not isinstance(
        feature_reference,
        FeatureVersionReference,
    ):
        raise TypeError(
            "feature_reference must be a "
            "FeatureVersionReference instance."
        )

    if not isinstance(
        dataset_reference,
        DatasetVersionReference,
    ):
        raise TypeError(
            "dataset_reference must be a "
            "DatasetVersionReference instance."
        )

    issues: list[
        VersionCompatibilityIssue
    ] = []

    try:
        _validate_feature_reference_type(
            feature_reference
        )
    except (TypeError, ValueError) as exc:
        issues.append(
            _build_issue(
                "INVALID_FEATURE_REFERENCE",
                str(exc),
            )
        )

    try:
        _validate_dataset_reference_type(
            dataset_reference
        )
    except (TypeError, ValueError) as exc:
        issues.append(
            _build_issue(
                "INVALID_DATASET_REFERENCE",
                str(exc),
            )
        )

    if not issues:
        if (
            feature_reference.feature_version
            != dataset_reference.feature_version
        ):
            issues.append(
                _build_issue(
                    "FEATURE_VERSION_MISMATCH",
                    (
                        "Feature version reference does not match "
                        "the dataset feature version."
                    ),
                )
            )

        if (
            feature_reference.identity
            != dataset_reference.feature_identity
        ):
            issues.append(
                _build_issue(
                    "FEATURE_IDENTITY_MISMATCH",
                    (
                        "Feature identity reference does not match "
                        "the dataset feature identity."
                    ),
                )
            )

        if (
            feature_reference.algorithm
            != dataset_reference.algorithm
        ):
            issues.append(
                _build_issue(
                    "IDENTITY_ALGORITHM_MISMATCH",
                    (
                        "Feature and dataset references do not use "
                        "the same identity algorithm."
                    ),
                )
            )

    final_issues = tuple(
        issues
    )

    return VersionCompatibilityResult(
        status=(
            INCOMPATIBLE
            if final_issues
            else COMPATIBLE
        ),
        issues=final_issues,
    )


def validate_feature_version_compatibility(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> None:
    """
    Require a feature reference and dataset reference to be compatible.

    Raises ValueError when the relationship is incompatible.
    """

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    if not result.is_compatible:
        messages = "; ".join(
            issue.message
            for issue in result.issues
        )

        raise ValueError(
            "Feature and dataset versions are incompatible: "
            + messages
        )


def is_feature_version_compatible(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> bool:
    """Return whether feature and dataset versions are compatible."""

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    return result.is_compatible


def get_compatibility_status(
    result: VersionCompatibilityResult,
) -> str:
    """Return the compatibility status."""

    if not isinstance(
        result,
        VersionCompatibilityResult,
    ):
        raise TypeError(
            "result must be a VersionCompatibilityResult instance."
        )

    return result.status


def get_compatibility_issues(
    result: VersionCompatibilityResult,
) -> tuple[VersionCompatibilityIssue, ...]:
    """Return all compatibility issues."""

    if not isinstance(
        result,
        VersionCompatibilityResult,
    ):
        raise TypeError(
            "result must be a VersionCompatibilityResult instance."
        )

    return result.issues


def is_version_compatibility_valid(
    result: VersionCompatibilityResult,
) -> bool:
    """Return whether the compatibility result is valid."""

    if not isinstance(
        result,
        VersionCompatibilityResult,
    ):
        raise TypeError(
            "result must be a VersionCompatibilityResult instance."
        )

    return result.is_compatible


__all__ = [
    "COMPATIBLE",
    "INCOMPATIBLE",
    "VersionCompatibilityIssue",
    "VersionCompatibilityResult",
    "check_feature_version_compatibility",
    "validate_feature_version_compatibility",
    "is_feature_version_compatible",
    "get_compatibility_status",
    "get_compatibility_issues",
    "is_version_compatibility_valid",
]