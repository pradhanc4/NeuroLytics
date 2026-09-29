from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.feature_schema import (
    FeatureSchema,
    validate_feature_schema,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
)
from features.versioning_contract import (
    FeatureVersionReference,
    build_feature_version_reference,
    validate_feature_version_reference,
)

VERSION_ALGORITHM = "sha256"
VERSION_PREFIX = "feature-"


@dataclass(frozen=True)
class FeatureVersionIdentity:
    """Deterministic identity of a feature definition."""

    feature_version: str
    identity: str
    algorithm: str
    canonical_definition: str


def _build_config_definition(
    config: FeatureConfig,
) -> dict:
    """Build a deterministic serializable config definition."""

    validate_feature_config(config)

    return {
        "feature_version": config.feature_version,
        "positions": list(config.positions),
        "lag_windows": list(config.lag_windows),
        "rolling_windows": list(
            config.rolling_windows
        ),
        "frequency_enabled": config.frequency_enabled,
        "frequency_window": config.frequency_window,
        "recency_enabled": config.recency_enabled,
        "recency_lookback": config.recency_lookback,
        "position_features_enabled": (
            config.position_features_enabled
        ),
    }


def _build_schema_definition(
    schemas: tuple[FeatureSchema, ...],
) -> list[dict]:
    """Build a deterministic serializable schema definition."""

    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple of FeatureSchema objects."
        )

    definitions: list[dict] = []

    for schema in schemas:
        validate_feature_schema(schema)

        definitions.append(
            {
                "feature_name": schema.feature_name,
                "feature_version": schema.feature_version,
                "feature_type": schema.feature_type,
                "source": schema.source,
                "position": schema.position,
                "window": schema.window,
                "lag": schema.lag,
                "description": schema.description,
                "availability_rule": (
                    schema.availability_rule
                ),
                "data_type": schema.data_type,
            }
        )

    return definitions


def _canonicalize_definition(
    definition: dict,
) -> str:
    """Convert a definition into deterministic JSON."""

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
    """Calculate deterministic SHA-256 identity."""

    digest = hashlib.sha256(
        canonical_definition.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"{VERSION_PREFIX}{digest}"
    )


def build_feature_version_identity(
    config: FeatureConfig,
    schemas: tuple[FeatureSchema, ...],
) -> FeatureVersionIdentity:
    """
    Build a deterministic identity from feature configuration
    and feature schema definitions.
    """

    validate_feature_config(
        config
    )

    schema_definition = _build_schema_definition(
        schemas
    )

    definition = {
        "config": _build_config_definition(
            config
        ),
        "schemas": schema_definition,
    }

    canonical_definition = (
        _canonicalize_definition(
            definition
        )
    )

    identity = _calculate_identity(
        canonical_definition
    )

    return FeatureVersionIdentity(
        feature_version=config.feature_version,
        identity=identity,
        algorithm=VERSION_ALGORITHM,
        canonical_definition=canonical_definition,
    )


def build_feature_version_from_dataset(
    dataset: UnifiedFeatureDataset,
    schemas: tuple[FeatureSchema, ...],
) -> FeatureVersionIdentity:
    """
    Build a deterministic identity for an existing dataset.

    The dataset's declared feature version is preserved.
    """

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple of FeatureSchema objects."
        )

    for schema in schemas:
        validate_feature_schema(
            schema
        )

    definition = {
        "feature_version": dataset.feature_version,
        "feature_names": list(
            dataset.feature_names
        ),
        "schemas": _build_schema_definition(
            schemas
        ),
    }

    canonical_definition = (
        _canonicalize_definition(
            definition
        )
    )

    identity = _calculate_identity(
        canonical_definition
    )

    return FeatureVersionIdentity(
        feature_version=dataset.feature_version,
        identity=identity,
        algorithm=VERSION_ALGORITHM,
        canonical_definition=canonical_definition,
    )


