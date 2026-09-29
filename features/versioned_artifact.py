from __future__ import annotations

from dataclasses import dataclass

from features.artifact_integrity import (
    ArtifactIntegrity,
    calculate_artifact_integrity,
    validate_artifact_integrity,
)
from features.feature_artifact import (
    FeatureArtifact,
    is_feature_artifact_valid,
)
from features.feature_versioning import (
    validate_feature_version_identity,
)
from features.version_compatibility import (
    check_feature_version_compatibility,
)
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)


@dataclass(frozen=True)
class VersionedFeatureArtifact:
    """
    Immutable integration of a FeatureArtifact with its
    feature-version reference, dataset-version reference,
    and artifact integrity identity.
    """

    artifact: FeatureArtifact
    integrity: ArtifactIntegrity
    feature_reference: FeatureVersionReference
    dataset_reference: DatasetVersionReference


def _validate_artifact_type(
    artifact: FeatureArtifact,
) -> None:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )


def _validate_integrity_type(
    integrity: ArtifactIntegrity,
) -> None:
    if not isinstance(
        integrity,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be an ArtifactIntegrity instance."
        )


def _validate_feature_reference_type(
    reference: FeatureVersionReference,
) -> None:
    if not isinstance(
        reference,
        FeatureVersionReference,
    ):
        raise TypeError(
            "feature_reference must be a "
            "FeatureVersionReference instance."
        )


def _validate_dataset_reference_type(
    reference: DatasetVersionReference,
) -> None:
    if not isinstance(
        reference,
        DatasetVersionReference,
    ):
        raise TypeError(
            "dataset_reference must be a "
            "DatasetVersionReference instance."
        )


def _validate_artifact_against_feature_reference(
    artifact: FeatureArtifact,
    feature_reference: FeatureVersionReference,
) -> None:
    """
    Verify that the artifact's concrete feature-version identity
    matches the supplied feature-version reference.
    """

    validate_feature_version_identity(
        artifact.version_identity
    )

    if (
        artifact.feature_version
        != feature_reference.feature_version
    ):
        raise ValueError(
            "Feature artifact version does not match "
            "the supplied feature version reference."
        )

    if (
        artifact.version_identity.feature_version
        != feature_reference.feature_version
    ):
        raise ValueError(
            "Feature artifact identity version does not match "
            "the supplied feature version reference."
        )

    if (
        artifact.version_identity.identity
        != feature_reference.identity
    ):
        raise ValueError(
            "Feature artifact identity does not match "
            "the supplied feature version reference."
        )

    if (
        artifact.version_identity.algorithm
        != feature_reference.algorithm
    ):
        raise ValueError(
            "Feature artifact identity algorithm does not match "
            "the supplied feature version reference."
        )


