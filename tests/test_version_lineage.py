from __future__ import annotations

from datetime import date

import pytest

from features.dataset_versioning import (
    build_dataset_version_identity,
    build_dataset_version_reference,
)
from features.feature_config import FeatureConfig
from features.feature_schema import FeatureSchema
from features.feature_versioning import (
    build_feature_version_identity,
    build_feature_version_reference_from_identity,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)
from features.version_lineage import (
    INVALID,
    VALID,
    build_version_lineage,
    build_version_lineage_from_references,
    compare_version_lineage,
    get_lineage_dataset_identity,
    get_lineage_dataset_version,
    get_lineage_feature_identity,
    get_lineage_feature_version,
    get_lineage_type,
    is_version_lineage_reproducible,
    is_version_lineage_valid,
    serialize_version_lineage,
    validate_complete_version_lineage,
    validate_lineage_against_dataset_identity,
    validate_lineage_against_feature_identity,
    validate_version_lineage,
    validate_version_lineage_from_references,
    validate_version_lineage_result,
)
from features.versioning_contract import VersionLineageReference


def _build_feature_identity(
    feature_version: str = "v1",
):
    config = FeatureConfig(
        feature_version=feature_version,
        positions=(
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
    )

    schemas = (
        FeatureSchema(
            feature_name="col1_lag_1",
            feature_version=feature_version,
            feature_type="lag",
            source="historical",
            position="col1",
            window=None,
            lag=1,
            description="Column 1 lag 1",
            availability_rule="available_at_prediction_time",
            data_type="float",
        ),
        FeatureSchema(
            feature_name="col2_lag_1",
            feature_version=feature_version,
            feature_type="lag",
            source="historical",
            position="col2",
            window=None,
            lag=1,
            description="Column 2 lag 1",
            availability_rule="available_at_prediction_time",
            data_type="float",
        ),
    )

    return build_feature_version_identity(
        config=config,
        schemas=schemas,
    )


def _build_dataset(
    feature_identity,
    target_date: date = date(2026, 8, 20),
):
    records = (
        UnifiedFeatureRecord(
            feature_name="col1_lag_1",
            value=1,
            feature_type="lag",
            source="historical",
        ),
        UnifiedFeatureRecord(
            feature_name="col2_lag_1",
            value=2,
            feature_type="lag",
            source="historical",
        ),
    )

    return UnifiedFeatureDataset(
        target_date=target_date,
        feature_version=feature_identity.feature_version,
        records=records,
    )


def _build_identities(
    feature_version: str = "v1",
    dataset_version: str = "dataset-v1",
):
    feature_identity = _build_feature_identity(
        feature_version=feature_version,
    )

    dataset = _build_dataset(
        feature_identity=feature_identity,
    )

    dataset_identity = build_dataset_version_identity(
        dataset=dataset,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
    )

    return feature_identity, dataset_identity


def test_build_version_lineage():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity=feature_identity,
        dataset_identity=dataset_identity,
    )

    assert lineage.lineage_type == "feature_to_dataset"
    assert lineage.feature_version == feature_identity.feature_version
    assert lineage.feature_identity == feature_identity.identity
    assert lineage.dataset_version == dataset_identity.dataset_version
    assert lineage.dataset_identity == dataset_identity.identity


def test_validate_version_lineage():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    validate_version_lineage(lineage)


def test_validate_against_feature_identity():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    validate_lineage_against_feature_identity(
        lineage,
        feature_identity,
    )


def test_validate_against_dataset_identity():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    validate_lineage_against_dataset_identity(
        lineage,
        dataset_identity,
    )


def test_complete_lineage_validation():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    validate_complete_version_lineage(
        lineage,
        feature_identity,
        dataset_identity,
    )


def test_complete_lineage_rejects_wrong_feature_identity():
    feature_identity, dataset_identity = _build_identities()

    wrong_feature_identity = _build_feature_identity(
        feature_version="v2",
    )

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    with pytest.raises(ValueError):
        validate_complete_version_lineage(
            lineage,
            wrong_feature_identity,
            dataset_identity,
        )


def test_complete_lineage_rejects_wrong_dataset_identity():
    feature_identity, dataset_identity = _build_identities()

    _, wrong_dataset_identity = _build_identities(
        dataset_version="dataset-v2",
    )

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    with pytest.raises(ValueError):
        validate_complete_version_lineage(
            lineage,
            feature_identity,
            wrong_dataset_identity,
        )


