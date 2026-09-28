from datetime import date

import pytest

from features.feature_schema import (
    FeatureSchema,
)
from features.feature_versioning import (
    FeatureVersionIdentity,
)
from features.sequence_dataset_artifact import (
    SEQUENCE_ARTIFACT_ALGORITHM,
    SEQUENCE_ARTIFACT_PREFIX,
    SequenceArtifactIntegrity,
    SequenceDatasetArtifact,
    build_sequence_dataset_artifact,
    calculate_sequence_artifact_integrity,
    calculate_sequence_dataset_fingerprint,
    get_sequence_artifact_fingerprint,
    get_sequence_artifact_integrity_algorithm,
    get_sequence_artifact_integrity_digest,
    get_sequence_artifact_integrity_identity,
    is_sequence_artifact_integrity_valid,
    serialize_sequence_dataset_artifact,
    validate_sequence_artifact_integrity,
    validate_sequence_dataset_artifact,
)


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


def _schema(
    name: str,
    version: str = "sequence-v1",
) -> FeatureSchema:
    return FeatureSchema(
        feature_name=name,
        feature_version=version,
        feature_type="sequence",
        source="sequence_dataset",
        position=None,
        window=3,
        lag=None,
        description="Sequence dataset feature.",
        availability_rule=(
            "Uses only observations strictly before "
            "the target date."
        ),
        data_type="integer",
    )


def _version_identity() -> FeatureVersionIdentity:
    canonical = (
        '{"feature_version":"sequence-v1",'
        '"schema":"sequence-dataset-v1"}'
    )

    import hashlib

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return FeatureVersionIdentity(
        feature_version="sequence-v1",
        identity=f"feature-{digest}",
        algorithm="sha256",
        canonical_definition=canonical,
    )


def _build_integration_result():
    from features.historical_data_loader import (
        HistoricalFeatureObservation,
    )
    from features.sequence_dataset import (
        SequenceDatasetConfig,
    )
    from features.sequence_dataset_integration import (
        build_sequence_dataset_integration,
    )
    from features.sequence_temporal_split import (
        TemporalSplitConfig,
    )

    observations = tuple(
        HistoricalFeatureObservation(
            result_id=index,
            market_id=1,
            result_date=date.fromisoformat(
                f"2026-01-0{index}"
            ),
            positions=(
                index,
                index + 1,
                index + 2,
                index + 3,
                index + 4,
                index + 5,
                index + 6,
                index + 7,
            ),
        )
        for index in range(1, 7)
    )

    config = SequenceDatasetConfig(
        sequence_length=3,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=("sequence_target_col1",),
        allow_incomplete_sequences=False,
    )

    split_config = TemporalSplitConfig(
        split_date=date(
            2026,
            1,
            5,
        )
    )

    return build_sequence_dataset_integration(
        observations=observations,
        sequence_config=config,
        temporal_split_config=split_config,
    )


def _build_artifact():
    result = _build_integration_result()

    schemas = (
        _schema(
            "sequence_target_col1"
        ),
    )

    return build_sequence_dataset_artifact(
        result=result,
        schemas=schemas,
        feature_version_identity=(
            _version_identity()
        ),
    )


def test_returns_expected_type():
    artifact = _build_artifact()

    assert isinstance(
        artifact,
        SequenceDatasetArtifact,
    )


def test_sample_count_is_preserved():
    artifact = _build_artifact()

    assert (
        artifact.sample_count
        == len(
            artifact.sequence_dataset.samples
        )
    )


def test_schema_count_is_preserved():
    artifact = _build_artifact()

    assert artifact.schema_count == 1


def test_schema_order_matches_feature_order():
    artifact = _build_artifact()

    assert tuple(
        schema.feature_name
        for schema in artifact.schemas
    ) == artifact.feature_names


def test_artifact_is_leakage_free():
    artifact = _build_artifact()

    assert artifact.is_leakage_free is True


def test_temporal_split_date_is_preserved():
    artifact = _build_artifact()

    assert artifact.temporal_split_date == date(
        2026,
        1,
        5,
    )


