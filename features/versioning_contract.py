from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date


VERSION_CONTRACT_ALGORITHM = "sha256"

VERSION_REFERENCE_TYPES = (
    "feature",
    "dataset",
)

LINEAGE_REFERENCE_TYPES = (
    "feature_to_dataset",
)


@dataclass(frozen=True)
class FeatureVersionReference:
    """
    Immutable reference to a feature-definition version.

    This contract identifies which feature version a downstream
    dataset or artifact was produced from.
    """

    feature_version: str
    identity: str
    algorithm: str


@dataclass(frozen=True)
class DatasetVersionReference:
    """
    Immutable reference to a concrete dataset version.

    The dataset version is explicitly associated with the
    feature version used to produce it.
    """

    dataset_version: str
    identity: str
    algorithm: str
    feature_version: str
    feature_identity: str


@dataclass(frozen=True)
class VersionLineageReference:
    """
    Immutable relationship between a feature version and dataset version.
    """

    lineage_type: str
    feature_version: str
    feature_identity: str
    dataset_version: str
    dataset_identity: str


def validate_feature_version_reference(
    reference: FeatureVersionReference,
) -> None:
    """Validate a feature-version reference."""

    if not isinstance(
        reference,
        FeatureVersionReference,
    ):
        raise TypeError(
            "reference must be a FeatureVersionReference instance."
        )

    if not isinstance(
        reference.feature_version,
        str,
    ) or not reference.feature_version.strip():
        raise ValueError(
            "feature_version must be a non-empty string."
        )

    if not isinstance(
        reference.identity,
        str,
    ) or not reference.identity.strip():
        raise ValueError(
            "identity must be a non-empty string."
        )

    if not isinstance(
        reference.algorithm,
        str,
    ) or not reference.algorithm.strip():
        raise ValueError(
            "algorithm must be a non-empty string."
        )


def validate_dataset_version_reference(
    reference: DatasetVersionReference,
) -> None:
    """Validate a dataset-version reference."""

    if not isinstance(
        reference,
        DatasetVersionReference,
    ):
        raise TypeError(
            "reference must be a DatasetVersionReference instance."
        )

    if not isinstance(
        reference.dataset_version,
        str,
    ) or not reference.dataset_version.strip():
        raise ValueError(
            "dataset_version must be a non-empty string."
        )

    if not isinstance(
        reference.identity,
        str,
    ) or not reference.identity.strip():
        raise ValueError(
            "identity must be a non-empty string."
        )

    if not isinstance(
        reference.algorithm,
        str,
    ) or not reference.algorithm.strip():
        raise ValueError(
            "algorithm must be a non-empty string."
        )

    if not isinstance(
        reference.feature_version,
        str,
    ) or not reference.feature_version.strip():
        raise ValueError(
            "feature_version must be a non-empty string."
        )

    if not isinstance(
        reference.feature_identity,
        str,
    ) or not reference.feature_identity.strip():
        raise ValueError(
            "feature_identity must be a non-empty string."
        )


def validate_version_lineage_reference(
    reference: VersionLineageReference,
) -> None:
    """Validate a feature-to-dataset lineage reference."""

    if not isinstance(
        reference,
        VersionLineageReference,
    ):
        raise TypeError(
            "reference must be a VersionLineageReference instance."
        )

    if reference.lineage_type not in LINEAGE_REFERENCE_TYPES:
        raise ValueError(
            f"Unsupported lineage type: {reference.lineage_type}"
        )

    if not isinstance(
        reference.feature_version,
        str,
    ) or not reference.feature_version.strip():
        raise ValueError(
            "feature_version must be a non-empty string."
        )

    if not isinstance(
        reference.feature_identity,
        str,
    ) or not reference.feature_identity.strip():
        raise ValueError(
            "feature_identity must be a non-empty string."
        )

    if not isinstance(
        reference.dataset_version,
        str,
    ) or not reference.dataset_version.strip():
        raise ValueError(
            "dataset_version must be a non-empty string."
        )

    if not isinstance(
        reference.dataset_identity,
        str,
    ) or not reference.dataset_identity.strip():
        raise ValueError(
            "dataset_identity must be a non-empty string."
        )


def build_feature_version_reference(
    feature_version: str,
    identity: str,
    algorithm: str,
) -> FeatureVersionReference:
    """Build and validate a feature-version reference."""

    reference = FeatureVersionReference(
        feature_version=feature_version,
        identity=identity,
        algorithm=algorithm,
    )

    validate_feature_version_reference(
        reference
    )

    return reference


def build_dataset_version_reference(
    dataset_version: str,
    identity: str,
    algorithm: str,
    feature_version: str,
    feature_identity: str,
) -> DatasetVersionReference:
    """Build and validate a dataset-version reference."""

    reference = DatasetVersionReference(
        dataset_version=dataset_version,
        identity=identity,
        algorithm=algorithm,
        feature_version=feature_version,
        feature_identity=feature_identity,
    )

    validate_dataset_version_reference(
        reference
    )

    return reference


