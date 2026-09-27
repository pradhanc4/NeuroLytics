from datetime import date

import pytest

from features.feature_schema import FeatureSchema
from features.feature_schema_builder import (
    DEFAULT_AVAILABILITY_RULE,
    build_feature_schema_from_record,
    build_feature_schemas,
    get_schema_by_feature_name,
    get_schema_count,
    get_schema_feature_names,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)


def make_record(
    feature_name="col1_lag_1",
    value=5,
    feature_type="lag",
    source="lag_features",
):
    return UnifiedFeatureRecord(
        feature_name=feature_name,
        value=value,
        feature_type=feature_type,
        source=source,
    )


def make_dataset(
    records=None,
    feature_version="v1",
):
    if records is None:
        records = (
            make_record(),
        )

    return UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version=feature_version,
        records=tuple(records),
    )


def test_build_schema_from_lag_record():
    record = make_record(
        feature_name="col1_lag_1",
        value=5,
        feature_type="lag",
        source="lag_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert isinstance(
        schema,
        FeatureSchema,
    )

    assert schema.feature_name == "col1_lag_1"
    assert schema.feature_version == "v1"
    assert schema.feature_type == "lag"
    assert schema.source == "lag_features"
    assert schema.position == "col1"
    assert schema.lag == 1
    assert schema.window is None


def test_build_schema_from_rolling_record():
    record = make_record(
        feature_name="col2_rolling_5_mean",
        value=4.5,
        feature_type="rolling",
        source="rolling_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v2",
    )

    assert schema.feature_name == "col2_rolling_5_mean"
    assert schema.feature_version == "v2"
    assert schema.feature_type == "rolling"
    assert schema.position == "col2"
    assert schema.window == 5
    assert schema.lag is None


