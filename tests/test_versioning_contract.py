from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from features.versioning_contract import (
    LINEAGE_REFERENCE_TYPES,
    VERSION_CONTRACT_ALGORITHM,
    DatasetVersionReference,
    FeatureVersionReference,
    VersionLineageReference,
    build_dataset_version_reference,
    build_feature_version_reference,
    build_version_lineage_reference,
    get_dataset_feature_identity,
    get_dataset_feature_version,
    get_dataset_identity,
    get_dataset_version,
    get_feature_identity,
    get_feature_version,
    get_lineage_type,
    is_dataset_version_reference_valid,
    is_feature_version_reference_valid,
    is_version_lineage_reference_valid,
    serialize_dataset_version_reference,
    serialize_feature_version_reference,
    serialize_version_lineage_reference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
    validate_version_lineage_reference,
)


FEATURE_VERSION = "feature-v15"
FEATURE_IDENTITY = "feature-abc123"

DATASET_VERSION = "dataset-v1"
DATASET_IDENTITY = "dataset-def456"


def test_contract_algorithm_is_defined():
    assert VERSION_CONTRACT_ALGORITHM == "sha256"


def test_lineage_reference_types_are_defined():
    assert LINEAGE_REFERENCE_TYPES == (
        "feature_to_dataset",
    )


def test_feature_version_reference_is_immutable():
    reference = FeatureVersionReference(
        feature_version=FEATURE_VERSION,
        identity=FEATURE_IDENTITY,
        algorithm="sha256",
    )

    with pytest.raises(FrozenInstanceError):
        reference.feature_version = "feature-v16"


def test_dataset_version_reference_is_immutable():
    reference = DatasetVersionReference(
        dataset_version=DATASET_VERSION,
        identity=DATASET_IDENTITY,
        algorithm="sha256",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
    )

    with pytest.raises(FrozenInstanceError):
        reference.dataset_version = "dataset-v2"


def test_lineage_reference_is_immutable():
    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    with pytest.raises(FrozenInstanceError):
        reference.feature_version = "feature-v16"


def test_feature_reference_builder():
    reference = build_feature_version_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        "sha256",
    )

    assert isinstance(
        reference,
        FeatureVersionReference,
    )

    assert reference.feature_version == FEATURE_VERSION
    assert reference.identity == FEATURE_IDENTITY
    assert reference.algorithm == "sha256"


def test_dataset_reference_builder():
    reference = build_dataset_version_reference(
        DATASET_VERSION,
        DATASET_IDENTITY,
        "sha256",
        FEATURE_VERSION,
        FEATURE_IDENTITY,
    )

    assert isinstance(
        reference,
        DatasetVersionReference,
    )

    assert reference.dataset_version == DATASET_VERSION
    assert reference.identity == DATASET_IDENTITY
    assert reference.feature_version == FEATURE_VERSION
    assert reference.feature_identity == FEATURE_IDENTITY


def test_lineage_reference_builder():
    reference = build_version_lineage_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        DATASET_VERSION,
        DATASET_IDENTITY,
    )

    assert isinstance(
        reference,
        VersionLineageReference,
    )

    assert reference.lineage_type == "feature_to_dataset"
    assert reference.feature_version == FEATURE_VERSION
    assert reference.feature_identity == FEATURE_IDENTITY
    assert reference.dataset_version == DATASET_VERSION
    assert reference.dataset_identity == DATASET_IDENTITY


def test_feature_reference_validation_accepts_valid_reference():
    reference = FeatureVersionReference(
        feature_version=FEATURE_VERSION,
        identity=FEATURE_IDENTITY,
        algorithm="sha256",
    )

    validate_feature_version_reference(
        reference
    )


def test_dataset_reference_validation_accepts_valid_reference():
    reference = DatasetVersionReference(
        dataset_version=DATASET_VERSION,
        identity=DATASET_IDENTITY,
        algorithm="sha256",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
    )

    validate_dataset_version_reference(
        reference
    )