def validate_feature_version_identity(
    identity: FeatureVersionIdentity,
) -> None:
    """Validate a feature version identity object."""

    if not isinstance(
        identity,
        FeatureVersionIdentity,
    ):
        raise TypeError(
            "identity must be a FeatureVersionIdentity instance."
        )

    if not isinstance(
        identity.feature_version,
        str,
    ) or not identity.feature_version.strip():
        raise ValueError(
            "feature_version must be a non-empty string."
        )

    if identity.algorithm != VERSION_ALGORITHM:
        raise ValueError(
            f"Unsupported version algorithm: "
            f"{identity.algorithm}"
        )

    if not isinstance(
        identity.canonical_definition,
        str,
    ) or not identity.canonical_definition:
        raise ValueError(
            "canonical_definition must be a non-empty string."
        )

    expected_identity = _calculate_identity(
        identity.canonical_definition
    )

    if identity.identity != expected_identity:
        raise ValueError(
            "Feature version identity does not "
            "match its canonical definition."
        )

def build_feature_version_reference_from_identity(
    identity: FeatureVersionIdentity,
) -> FeatureVersionReference:
    """
    Build a versioning-contract reference from an existing
    FeatureVersionIdentity.

    The existing FeatureVersionIdentity remains the authoritative
    source of the feature version, identity, and algorithm.
    """

    validate_feature_version_identity(
        identity
    )

    return build_feature_version_reference(
        feature_version=identity.feature_version,
        identity=identity.identity,
        algorithm=identity.algorithm,
    )


def validate_feature_version_reference_against_identity(
    reference: FeatureVersionReference,
    identity: FeatureVersionIdentity,
) -> None:
    """
    Validate that a FeatureVersionReference belongs to a
    FeatureVersionIdentity.

    This does not recalculate or replace the existing feature
    identity. It validates consistency between the two contracts.
    """

    validate_feature_version_reference(
        reference
    )

    validate_feature_version_identity(
        identity
    )

    if reference.feature_version != identity.feature_version:
        raise ValueError(
            "Feature version reference does not match "
            "the FeatureVersionIdentity feature version."
        )

    if reference.identity != identity.identity:
        raise ValueError(
            "Feature version reference does not match "
            "the FeatureVersionIdentity identity."
        )

    if reference.algorithm != identity.algorithm:
        raise ValueError(
            "Feature version reference does not match "
            "the FeatureVersionIdentity algorithm."
        )


def is_feature_version_reference_consistent(
    reference: FeatureVersionReference,
    identity: FeatureVersionIdentity,
) -> bool:
    """
    Return whether a feature-version reference is consistent
    with a FeatureVersionIdentity.
    """

    try:
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )
    except (TypeError, ValueError):
        return False

    return True

def is_feature_version_reproducible(
    first: FeatureVersionIdentity,
    second: FeatureVersionIdentity,
) -> bool:
    """Check whether two identities are exactly reproducible."""

    validate_feature_version_identity(
        first
    )

    validate_feature_version_identity(
        second
    )

    return (
        first.identity
        == second.identity
        and first.feature_version
        == second.feature_version
        and first.algorithm
        == second.algorithm
    )


def get_feature_version_identity(
    identity: FeatureVersionIdentity,
) -> str:
    """Return deterministic identity string."""

    validate_feature_version_identity(
        identity
    )

    return identity.identity


def get_feature_version_label(
    identity: FeatureVersionIdentity,
) -> str:
    """Return declared feature version label."""

    validate_feature_version_identity(
        identity
    )

    return identity.feature_version


def get_canonical_feature_definition(
    identity: FeatureVersionIdentity,
) -> str:
    """Return canonical serialized definition."""

    validate_feature_version_identity(
        identity
    )

    return identity.canonical_definition


def get_version_algorithm(
    identity: FeatureVersionIdentity,
) -> str:
    """Return versioning algorithm."""

    validate_feature_version_identity(
        identity
    )

    return identity.algorithm