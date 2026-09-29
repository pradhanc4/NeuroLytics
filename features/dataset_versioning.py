from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from features.feature_versioning import (
    FeatureVersionIdentity,
    validate_feature_version_identity,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
)
from features.versioning_contract import (
    DatasetVersionReference,
    build_dataset_version_reference as build_dataset_version_reference_contract,
    validate_dataset_version_reference,
)


DATASET_VERSION_ALGORITHM = "sha256"
DATASET_VERSION_PREFIX = "dataset-"


@dataclass(frozen=True)
class DatasetVersionIdentity:
    """
    Deterministic identity of a concrete feature dataset.

    The identity represents the exact dataset state together with
    the feature definition identity from which the dataset was built.
    """

    dataset_version: str
    identity: str
    algorithm: str
    canonical_definition: str
    feature_version: str
    feature_identity: str


def _validate_dataset_version_label(
    dataset_version: str,
) -> None:
    """Validate the declared dataset version label."""

    if not isinstance(
        dataset_version,
        str,
    ) or not dataset_version.strip():
        raise ValueError(
            "dataset_version must be a non-empty string."
        )


def _validate_dataset(
    dataset: UnifiedFeatureDataset,
) -> None:
    """Validate the concrete dataset before identity construction."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    if not dataset.records:
        raise ValueError(
            "dataset must contain at least one feature record."
        )

    if not dataset.feature_version.strip():
        raise ValueError(
            "dataset feature_version must be a non-empty string."
        )

    feature_names = dataset.feature_names

    if len(feature_names) != len(
        set(feature_names)
    ):
        raise ValueError(
            "dataset feature names must be unique."
        )

    for record in dataset.records:
        if not isinstance(
            record.feature_name,
            str,
        ) or not record.feature_name:
            raise ValueError(
                "Every dataset feature name must be a non-empty string."
            )

        if not isinstance(
            record.feature_type,
            str,
        ) or not record.feature_type:
            raise ValueError(
                "Every dataset feature type must be a non-empty string."
            )

        if not isinstance(
            record.source,
            str,
        ) or not record.source:
            raise ValueError(
                "Every dataset feature source must be a non-empty string."
            )


def _build_record_definition(
    dataset: UnifiedFeatureDataset,
) -> list[dict]:
    """
    Build the ordered concrete feature-record definition.

    Record order is preserved intentionally because the unified
    dataset contract treats feature ordering as deterministic.
    """

    return [
        {
            "feature_name": record.feature_name,
            "value": record.value,
            "feature_type": record.feature_type,
            "source": record.source,
        }
        for record in dataset.records
    ]


def _build_dataset_definition(
    dataset: UnifiedFeatureDataset,
    feature_identity: FeatureVersionIdentity,
    dataset_version: str,
) -> dict:
    """Build the canonical dataset-version definition."""

    _validate_dataset_version_label(
        dataset_version
    )

    _validate_dataset(
        dataset
    )

    validate_feature_version_identity(
        feature_identity
    )

    if (
        dataset.feature_version
        != feature_identity.feature_version
    ):
        raise ValueError(
            "Dataset feature_version does not match "
            "the FeatureVersionIdentity feature_version."
        )

    return {
        "dataset_version": dataset_version,
        "feature_identity": feature_identity.identity,
        "feature_version": dataset.feature_version,
        "records": _build_record_definition(
            dataset
        ),
        "target_date": dataset.target_date.isoformat(),
    }


def _canonicalize_definition(
    definition: dict,
) -> str:
    """Serialize the dataset definition deterministically."""

    return json.dumps(
        definition,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def _calculate_identity(
    canonical_definition: str,
) -> str:
    """Calculate deterministic SHA-256 dataset identity."""

    digest = hashlib.sha256(
        canonical_definition.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"{DATASET_VERSION_PREFIX}{digest}"
    )


def build_dataset_version_identity(
    dataset: UnifiedFeatureDataset,
    feature_identity: FeatureVersionIdentity,
    dataset_version: str,
) -> DatasetVersionIdentity:
    """
    Build a deterministic identity for a concrete dataset.

    The dataset identity depends on the declared dataset version,
    target date, feature version, feature identity, ordered feature
    names, feature values, feature types, and feature sources.
    """

    definition = _build_dataset_definition(
        dataset=dataset,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
    )

    canonical_definition = _canonicalize_definition(
        definition
    )

    identity = _calculate_identity(
        canonical_definition
    )

    return DatasetVersionIdentity(
        dataset_version=dataset_version,
        identity=identity,
        algorithm=DATASET_VERSION_ALGORITHM,
        canonical_definition=canonical_definition,
        feature_version=dataset.feature_version,
        feature_identity=feature_identity.identity,
    )


def validate_dataset_version_identity(
    identity: DatasetVersionIdentity,
) -> None:
    """Validate a dataset-version identity."""

    if not isinstance(
        identity,
        DatasetVersionIdentity,
    ):
        raise TypeError(
            "identity must be a DatasetVersionIdentity instance."
        )

    _validate_dataset_version_label(
        identity.dataset_version
    )

    if identity.algorithm != DATASET_VERSION_ALGORITHM:
        raise ValueError(
            f"Unsupported dataset version algorithm: "
            f"{identity.algorithm}"
        )

    if not isinstance(
        identity.canonical_definition,
        str,
    ) or not identity.canonical_definition:
        raise ValueError(
            "canonical_definition must be a non-empty string."
        )

    if not isinstance(
        identity.feature_version,
        str,
    ) or not identity.feature_version.strip():
        raise ValueError(
            "feature_version must be a non-empty string."
        )

    if not isinstance(
        identity.feature_identity,
        str,
    ) or not identity.feature_identity.strip():
        raise ValueError(
            "feature_identity must be a non-empty string."
        )

    expected_identity = _calculate_identity(
        identity.canonical_definition
    )

    if identity.identity != expected_identity:
        raise ValueError(
            "Dataset version identity does not match "
            "its canonical definition."
        )


def build_dataset_version_reference(
    identity: DatasetVersionIdentity,
) -> DatasetVersionReference:
    """
    Convert a validated dataset identity into the Phase 17
    versioning-contract reference.
    """

    validate_dataset_version_identity(
        identity
    )

    reference = build_dataset_version_reference_contract(
        dataset_version=identity.dataset_version,
        identity=identity.identity,
        algorithm=identity.algorithm,
        feature_version=identity.feature_version,
        feature_identity=identity.feature_identity,
    )

    validate_dataset_version_reference(
        reference
    )

    return reference


def validate_dataset_version_reference_against_identity(
    reference: DatasetVersionReference,
    identity: DatasetVersionIdentity,
) -> None:
    """Validate a dataset reference against its concrete identity."""

    validate_dataset_version_reference(
        reference
    )

    validate_dataset_version_identity(
        identity
    )

    if (
        reference.dataset_version
        != identity.dataset_version
    ):
        raise ValueError(
            "Dataset version reference does not match "
            "the DatasetVersionIdentity dataset version."
        )

    if reference.identity != identity.identity:
        raise ValueError(
            "Dataset version reference does not match "
            "the DatasetVersionIdentity identity."
        )

    if reference.algorithm != identity.algorithm:
        raise ValueError(
            "Dataset version reference does not match "
            "the DatasetVersionIdentity algorithm."
        )

    if (
        reference.feature_version
        != identity.feature_version
    ):
        raise ValueError(
            "Dataset version reference does not match "
            "the DatasetVersionIdentity feature version."
        )

    if (
        reference.feature_identity
        != identity.feature_identity
    ):
        raise ValueError(
            "Dataset version reference does not match "
            "the DatasetVersionIdentity feature identity."
        )


def is_dataset_version_reproducible(
    first: DatasetVersionIdentity,
    second: DatasetVersionIdentity,
) -> bool:
    """Return whether two dataset identities are exactly reproducible."""

    validate_dataset_version_identity(
        first
    )

    validate_dataset_version_identity(
        second
    )

    return (
        first.dataset_version
        == second.dataset_version
        and first.identity
        == second.identity
        and first.algorithm
        == second.algorithm
        and first.feature_version
        == second.feature_version
        and first.feature_identity
        == second.feature_identity
    )


def get_dataset_version_identity(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the deterministic dataset identity."""

    validate_dataset_version_identity(
        identity
    )

    return identity.identity