def build_version_lineage_reference(
    feature_version: str,
    feature_identity: str,
    dataset_version: str,
    dataset_identity: str,
) -> VersionLineageReference:
    """Build and validate feature-to-dataset lineage."""

    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=feature_version,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
        dataset_identity=dataset_identity,
    )

    validate_version_lineage_reference(
        reference
    )

    return reference


def serialize_feature_version_reference(
    reference: FeatureVersionReference,
) -> str:
    """Serialize a feature-version reference deterministically."""

    validate_feature_version_reference(
        reference
    )

    definition = {
        "algorithm": reference.algorithm,
        "feature_version": reference.feature_version,
        "identity": reference.identity,
        "reference_type": "feature",
    }

    return json.dumps(
        definition,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def serialize_dataset_version_reference(
    reference: DatasetVersionReference,
) -> str:
    """Serialize a dataset-version reference deterministically."""

    validate_dataset_version_reference(
        reference
    )

    definition = {
        "algorithm": reference.algorithm,
        "dataset_version": reference.dataset_version,
        "feature_identity": reference.feature_identity,
        "feature_version": reference.feature_version,
        "identity": reference.identity,
        "reference_type": "dataset",
    }

    return json.dumps(
        definition,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def serialize_version_lineage_reference(
    reference: VersionLineageReference,
) -> str:
    """Serialize lineage deterministically."""

    validate_version_lineage_reference(
        reference
    )

    definition = {
        "dataset_identity": reference.dataset_identity,
        "dataset_version": reference.dataset_version,
        "feature_identity": reference.feature_identity,
        "feature_version": reference.feature_version,
        "lineage_type": reference.lineage_type,
    }

    return json.dumps(
        definition,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def get_feature_version(
    reference: FeatureVersionReference,
) -> str:
    """Return the declared feature version."""

    validate_feature_version_reference(
        reference
    )

    return reference.feature_version


def get_feature_identity(
    reference: FeatureVersionReference,
) -> str:
    """Return the feature identity."""

    validate_feature_version_reference(
        reference
    )

    return reference.identity


def get_dataset_version(
    reference: DatasetVersionReference,
) -> str:
    """Return the declared dataset version."""

    validate_dataset_version_reference(
        reference
    )

    return reference.dataset_version


def get_dataset_identity(
    reference: DatasetVersionReference,
) -> str:
    """Return the dataset identity."""

    validate_dataset_version_reference(
        reference
    )

    return reference.identity


def get_dataset_feature_version(
    reference: DatasetVersionReference,
) -> str:
    """Return the feature version associated with a dataset."""

    validate_dataset_version_reference(
        reference
    )

    return reference.feature_version


def get_dataset_feature_identity(
    reference: DatasetVersionReference,
) -> str:
    """Return the feature identity associated with a dataset."""

    validate_dataset_version_reference(
        reference
    )

    return reference.feature_identity


def get_lineage_type(
    reference: VersionLineageReference,
) -> str:
    """Return lineage type."""

    validate_version_lineage_reference(
        reference
    )

    return reference.lineage_type


def is_feature_version_reference_valid(
    reference: FeatureVersionReference,
) -> bool:
    """Return whether a feature-version reference is valid."""

    try:
        validate_feature_version_reference(
            reference
        )
    except (TypeError, ValueError):
        return False

    return True


def is_dataset_version_reference_valid(
    reference: DatasetVersionReference,
) -> bool:
    """Return whether a dataset-version reference is valid."""

    try:
        validate_dataset_version_reference(
            reference
        )
    except (TypeError, ValueError):
        return False

    return True


def is_version_lineage_reference_valid(
    reference: VersionLineageReference,
) -> bool:
    """Return whether a lineage reference is valid."""

    try:
        validate_version_lineage_reference(
            reference
        )
    except (TypeError, ValueError):
        return False

    return True


__all__ = [
    "VERSION_CONTRACT_ALGORITHM",
    "VERSION_REFERENCE_TYPES",
    "LINEAGE_REFERENCE_TYPES",
    "FeatureVersionReference",
    "DatasetVersionReference",
    "VersionLineageReference",
    "validate_feature_version_reference",
    "validate_dataset_version_reference",
    "validate_version_lineage_reference",
    "build_feature_version_reference",
    "build_dataset_version_reference",
    "build_version_lineage_reference",
    "serialize_feature_version_reference",
    "serialize_dataset_version_reference",
    "serialize_version_lineage_reference",
    "get_feature_version",
    "get_feature_identity",
    "get_dataset_version",
    "get_dataset_identity",
    "get_dataset_feature_version",
    "get_dataset_feature_identity",
    "get_lineage_type",
    "is_feature_version_reference_valid",
    "is_dataset_version_reference_valid",
    "is_version_lineage_reference_valid",
]