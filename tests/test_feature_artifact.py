from datetime import date

import pytest

from database.services import HistoricalResultService

from features.feature_artifact import (
    FeatureArtifact,
    build_feature_artifact,
    build_feature_artifact_from_contract_and_values,
    get_artifact_feature_count,
    get_artifact_feature_names,
    get_artifact_feature_values,
    get_artifact_schema_count,
    get_artifact_version_identity,
    is_feature_artifact_valid,
    serialize_feature_artifact,
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
        "TEST_ARTIFACT_MARKET"
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


def build_contract(
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

    return (
        build_feature_dataset_contract(
            pipeline
        ),
        pipeline,
    )


def make_feature_values(
    contract,
):
    return {
        feature_name: index
        for index, feature_name
        in enumerate(
            contract.feature_names
        )
    }


def test_build_artifact_returns_expected_type(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert isinstance(
        artifact,
        FeatureArtifact,
    )


def test_artifact_preserves_target_date(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert artifact.target_date == date(
        2026,
        1,
        5,
    )


def test_artifact_preserves_feature_version(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version="v7",
        ),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    artifact = build_feature_artifact(
        contract
    )

    assert artifact.feature_version == "v7"


def test_artifact_preserves_feature_names(
    db,
):
    contract, pipeline = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.feature_names
        == pipeline.dataset.feature_names
    )


def test_artifact_preserves_schemas(
    db,
):
    contract, pipeline = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert artifact.schemas == pipeline.schemas


def test_artifact_preserves_version_identity(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.version_identity
        == contract.version_identity
    )


def test_artifact_preserves_validation_status(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.validation_status
        == "VALID"
    )


def test_artifact_preserves_leakage_status(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.leakage_status
        == "CLEAN"
    )


def test_artifact_feature_count(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.feature_count
        == len(artifact.feature_names)
    )


def test_artifact_schema_count(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.schema_count
        == len(artifact.schemas)
    )


def test_artifact_with_values_preserves_values(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    assert (
        artifact.feature_values
        == values
    )


def test_artifact_with_values_preserves_feature_names(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    assert (
        artifact.feature_names
        == contract.feature_names
    )


def test_artifact_with_values_preserves_schema_order(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    schema_names = tuple(
        schema.feature_name
        for schema in artifact.schemas
    )

    assert (
        schema_names
        == artifact.feature_names
    )


def test_get_artifact_feature_count(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        get_artifact_feature_count(artifact)
        == artifact.feature_count
    )


def test_get_artifact_schema_count(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        get_artifact_schema_count(artifact)
        == artifact.schema_count
    )


def test_get_artifact_feature_names(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        get_artifact_feature_names(artifact)
        == artifact.feature_names
    )


def test_get_artifact_feature_values(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    returned = get_artifact_feature_values(
        artifact
    )

    assert returned == values


def test_get_artifact_version_identity(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        get_artifact_version_identity(artifact)
        == artifact.version_identity
    )


def test_artifact_is_valid(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        is_feature_artifact_valid(artifact)
        is True
    )


def test_artifact_serialization_returns_string(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    serialized = serialize_feature_artifact(
        artifact
    )

    assert isinstance(
        serialized,
        str,
    )

    assert serialized


def test_artifact_serialization_is_json(
    db,
):
    import json

    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    serialized = serialize_feature_artifact(
        artifact
    )

    payload = json.loads(
        serialized
    )

    assert isinstance(
        payload,
        dict,
    )


def test_artifact_serialization_contains_metadata(
    db,
):
    import json

    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    payload = json.loads(
        serialize_feature_artifact(
            artifact
        )
    )

    assert payload[
        "target_date"
    ] == "2026-01-05"

    assert payload[
        "feature_version"
    ] == "v1"

    assert payload[
        "feature_names"
    ] == list(
        artifact.feature_names
    )

    assert payload[
        "validation_status"
    ] == "VALID"

    assert payload[
        "leakage_status"
    ] == "CLEAN"


def test_artifact_serialization_contains_version_identity(
    db,
):
    import json

    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    payload = json.loads(
        serialize_feature_artifact(
            artifact
        )
    )

    identity = payload[
        "version_identity"
    ]

    assert identity[
        "identity"
    ] == artifact.version_identity.identity

    assert identity[
        "algorithm"
    ] == artifact.version_identity.algorithm


def test_artifact_serialization_is_deterministic(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact_a = build_feature_artifact(
        contract
    )

    artifact_b = build_feature_artifact(
        contract
    )

    serialized_a = serialize_feature_artifact(
        artifact_a
    )

    serialized_b = serialize_feature_artifact(
        artifact_b
    )

    assert serialized_a == serialized_b


def test_artifact_serialization_preserves_none_values(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = {
        feature_name: None
        for feature_name in contract.feature_names
    }

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    returned = get_artifact_feature_values(
        artifact
    )

    assert all(
        value is None
        for value in returned.values()
    )


def test_artifact_accepts_zero_values(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = {
        feature_name: 0
        for feature_name in contract.feature_names
    }

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    assert all(
        value == 0
        for value in artifact.feature_values.values()
    )


def test_none_and_zero_remain_distinct(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = {
        feature_name: (
            None
            if index % 2 == 0
            else 0
        )
        for index, feature_name
        in enumerate(
            contract.feature_names
        )
    }

    artifact = (
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )
    )

    for index, feature_name in enumerate(
        contract.feature_names
    ):
        if index % 2 == 0:
            assert (
                artifact.feature_values[
                    feature_name
                ]
                is None
            )
        else:
            assert (
                artifact.feature_values[
                    feature_name
                ]
                == 0
            )


def test_missing_feature_value_is_rejected(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    values.pop(
        contract.feature_names[0]
    )

    with pytest.raises(ValueError):
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )


def test_extra_feature_value_is_rejected(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    values[
        "unexpected_feature"
    ] = 123

    with pytest.raises(ValueError):
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )


def test_invalid_feature_values_type_is_rejected(
    db,
):
    contract, _ = build_contract(
        db
    )

    with pytest.raises(TypeError):
        build_feature_artifact_from_contract_and_values(
            contract,
            "invalid",
        )


def test_unsupported_feature_value_type_is_rejected(
    db,
):
    contract, _ = build_contract(
        db
    )

    values = make_feature_values(
        contract
    )

    values[
        contract.feature_names[0]
    ] = object()

    with pytest.raises(TypeError):
        build_feature_artifact_from_contract_and_values(
            contract,
            values,
        )


def test_invalid_contract_type_is_rejected():
    with pytest.raises(TypeError):
        build_feature_artifact(
            "invalid"
        )


def test_invalid_contract_for_value_artifact_is_rejected():
    with pytest.raises(TypeError):
        build_feature_artifact_from_contract_and_values(
            "invalid",
            {},
        )


def test_invalid_artifact_getters_are_rejected():
    with pytest.raises(TypeError):
        get_artifact_feature_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_artifact_schema_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_artifact_feature_names(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_artifact_feature_values(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_artifact_version_identity(
            "invalid"
        )

    with pytest.raises(TypeError):
        is_feature_artifact_valid(
            "invalid"
        )

    with pytest.raises(TypeError):
        serialize_feature_artifact(
            "invalid"
        )


def test_artifact_is_immutable(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    with pytest.raises(
        AttributeError
    ):
        artifact.feature_version = "changed"


def test_artifact_feature_names_are_ordered(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact = build_feature_artifact(
        contract
    )

    assert (
        artifact.feature_names
        == tuple(
            schema.feature_name
            for schema in artifact.schemas
        )
    )


def test_artifact_version_identity_is_reproducible(
    db,
):
    contract, _ = build_contract(
        db
    )

    artifact_a = build_feature_artifact(
        contract
    )

    artifact_b = build_feature_artifact(
        contract
    )

    assert (
        artifact_a.version_identity.identity
        == artifact_b.version_identity.identity
    )