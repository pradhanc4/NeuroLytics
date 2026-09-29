from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from database.models import Market
from database.services import HistoricalResultService

from features.artifact_integrity import (
    ArtifactIntegrity,
    calculate_artifact_integrity,
)

from features.dataset_versioning import (
    DatasetVersionIdentity,
    build_dataset_version_identity,
    build_dataset_version_reference,
)

from features.feature_artifact import (
    FeatureArtifact,
    build_feature_artifact_from_contract_and_values,
)

from features.feature_dataset_contract import (
    build_feature_dataset_contract,
)

from features.feature_pipeline import (
    build_feature_pipeline,
)

from features.feature_versioning import (
    build_feature_version_identity,
    build_feature_version_reference_from_identity,
)

from features.version_compatibility import (
    check_feature_version_compatibility,
)

from features.version_validation import (
   VALID,
    INVALID,
    ARTIFACT_INTEGRITY_INVALID,
    DATASET_IDENTITY_INVALID,
    DATASET_REFERENCE_INVALID,
    DATASET_REFERENCE_MISMATCH,
    FEATURE_IDENTITY_INVALID,
    FEATURE_REFERENCE_INVALID,
    FEATURE_REFERENCE_MISMATCH,
    VERSIONED_ARTIFACT_INVALID,
    VERSION_COMPATIBILITY_INVALID,
    VersionValidationResult,
    get_version_validation_issue_count,
    get_version_validation_issues,
    get_version_validation_status,
    is_version_validation_valid,
    validate_artifact_version_integrity,
    validate_version_compatibility,
    validate_version_identities,
    validate_version_references,
    validate_versioned_artifact,
    validate_versioned_feature_artifact_integrity,
)

from features.versioned_artifact import (
    VersionedFeatureArtifact,
    build_versioned_feature_artifact,
)


from features.feature_config import FeatureConfig


def make_config(
    feature_version: str = "v1",
) -> FeatureConfig:
    return FeatureConfig(
        feature_version=feature_version,
    )


def seed_market(db):
    service = HistoricalResultService(db)

    market_name = (
        "TEST_VERSION_VALIDATION_MARKET"
    )

    market = db.scalar(
        select(Market).where(
            Market.name == market_name
        )
    )

    if market is not None:
        return service, market

    market = service.create_market(
        market_name
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 2),
        open_result="234",
        jodi_result="56",
        close_result="789",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 3),
        open_result="345",
        jodi_result="67",
        close_result="890",
    )

    return service, market


def build_pipeline(
    db,
    feature_version: str = "v1",
):
    service, market = seed_market(db)

    return build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version
        ),
    )


def build_artifact(
    db,
    feature_version: str = "v1",
):
    pipeline = build_pipeline(
        db,
        feature_version,
    )

    contract = (
        build_feature_dataset_contract(
            pipeline
        )
    )

    values = dict(
        pipeline.dataset.values
    )

    return (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        ),
        pipeline,
    )


def build_versioned_artifact(
    db,
):
    artifact, pipeline = build_artifact(
        db
    )

    feature_identity = (
        artifact.version_identity
    )

    feature_reference = (
        build_feature_version_reference_from_identity(
            feature_identity
        )
    )

    dataset_identity = (
        build_dataset_version_identity(
            dataset=pipeline.dataset,
            feature_identity=feature_identity,
            dataset_version="dataset-v1",
        )
    )

    dataset_reference = (
        build_dataset_version_reference(
            dataset_identity
        )
    )

    versioned = (
        build_versioned_feature_artifact(
            artifact=artifact,
            feature_reference=feature_reference,
            dataset_reference=dataset_reference,
        )
    )

    return (
        versioned,
        feature_identity,
        dataset_identity,
    )


def test_valid_version_validation_result():
    result = VersionValidationResult(
        status=VALID,
        issues=(),
    )

    assert result.is_valid is True
    assert result.is_invalid is False
    assert result.issue_count == 0


def test_invalid_version_validation_result():
    result = VersionValidationResult(
        status=INVALID,
        issues=(),
    )

    assert result.is_valid is False
    assert result.is_invalid is True
    assert result.issue_count == 0


