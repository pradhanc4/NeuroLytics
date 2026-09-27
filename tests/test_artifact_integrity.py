from datetime import date

import pytest

from database.services import HistoricalResultService

from features.artifact_integrity import (
    INTEGRITY_ALGORITHM,
    INTEGRITY_PREFIX,
    ArtifactIntegrity,
    calculate_artifact_integrity,
    get_artifact_integrity_algorithm,
    get_artifact_integrity_digest,
    get_artifact_integrity_identity,
    is_artifact_integrity_valid,
    validate_artifact_integrity,
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

    values.update(overrides)

    return FeatureConfig(
        **values
    )


def seed_market(
    db,
):
    service = HistoricalResultService(db)

    market = service.create_market(
        "TEST_INTEGRITY_MARKET"
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


def build_artifact(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values = dict(
        pipeline.dataset.values
    )

    return build_feature_artifact_from_contract_and_values(
        contract,
        values,
    )


def test_integrity_returns_expected_type(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert isinstance(
        integrity,
        ArtifactIntegrity,
    )


def test_integrity_uses_sha256(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        integrity.algorithm
        == INTEGRITY_ALGORITHM
    )

    assert integrity.algorithm == "sha256"


def test_integrity_digest_is_not_empty(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert integrity.digest
    assert isinstance(
        integrity.digest,
        str,
    )


def test_integrity_digest_has_sha256_length(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert len(
        integrity.digest
    ) == 64


def test_integrity_identity_has_expected_prefix(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert integrity.identity.startswith(
        INTEGRITY_PREFIX
    )


def test_integrity_identity_contains_digest(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert integrity.identity == (
        f"{INTEGRITY_PREFIX}"
        f"{integrity.digest}"
    )


def test_same_artifact_produces_same_integrity(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity_a = calculate_artifact_integrity(
        artifact
    )

    integrity_b = calculate_artifact_integrity(
        artifact
    )

    assert integrity_a == integrity_b


def test_same_artifact_is_valid_against_its_integrity(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    validate_artifact_integrity(
        artifact,
        integrity,
    )

    assert is_artifact_integrity_valid(
        artifact,
        integrity,
    ) is True


def test_invalid_digest_is_rejected(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    tampered_integrity = ArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest="0" * 64,
        identity=integrity.identity,
    )

    with pytest.raises(
        ValueError
    ):
        validate_artifact_integrity(
            artifact,
            tampered_integrity,
        )


def test_invalid_identity_is_rejected(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    tampered_integrity = ArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest=integrity.digest,
        identity="artifact-invalid",
    )

    with pytest.raises(
        ValueError
    ):
        validate_artifact_integrity(
            artifact,
            tampered_integrity,
        )


def test_invalid_algorithm_is_rejected(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    tampered_integrity = ArtifactIntegrity(
        algorithm="md5",
        digest=integrity.digest,
        identity=integrity.identity,
    )

    with pytest.raises(
        ValueError
    ):
        validate_artifact_integrity(
            artifact,
            tampered_integrity,
        )


def test_invalid_artifact_type_is_rejected():
    integrity = ArtifactIntegrity(
        algorithm=INTEGRITY_ALGORITHM,
        digest="0" * 64,
        identity=f"{INTEGRITY_PREFIX}{'0' * 64}",
    )

    with pytest.raises(
        TypeError
    ):
        calculate_artifact_integrity(
            "invalid"
        )

    with pytest.raises(
        TypeError
    ):
        validate_artifact_integrity(
            "invalid",
            integrity,
        )

    assert (
        is_artifact_integrity_valid(
            "invalid",
            integrity,
        )
        is False
    )


def test_invalid_integrity_type_is_rejected(
    db,
):
    artifact = build_artifact(
        db
    )

    with pytest.raises(
        TypeError
    ):
        validate_artifact_integrity(
            artifact,
            "invalid",
        )

    assert (
        is_artifact_integrity_valid(
            artifact,
            "invalid",
        )
        is False
    )


def test_integrity_digest_getter(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        get_artifact_integrity_digest(
            integrity
        )
        == integrity.digest
    )


def test_integrity_identity_getter(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        get_artifact_integrity_identity(
            integrity
        )
        == integrity.identity
    )


def test_integrity_algorithm_getter(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        get_artifact_integrity_algorithm(
            integrity
        )
        == integrity.algorithm
    )


def test_integrity_getters_reject_invalid_type():
    with pytest.raises(
        TypeError
    ):
        get_artifact_integrity_digest(
            "invalid"
        )

    with pytest.raises(
        TypeError
    ):
        get_artifact_integrity_identity(
            "invalid"
        )

    with pytest.raises(
        TypeError
    ):
        get_artifact_integrity_algorithm(
            "invalid"
        )


def test_feature_value_change_changes_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values_a = dict(
        pipeline.dataset.values
    )

    values_b = dict(
        values_a
    )

    first_name = pipeline.dataset.feature_names[0]

    values_b[
        first_name
    ] = 999

    artifact_a = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_a,
        )
    )

    artifact_b = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_b,
        )
    )

    integrity_a = calculate_artifact_integrity(
        artifact_a
    )

    integrity_b = calculate_artifact_integrity(
        artifact_b
    )

    assert (
        integrity_a.digest
        != integrity_b.digest
    )


def test_feature_version_change_changes_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline_a = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version="v1",
        ),
    )

    pipeline_b = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version="v2",
        ),
    )

    contract_a = build_feature_dataset_contract(
        pipeline_a
    )

    contract_b = build_feature_dataset_contract(
        pipeline_b
    )

    artifact_a = (
        build_feature_artifact_from_contract_and_values(
            contract_a,
            pipeline_a.dataset.values,
        )
    )

    artifact_b = (
        build_feature_artifact_from_contract_and_values(
            contract_b,
            pipeline_b.dataset.values,
        )
    )

    integrity_a = calculate_artifact_integrity(
        artifact_a
    )

    integrity_b = calculate_artifact_integrity(
        artifact_b
    )

    assert (
        integrity_a.digest
        != integrity_b.digest
    )


def test_target_date_change_changes_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline_a = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    pipeline_b = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 6),
        config=make_config(),
    )

    contract_a = build_feature_dataset_contract(
        pipeline_a
    )

    contract_b = build_feature_dataset_contract(
        pipeline_b
    )

    artifact_a = (
        build_feature_artifact_from_contract_and_values(
            contract_a,
            pipeline_a.dataset.values,
        )
    )

    artifact_b = (
        build_feature_artifact_from_contract_and_values(
            contract_b,
            pipeline_b.dataset.values,
        )
    )

    integrity_a = calculate_artifact_integrity(
        artifact_a
    )

    integrity_b = calculate_artifact_integrity(
        artifact_b
    )

    assert (
        integrity_a.digest
        != integrity_b.digest
    )


def test_zero_value_is_part_of_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values = dict(
        pipeline.dataset.values
    )

    first_name = pipeline.dataset.feature_names[0]

    values[
        first_name
    ] = 0

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert is_artifact_integrity_valid(
        artifact,
        integrity,
    )


def test_none_value_is_part_of_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values = dict(
        pipeline.dataset.values
    )

    first_name = pipeline.dataset.feature_names[0]

    values[
        first_name
    ] = None

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert is_artifact_integrity_valid(
        artifact,
        integrity,
    )


def test_none_and_zero_produce_different_integrity(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values_none = dict(
        pipeline.dataset.values
    )

    values_zero = dict(
        pipeline.dataset.values
    )

    first_name = pipeline.dataset.feature_names[0]

    values_none[
        first_name
    ] = None

    values_zero[
        first_name
    ] = 0

    artifact_none = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_none,
        )
    )

    artifact_zero = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_zero,
        )
    )

    integrity_none = calculate_artifact_integrity(
        artifact_none
    )

    integrity_zero = calculate_artifact_integrity(
        artifact_zero
    )

    assert (
        integrity_none.digest
        != integrity_zero.digest
    )


