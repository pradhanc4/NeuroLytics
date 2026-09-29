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
    build_dataset_version_identity,
    build_dataset_version_reference,
)

from features.feature_artifact import (
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
    build_feature_version_identity,
    build_feature_version_reference_from_identity,
)

from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)

from features.version_reproducibility import (
    get_versioned_feature_artifact_integrity,
    is_artifact_integrity_reproducible,
    is_dataset_version_identity_reproducible,
    is_dataset_version_reference_reproducible,
    is_feature_version_identity_reproducible,
    is_feature_version_reference_reproducible,
    is_versioned_feature_artifact_reproducible,
)

from features.versioned_artifact import (
    VersionedFeatureArtifact,
    build_versioned_feature_artifact,
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
    """
    Create the reproducibility test market once and reuse it
    for repeated deterministic-build checks.
    """

    service = HistoricalResultService(
        db
    )

    market_name = (
        "TEST_VERSION_REPRODUCIBILITY_MARKET"
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


def build_feature_identity(
    db,
    feature_version="v1",
    lag_windows=(1, 2, 3),
):
    service, market = seed_market(
        db
    )

    config = make_config(
        feature_version=feature_version,
        lag_windows=lag_windows,
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

    return build_feature_version_identity(
        config=config,
        schemas=pipeline.schemas,
    )


def build_dataset_identity(
    db,
    dataset_version="dataset-v1",
    feature_version="v1",
    first_value=None,
):
    """
    Build a dataset version identity.

    The important part of this helper is that first_value is
    applied to the actual UnifiedFeatureDataset records that
    are passed to build_dataset_version_identity().

    This ensures None and 0 remain distinct dataset values.
    """

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

    original_records = pipeline.dataset.records

    if not original_records:
        raise AssertionError(
            "Feature pipeline produced no dataset records."
        )

    modified_records = (
        UnifiedFeatureRecord(
            feature_name=record.feature_name,
            value=(
                first_value
                if index == 0
                else record.value
            ),
            feature_type=record.feature_type,
            source=record.source,
        )
        for index, record in enumerate(
            original_records
        )
    )

    dataset = UnifiedFeatureDataset(
        target_date=pipeline.dataset.target_date,
        feature_version=pipeline.dataset.feature_version,
        records=tuple(
            modified_records
        ),
    )

    return build_dataset_version_identity(
        dataset=dataset,
        feature_identity=pipeline.version_identity,
        dataset_version=dataset_version,
    )


def build_versioned_artifact(
    db,
    dataset_version="dataset-v1",
    feature_version="v1",
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

    return build_versioned_feature_artifact(
        artifact,
        feature_reference,
        dataset_reference,
    )


def test_feature_identity_is_reproducible(
    db,
):
    first = build_feature_identity(
        db
    )

    second = build_feature_identity(
        db
    )

    assert (
        is_feature_version_identity_reproducible(
            first,
            second,
        )
        is True
    )


def test_feature_identity_changes_when_definition_changes(
    db,
):
    first = build_feature_identity(
        db,
        lag_windows=(1, 2, 3),
    )

    second = build_feature_identity(
        db,
        lag_windows=(1, 2),
    )

    assert (
        is_feature_version_identity_reproducible(
            first,
            second,
        )
        is False
    )


def test_feature_identity_changes_when_version_changes(
    db,
):
    first = build_feature_identity(
        db,
        feature_version="v1",
    )

    second = build_feature_identity(
        db,
        feature_version="v2",
    )

    assert (
        is_feature_version_identity_reproducible(
            first,
            second,
        )
        is False
    )


def test_dataset_identity_is_reproducible(
    db,
):
    first = build_dataset_identity(
        db,
        first_value=None,
    )

    second = build_dataset_identity(
        db,
        first_value=None,
    )

    assert (
        is_dataset_version_identity_reproducible(
            first,
            second,
        )
        is True
    )


def test_dataset_identity_changes_when_value_changes(
    db,
):
    first = build_dataset_identity(
        db,
        first_value=None,
    )

    second = build_dataset_identity(
        db,
        first_value=0,
    )

    assert (
        is_dataset_version_identity_reproducible(
            first,
            second,
        )
        is False
    )


def test_dataset_identity_changes_when_version_changes(
    db,
):
    first = build_dataset_identity(
        db,
        dataset_version="dataset-v1",
    )

    second = build_dataset_identity(
        db,
        dataset_version="dataset-v2",
    )

    assert (
        is_dataset_version_identity_reproducible(
            first,
            second,
        )
        is False
    )


def test_feature_reference_is_reproducible(
    db,
):
    identity = build_feature_identity(
        db
    )

    first = (
        build_feature_version_reference_from_identity(
            identity
        )
    )

    second = (
        build_feature_version_reference_from_identity(
            identity
        )
    )

    assert (
        is_feature_version_reference_reproducible(
            first,
            second,
        )
        is True
    )


def test_dataset_reference_is_reproducible(
    db,
):
    identity = build_dataset_identity(
        db
    )

    first = build_dataset_version_reference(
        identity
    )

    second = build_dataset_version_reference(
        identity
    )

    assert (
        is_dataset_version_reference_reproducible(
            first,
            second,
        )
        is True
    )


def test_artifact_integrity_is_reproducible(
    db,
):
    versioned = build_versioned_artifact(
        db
    )

    first = calculate_artifact_integrity(
        versioned.artifact
    )

    second = calculate_artifact_integrity(
        versioned.artifact
    )

    assert (
        is_artifact_integrity_reproducible(
            first,
            second,
        )
        is True
    )


def test_versioned_artifact_is_reproducible(
    db,
):
    first = build_versioned_artifact(
        db
    )

    second = build_versioned_artifact(
        db
    )

    assert (
        is_versioned_feature_artifact_reproducible(
            first,
            second,
        )
        is True
    )


def test_versioned_artifact_integrity_getter_is_deterministic(
    db,
):
    versioned = build_versioned_artifact(
        db
    )

    first = get_versioned_feature_artifact_integrity(
        versioned
    )

    second = get_versioned_feature_artifact_integrity(
        versioned
    )

    assert first == second


def test_changed_feature_definition_breaks_reproducibility(
    db,
):
    first = build_versioned_artifact(
        db,
        feature_version="v1",
    )

    second = build_versioned_artifact(
        db,
        feature_version="v2",
    )

    assert (
        is_versioned_feature_artifact_reproducible(
            first,
            second,
        )
        is False
    )


def test_changed_dataset_version_breaks_reproducibility(
    db,
):
    first = build_versioned_artifact(
        db,
        dataset_version="dataset-v1",
    )

    second = build_versioned_artifact(
        db,
        dataset_version="dataset-v2",
    )

    assert (
        is_versioned_feature_artifact_reproducible(
            first,
            second,
        )
        is False
    )


def test_invalid_artifact_integrity_type_is_rejected():
    with pytest.raises(
        TypeError
    ):
        is_artifact_integrity_reproducible(
            "invalid",
            "invalid",
        )


def test_invalid_versioned_artifact_type_is_rejected():
    with pytest.raises(
        TypeError
    ):
        is_versioned_feature_artifact_reproducible(
            "invalid",
            "invalid",
        )


def test_versioned_artifact_integrity_mismatch_is_detected(
    db,
):
    versioned = build_versioned_artifact(
        db
    )

    invalid_integrity = ArtifactIntegrity(
        algorithm=versioned.integrity.algorithm,
        digest="0" * 64,
        identity=versioned.integrity.identity,
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

    assert (
        is_versioned_feature_artifact_reproducible(
            versioned,
            tampered,
        )
        is False
    )


def test_zero_and_none_are_not_reproducible_as_dataset_versions(
    db,
):
    first = build_dataset_identity(
        db,
        first_value=None,
    )

    second = build_dataset_identity(
        db,
        first_value=0,
    )

    assert (
        is_dataset_version_identity_reproducible(
            first,
            second,
        )
        is False
    )