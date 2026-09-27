from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Mapping

from features.feature_dataset_contract import (
    FeatureDatasetContract,
    validate_feature_dataset_contract,
)
from features.feature_schema import FeatureSchema
from features.feature_validator import VALID
from features.feature_versioning import (
    FeatureVersionIdentity,
    validate_feature_version_identity,
)


@dataclass(frozen=True)
class FeatureArtifact:
    """Immutable reproducible representation of a feature dataset."""

    target_date: date
    feature_version: str
    feature_names: tuple[str, ...]
    feature_values: Mapping[
        str,
        int | float | str | bool | None,
    ]
    schemas: tuple[FeatureSchema, ...]
    version_identity: FeatureVersionIdentity
    validation_status: str
    leakage_status: str

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)

    @property
    def schema_count(self) -> int:
        return len(self.schemas)


def _validate_feature_names(
    feature_names: tuple[str, ...],
) -> None:
    if not isinstance(
        feature_names,
        tuple,
    ):
        raise TypeError(
            "feature_names must be a tuple."
        )

    for feature_name in feature_names:
        if (
            not isinstance(
                feature_name,
                str,
            )
            or not feature_name
        ):
            raise ValueError(
                "Every feature name must be a non-empty string."
            )

    if len(feature_names) != len(
        set(feature_names)
    ):
        raise ValueError(
            "Feature names must be unique."
        )


def _validate_feature_values(
    feature_names: tuple[str, ...],
    feature_values: Mapping[
        str,
        int | float | str | bool | None,
    ],
) -> None:
    if not isinstance(
        feature_values,
        Mapping,
    ):
        raise TypeError(
            "feature_values must be a mapping."
        )

    value_names = tuple(
        feature_values.keys()
    )

    if set(value_names) != set(
        feature_names
    ):
        raise ValueError(
            "Feature values must contain exactly "
            "the declared feature names."
        )

    for feature_name, value in (
        feature_values.items()
    ):
        if not isinstance(
            feature_name,
            str,
        ):
            raise TypeError(
                "Feature value keys must be strings."
            )

        if value is None:
            continue

        if isinstance(
            value,
            (
                bool,
                int,
                float,
                str,
            ),
        ):
            continue

        raise TypeError(
            "Feature values must contain only "
            "supported scalar types or None."
        )


def _validate_schema_alignment(
    feature_names: tuple[str, ...],
    schemas: tuple[FeatureSchema, ...],
) -> None:
    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple."
        )

    schema_names = tuple(
        schema.feature_name
        for schema in schemas
    )

    if schema_names != feature_names:
        raise ValueError(
            "Schema names and feature names must "
            "match exactly and preserve order."
        )


def build_feature_artifact(
    contract: FeatureDatasetContract,
) -> FeatureArtifact:
    """
    Build a reproducible artifact from a validated dataset contract.

    The contract must already represent a structurally valid,
    leakage-free feature dataset.
    """

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    contract_validation = (
        validate_feature_dataset_contract(
            contract
        )
    )

    if not contract_validation.is_valid:
        raise ValueError(
            "Feature dataset contract is invalid."
        )

    if contract.validation_status != VALID:
        raise ValueError(
            "Feature dataset validation status must be VALID."
        )

    if contract.leakage_status != "CLEAN":
        raise ValueError(
            "Feature dataset leakage status must be CLEAN."
        )

    validate_feature_version_identity(
        contract.version_identity
    )

    feature_values = {
        feature_name: None
        for feature_name in contract.feature_names
    }

    return FeatureArtifact(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_names=contract.feature_names,
        feature_values=feature_values,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=contract.validation_status,
        leakage_status=contract.leakage_status,
    )


def build_feature_artifact_from_contract_and_values(
    contract: FeatureDatasetContract,
    feature_values: Mapping[
        str,
        int | float | str | bool | None,
    ],
) -> FeatureArtifact:
    """
    Build an artifact using the actual feature values associated
    with an already validated contract.
    """

    if not isinstance(
        contract,
        FeatureDatasetContract,
    ):
        raise TypeError(
            "contract must be a FeatureDatasetContract instance."
        )

    contract_validation = (
        validate_feature_dataset_contract(
            contract
        )
    )

    if not contract_validation.is_valid:
        raise ValueError(
            "Feature dataset contract is invalid."
        )

    validate_feature_version_identity(
        contract.version_identity
    )

    _validate_feature_names(
        contract.feature_names
    )

    _validate_feature_values(
        contract.feature_names,
        feature_values,
    )

    _validate_schema_alignment(
        contract.feature_names,
        contract.schemas,
    )

    return FeatureArtifact(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_names=contract.feature_names,
        feature_values=dict(
            feature_values
        ),
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=contract.validation_status,
        leakage_status=contract.leakage_status,
    )


def get_artifact_feature_count(
    artifact: FeatureArtifact,
) -> int:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return artifact.feature_count


def get_artifact_schema_count(
    artifact: FeatureArtifact,
) -> int:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return artifact.schema_count


def get_artifact_feature_names(
    artifact: FeatureArtifact,
) -> tuple[str, ...]:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return artifact.feature_names


def get_artifact_feature_values(
    artifact: FeatureArtifact,
) -> Mapping[
    str,
    int | float | str | bool | None,
]:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return dict(
        artifact.feature_values
    )


def get_artifact_version_identity(
    artifact: FeatureArtifact,
) -> FeatureVersionIdentity:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return artifact.version_identity


def serialize_feature_artifact(
    artifact: FeatureArtifact,
) -> str:
    """Serialize the artifact into deterministic JSON."""

    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    payload = {
        "target_date": artifact.target_date.isoformat(),
        "feature_version": artifact.feature_version,
        "feature_names": list(
            artifact.feature_names
        ),
        "feature_values": {
            name: artifact.feature_values[name]
            for name in artifact.feature_names
        },
        "schemas": [
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
            for schema in artifact.schemas
        ],
        "version_identity": {
            "feature_version": (
                artifact.version_identity.feature_version
            ),
            "identity": (
                artifact.version_identity.identity
            ),
            "algorithm": (
                artifact.version_identity.algorithm
            ),
            "canonical_definition": (
                artifact.version_identity.canonical_definition
            ),
        },
        "validation_status": (
            artifact.validation_status
        ),
        "leakage_status": (
            artifact.leakage_status
        ),
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def is_feature_artifact_valid(
    artifact: FeatureArtifact,
) -> bool:
    if not isinstance(
        artifact,
        FeatureArtifact,
    ):
        raise TypeError(
            "artifact must be a FeatureArtifact instance."
        )

    return (
        artifact.validation_status == VALID
        and artifact.leakage_status == "CLEAN"
    )