def test_integrity_is_immutable(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    with pytest.raises(
        AttributeError
    ):
        integrity.digest = "changed"


def test_integrity_validation_is_deterministic(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        is_artifact_integrity_valid(
            artifact,
            integrity,
        )
        is True
    )

    assert (
        is_artifact_integrity_valid(
            artifact,
            integrity,
        )
        is True
    )


def test_integrity_identity_is_reproducible(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity_a = calculate_artifact_integrity(
        artifact
    )

    integrity_b = calculate_artifact_integrity(
        artifact
    )

    assert (
        integrity_a.identity
        == integrity_b.identity
    )


def test_integrity_detects_changed_schema_metadata(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values = dict(
        pipeline.dataset.values
    )

    artifact_a = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    from features.feature_schema import (
        FeatureSchema,
    )

    first_schema = artifact_a.schemas[0]

    modified_schema = FeatureSchema(
        feature_name=first_schema.feature_name,
        feature_version=first_schema.feature_version,
        feature_type=first_schema.feature_type,
        source=first_schema.source,
        position=first_schema.position,
        window=first_schema.window,
        lag=first_schema.lag,
        description="Modified description.",
        availability_rule=(
            first_schema.availability_rule
        ),
        data_type=first_schema.data_type,
    )

    modified_schemas = (
        modified_schema,
        *artifact_a.schemas[1:],
    )

    from features.feature_artifact import (
        FeatureArtifact,
    )

    artifact_b = FeatureArtifact(
        target_date=artifact_a.target_date,
        feature_version=artifact_a.feature_version,
        feature_names=artifact_a.feature_names,
        feature_values=artifact_a.feature_values,
        schemas=modified_schemas,
        version_identity=artifact_a.version_identity,
        validation_status=artifact_a.validation_status,
        leakage_status=artifact_a.leakage_status,
    )

    integrity_a = calculate_artifact_integrity(
        artifact_a
    )

    integrity_b = calculate_artifact_integrity(
        artifact_b
    )

    assert (
        integrity_a.digest
        != integrity_b.digest
    )


def test_integrity_validation_detects_artifact_change(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    values_a = dict(
        pipeline.dataset.values
    )

    values_b = dict(
        values_a
    )

    first_name = pipeline.dataset.feature_names[0]

    values_b[
        first_name
    ] = 777

    artifact_a = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_a,
        )
    )

    artifact_b = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values_b,
        )
    )

    integrity_a = calculate_artifact_integrity(
        artifact_a
    )

    assert (
        is_artifact_integrity_valid(
            artifact_a,
            integrity_a,
        )
        is True
    )

    assert (
        is_artifact_integrity_valid(
            artifact_b,
            integrity_a,
        )
        is False
    )


def test_integrity_algorithm_getter_returns_expected_value(
    db,
):
    artifact = build_artifact(
        db
    )

    integrity = calculate_artifact_integrity(
        artifact
    )

    assert (
        get_artifact_integrity_algorithm(
            integrity
        )
        == "sha256"
    )