def test_build_lineage_rejects_feature_dataset_mismatch():
    _, dataset_identity = _build_identities()

    wrong_feature_identity = _build_feature_identity(
        feature_version="v2",
    )

    with pytest.raises(ValueError):
        build_version_lineage(
            wrong_feature_identity,
            dataset_identity,
        )


def test_build_lineage_from_references():
    feature_identity, dataset_identity = _build_identities()

    feature_reference = build_feature_version_reference_from_identity(
        feature_identity
    )

    dataset_reference = build_dataset_version_reference(
        dataset_identity
    )

    lineage = build_version_lineage_from_references(
        feature_reference,
        dataset_reference,
    )

    assert lineage.feature_version == feature_reference.feature_version
    assert lineage.feature_identity == feature_reference.identity
    assert lineage.dataset_version == dataset_reference.dataset_version
    assert lineage.dataset_identity == dataset_reference.identity


def test_validate_lineage_from_references():
    feature_identity, dataset_identity = _build_identities()

    feature_reference = build_feature_version_reference_from_identity(
        feature_identity
    )

    dataset_reference = build_dataset_version_reference(
        dataset_identity
    )

    lineage = build_version_lineage_from_references(
        feature_reference,
        dataset_reference,
    )

    validate_version_lineage_from_references(
        lineage,
        feature_reference,
        dataset_reference,
    )


def test_compare_identical_lineage():
    feature_identity, dataset_identity = _build_identities()

    first = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    second = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    assert compare_version_lineage(
        first,
        second,
    )


def test_compare_changed_lineage():
    feature_identity, dataset_identity = _build_identities()

    first = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    second = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version=feature_identity.feature_version,
        feature_identity=feature_identity.identity,
        dataset_version="dataset-v2",
        dataset_identity=dataset_identity.identity,
    )

    assert not compare_version_lineage(
        first,
        second,
    )


def test_lineage_reproducibility():
    feature_identity, dataset_identity = _build_identities()

    first = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    second = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    assert is_version_lineage_reproducible(
        first,
        second,
    )


def test_lineage_serialization_is_deterministic():
    feature_identity, dataset_identity = _build_identities()

    first = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    second = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    assert (
        serialize_version_lineage(first)
        == serialize_version_lineage(second)
    )


def test_validation_result_valid():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    result = validate_version_lineage_result(
        lineage,
        feature_identity,
        dataset_identity,
    )

    assert result.status == VALID
    assert result.is_valid
    assert not result.is_invalid
    assert result.issue_count == 0


def test_validation_result_invalid():
    feature_identity, dataset_identity = _build_identities()

    lineage = VersionLineageReference(
        lineage_type="feature_to_dataset",
        feature_version="wrong",
        feature_identity=feature_identity.identity,
        dataset_version=dataset_identity.dataset_version,
        dataset_identity=dataset_identity.identity,
    )

    result = validate_version_lineage_result(
        lineage,
        feature_identity,
        dataset_identity,
    )

    assert result.status == INVALID
    assert result.is_invalid
    assert not result.is_valid
    assert result.issue_count == 1


def test_is_version_lineage_valid():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    assert is_version_lineage_valid(
        lineage,
        feature_identity,
        dataset_identity,
    )


def test_lineage_getters():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    assert (
        get_lineage_type(lineage)
        == "feature_to_dataset"
    )

    assert (
        get_lineage_feature_version(lineage)
        == feature_identity.feature_version
    )

    assert (
        get_lineage_feature_identity(lineage)
        == feature_identity.identity
    )

    assert (
        get_lineage_dataset_version(lineage)
        == dataset_identity.dataset_version
    )

    assert (
        get_lineage_dataset_identity(lineage)
        == dataset_identity.identity
    )


def test_invalid_lineage_type_rejected():
    lineage = VersionLineageReference(
        lineage_type="invalid",
        feature_version="v1",
        feature_identity="feature-id",
        dataset_version="dataset-v1",
        dataset_identity="dataset-id",
    )

    with pytest.raises(ValueError):
        validate_version_lineage(lineage)


def test_lineage_is_immutable():
    feature_identity, dataset_identity = _build_identities()

    lineage = build_version_lineage(
        feature_identity,
        dataset_identity,
    )

    with pytest.raises(AttributeError):
        lineage.dataset_version = "dataset-v2"