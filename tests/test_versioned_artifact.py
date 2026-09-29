from __future__ import annotations

from datetime import date

import pytest

from database.services import HistoricalResultService

from features.artifact_integrity import (
    ArtifactIntegrity,
    calculate_artifact_integrity,
)

from features.dataset_versioning import (
    build_dataset_version_identity,
    build_dataset_version_reference,
)

from features.feature_artifact import (
    FeatureArtifact,
    build_feature_artifact_from_contract_and_values,
)

from features.feature_config import FeatureConfig

from features.feature_dataset_contract import (
    build_feature_dataset_contract,
)

from features.feature_pipeline import (
    build_feature_pipeline,
)

from features.feature_versioning import (
    build_feature_version_reference_from_identity,
)

from features.versioned_artifact import (
    VersionedFeatureArtifact,
    build_versioned_feature_artifact,
    build_versioned_feature_artifact_with_integrity,
    get_versioned_artifact,
    get_versioned_artifact_integrity,
    get_versioned_artifact_integrity_identity,
    get_versioned_dataset_reference,
    get_versioned_dataset_version,
    get_versioned_feature_reference,
    get_versioned_feature_version,
    is_versioned_feature_artifact_valid,
    validate_versioned_feature_artifact,
)


def make_config(
    **overrides,
):
    values = {
        "feature_version": "v1",
        "positions": (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
        "lag_windows": (1, 2, 3),
        "rolling_windows": (3, 5, 7),
        "frequency_enabled": True,
        "frequency_window": 5,
        "recency_enabled": True,
        "recency_lookback": 10,
        "position_features_enabled": True,
    }

    values.update(
        overrides
    )

    return FeatureConfig(
        **values
    )


def seed_market(
    db,
):
    service = HistoricalResultService(
        db
    )

    market = service.create_market(
        "TEST_VERSIONED_ARTIFACT_MARKET"
    )

    service.create_historical_result(
        market=market,
        result_date=date(
            2026,
            1,
            1,
        ),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(
            2026,
            1,
            2,
        ),
        open_result="234",
        jodi_result="56",
        close_result="789",
    )

    service.create_historical_result(
        market=market,
        result_date=date(
            2026,
            1,
            3,
        ),
        open_result="345",
        jodi_result="67",
        close_result="890",
    )

    return service, market


def build_artifact_and_references(
    db,
    feature_version="v1",
    dataset_version="dataset-v1",
):
    service, market = seed_market(
        db
    )

    config = make_config(
        feature_version=feature_version
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(
            2026,
            1,
            5,
        ),
        config=config,
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            dict(
                pipeline.dataset.values
            ),
        )
    )

    # The FeatureArtifact's embedded version identity
    # is the authoritative feature-version identity.
    feature_identity = artifact.version_identity

    dataset_identity = build_dataset_version_identity(
        dataset=pipeline.dataset,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
    )

    feature_reference = (
        build_feature_version_reference_from_identity(
            feature_identity
        )
    )

    dataset_reference = (
        build_dataset_version_reference(
            dataset_identity
        )
    )

    return (
        artifact,
        feature_reference,
        dataset_reference,
    )


def test_build_returns_expected_type(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert isinstance(
        result,
        VersionedFeatureArtifact,
    )


def test_underlying_artifact_is_preserved(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert result.artifact == artifact


def test_feature_reference_is_preserved(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        result.feature_reference
        == feature_reference
    )


def test_dataset_reference_is_preserved(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        result.dataset_reference
        == dataset_reference
    )


def test_integrity_is_calculated_from_existing_artifact_system(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    expected = calculate_artifact_integrity(
        artifact
    )

    assert result.integrity == expected


def test_valid_versioned_artifact_passes_validation(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    validate_versioned_feature_artifact(
        result
    )

    assert (
        is_versioned_feature_artifact_valid(
            result
        )
        is True
    )


def test_feature_version_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_feature_version(
            result
        )
        == feature_reference.feature_version
    )


def test_dataset_version_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_dataset_version(
            result
        )
        == dataset_reference.dataset_version
    )


def test_artifact_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_artifact(result)
        == artifact
    )


def test_integrity_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_artifact_integrity(
            result
        )
        == result.integrity
    )


def test_feature_reference_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_feature_reference(
            result
        )
        == feature_reference
    )


def test_dataset_reference_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_dataset_reference(
            result
        )
        == dataset_reference
    )


