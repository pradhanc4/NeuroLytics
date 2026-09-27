from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.feature_schema import FeatureSchema
from features.feature_versioning import (
    VERSION_ALGORITHM,
    VERSION_PREFIX,
    FeatureVersionIdentity,
    build_feature_version_from_dataset,
    build_feature_version_identity,
    get_canonical_feature_definition,
    get_feature_version_identity,
    get_feature_version_label,
    get_version_algorithm,
    is_feature_version_reproducible,
    validate_feature_version_identity,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)


def make_schema(
    feature_name="col1_lag_1",
    feature_version="v1",
    feature_type="lag",
    source="lag_features",
    position="col1",
    window=None,
    lag=1,
    description="Previous historical value.",
    availability_rule=(
        "Uses only observations strictly before the target date."
    ),
    data_type="integer",
):
    return FeatureSchema(
        feature_name=feature_name,
        feature_version=feature_version,
        feature_type=feature_type,
        source=source,
        position=position,
        window=window,
        lag=lag,
        description=description,
        availability_rule=availability_rule,
        data_type=data_type,
    )


def make_dataset(
    feature_version="v1",
    feature_name="col1_lag_1",
    value=5,
):
    record = UnifiedFeatureRecord(
        feature_name=feature_name,
        value=value,
        feature_type="lag",
        source="lag_features",
    )

    return UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version=feature_version,
        records=(record,),
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


def test_version_identity_can_be_created():
    config = make_config()

    schemas = (
        make_schema(),
    )

    identity = build_feature_version_identity(
        config,
        schemas,
    )

    assert isinstance(
        identity,
        FeatureVersionIdentity,
    )


def test_version_identity_has_expected_algorithm():
    config = make_config()

    identity = build_feature_version_identity(
        config,
        (make_schema(),),
    )

    assert identity.algorithm == VERSION_ALGORITHM
    assert identity.algorithm == "sha256"


def test_version_identity_has_expected_prefix():
    identity = build_feature_version_identity(
        make_config(),
        (make_schema(),),
    )

    assert identity.identity.startswith(
        VERSION_PREFIX
    )


def test_version_identity_preserves_feature_version():
    identity = build_feature_version_identity(
        make_config(
            feature_version="v7"
        ),
        (
            make_schema(
                feature_version="v7"
            ),
        ),
    )

    assert identity.feature_version == "v7"


def test_version_identity_is_deterministic():
    config = make_config()
    schemas = (
        make_schema(),
    )

    identity_a = build_feature_version_identity(
        config,
        schemas,
    )

    identity_b = build_feature_version_identity(
        config,
        schemas,
    )

    assert identity_a == identity_b


def test_same_definition_produces_same_identity():
    config_a = make_config()
    config_b = make_config()

    schemas_a = (
        make_schema(),
    )

    schemas_b = (
        make_schema(),
    )

    identity_a = build_feature_version_identity(
        config_a,
        schemas_a,
    )

    identity_b = build_feature_version_identity(
        config_b,
        schemas_b,
    )

    assert identity_a.identity == identity_b.identity