def test_lineage_reference_validation_accepts_valid_reference():
    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    validate_version_lineage_reference(
        reference
    )


def test_invalid_feature_reference_type():
    with pytest.raises(TypeError):
        validate_feature_version_reference(
            object()
        )


def test_invalid_dataset_reference_type():
    with pytest.raises(TypeError):
        validate_dataset_version_reference(
            object()
        )


def test_invalid_lineage_reference_type():
    with pytest.raises(TypeError):
        validate_version_lineage_reference(
            object()
        )


@pytest.mark.parametrize(
    "field",
    (
        "feature_version",
        "identity",
        "algorithm",
    ),
)
def test_empty_feature_reference_fields_are_rejected(field):
    values = {
        "feature_version": FEATURE_VERSION,
        "identity": FEATURE_IDENTITY,
        "algorithm": "sha256",
    }

    values[field] = ""

    reference = FeatureVersionReference(
        **values
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference(
            reference
        )


@pytest.mark.parametrize(
    "field",
    (
        "dataset_version",
        "identity",
        "algorithm",
        "feature_version",
        "feature_identity",
    ),
)
def test_empty_dataset_reference_fields_are_rejected(field):
    values = {
        "dataset_version": DATASET_VERSION,
        "identity": DATASET_IDENTITY,
        "algorithm": "sha256",
        "feature_version": FEATURE_VERSION,
        "feature_identity": FEATURE_IDENTITY,
    }

    values[field] = ""

    reference = DatasetVersionReference(
        **values
    )

    with pytest.raises(ValueError):
        validate_dataset_version_reference(
            reference
        )


def test_invalid_lineage_type_is_rejected():
    reference = VersionLineageReference(
        lineage_type="unsupported",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    with pytest.raises(ValueError, match="Unsupported lineage type"):
        validate_version_lineage_reference(
            reference
        )


def test_empty_lineage_fields_are_rejected():
    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version="",
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    with pytest.raises(ValueError):
        validate_version_lineage_reference(
            reference
        )


def test_feature_reference_serialization_is_deterministic():
    reference = FeatureVersionReference(
        feature_version=FEATURE_VERSION,
        identity=FEATURE_IDENTITY,
        algorithm="sha256",
    )

    first = serialize_feature_version_reference(
        reference
    )

    second = serialize_feature_version_reference(
        reference
    )

    assert first == second


def test_dataset_reference_serialization_is_deterministic():
    reference = DatasetVersionReference(
        dataset_version=DATASET_VERSION,
        identity=DATASET_IDENTITY,
        algorithm="sha256",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
    )

    first = serialize_dataset_version_reference(
        reference
    )

    second = serialize_dataset_version_reference(
        reference
    )

    assert first == second


def test_lineage_serialization_is_deterministic():
    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    first = serialize_version_lineage_reference(
        reference
    )

    second = serialize_version_lineage_reference(
        reference
    )

    assert first == second


def test_feature_serialization_is_canonical():
    reference = FeatureVersionReference(
        feature_version=FEATURE_VERSION,
        identity=FEATURE_IDENTITY,
        algorithm="sha256",
    )

    serialized = serialize_feature_version_reference(
        reference
    )

    assert serialized == (
        '{"algorithm":"sha256",'
        '"feature_version":"feature-v15",'
        '"identity":"feature-abc123",'
        '"reference_type":"feature"}'
    )


def test_dataset_serialization_is_canonical():
    reference = DatasetVersionReference(
        dataset_version=DATASET_VERSION,
        identity=DATASET_IDENTITY,
        algorithm="sha256",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
    )

    serialized = serialize_dataset_version_reference(
        reference
    )

    assert serialized == (
        '{"algorithm":"sha256",'
        '"dataset_version":"dataset-v1",'
        '"feature_identity":"feature-abc123",'
        '"feature_version":"feature-v15",'
        '"identity":"dataset-def456",'
        '"reference_type":"dataset"}'
    )


def test_lineage_serialization_is_canonical():
    reference = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
        dataset_version=DATASET_VERSION,
        dataset_identity=DATASET_IDENTITY,
    )

    serialized = serialize_version_lineage_reference(
        reference
    )

    assert serialized == (
        '{"dataset_identity":"dataset-def456",'
        '"dataset_version":"dataset-v1",'
        '"feature_identity":"feature-abc123",'
        '"feature_version":"feature-v15",'
        '"lineage_type":"feature_to_dataset"}'
    )


def test_feature_getters():
    reference = build_feature_version_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        "sha256",
    )

    assert get_feature_version(reference) == FEATURE_VERSION
    assert get_feature_identity(reference) == FEATURE_IDENTITY


