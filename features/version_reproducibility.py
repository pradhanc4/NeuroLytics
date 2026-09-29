from __future__ import annotations

from features.artifact_integrity import (
    ArtifactIntegrity,
    calculate_artifact_integrity,
)
from features.feature_versioning import (
    FeatureVersionIdentity,
    is_feature_version_reproducible,
)
from features.dataset_versioning import (
    DatasetVersionIdentity,
    is_dataset_version_reproducible,
)
from features.versioned_artifact import (
    VersionedFeatureArtifact,
    is_versioned_feature_artifact_valid,
    validate_versioned_feature_artifact,
)
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    serialize_dataset_version_reference,
    serialize_feature_version_reference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)


def is_feature_version_identity_reproducible(
    first: FeatureVersionIdentity,
    second: FeatureVersionIdentity,
) -> bool:
    """
    Return whether two feature-version identities are
    deterministically reproducible.
    """

    return is_feature_version_reproducible(
        first,
        second,
    )


def is_dataset_version_identity_reproducible(
    first: DatasetVersionIdentity,
    second: DatasetVersionIdentity,
) -> bool:
    """
    Return whether two dataset-version identities are
    deterministically reproducible.
    """

    return is_dataset_version_reproducible(
        first,
        second,
    )


def is_feature_version_reference_reproducible(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> bool:
    """
    Return whether two feature-version references have
    identical deterministic definitions.
    """

    validate_feature_version_reference(
        first
    )

    validate_feature_version_reference(
        second
    )

    return (
        serialize_feature_version_reference(
            first
        )
        == serialize_feature_version_reference(
            second
        )
    )


def is_dataset_version_reference_reproducible(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> bool:
    """
    Return whether two dataset-version references have
    identical deterministic definitions.
    """

    validate_dataset_version_reference(
        first
    )

    validate_dataset_version_reference(
        second
    )

    return (
        serialize_dataset_version_reference(
            first
        )
        == serialize_dataset_version_reference(
            second
        )
    )


def is_artifact_integrity_reproducible(
    first: ArtifactIntegrity,
    second: ArtifactIntegrity,
) -> bool:
    """
    Return whether two artifact-integrity identities are
    identical and therefore reproducible.
    """

    if not isinstance(
        first,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "first must be an ArtifactIntegrity instance."
        )

    if not isinstance(
        second,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "second must be an ArtifactIntegrity instance."
        )

    return first == second


def is_versioned_feature_artifact_reproducible(
    first: VersionedFeatureArtifact,
    second: VersionedFeatureArtifact,
) -> bool:
    """
    Return whether two complete versioned feature artifacts
    are deterministically reproducible.

    Invalid or tampered artifacts return False rather than
    raising validation errors.

    Existing artifact integrity remains the source of truth.
    """

    if not isinstance(
        first,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "first must be a VersionedFeatureArtifact instance."
        )

    if not isinstance(
        second,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "second must be a VersionedFeatureArtifact instance."
        )

    if not is_versioned_feature_artifact_valid(
        first
    ):
        return False

    if not is_versioned_feature_artifact_valid(
        second
    ):
        return False

    first_integrity = calculate_artifact_integrity(
        first.artifact
    )

    second_integrity = calculate_artifact_integrity(
        second.artifact
    )

    if first.integrity != first_integrity:
        return False

    if second.integrity != second_integrity:
        return False

    return (
        first.artifact == second.artifact
        and first.integrity == second.integrity
        and first.feature_reference
        == second.feature_reference
        and first.dataset_reference
        == second.dataset_reference
    )


def get_versioned_feature_artifact_integrity(
    versioned_artifact: VersionedFeatureArtifact,
) -> ArtifactIntegrity:
    """
    Recalculate and return the deterministic artifact
    integrity for a versioned feature artifact.
    """

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    validate_versioned_feature_artifact(
        versioned_artifact
    )

    integrity = calculate_artifact_integrity(
        versioned_artifact.artifact
    )

    if (
        integrity
        != versioned_artifact.integrity
    ):
        raise ValueError(
            "Versioned feature artifact integrity "
            "does not match its artifact content."
        )

    return integrity


__all__ = [
    "is_feature_version_identity_reproducible",
    "is_dataset_version_identity_reproducible",
    "is_feature_version_reference_reproducible",
    "is_dataset_version_reference_reproducible",
    "is_artifact_integrity_reproducible",
    "is_versioned_feature_artifact_reproducible",
    "get_versioned_feature_artifact_integrity",
]