def test_different_lag_windows_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            lag_windows=(1,),
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            lag_windows=(1, 2),
        ),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_rolling_windows_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            rolling_windows=(3,),
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            rolling_windows=(3, 5),
        ),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_frequency_settings_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            frequency_window=5,
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            frequency_window=10,
        ),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_recency_settings_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            recency_lookback=10,
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            recency_lookback=20,
        ),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_positions_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            positions=("col1",),
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            positions=("col1", "col2"),
        ),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_schema_feature_names_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(),
        (
            make_schema(
                feature_name="col1_lag_1",
            ),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(),
        (
            make_schema(
                feature_name="col1_lag_2",
                lag=2,
            ),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_different_schema_data_types_produce_different_identity():
    identity_a = build_feature_version_identity(
        make_config(),
        (
            make_schema(
                data_type="integer",
            ),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(),
        (
            make_schema(
                data_type="float",
            ),
        ),
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_canonical_definition_is_not_empty():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert identity.canonical_definition
    assert isinstance(
        identity.canonical_definition,
        str,
    )


def test_canonical_definition_is_deterministic():
    identity_a = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert (
        identity_a.canonical_definition
        == identity_b.canonical_definition
    )


def test_validate_identity_accepts_valid_identity():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    validate_feature_version_identity(
        identity
    )


def test_get_feature_version_identity():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert (
        get_feature_version_identity(identity)
        == identity.identity
    )


def test_get_feature_version_label():
    identity = build_feature_version_identity(
        make_config(
            feature_version="v4"
        ),
        (
            make_schema(
                feature_version="v4"
            ),
        ),
    )

    assert (
        get_feature_version_label(identity)
        == "v4"
    )


def test_get_canonical_feature_definition():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert (
        get_canonical_feature_definition(identity)
        == identity.canonical_definition
    )


def test_get_version_algorithm():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert (
        get_version_algorithm(identity)
        == "sha256"
    )


def test_reproducibility_returns_true_for_same_identity():
    identity_a = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    assert is_feature_version_reproducible(
        identity_a,
        identity_b,
    ) is True


def test_reproducibility_returns_false_for_different_identity():
    identity_a = build_feature_version_identity(
        make_config(
            lag_windows=(1,),
        ),
        (
            make_schema(),
        ),
    )

    identity_b = build_feature_version_identity(
        make_config(
            lag_windows=(1, 2),
        ),
        (
            make_schema(),
        ),
    )

    assert is_feature_version_reproducible(
        identity_a,
        identity_b,
    ) is False


def test_dataset_version_identity_can_be_created():
    dataset = make_dataset()

    schemas = (
        make_schema(),
    )

    identity = build_feature_version_from_dataset(
        dataset,
        schemas,
    )

    assert isinstance(
        identity,
        FeatureVersionIdentity,
    )


def test_dataset_version_identity_preserves_dataset_version():
    dataset = make_dataset(
        feature_version="v8",
    )

    schemas = (
        make_schema(
            feature_version="v8",
        ),
    )

    identity = build_feature_version_from_dataset(
        dataset,
        schemas,
    )

    assert identity.feature_version == "v8"


def test_dataset_version_identity_is_deterministic():
    dataset = make_dataset()

    schemas = (
        make_schema(),
    )

    identity_a = build_feature_version_from_dataset(
        dataset,
        schemas,
    )

    identity_b = build_feature_version_from_dataset(
        dataset,
        schemas,
    )

    assert identity_a == identity_b


def test_dataset_feature_name_changes_identity():
    dataset_a = make_dataset(
        feature_name="col1_lag_1",
    )

    dataset_b = make_dataset(
        feature_name="col1_lag_2",
    )

    schemas_a = (
        make_schema(
            feature_name="col1_lag_1",
        ),
    )

    schemas_b = (
        make_schema(
            feature_name="col1_lag_2",
            lag=2,
        ),
    )

    identity_a = build_feature_version_from_dataset(
        dataset_a,
        schemas_a,
    )

    identity_b = build_feature_version_from_dataset(
        dataset_b,
        schemas_b,
    )

    assert (
        identity_a.identity
        != identity_b.identity
    )


def test_invalid_identity_type_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_version_identity(
            "invalid"
        )


def test_invalid_identity_algorithm_is_rejected():
    identity = FeatureVersionIdentity(
        feature_version="v1",
        identity="feature-invalid",
        algorithm="md5",
        canonical_definition="{}",
    )

    with pytest.raises(ValueError):
        validate_feature_version_identity(
            identity
        )


def test_invalid_identity_definition_is_rejected():
    identity = FeatureVersionIdentity(
        feature_version="v1",
        identity="feature-invalid",
        algorithm="sha256",
        canonical_definition="",
    )

    with pytest.raises(ValueError):
        validate_feature_version_identity(
            identity
        )


def test_tampered_identity_is_rejected():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    tampered = FeatureVersionIdentity(
        feature_version=identity.feature_version,
        identity="feature-tampered",
        algorithm=identity.algorithm,
        canonical_definition=identity.canonical_definition,
    )

    with pytest.raises(ValueError):
        validate_feature_version_identity(
            tampered
        )


def test_invalid_config_type_is_rejected():
    with pytest.raises(TypeError):
        build_feature_version_identity(
            "invalid",
            (
                make_schema(),
            ),
        )


def test_invalid_schema_collection_type_is_rejected():
    with pytest.raises(TypeError):
        build_feature_version_identity(
            make_config(),
            "invalid",
        )


def test_invalid_schema_member_is_rejected():
    with pytest.raises(TypeError):
        build_feature_version_identity(
            make_config(),
            (
                "invalid",
            ),
        )


def test_dataset_identity_rejects_invalid_dataset():
    with pytest.raises(TypeError):
        build_feature_version_from_dataset(
            "invalid",
            (
                make_schema(),
            ),
        )


def test_dataset_identity_rejects_invalid_schema_collection():
    with pytest.raises(TypeError):
        build_feature_version_from_dataset(
            make_dataset(),
            "invalid",
        )


def test_dataset_identity_rejects_invalid_schema_member():
    with pytest.raises(TypeError):
        build_feature_version_from_dataset(
            make_dataset(),
            (
                "invalid",
            ),
        )


def test_identity_getters_reject_invalid_identity():
    with pytest.raises(TypeError):
        get_feature_version_identity(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_feature_version_label(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_canonical_feature_definition(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_version_algorithm(
            "invalid"
        )


def test_reproducibility_rejects_invalid_first_identity():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    with pytest.raises(TypeError):
        is_feature_version_reproducible(
            "invalid",
            identity,
        )


def test_reproducibility_rejects_invalid_second_identity():
    identity = build_feature_version_identity(
        make_config(),
        (
            make_schema(),
        ),
    )

    with pytest.raises(TypeError):
        is_feature_version_reproducible(
            identity,
            "invalid",
        )