def test_dataset_getters():
    reference = build_dataset_version_reference(
        DATASET_VERSION,
        DATASET_IDENTITY,
        "sha256",
        FEATURE_VERSION,
        FEATURE_IDENTITY,
    )

    assert get_dataset_version(reference) == DATASET_VERSION
    assert get_dataset_identity(reference) == DATASET_IDENTITY
    assert get_dataset_feature_version(reference) == FEATURE_VERSION
    assert get_dataset_feature_identity(reference) == FEATURE_IDENTITY


def test_lineage_getter():
    reference = build_version_lineage_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        DATASET_VERSION,
        DATASET_IDENTITY,
    )

    assert get_lineage_type(reference) == "feature_to_dataset"


def test_feature_validity_helper():
    reference = build_feature_version_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        "sha256",
    )

    assert is_feature_version_reference_valid(
        reference
    ) is True

    assert is_feature_version_reference_valid(
        object()
    ) is False


def test_dataset_validity_helper():
    reference = build_dataset_version_reference(
        DATASET_VERSION,
        DATASET_IDENTITY,
        "sha256",
        FEATURE_VERSION,
        FEATURE_IDENTITY,
    )

    assert is_dataset_version_reference_valid(
        reference
    ) is True

    assert is_dataset_version_reference_valid(
        object()
    ) is False


def test_lineage_validity_helper():
    reference = build_version_lineage_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        DATASET_VERSION,
        DATASET_IDENTITY,
    )

    assert is_version_lineage_reference_valid(
        reference
    ) is True

    assert is_version_lineage_reference_valid(
        object()
    ) is False


def test_whitespace_only_feature_version_is_rejected():
    reference = FeatureVersionReference(
        feature_version="   ",
        identity=FEATURE_IDENTITY,
        algorithm="sha256",
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference(
            reference
        )


def test_whitespace_only_dataset_version_is_rejected():
    reference = DatasetVersionReference(
        dataset_version="   ",
        identity=DATASET_IDENTITY,
        algorithm="sha256",
        feature_version=FEATURE_VERSION,
        feature_identity=FEATURE_IDENTITY,
    )

    with pytest.raises(ValueError):
        validate_dataset_version_reference(
            reference
        )


def test_whitespace_only_identity_is_rejected():
    reference = FeatureVersionReference(
        feature_version=FEATURE_VERSION,
        identity="   ",
        algorithm="sha256",
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference(
            reference
        )


def test_builder_returns_valid_contract():
    feature = build_feature_version_reference(
        FEATURE_VERSION,
        FEATURE_IDENTITY,
        "sha256",
    )

    dataset = build_dataset_version_reference(
        DATASET_VERSION,
        DATASET_IDENTITY,
        "sha256",
        feature.feature_version,
        feature.identity,
    )

    lineage = build_version_lineage_reference(
        feature.feature_version,
        feature.identity,
        dataset.dataset_version,
        dataset.identity,
    )

    assert is_feature_version_reference_valid(feature)
    assert is_dataset_version_reference_valid(dataset)
    assert is_version_lineage_reference_valid(lineage)