def test_fingerprint_is_not_empty():
    artifact = _build_artifact()

    assert artifact.fingerprint
    assert isinstance(
        artifact.fingerprint,
        str,
    )


def test_fingerprint_has_sha256_length():
    artifact = _build_artifact()

    assert len(
        artifact.fingerprint
    ) == 64


def test_fingerprint_is_deterministic():
    artifact_a = _build_artifact()
    artifact_b = _build_artifact()

    assert (
        artifact_a.fingerprint
        == artifact_b.fingerprint
    )


def test_serialization_is_deterministic():
    artifact = _build_artifact()

    serialized_a = (
        serialize_sequence_dataset_artifact(
            artifact
        )
    )

    serialized_b = (
        serialize_sequence_dataset_artifact(
            artifact
        )
    )

    assert serialized_a == serialized_b


def test_calculated_fingerprint_matches_stored():
    artifact = _build_artifact()

    assert (
        calculate_sequence_dataset_fingerprint(
            artifact
        )
        == artifact.fingerprint
    )


def test_artifact_validation_passes():
    artifact = _build_artifact()

    validate_sequence_dataset_artifact(
        artifact
    )


def test_integrity_returns_expected_type():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert isinstance(
        integrity,
        SequenceArtifactIntegrity,
    )


def test_integrity_uses_sha256():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        integrity.algorithm
        == SEQUENCE_ARTIFACT_ALGORITHM
    )


def test_integrity_digest_matches_fingerprint():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        integrity.digest
        == artifact.fingerprint
    )


def test_integrity_identity_has_expected_prefix():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert integrity.identity.startswith(
        SEQUENCE_ARTIFACT_PREFIX
    )


def test_integrity_identity_contains_digest():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert integrity.identity == (
        f"{SEQUENCE_ARTIFACT_PREFIX}"
        f"{integrity.digest}"
    )


def test_integrity_validation_passes():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    validate_sequence_artifact_integrity(
        artifact,
        integrity,
    )

    assert (
        is_sequence_artifact_integrity_valid(
            artifact,
            integrity,
        )
        is True
    )


def test_integrity_is_reproducible():
    artifact = _build_artifact()

    integrity_a = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    integrity_b = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert integrity_a == integrity_b


def test_fingerprint_getter():
    artifact = _build_artifact()

    assert (
        get_sequence_artifact_fingerprint(
            artifact
        )
        == artifact.fingerprint
    )


def test_integrity_digest_getter():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        get_sequence_artifact_integrity_digest(
            integrity
        )
        == integrity.digest
    )


def test_integrity_identity_getter():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        get_sequence_artifact_integrity_identity(
            integrity
        )
        == integrity.identity
    )


def test_integrity_algorithm_getter():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        get_sequence_artifact_integrity_algorithm(
            integrity
        )
        == integrity.algorithm
    )


def test_invalid_artifact_type_is_rejected():
    with pytest.raises(TypeError):
        calculate_sequence_artifact_integrity(
            "invalid"
        )


def test_invalid_integrity_type_is_rejected():
    artifact = _build_artifact()

    with pytest.raises(TypeError):
        validate_sequence_artifact_integrity(
            artifact,
            "invalid",
        )


def test_invalid_fingerprint_is_rejected():
    artifact = _build_artifact()

    invalid_artifact = SequenceDatasetArtifact(
        sequence_length=artifact.sequence_length,
        input_positions=artifact.input_positions,
        target_positions=artifact.target_positions,
        feature_names=artifact.feature_names,
        schemas=artifact.schemas,
        sequence_dataset=artifact.sequence_dataset,
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
        fingerprint="0" * 64,
    )

    with pytest.raises(ValueError):
        validate_sequence_dataset_artifact(
            invalid_artifact
        )


def test_tampered_integrity_digest_is_rejected():
    artifact = _build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    tampered = SequenceArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest="0" * 64,
        identity=integrity.identity,
    )

    with pytest.raises(ValueError):
        validate_sequence_artifact_integrity(
            artifact,
            tampered,
        )