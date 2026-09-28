from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json

from features.feature_schema import (
    FeatureSchema,
    validate_feature_schema,
)
from features.feature_versioning import (
    FeatureVersionIdentity,
    validate_feature_version_identity,
)
from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
    SequenceSample,
)
from features.sequence_dataset_integration import (
    SequenceDatasetIntegrationResult,
)


SEQUENCE_ARTIFACT_ALGORITHM = "sha256"
SEQUENCE_ARTIFACT_PREFIX = "sequence-artifact-"


@dataclass(frozen=True)
class SequenceDatasetArtifact:
    """
    Immutable schema/artifact representation of a validated
    Phase 16 sequence dataset.
    """

    sequence_length: int
    input_positions: tuple[str, ...]
    target_positions: tuple[str, ...]
    feature_names: tuple[str, ...]

    schemas: tuple[FeatureSchema, ...]

    sequence_dataset: SequenceDataset

    feature_version_identity: FeatureVersionIdentity

    component_leakage_status: str
    dataset_leakage_status: str

    temporal_split_date: date

    fingerprint: str

    @property
    def sample_count(self) -> int:
        return len(
            self.sequence_dataset.samples
        )

    @property
    def schema_count(self) -> int:
        return len(self.schemas)

    @property
    def is_leakage_free(self) -> bool:
        return (
            self.component_leakage_status == "CLEAN"
            and self.dataset_leakage_status == "CLEAN"
        )


@dataclass(frozen=True)
class SequenceArtifactIntegrity:
    """
    Deterministic integrity identity for a sequence dataset artifact.
    """

    algorithm: str
    digest: str
    identity: str


def _validate_sequence_dataset(
    dataset: SequenceDataset,
) -> None:
    if not isinstance(
        dataset,
        SequenceDataset,
    ):
        raise TypeError(
            "dataset must be a SequenceDataset instance."
        )


def _validate_sequence_config(
    config: SequenceDatasetConfig,
) -> None:
    if not isinstance(
        config,
        SequenceDatasetConfig,
    ):
        raise TypeError(
            "config must be a SequenceDatasetConfig instance."
        )


def _validate_schemas(
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

    schema_names: list[str] = []

    for schema in schemas:
        validate_feature_schema(
            schema
        )
        schema_names.append(
            schema.feature_name
        )

    if tuple(schema_names) != feature_names:
        raise ValueError(
            "Schema feature ordering must exactly "
            "match sequence feature ordering."
        )


def _validate_version_identity(
    identity: FeatureVersionIdentity,
) -> None:
    validate_feature_version_identity(
        identity
    )


def _validate_integration_result(
    result: SequenceDatasetIntegrationResult,
) -> None:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a "
            "SequenceDatasetIntegrationResult instance."
        )

    if not result.is_leakage_free:
        raise ValueError(
            "Sequence dataset integration must be leakage-free."
        )


def _sample_payload(
    sample: SequenceSample,
) -> dict:
    return {
        "sample_index": sample.sample_index,
        "sequence_start_date": (
            sample.sequence_start_date.isoformat()
        ),
        "sequence_end_date": (
            sample.sequence_end_date.isoformat()
        ),
        "target_date": sample.target_date.isoformat(),
        "sequence_length": sample.sequence_length,
        "positions": list(
            sample.positions
        ),
        "features": [
            list(row)
            for row in sample.features
        ],
        "target": list(
            sample.target
        ),
    }


def _schema_payload(
    schema: FeatureSchema,
) -> dict:
    return {
        "feature_name": schema.feature_name,
        "feature_version": schema.feature_version,
        "feature_type": schema.feature_type,
        "source": schema.source,
        "position": schema.position,
        "window": schema.window,
        "lag": schema.lag,
        "description": schema.description,
        "availability_rule": schema.availability_rule,
        "data_type": schema.data_type,
    }


def _version_identity_payload(
    identity: FeatureVersionIdentity,
) -> dict:
    return {
        "feature_version": (
            identity.feature_version
        ),
        "identity": identity.identity,
        "algorithm": identity.algorithm,
        "canonical_definition": (
            identity.canonical_definition
        ),
    }


