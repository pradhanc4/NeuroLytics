from __future__ import annotations

import hashlib
from dataclasses import dataclass

from features.feature_artifact import (
    FeatureArtifact,
    serialize_feature_artifact,
)


INTEGRITY_ALGORITHM = "sha256"
INTEGRITY_PREFIX = "artifact-"


@dataclass(frozen=True)
class ArtifactIntegrity:
    """Deterministic integrity identity for a feature artifact."""

    algorithm: str
    digest: str
    identity: str


def _calculate_digest(
    serialized_artifact: str,
) -> str:
    """Calculate the SHA-256 digest of serialized artifact content."""

    if not isinstance(
        serialized_artifact,
        str,
    ):
        raise TypeError(
            "serialized_artifact must be a string."
        )

    return hashlib.sha256(
        serialized_artifact.encode(
            "utf-8"
        )
    ).hexdigest()


def calculate_artifact_integrity(
    artifact: FeatureArtifact,
) -> ArtifactIntegrity:
    """
    Calculate a deterministic integrity identity for an artifact.
    """

    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    serialized_artifact = serialize_feature_artifact(
        artifact
    )

    digest = _calculate_digest(
        serialized_artifact
    )

    return ArtifactIntegrity(
        algorithm=INTEGRITY_ALGORITHM,
        digest=digest,
        identity=(
            f"{INTEGRITY_PREFIX}{digest}"
        ),
    )


def validate_artifact_integrity(
    artifact: FeatureArtifact,
    integrity: ArtifactIntegrity,
) -> None:
    """
    Verify that the artifact still matches its recorded integrity.
    """

    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    if not isinstance(
        integrity,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be an ArtifactIntegrity instance."
        )

    if integrity.algorithm != INTEGRITY_ALGORITHM:
        raise ValueError(
            f"Unsupported integrity algorithm: "
            f"{integrity.algorithm}"
        )

    expected = calculate_artifact_integrity(
        artifact
    )

    if integrity.digest != expected.digest:
        raise ValueError(
            "Artifact integrity validation failed: "
            "digest does not match artifact content."
        )

    if integrity.identity != expected.identity:
        raise ValueError(
            "Artifact integrity validation failed: "
            "identity does not match artifact content."
        )


def is_artifact_integrity_valid(
    artifact: FeatureArtifact,
    integrity: ArtifactIntegrity,
) -> bool:
    """Return whether artifact content matches its integrity identity."""

    try:
        validate_artifact_integrity(
            artifact,
            integrity,
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return True


def get_artifact_integrity_digest(
    integrity: ArtifactIntegrity,
) -> str:
    """Return the raw integrity digest."""

    if not isinstance(
        integrity,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be an ArtifactIntegrity instance."
        )

    return integrity.digest


def get_artifact_integrity_identity(
    integrity: ArtifactIntegrity,
) -> str:
    """Return the prefixed integrity identity."""

    if not isinstance(
        integrity,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be an ArtifactIntegrity instance."
        )

    return integrity.identity


def get_artifact_integrity_algorithm(
    integrity: ArtifactIntegrity,
) -> str:
    """Return the integrity algorithm."""

    if not isinstance(
        integrity,
        ArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be an ArtifactIntegrity instance."
        )

    return integrity.algorithm