from datetime import date

import pytest

from features.feature_schema import (
    FEATURE_TYPES,
    POSITIONS,
    FeatureSchema,
    build_feature_schema,
    get_feature_availability_rule,
    get_feature_data_type,
    get_feature_description,
    get_feature_lag,
    get_feature_name,
    get_feature_position,
    get_feature_source,
    get_feature_type,
    get_feature_version,
    get_feature_window,
    validate_feature_schema,
)


def make_schema(
    **overrides,
) -> FeatureSchema:
    values = {
        "feature_name": "col1_lag_1",
        "feature_version": "v1",
        "feature_type": "lag",
        "source": "lag_features",
        "position": "col1",
        "window": None,
        "lag": 1,
        "description": "Previous historical value for col1.",
        "availability_rule": (
            "Uses only observations strictly before the target date."
        ),
        "data_type": "integer",
    }

    values.update(overrides)

    return FeatureSchema(**values)


def test_feature_schema_can_be_created():
    schema = make_schema()

    assert isinstance(
        schema,
        FeatureSchema,
    )


def test_feature_schema_contains_expected_metadata():
    schema = make_schema()

    assert schema.feature_name == "col1_lag_1"
    assert schema.feature_version == "v1"
    assert schema.feature_type == "lag"
    assert schema.source == "lag_features"
    assert schema.position == "col1"
    assert schema.window is None
    assert schema.lag == 1
    assert schema.data_type == "integer"


def test_all_supported_feature_types_are_defined():
    assert FEATURE_TYPES == (
        # Phase 13
        "lag",
        "rolling",
        "recency",
        "position",
        "frequency",
        "sequence",
        "cross_position",

        # Phase 14
        "time",
        "historical_interval",
        "observation_density",
        "historical_frequency",
        "rolling_frequency",
        "frequency_change",
        "frequency_concentration",
        "recency_expansion",
        "recency_distribution",
        "recency_bucket",
        "change_trend",
    )


def test_all_supported_positions_are_defined():
    assert POSITIONS == (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    )


def test_validate_feature_schema_accepts_valid_schema():
    schema = make_schema()

    validate_feature_schema(schema)


def test_build_feature_schema_creates_valid_schema():
    schema = build_feature_schema(
        feature_name="col1_lag_1",
        feature_version="v1",
        feature_type="lag",
        source="lag_features",
        position="col1",
        window=None,
        lag=1,
        description="Previous historical value for col1.",
        availability_rule=(
            "Uses only observations strictly before the target date."
        ),
        data_type="integer",
    )

    assert isinstance(
        schema,
        FeatureSchema,
    )

    assert schema.feature_name == "col1_lag_1"


def test_feature_name_getter():
    schema = make_schema()

    assert get_feature_name(schema) == "col1_lag_1"


def test_feature_version_getter():
    schema = make_schema()

    assert get_feature_version(schema) == "v1"


def test_feature_type_getter():
    schema = make_schema()

    assert get_feature_type(schema) == "lag"


def test_feature_source_getter():
    schema = make_schema()

    assert get_feature_source(schema) == "lag_features"


def test_feature_position_getter():
    schema = make_schema()

    assert get_feature_position(schema) == "col1"


def test_feature_window_getter():
    schema = make_schema(
        feature_name="col1_rolling_3_mean",
        feature_type="rolling",
        source="rolling_features",
        window=3,
        lag=None,
    )

    assert get_feature_window(schema) == 3


def test_feature_lag_getter():
    schema = make_schema()

    assert get_feature_lag(schema) == 1


def test_feature_description_getter():
    schema = make_schema()

    assert (
        get_feature_description(schema)
        == "Previous historical value for col1."
    )


def test_feature_availability_rule_getter():
    schema = make_schema()

    assert (
        get_feature_availability_rule(schema)
        == "Uses only observations strictly before the target date."
    )


def test_feature_data_type_getter():
    schema = make_schema()

    assert get_feature_data_type(schema) == "integer"


def test_position_can_be_none():
    schema = make_schema(
        feature_name="cross_position_same",
        feature_type="cross_position",
        source="cross_position_features",
        position=None,
        lag=None,
    )

    validate_feature_schema(schema)

    assert get_feature_position(schema) is None


def test_window_can_be_none():
    schema = make_schema(
        window=None,
    )

    validate_feature_schema(schema)

    assert get_feature_window(schema) is None


def test_lag_can_be_none():
    schema = make_schema(
        lag=None,
    )

    validate_feature_schema(schema)

    assert get_feature_lag(schema) is None


def test_rolling_feature_can_define_window():
    schema = make_schema(
        feature_name="col1_rolling_5_mean",
        feature_type="rolling",
        source="rolling_features",
        window=5,
        lag=None,
    )

    validate_feature_schema(schema)

    assert schema.window == 5


def test_feature_schema_is_immutable():
    schema = make_schema()

    with pytest.raises(
        AttributeError,
    ):
        schema.feature_name = "changed"


def test_non_schema_object_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_schema(
            "invalid",
        )


def test_empty_feature_name_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                feature_name="",
            )
        )


def test_whitespace_feature_name_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                feature_name="   ",
            )
        )


def test_empty_feature_version_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                feature_version="",
            )
        )


def test_unsupported_feature_type_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                feature_type="unknown",
            )
        )


def test_empty_source_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                source="",
            )
        )


def test_unsupported_position_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                position="col9",
            )
        )


def test_zero_window_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                window=0,
                lag=None,
            )
        )


def test_negative_window_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                window=-1,
                lag=None,
            )
        )


def test_boolean_window_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_schema(
            make_schema(
                window=True,
                lag=None,
            )
        )


def test_zero_lag_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                lag=0,
            )
        )


def test_negative_lag_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                lag=-1,
            )
        )


def test_boolean_lag_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_schema(
            make_schema(
                lag=False,
            )
        )


def test_empty_description_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                description="",
            )
        )


def test_empty_availability_rule_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                availability_rule="",
            )
        )


def test_empty_data_type_is_rejected():
    with pytest.raises(ValueError):
        validate_feature_schema(
            make_schema(
                data_type="",
            )
        )


def test_invalid_feature_name_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_name("invalid")


def test_invalid_feature_version_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_version("invalid")


def test_invalid_feature_type_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_type("invalid")


def test_invalid_feature_source_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_source("invalid")


def test_invalid_feature_position_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_position("invalid")


def test_invalid_feature_window_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_window("invalid")


def test_invalid_feature_lag_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_lag("invalid")


def test_invalid_feature_description_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_description("invalid")


def test_invalid_feature_availability_rule_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_availability_rule("invalid")


def test_invalid_feature_data_type_getter_type_is_rejected():
    with pytest.raises(TypeError):
        get_feature_data_type("invalid")