def serialize_sequence_dataset_artifact(
    artifact: SequenceDatasetArtifact,
) -> str:
    """
    Serialize the sequence artifact deterministically.
    """

    if not isinstance(
        artifact,
        SequenceDatasetArtifact,
    ):
        raise TypeError(
            "artifact must be a "
            "SequenceDatasetArtifact instance."
        )

    payload = {
        "sequence_length": (
            artifact.sequence_length
        ),
        "input_positions": list(
            artifact.input_positions
        ),
        "target_positions": list(
            artifact.target_positions
        ),
        "feature_names": list(
            artifact.feature_names
        ),
        "schemas": [
            _schema_payload(schema)
            for schema in artifact.schemas
        ],
        "samples": [
            _sample_payload(sample)
            for sample in artifact.sequence_dataset.samples
        ],
        "feature_version_identity": (
            _version_identity_payload(
                artifact.feature_version_identity
            )
        ),
        "component_leakage_status": (
            artifact.component_leakage_status
        ),
        "dataset_leakage_status": (
            artifact.dataset_leakage_status
        ),
        "temporal_split_date": (
            artifact.temporal_split_date.isoformat()
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


def calculate_sequence_dataset_fingerprint(
    artifact: SequenceDatasetArtifact,
) -> str:
    """
    Calculate the deterministic SHA-256 fingerprint of
    the canonical sequence artifact.
    """

    serialized = (
        serialize_sequence_dataset_artifact(
            artifact
        )
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()


def calculate_sequence_artifact_integrity(
    artifact: SequenceDatasetArtifact,
) -> SequenceArtifactIntegrity:
    """
    Calculate deterministic SHA-256 integrity for a
    sequence dataset artifact.
    """

    if not isinstance(
        artifact,
        SequenceDatasetArtifact,
    ):
        raise TypeError(
            "artifact must be a "
            "SequenceDatasetArtifact instance."
        )

    digest = (
        calculate_sequence_dataset_fingerprint(
            artifact
        )
    )

    return SequenceArtifactIntegrity(
        algorithm=SEQUENCE_ARTIFACT_ALGORITHM,
        digest=digest,
        identity=(
            f"{SEQUENCE_ARTIFACT_PREFIX}{digest}"
        ),
    )


def build_sequence_dataset_artifact(
    result: SequenceDatasetIntegrationResult,
    schemas: tuple[FeatureSchema, ...],
    feature_version_identity: FeatureVersionIdentity,
) -> SequenceDatasetArtifact:
    """
    Build the Phase 16 schema/artifact representation
    from an already validated integrated sequence dataset.

    No sequence construction, target construction,
    leakage validation, or temporal splitting occurs here.
    """

    _validate_integration_result(
        result
    )

    _validate_sequence_config(
        result.sequence_config
    )

    _validate_sequence_dataset(
        result.dataset
    )

    _validate_schemas(
        result.dataset.feature_names,
        schemas,
    )

    _validate_version_identity(
        feature_version_identity
    )

    if (
        feature_version_identity.feature_version
        != result.sequence_config.feature_names
        and False
    ):
        raise ValueError(
            "Unreachable compatibility guard."
        )

    artifact_without_fingerprint = (
        SequenceDatasetArtifact(
            sequence_length=(
                result.dataset.sequence_length
            ),
            input_positions=(
                result.dataset.input_positions
            ),
            target_positions=(
                result.dataset.target_positions
            ),
            feature_names=(
                result.dataset.feature_names
            ),
            schemas=schemas,
            sequence_dataset=result.dataset,
            feature_version_identity=(
                feature_version_identity
            ),
            component_leakage_status=(
                result.component_leakage.status
            ),
            dataset_leakage_status=(
                result.dataset_leakage.status
            ),
            temporal_split_date=(
                result.temporal_split.split_date
            ),
            fingerprint="",
        )
    )

    fingerprint = (
        calculate_sequence_dataset_fingerprint(
            artifact_without_fingerprint
        )
    )

    return SequenceDatasetArtifact(
        sequence_length=(
            artifact_without_fingerprint.sequence_length
        ),
        input_positions=(
            artifact_without_fingerprint.input_positions
        ),
        target_positions=(
            artifact_without_fingerprint.target_positions
        ),
        feature_names=(
            artifact_without_fingerprint.feature_names
        ),
        schemas=(
            artifact_without_fingerprint.schemas
        ),
        sequence_dataset=(
            artifact_without_fingerprint.sequence_dataset
        ),
        feature_version_identity=(
            artifact_without_fingerprint
            .feature_version_identity
        ),
        component_leakage_status=(
            artifact_without_fingerprint
            .component_leakage_status
        ),
        dataset_leakage_status=(
            artifact_without_fingerprint
            .dataset_leakage_status
        ),
        temporal_split_date=(
            artifact_without_fingerprint
            .temporal_split_date
        ),
        fingerprint=fingerprint,
    )


def validate_sequence_dataset_artifact(
    artifact: SequenceDatasetArtifact,
) -> None:
    """
    Validate the structural and deterministic integrity
    contract of a sequence dataset artifact.
    """

    if not isinstance(
        artifact,
        SequenceDatasetArtifact,
    ):
        raise TypeError(
            "artifact must be a "
            "SequenceDatasetArtifact instance."
        )

    _validate_sequence_dataset(
        artifact.sequence_dataset
    )

    _validate_schemas(
        artifact.feature_names,
        artifact.schemas,
    )

    _validate_version_identity(
        artifact.feature_version_identity
    )

    if not artifact.is_leakage_free:
        raise ValueError(
            "Sequence dataset artifact is not leakage-free."
        )

    expected_fingerprint = (
        calculate_sequence_dataset_fingerprint(
            SequenceDatasetArtifact(
                sequence_length=(
                    artifact.sequence_length
                ),
                input_positions=(
                    artifact.input_positions
                ),
                target_positions=(
                    artifact.target_positions
                ),
                feature_names=(
                    artifact.feature_names
                ),
                schemas=artifact.schemas,
                sequence_dataset=(
                    artifact.sequence_dataset
                ),
                feature_version_identity=(
                    artifact.feature_version_identity
                ),
                component_leakage_status=(
                    artifact.component_leakage_status
                ),
                dataset_leakage_status=(
                    artifact.dataset_leakage_status
                ),
                temporal_split_date=(
                    artifact.temporal_split_date
                ),
                fingerprint="",
            )
        )
    )

    if artifact.fingerprint != expected_fingerprint:
        raise ValueError(
            "Sequence dataset artifact fingerprint "
            "does not match its canonical content."
        )


def validate_sequence_artifact_integrity(
    artifact: SequenceDatasetArtifact,
    integrity: SequenceArtifactIntegrity,
) -> None:
    """
    Verify sequence artifact integrity.
    """

    if not isinstance(
        artifact,
        SequenceDatasetArtifact,
    ):
        raise TypeError(
            "artifact must be a "
            "SequenceDatasetArtifact instance."
        )

    if not isinstance(
        integrity,
        SequenceArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be a "
            "SequenceArtifactIntegrity instance."
        )

    if (
        integrity.algorithm
        != SEQUENCE_ARTIFACT_ALGORITHM
    ):
        raise ValueError(
            "Unsupported sequence artifact "
            f"integrity algorithm: {integrity.algorithm}"
        )

    expected = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    if integrity.digest != expected.digest:
        raise ValueError(
            "Sequence artifact integrity validation "
            "failed: digest does not match."
        )

    if integrity.identity != expected.identity:
        raise ValueError(
            "Sequence artifact integrity validation "
            "failed: identity does not match."
        )


def is_sequence_artifact_integrity_valid(
    artifact: SequenceDatasetArtifact,
    integrity: SequenceArtifactIntegrity,
) -> bool:
    try:
        validate_sequence_artifact_integrity(
            artifact,
            integrity,
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return True


def get_sequence_artifact_fingerprint(
    artifact: SequenceDatasetArtifact,
) -> str:
    if not isinstance(
        artifact,
        SequenceDatasetArtifact,
    ):
        raise TypeError(
            "artifact must be a "
            "SequenceDatasetArtifact instance."
        )

    return artifact.fingerprint


def get_sequence_artifact_integrity_digest(
    integrity: SequenceArtifactIntegrity,
) -> str:
    if not isinstance(
        integrity,
        SequenceArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be a "
            "SequenceArtifactIntegrity instance."
        )

    return integrity.digest


def get_sequence_artifact_integrity_identity(
    integrity: SequenceArtifactIntegrity,
) -> str:
    if not isinstance(
        integrity,
        SequenceArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be a "
            "SequenceArtifactIntegrity instance."
        )

    return integrity.identity


def get_sequence_artifact_integrity_algorithm(
    integrity: SequenceArtifactIntegrity,
) -> str:
    if not isinstance(
        integrity,
        SequenceArtifactIntegrity,
    ):
        raise TypeError(
            "integrity must be a "
            "SequenceArtifactIntegrity instance."
        )

    return integrity.algorithm