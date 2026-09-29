from __future__ import annotations

from dataclasses import dataclass

from features.dataset_versioning import (
    DatasetVersionIdentity,
    build_dataset_version_reference,
    validate_dataset_version_identity,
    validate_dataset_version_reference_against_identity,
)
from features.feature_versioning import (
    FeatureVersionIdentity,
    build_feature_version_reference_from_identity,
    validate_feature_version_identity,
    validate_feature_version_reference_against_identity,
)
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    VersionLineageReference,
    build_version_lineage_reference,
    serialize_version_lineage_reference,
    validate_version_lineage_reference,
)


LINEAGE_TYPE = "feature_to_dataset"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class VersionLineageResult:
    """Result of validating feature-to-dataset version lineage."""

    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the lineage is valid."""

        return self.status == VALID

    @property
    def is_invalid(self) -> bool:
        """Return whether the lineage is invalid."""

        return self.status == INVALID

    @property
    def issue_count(self) -> int:
        """Return the number of lineage validation issues."""

        return len(self.issues)


def build_version_lineage(
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> VersionLineageReference:
    """
    Build a feature-to-dataset lineage reference from authoritative identities.

    Existing feature and dataset identities remain the source of truth.
    """

    validate_feature_version_identity(
        feature_identity
    )

    validate_dataset_version_identity(
        dataset_identity
    )

    if (
        dataset_identity.feature_version
        != feature_identity.feature_version
    ):
        raise ValueError(
            "Dataset feature_version does not match "
            "the FeatureVersionIdentity feature_version."
        )

    if (
        dataset_identity.feature_identity
        != feature_identity.identity
    ):
        raise ValueError(
            "Dataset feature_identity does not match "
            "the FeatureVersionIdentity identity."
        )

    if (
        dataset_identity.algorithm
        != feature_identity.algorithm
    ):
        raise ValueError(
            "Feature and dataset version algorithms do not match."
        )

    lineage = build_version_lineage_reference(
        feature_version=feature_identity.feature_version,
        feature_identity=feature_identity.identity,
        dataset_version=dataset_identity.dataset_version,
        dataset_identity=dataset_identity.identity,
    )

    validate_version_lineage_reference(
        lineage
    )

    return lineage


def validate_version_lineage(
    lineage: VersionLineageReference,
) -> None:
    """Validate the structural lineage contract."""

    validate_version_lineage_reference(
        lineage
    )


def validate_lineage_against_feature_identity(
    lineage: VersionLineageReference,
    feature_identity: FeatureVersionIdentity,
) -> None:
    """Validate lineage against the authoritative feature identity."""

    validate_version_lineage_reference(
        lineage
    )

    validate_feature_version_identity(
        feature_identity
    )

    if lineage.feature_version != feature_identity.feature_version:
        raise ValueError(
            "Lineage feature_version does not match "
            "the FeatureVersionIdentity feature_version."
        )

    if lineage.feature_identity != feature_identity.identity:
        raise ValueError(
            "Lineage feature_identity does not match "
            "the FeatureVersionIdentity identity."
        )

    if feature_identity.algorithm != "sha256":
        raise ValueError(
            "Unsupported feature version algorithm."
        )


def validate_lineage_against_dataset_identity(
    lineage: VersionLineageReference,
    dataset_identity: DatasetVersionIdentity,
) -> None:
    """Validate lineage against the authoritative dataset identity."""

    validate_version_lineage_reference(
        lineage
    )

    validate_dataset_version_identity(
        dataset_identity
    )

    if lineage.dataset_version != dataset_identity.dataset_version:
        raise ValueError(
            "Lineage dataset_version does not match "
            "the DatasetVersionIdentity dataset_version."
        )

    if lineage.dataset_identity != dataset_identity.identity:
        raise ValueError(
            "Lineage dataset_identity does not match "
            "the DatasetVersionIdentity identity."
        )

    if lineage.feature_version != dataset_identity.feature_version:
        raise ValueError(
            "Lineage feature_version does not match "
            "the DatasetVersionIdentity feature_version."
        )

    if lineage.feature_identity != dataset_identity.feature_identity:
        raise ValueError(
            "Lineage feature_identity does not match "
            "the DatasetVersionIdentity feature_identity."
        )


def validate_complete_version_lineage(
    lineage: VersionLineageReference,
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> None:
    """
    Validate complete feature-to-dataset lineage.

    Both authoritative identities must agree with the lineage reference,
    and the dataset must itself reference the same feature identity.
    """

    validate_version_lineage_reference(
        lineage
    )

    validate_feature_version_identity(
        feature_identity
    )

    validate_dataset_version_identity(
        dataset_identity
    )

    validate_lineage_against_feature_identity(
        lineage,
        feature_identity,
    )

    validate_lineage_against_dataset_identity(
        lineage,
        dataset_identity,
    )

    if (
        dataset_identity.feature_version
        != feature_identity.feature_version
    ):
        raise ValueError(
            "Dataset feature_version does not match "
            "the FeatureVersionIdentity feature_version."
        )

    if (
        dataset_identity.feature_identity
        != feature_identity.identity
    ):
        raise ValueError(
            "Dataset feature_identity does not match "
            "the FeatureVersionIdentity identity."
        )

    if (
        dataset_identity.algorithm
        != feature_identity.algorithm
    ):
        raise ValueError(
            "Feature and dataset version algorithms do not match."
        )


def build_version_lineage_from_references(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> VersionLineageReference:
    """
    Build lineage from existing validated version references.

    The references remain authoritative for their declared values;
    no new identity is calculated.
    """

    validate_version_lineage_reference(
        build_version_lineage_reference(
            feature_version=feature_reference.feature_version,
            feature_identity=feature_reference.identity,
            dataset_version=dataset_reference.dataset_version,
            dataset_identity=dataset_reference.identity,
        )
    )

    if (
        feature_reference.feature_version
        != dataset_reference.feature_version
    ):
        raise ValueError(
            "Feature and dataset references have different "
            "feature versions."
        )

    if (
        feature_reference.identity
        != dataset_reference.feature_identity
    ):
        raise ValueError(
            "Feature and dataset references have different "
            "feature identities."
        )

    if (
        feature_reference.algorithm
        != dataset_reference.algorithm
    ):
        raise ValueError(
            "Feature and dataset reference algorithms do not match."
        )

    return build_version_lineage_reference(
        feature_version=feature_reference.feature_version,
        feature_identity=feature_reference.identity,
        dataset_version=dataset_reference.dataset_version,
        dataset_identity=dataset_reference.identity,
    )


def validate_version_lineage_from_references(
    lineage: VersionLineageReference,
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> None:
    """Validate lineage against existing feature and dataset references."""

    validate_version_lineage_reference(
        lineage
    )

    if lineage.feature_version != feature_reference.feature_version:
        raise ValueError(
            "Lineage feature_version does not match "
            "the FeatureVersionReference."
        )

    if lineage.feature_identity != feature_reference.identity:
        raise ValueError(
            "Lineage feature_identity does not match "
            "the FeatureVersionReference."
        )

    if lineage.dataset_version != dataset_reference.dataset_version:
        raise ValueError(
            "Lineage dataset_version does not match "
            "the DatasetVersionReference."
        )

    if lineage.dataset_identity != dataset_reference.identity:
        raise ValueError(
            "Lineage dataset_identity does not match "
            "the DatasetVersionReference."
        )

    if (
        feature_reference.feature_version
        != dataset_reference.feature_version
    ):
        raise ValueError(
            "Feature and dataset references have different "
            "feature versions."
        )

    if (
        feature_reference.identity
        != dataset_reference.feature_identity
    ):
        raise ValueError(
            "Feature and dataset references have different "
            "feature identities."
        )

    if (
        feature_reference.algorithm
        != dataset_reference.algorithm
    ):
        raise ValueError(
            "Feature and dataset reference algorithms do not match."
        )


def compare_version_lineage(
    first: VersionLineageReference,
    second: VersionLineageReference,
) -> bool:
    """Return whether two lineage references are exactly identical."""

    validate_version_lineage_reference(
        first
    )

    validate_version_lineage_reference(
        second
    )

    return (
        first.lineage_type == second.lineage_type
        and first.feature_version == second.feature_version
        and first.feature_identity == second.feature_identity
        and first.dataset_version == second.dataset_version
        and first.dataset_identity == second.dataset_identity
    )


def is_version_lineage_reproducible(
    first: VersionLineageReference,
    second: VersionLineageReference,
) -> bool:
    """Return whether two lineage references are reproducible."""

    if not compare_version_lineage(
        first,
        second,
    ):
        return False

    return (
        serialize_version_lineage_reference(first)
        == serialize_version_lineage_reference(second)
    )


def serialize_version_lineage(
    lineage: VersionLineageReference,
) -> str:
    """Return the canonical deterministic lineage serialization."""

    return serialize_version_lineage_reference(
        lineage
    )


def validate_version_lineage_result(
    lineage: VersionLineageReference,
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> VersionLineageResult:
    """
    Return a structured validation result for complete lineage.

    This helper does not replace the strict validation APIs.
    """

    try:
        validate_complete_version_lineage(
            lineage=lineage,
            feature_identity=feature_identity,
            dataset_identity=dataset_identity,
        )
    except (TypeError, ValueError) as exc:
        return VersionLineageResult(
            status=INVALID,
            issues=(str(exc),),
        )

    return VersionLineageResult(
        status=VALID,
        issues=(),
    )


def is_version_lineage_valid(
    lineage: VersionLineageReference,
    feature_identity: FeatureVersionIdentity,
    dataset_identity: DatasetVersionIdentity,
) -> bool:
    """Return whether complete version lineage is valid."""

    return validate_version_lineage_result(
        lineage=lineage,
        feature_identity=feature_identity,
        dataset_identity=dataset_identity,
    ).is_valid


def get_lineage_feature_version(
    lineage: VersionLineageReference,
) -> str:
    """Return the feature version recorded by the lineage."""

    validate_version_lineage_reference(
        lineage
    )

    return lineage.feature_version


def get_lineage_feature_identity(
    lineage: VersionLineageReference,
) -> str:
    """Return the feature identity recorded by the lineage."""

    validate_version_lineage_reference(
        lineage
    )

    return lineage.feature_identity


def get_lineage_dataset_version(
    lineage: VersionLineageReference,
) -> str:
    """Return the dataset version recorded by the lineage."""

    validate_version_lineage_reference(
        lineage
    )

    return lineage.dataset_version


def get_lineage_dataset_identity(
    lineage: VersionLineageReference,
) -> str:
    """Return the dataset identity recorded by the lineage."""

    validate_version_lineage_reference(
        lineage
    )

    return lineage.dataset_identity


def get_lineage_type(
    lineage: VersionLineageReference,
) -> str:
    """Return the lineage relationship type."""

    validate_version_lineage_reference(
        lineage
    )

    return lineage.lineage_type


__all__ = [
    "LINEAGE_TYPE",
    "VALID",
    "INVALID",
    "VersionLineageResult",
    "build_version_lineage",
    "build_version_lineage_from_references",
    "validate_version_lineage",
    "validate_lineage_against_feature_identity",
    "validate_lineage_against_dataset_identity",
    "validate_complete_version_lineage",
    "validate_version_lineage_from_references",
    "compare_version_lineage",
    "is_version_lineage_reproducible",
    "serialize_version_lineage",
    "validate_version_lineage_result",
    "is_version_lineage_valid",
    "get_lineage_feature_version",
    "get_lineage_feature_identity",
    "get_lineage_dataset_version",
    "get_lineage_dataset_identity",
    "get_lineage_type",
]