def get_dataset_version_label(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the declared dataset version."""

    validate_dataset_version_identity(
        identity
    )

    return identity.dataset_version


def get_dataset_version_algorithm(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the dataset identity algorithm."""

    validate_dataset_version_identity(
        identity
    )

    return identity.algorithm


def get_dataset_feature_version(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the feature version associated with the dataset."""

    validate_dataset_version_identity(
        identity
    )

    return identity.feature_version


def get_dataset_feature_identity(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the feature identity associated with the dataset."""

    validate_dataset_version_identity(
        identity
    )

    return identity.feature_identity


def get_canonical_dataset_definition(
    identity: DatasetVersionIdentity,
) -> str:
    """Return the canonical dataset definition."""

    validate_dataset_version_identity(
        identity
    )

    return identity.canonical_definition


def is_dataset_version_identity_valid(
    identity: DatasetVersionIdentity,
) -> bool:
    """Return whether a dataset identity is valid."""

    try:
        validate_dataset_version_identity(
            identity
        )
    except (TypeError, ValueError):
        return False

    return True


__all__ = [
    "DATASET_VERSION_ALGORITHM",
    "DATASET_VERSION_PREFIX",
    "DatasetVersionIdentity",
    "build_dataset_version_identity",
    "validate_dataset_version_identity",
    "build_dataset_version_reference",
    "validate_dataset_version_reference_against_identity",
    "is_dataset_version_reproducible",
    "get_dataset_version_identity",
    "get_dataset_version_label",
    "get_dataset_version_algorithm",
    "get_dataset_feature_version",
    "get_dataset_feature_identity",
    "get_canonical_dataset_definition",
    "is_dataset_version_identity_valid",
]