def test_feature_identity_validation_passes(
    db,
):
    artifact, _ = build_artifact(
        db
    )

    dataset_identity = build_dataset_version_identity(
        dataset=build_pipeline(db).dataset,
        feature_identity=artifact.version_identity,
        dataset_version="dataset-v1",
    )

    result = validate_version_identities(
        artifact.version_identity,
        dataset_identity,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_invalid_feature_identity_is_detected(
    db,
):
    artifact, _ = build_artifact(
        db
    )

    invalid_feature_identity = (
        type(artifact.version_identity)(
            feature_version=(
                artifact.version_identity.feature_version
            ),
            identity="feature-invalid",
            algorithm=(
                artifact.version_identity.algorithm
            ),
            canonical_definition=(
                artifact.version_identity.canonical_definition
            ),
        )
    )

    dataset_identity = build_dataset_version_identity(
        dataset=build_pipeline(db).dataset,
        feature_identity=artifact.version_identity,
        dataset_version="dataset-v1",
    )

    result = validate_version_identities(
        invalid_feature_identity,
        dataset_identity,
    )

    assert result.is_valid is False

    assert any(
        issue.code == FEATURE_IDENTITY_INVALID
        for issue in result.issues
    )


def test_invalid_dataset_identity_is_detected(
    db,
):
    artifact, pipeline = build_artifact(
        db
    )

    dataset_identity = (
        build_dataset_version_identity(
            dataset=pipeline.dataset,
            feature_identity=artifact.version_identity,
            dataset_version="dataset-v1",
        )
    )

    invalid_dataset_identity = (
        DatasetVersionIdentity(
            dataset_version=(
                dataset_identity.dataset_version
            ),
            identity="dataset-invalid",
            algorithm=(
                dataset_identity.algorithm
            ),
            canonical_definition=(
                dataset_identity.canonical_definition
            ),
            feature_version=(
                dataset_identity.feature_version
            ),
            feature_identity=(
                dataset_identity.feature_identity
            ),
        )
    )

    result = validate_version_identities(
        artifact.version_identity,
        invalid_dataset_identity,
    )

    assert result.is_valid is False

    assert any(
        issue.code == DATASET_IDENTITY_INVALID
        for issue in result.issues
    )


def test_valid_references_pass_validation(
    db,
):
    versioned, feature_identity, dataset_identity = (
        build_versioned_artifact(db)
    )

    result = validate_version_references(
        versioned.feature_reference,
        versioned.dataset_reference,
        feature_identity,
        dataset_identity,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_invalid_feature_reference_is_detected(
    db,
):
    versioned, _, dataset_identity = (
        build_versioned_artifact(db)
    )

    invalid_feature_reference = (
        type(versioned.feature_reference)(
            feature_version=(
                versioned.feature_reference.feature_version
            ),
            identity="feature-invalid",
            algorithm=(
                versioned.feature_reference.algorithm
            ),
        )
    )

    result = validate_version_references(
        invalid_feature_reference,
        versioned.dataset_reference,
        versioned.artifact.version_identity,
        dataset_identity,
    )

    assert result.is_valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        FEATURE_REFERENCE_INVALID in codes
        or FEATURE_REFERENCE_MISMATCH in codes
    )


def test_invalid_dataset_reference_is_detected(
    db,
):
    versioned, feature_identity, dataset_identity = (
        build_versioned_artifact(db)
    )

    invalid_dataset_reference = (
        type(versioned.dataset_reference)(
            dataset_version=(
                versioned.dataset_reference.dataset_version
            ),
            identity="dataset-invalid",
            algorithm=(
                versioned.dataset_reference.algorithm
            ),
            feature_version=(
                versioned.dataset_reference.feature_version
            ),
            feature_identity=(
                versioned.dataset_reference.feature_identity
            ),
        )
    )

    result = validate_version_references(
        versioned.feature_reference,
        invalid_dataset_reference,
        feature_identity,
        dataset_identity,
    )

    assert result.is_valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert DATASET_REFERENCE_MISMATCH in codes


def test_valid_version_compatibility_passes(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    result = validate_version_compatibility(
        versioned.feature_reference,
        versioned.dataset_reference,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_incompatible_versions_are_detected(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    incompatible_dataset_reference = (
        type(versioned.dataset_reference)(
            dataset_version=(
                versioned.dataset_reference.dataset_version
            ),
            identity=(
                versioned.dataset_reference.identity
            ),
            algorithm=(
                versioned.dataset_reference.algorithm
            ),
            feature_version="v2",
            feature_identity=(
                versioned.dataset_reference.feature_identity
            ),
        )
    )

    result = validate_version_compatibility(
        versioned.feature_reference,
        incompatible_dataset_reference,
    )

    assert result.is_valid is False

    assert any(
        issue.code == VERSION_COMPATIBILITY_INVALID
        for issue in result.issues
    )


def test_valid_artifact_integrity_passes(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    result = validate_artifact_version_integrity(
        versioned.artifact,
        versioned.integrity,
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_corrupted_artifact_integrity_is_detected(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    invalid_integrity = ArtifactIntegrity(
        algorithm=(
            versioned.integrity.algorithm
        ),
        digest="0" * 64,
        identity=(
            versioned.integrity.identity
        ),
    )

    result = validate_artifact_version_integrity(
        versioned.artifact,
        invalid_integrity,
    )

    assert result.is_valid is False

    assert any(
        issue.code == ARTIFACT_INTEGRITY_INVALID
        for issue in result.issues
    )


def test_valid_versioned_artifact_passes(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    result = validate_versioned_artifact(
        versioned
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_invalid_versioned_artifact_is_detected(
    db,
):
    versioned, _, _ = (
        build_versioned_artifact(db)
    )

    invalid_integrity = ArtifactIntegrity(
        algorithm=(
            versioned.integrity.algorithm
        ),
        digest="0" * 64,
        identity=(
            versioned.integrity.identity
        ),
    )

    tampered = VersionedFeatureArtifact(
        artifact=versioned.artifact,
        integrity=invalid_integrity,
        feature_reference=(
            versioned.feature_reference
        ),
        dataset_reference=(
            versioned.dataset_reference
        ),
    )

    result = validate_versioned_artifact(
        tampered
    )

    assert result.is_valid is False

    assert any(
        issue.code == VERSIONED_ARTIFACT_INVALID
        for issue in result.issues
    )


def test_complete_versioned_feature_artifact_integrity_passes(
    db,
):
    versioned, _, dataset_identity = (
        build_versioned_artifact(db)
    )

    result = (
        validate_versioned_feature_artifact_integrity(
            versioned,
            dataset_identity,
        )
    )

    assert result.is_valid is True
    assert result.issue_count == 0


def test_complete_validation_detects_corrupted_integrity(
    db,
):
    versioned, _, dataset_identity = (
        build_versioned_artifact(db)
    )

    invalid_integrity = ArtifactIntegrity(
        algorithm=(
            versioned.integrity.algorithm
        ),
        digest="0" * 64,
        identity=(
            versioned.integrity.identity
        ),
    )

    tampered = VersionedFeatureArtifact(
        artifact=versioned.artifact,
        integrity=invalid_integrity,
        feature_reference=(
            versioned.feature_reference
        ),
        dataset_reference=(
            versioned.dataset_reference
        ),
    )

    result = (
        validate_versioned_feature_artifact_integrity(
            tampered,
            dataset_identity,
        )
    )

    assert result.is_valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        ARTIFACT_INTEGRITY_INVALID in codes
        or VERSIONED_ARTIFACT_INVALID in codes
    )


def test_validation_helpers(
    db,
):
    versioned, _, dataset_identity = (
        build_versioned_artifact(db)
    )

    result = (
        validate_versioned_feature_artifact_integrity(
            versioned,
            dataset_identity,
        )
    )

    assert (
        is_version_validation_valid(
            result
        )
        is True
    )

    assert (
        get_version_validation_status(
            result
        )
        == VALID
    )

    assert (
        get_version_validation_issues(
            result
        )
        == ()
    )

    assert (
        get_version_validation_issue_count(
            result
        )
        == 0
    )


def test_validation_rejects_invalid_input_type():
    with pytest.raises(TypeError):
        is_version_validation_valid(
            object()
        )

    with pytest.raises(TypeError):
        get_version_validation_status(
            object()
        )

    with pytest.raises(TypeError):
        get_version_validation_issues(
            object()
        )

    with pytest.raises(TypeError):
        get_version_validation_issue_count(
            object()
        )


def test_dataset_identity_is_not_reconstructed_from_reference(
    db,
):
    versioned, _, dataset_identity = (
        build_versioned_artifact(db)
    )

    assert (
        dataset_identity.identity
        == versioned.dataset_reference.identity
    )

    result = (
        validate_versioned_feature_artifact_integrity(
            versioned,
            dataset_identity,
        )
    )

    assert result.is_valid is True