def test_build_schema_from_position_record():
    record = make_record(
        feature_name="col3_latest_value",
        value=7,
        feature_type="position",
        source="position_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.position == "col3"
    assert schema.window is None
    assert schema.lag is None


def test_build_schema_from_recency_record():
    record = make_record(
        feature_name="col4_digit_7_recency",
        value=2,
        feature_type="recency",
        source="recency_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.position == "col4"
    assert schema.feature_type == "recency"


def test_build_schema_from_frequency_record():
    record = make_record(
        feature_name="col5_digit_3_frequency_count",
        value=4,
        feature_type="frequency",
        source="frequency_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.position == "col5"
    assert schema.feature_type == "frequency"
    assert schema.window is None


def test_build_schema_from_sequence_record():
    record = make_record(
        feature_name="col6_sequence_transition",
        value="2_to_7",
        feature_type="sequence",
        source="sequence_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.position == "col6"
    assert schema.feature_type == "sequence"


def test_build_schema_from_cross_position_record():
    record = make_record(
        feature_name="col1_col2_same",
        value=1,
        feature_type="cross_position",
        source="cross_position_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.position == "col1"
    assert schema.feature_type == "cross_position"


def test_integer_value_gets_integer_data_type():
    schema = build_feature_schema_from_record(
        make_record(value=5),
        "v1",
    )

    assert schema.data_type == "integer"


def test_float_value_gets_float_data_type():
    record = make_record(
        feature_name="col1_rolling_3_mean",
        value=3.5,
        feature_type="rolling",
        source="rolling_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.data_type == "float"


def test_string_value_gets_string_data_type():
    record = make_record(
        feature_name="col1_sequence_transition",
        value="1_to_2",
        feature_type="sequence",
        source="sequence_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.data_type == "string"


def test_boolean_value_gets_boolean_data_type():
    record = make_record(
        feature_name="col1_flag",
        value=True,
        feature_type="position",
        source="position_features",
    )

    schema = build_feature_schema_from_record(
        record,
        "v1",
    )

    assert schema.data_type == "boolean"


def test_none_value_gets_unknown_data_type():
    schema = build_feature_schema_from_record(
        make_record(value=None),
        "v1",
    )

    assert schema.data_type == "unknown"


def test_default_availability_rule_is_applied():
    schema = build_feature_schema_from_record(
        make_record(),
        "v1",
    )

    assert (
        schema.availability_rule
        == DEFAULT_AVAILABILITY_RULE
    )


def test_description_is_generated():
    schema = build_feature_schema_from_record(
        make_record(
            feature_type="lag",
            source="lag_features",
        ),
        "v1",
    )

    assert (
        schema.description
        == "lag feature generated by lag_features."
    )


def test_build_feature_schemas_builds_all_records():
    records = (
        make_record(
            feature_name="col1_lag_1",
            value=1,
        ),
        make_record(
            feature_name="col2_lag_2",
            value=2,
        ),
        make_record(
            feature_name="col3_lag_3",
            value=3,
        ),
    )

    dataset = make_dataset(
        records=records,
    )

    schemas = build_feature_schemas(
        dataset,
    )

    assert len(schemas) == 3
    assert all(
        isinstance(
            schema,
            FeatureSchema,
        )
        for schema in schemas
    )


def test_build_feature_schemas_preserves_order():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col2_lag_2",
        ),
        make_record(
            feature_name="col3_lag_3",
        ),
    )

    dataset = make_dataset(
        records=records,
    )

    schemas = build_feature_schemas(
        dataset,
    )

    assert tuple(
        schema.feature_name
        for schema in schemas
    ) == (
        "col1_lag_1",
        "col2_lag_2",
        "col3_lag_3",
    )


def test_feature_version_is_inherited_from_dataset():
    dataset = make_dataset(
        feature_version="v7",
    )

    schemas = build_feature_schemas(
        dataset,
    )

    assert schemas[0].feature_version == "v7"


def test_duplicate_schema_names_are_rejected():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col1_lag_1",
        ),
    )

    dataset = make_dataset(
        records=records,
    )

    with pytest.raises(ValueError):
        build_feature_schemas(
            dataset,
        )


def test_invalid_record_type_is_rejected():
    with pytest.raises(TypeError):
        build_feature_schema_from_record(
            "invalid",
            "v1",
        )


def test_invalid_feature_version_type_is_rejected():
    record = make_record()

    with pytest.raises(TypeError):
        build_feature_schema_from_record(
            record,
            1,
        )


def test_invalid_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        build_feature_schemas(
            "invalid",
        )


def test_schema_lookup_returns_matching_schema():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col2_lag_2",
        ),
    )

    dataset = make_dataset(
        records=records,
    )

    schemas = build_feature_schemas(
        dataset,
    )

    schema = get_schema_by_feature_name(
        schemas,
        "col2_lag_2",
    )

    assert schema.feature_name == "col2_lag_2"


def test_schema_lookup_rejects_unknown_feature():
    schemas = build_feature_schemas(
        make_dataset(),
    )

    with pytest.raises(ValueError):
        get_schema_by_feature_name(
            schemas,
            "does_not_exist",
        )


def test_schema_lookup_rejects_invalid_feature_name_type():
    schemas = build_feature_schemas(
        make_dataset(),
    )

    with pytest.raises(TypeError):
        get_schema_by_feature_name(
            schemas,
            123,
        )


def test_schema_lookup_rejects_invalid_schema_collection():
    with pytest.raises(TypeError):
        get_schema_by_feature_name(
            "invalid",
            "col1_lag_1",
        )


def test_schema_names_are_returned_in_order():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col2_lag_2",
        ),
    )

    schemas = build_feature_schemas(
        make_dataset(records=records),
    )

    assert get_schema_feature_names(
        schemas,
    ) == (
        "col1_lag_1",
        "col2_lag_2",
    )


def test_schema_count_returns_number_of_schemas():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col2_lag_2",
        ),
        make_record(
            feature_name="col3_lag_3",
        ),
    )

    schemas = build_feature_schemas(
        make_dataset(records=records),
    )

    assert get_schema_count(
        schemas,
    ) == 3


def test_empty_dataset_returns_empty_schema_collection():
    dataset = make_dataset(
        records=(),
    )

    schemas = build_feature_schemas(
        dataset,
    )

    assert schemas == ()
    assert get_schema_count(schemas) == 0


def test_schema_names_reject_invalid_collection():
    with pytest.raises(TypeError):
        get_schema_feature_names(
            "invalid",
        )


def test_schema_count_rejects_invalid_collection():
    with pytest.raises(TypeError):
        get_schema_count(
            "invalid",
        )


def test_schema_name_collection_rejects_invalid_schema_member():
    with pytest.raises(TypeError):
        get_schema_feature_names(
            (
                "invalid",
            ),
        )


def test_schema_count_does_not_modify_dataset():
    record = make_record()

    dataset = make_dataset(
        records=(record,),
    )

    before = dataset.records

    schemas = build_feature_schemas(
        dataset,
    )

    assert dataset.records == before
    assert len(schemas) == 1


def test_builder_is_deterministic():
    records = (
        make_record(
            feature_name="col1_lag_1",
            value=1,
        ),
        make_record(
            feature_name="col2_lag_2",
            value=2,
        ),
    )

    dataset = make_dataset(
        records=records,
        feature_version="v3",
    )

    schemas_a = build_feature_schemas(
        dataset,
    )

    schemas_b = build_feature_schemas(
        dataset,
    )

    assert schemas_a == schemas_b