def test_integrity_identity_getter(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert (
        get_versioned_artifact_integrity_identity(
            result
        )
        == result.integrity.identity
    )


def test_supplied_integrity_is_accepted(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    result = (
        build_versioned_feature_artifact_with_integrity(
            artifact,
            feature_reference,
            dataset_reference,
            integrity,
        )
    )

    assert result.integrity == integrity


def test_invalid_integrity_is_rejected(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    invalid_integrity = ArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest="0" * 64,
        identity=integrity.identity,
    )

    with pytest.raises(
        ValueError
    ):
        build_versioned_feature_artifact_with_integrity(
            artifact,
            feature_reference,
            dataset_reference,
            invalid_integrity,
        )


def test_feature_reference_mismatch_is_rejected(
    db,
):
    (
        artifact,
        _,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    wrong_feature_reference = type(
        build_feature_version_reference_from_identity(
            artifact.version_identity
        )
    )(
        feature_version=(
            artifact.version_identity.feature_version
        ),
        identity="feature-tampered",
        algorithm=(
            artifact.version_identity.algorithm
        ),
    )

    with pytest.raises(
        ValueError
    ):
        build_versioned_feature_artifact(
            artifact,
            wrong_feature_reference,
            dataset_reference,
        )


def test_dataset_feature_version_mismatch_is_rejected(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    wrong_dataset_reference = type(
        dataset_reference
    )(
        dataset_version=(
            dataset_reference.dataset_version
        ),
        identity=dataset_reference.identity,
        algorithm=dataset_reference.algorithm,
        feature_version="v2",
        feature_identity=(
            dataset_reference.feature_identity
        ),
    )

    with pytest.raises(
        ValueError
    ):
        build_versioned_feature_artifact(
            artifact,
            feature_reference,
            wrong_dataset_reference,
        )


def test_dataset_feature_identity_mismatch_is_rejected(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    wrong_dataset_reference = type(
        dataset_reference
    )(
        dataset_version=(
            dataset_reference.dataset_version
        ),
        identity=dataset_reference.identity,
        algorithm=dataset_reference.algorithm,
        feature_version=(
            dataset_reference.feature_version
        ),
        feature_identity="feature-tampered",
    )

    with pytest.raises(
        ValueError
    ):
        build_versioned_feature_artifact(
            artifact,
            feature_reference,
            wrong_dataset_reference,
        )


def test_artifact_identity_mismatch_is_rejected(
    db,
):
    (
        artifact,
        _,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    wrong_reference = type(
        build_feature_version_reference_from_identity(
            artifact.version_identity
        )
    )(
        feature_version=(
            artifact.version_identity.feature_version
        ),
        identity="feature-tampered",
        algorithm=(
            artifact.version_identity.algorithm
        ),
    )

    with pytest.raises(
        ValueError
    ):
        build_versioned_feature_artifact(
            artifact,
            wrong_reference,
            dataset_reference,
        )


def test_invalid_artifact_type_is_rejected():
    with pytest.raises(
        TypeError
    ):
        build_versioned_feature_artifact(
            "invalid",
            "invalid",
            "invalid",
        )


def test_invalid_feature_reference_type_is_rejected(
    db,
):
    (
        artifact,
        _,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    with pytest.raises(
        TypeError
    ):
        build_versioned_feature_artifact(
            artifact,
            "invalid",
            dataset_reference,
        )


def test_invalid_dataset_reference_type_is_rejected(
    db,
):
    (
        artifact,
        feature_reference,
        _,
    ) = build_artifact_and_references(
        db
    )

    with pytest.raises(
        TypeError
    ):
        build_versioned_feature_artifact(
            artifact,
            feature_reference,
            "invalid",
        )


def test_invalid_versioned_artifact_type_is_rejected():
    with pytest.raises(
        TypeError
    ):
        validate_versioned_feature_artifact(
            "invalid"
        )


def test_invalid_versioned_artifact_returns_false():
    assert (
        is_versioned_feature_artifact_valid(
            "invalid"
        )
        is False
    )


def test_versioned_artifact_is_immutable(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    result = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    with pytest.raises(
        AttributeError
    ):
        result.dataset_reference = (
            dataset_reference
        )


def test_versioned_artifact_is_reproducible(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    first = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    second = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    assert first == second


def test_changed_artifact_fails_integrity(
    db,
):
    (
        artifact,
        feature_reference,
        dataset_reference,
    ) = build_artifact_and_references(
        db
    )

    versioned = build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )

    changed_values = dict(
        artifact.feature_values
    )

    first_name = artifact.feature_names[0]

    changed_values[first_name] = 999

    changed_artifact = FeatureArtifact(
        target_date=artifact.target_date,
        feature_version=artifact.feature_version,
        feature_names=artifact.feature_names,
        feature_values=changed_values,
        schemas=artifact.schemas,
        version_identity=artifact.version_identity,
        validation_status=artifact.validation_status,
        leakage_status=artifact.leakage_status,
    )

    changed_versioned = VersionedFeatureArtifact(
        artifact=changed_artifact,
        integrity=versioned.integrity,
        feature_reference=(
            versioned.feature_reference
        ),
        dataset_reference=(
            versioned.dataset_reference
        ),
    )

    assert (
        is_versioned_feature_artifact_valid(
            changed_versioned
        )
        is False
    )