def _validate_version_compatibility(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> None:
    result = check_feature_version_compatibility(
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
    )

    if not result.is_compatible:
        messages = "; ".join(
            issue.message
            for issue in result.issues
        )

        raise ValueError(
            "Feature and dataset version references are "
            f"incompatible: {messages}"
        )


def build_versioned_feature_artifact(
    artifact: FeatureArtifact,
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> VersionedFeatureArtifact:
    """
    Build a fully versioned feature artifact.

    The existing FeatureArtifact and ArtifactIntegrity systems
    remain the source of truth.
    """

    _validate_artifact_type(
        artifact
    )

    _validate_feature_reference_type(
        feature_reference
    )

    _validate_dataset_reference_type(
        dataset_reference
    )

    validate_feature_version_reference(
        feature_reference
    )

    validate_dataset_version_reference(
        dataset_reference
    )

    if not is_feature_artifact_valid(
        artifact
    ):
        raise ValueError(
            "Feature artifact must have VALID validation status "
            "and CLEAN leakage status."
        )

    _validate_artifact_against_feature_reference(
        artifact=artifact,
        feature_reference=feature_reference,
    )

    _validate_version_compatibility(
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    return VersionedFeatureArtifact(
        artifact=artifact,
        integrity=integrity,
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
    )


def build_versioned_feature_artifact_with_integrity(
    artifact: FeatureArtifact,
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
    integrity: ArtifactIntegrity,
) -> VersionedFeatureArtifact:
    """
    Build a versioned feature artifact using a supplied
    precomputed artifact integrity identity.
    """

    _validate_artifact_type(
        artifact
    )

    _validate_integrity_type(
        integrity
    )

    _validate_feature_reference_type(
        feature_reference
    )

    _validate_dataset_reference_type(
        dataset_reference
    )

    validate_feature_version_reference(
        feature_reference
    )

    validate_dataset_version_reference(
        dataset_reference
    )

    if not is_feature_artifact_valid(
        artifact
    ):
        raise ValueError(
            "Feature artifact must have VALID validation status "
            "and CLEAN leakage status."
        )

    _validate_artifact_against_feature_reference(
        artifact=artifact,
        feature_reference=feature_reference,
    )

    _validate_version_compatibility(
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
    )

    validate_artifact_integrity(
        artifact,
        integrity,
    )

    return VersionedFeatureArtifact(
        artifact=artifact,
        integrity=integrity,
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
    )


def validate_versioned_feature_artifact(
    versioned_artifact: VersionedFeatureArtifact,
) -> None:
    """
    Validate the complete versioned artifact integration.
    """

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    _validate_artifact_type(
        versioned_artifact.artifact
    )

    _validate_integrity_type(
        versioned_artifact.integrity
    )

    _validate_feature_reference_type(
        versioned_artifact.feature_reference
    )

    _validate_dataset_reference_type(
        versioned_artifact.dataset_reference
    )

    validate_feature_version_reference(
        versioned_artifact.feature_reference
    )

    validate_dataset_version_reference(
        versioned_artifact.dataset_reference
    )

    if not is_feature_artifact_valid(
        versioned_artifact.artifact
    ):
        raise ValueError(
            "Feature artifact is not valid."
        )

    _validate_artifact_against_feature_reference(
        artifact=versioned_artifact.artifact,
        feature_reference=(
            versioned_artifact.feature_reference
        ),
    )

    _validate_version_compatibility(
        feature_reference=(
            versioned_artifact.feature_reference
        ),
        dataset_reference=(
            versioned_artifact.dataset_reference
        ),
    )

    validate_artifact_integrity(
        versioned_artifact.artifact,
        versioned_artifact.integrity,
    )


def is_versioned_feature_artifact_valid(
    versioned_artifact: VersionedFeatureArtifact,
) -> bool:
    """Return whether the complete versioned artifact is valid."""

    try:
        validate_versioned_feature_artifact(
            versioned_artifact
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return True


def get_versioned_artifact(
    versioned_artifact: VersionedFeatureArtifact,
) -> FeatureArtifact:
    """Return the underlying feature artifact."""

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    return versioned_artifact.artifact


def get_versioned_artifact_integrity(
    versioned_artifact: VersionedFeatureArtifact,
) -> ArtifactIntegrity:
    """Return the artifact integrity identity."""

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    return versioned_artifact.integrity


def get_versioned_feature_reference(
    versioned_artifact: VersionedFeatureArtifact,
) -> FeatureVersionReference:
    """Return the feature-version reference."""

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    return versioned_artifact.feature_reference


def get_versioned_dataset_reference(
    versioned_artifact: VersionedFeatureArtifact,
) -> DatasetVersionReference:
    """Return the dataset-version reference."""

    if not isinstance(
        versioned_artifact,
        VersionedFeatureArtifact,
    ):
        raise TypeError(
            "versioned_artifact must be a "
            "VersionedFeatureArtifact instance."
        )

    return versioned_artifact.dataset_reference


def get_versioned_feature_version(
    versioned_artifact: VersionedFeatureArtifact,
) -> str:
    """Return the declared feature version."""

    return get_versioned_feature_reference(
        versioned_artifact
    ).feature_version


def get_versioned_dataset_version(
    versioned_artifact: VersionedFeatureArtifact,
) -> str:
    """Return the declared dataset version."""

    return get_versioned_dataset_reference(
        versioned_artifact
    ).dataset_version


def get_versioned_artifact_integrity_identity(
    versioned_artifact: VersionedFeatureArtifact,
) -> str:
    """Return the artifact integrity identity."""

    return get_versioned_artifact_integrity(
        versioned_artifact
    ).identity


__all__ = [
    "VersionedFeatureArtifact",
    "build_versioned_feature_artifact",
    "build_versioned_feature_artifact_with_integrity",
    "validate_versioned_feature_artifact",
    "is_versioned_feature_artifact_valid",
    "get_versioned_artifact",
    "get_versioned_artifact_integrity",
    "get_versioned_feature_reference",
    "get_versioned_dataset_reference",
    "get_versioned_feature_version",
    "get_versioned_dataset_version",
    "get_versioned_artifact_integrity_identity",
]