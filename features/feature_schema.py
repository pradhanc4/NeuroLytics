from __future__ import annotations

from dataclasses import dataclass


FEATURE_TYPES = (
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

    # Phase 15
    "historical_family_frequency",
    "family_recency",
)


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


@dataclass(frozen=True)
class FeatureSchema:
    """Metadata describing one leakage-safe ML feature."""

    feature_name: str
    feature_version: str
    feature_type: str
    source: str
    position: str | None
    window: int | None
    lag: int | None
    description: str
    availability_rule: str
    data_type: str


def _validate_non_empty_string(
    value: str,
    field_name: str,
) -> None:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    if not value.strip():
        raise ValueError(
            f"{field_name} must not be empty."
        )


def _validate_optional_positive_integer(
    value: int | None,
    field_name: str,
) -> None:
    if value is None:
        return

    if isinstance(value, bool):
        raise TypeError(
            f"{field_name} must be an integer or None."
        )

    if not isinstance(value, int):
        raise TypeError(
            f"{field_name} must be an integer or None."
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )


def validate_feature_schema(
    schema: FeatureSchema,
) -> None:
    """Validate one feature schema definition."""

    if not isinstance(
        schema,
        FeatureSchema,
    ):
        raise TypeError(
            "schema must be a FeatureSchema instance."
        )

    _validate_non_empty_string(
        schema.feature_name,
        "feature_name",
    )

    _validate_non_empty_string(
        schema.feature_version,
        "feature_version",
    )

    _validate_non_empty_string(
        schema.feature_type,
        "feature_type",
    )

    if schema.feature_type not in FEATURE_TYPES:
        raise ValueError(
            f"Unsupported feature type: "
            f"{schema.feature_type}"
        )

    _validate_non_empty_string(
        schema.source,
        "source",
    )

    if schema.position is not None:
        if schema.position not in POSITIONS:
            raise ValueError(
                f"Unsupported position: "
                f"{schema.position}"
            )

    _validate_optional_positive_integer(
        schema.window,
        "window",
    )

    _validate_optional_positive_integer(
        schema.lag,
        "lag",
    )

    _validate_non_empty_string(
        schema.description,
        "description",
    )

    _validate_non_empty_string(
        schema.availability_rule,
        "availability_rule",
    )

    _validate_non_empty_string(
        schema.data_type,
        "data_type",
    )


def build_feature_schema(
    feature_name: str,
    feature_version: str,
    feature_type: str,
    source: str,
    position: str | None,
    window: int | None,
    lag: int | None,
    description: str,
    availability_rule: str,
    data_type: str,
) -> FeatureSchema:
    """Create and validate one feature schema."""

    schema = FeatureSchema(
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

    validate_feature_schema(schema)

    return schema


def get_feature_name(
    schema: FeatureSchema,
) -> str:
    """Return the feature name."""

    validate_feature_schema(schema)

    return schema.feature_name


def get_feature_version(
    schema: FeatureSchema,
) -> str:
    """Return the feature version."""

    validate_feature_schema(schema)

    return schema.feature_version


def get_feature_type(
    schema: FeatureSchema,
) -> str:
    """Return the feature type."""

    validate_feature_schema(schema)

    return schema.feature_type


def get_feature_source(
    schema: FeatureSchema,
) -> str:
    """Return the feature source."""

    validate_feature_schema(schema)

    return schema.source


def get_feature_position(
    schema: FeatureSchema,
) -> str | None:
    """Return the associated position."""

    validate_feature_schema(schema)

    return schema.position


def get_feature_window(
    schema: FeatureSchema,
) -> int | None:
    """Return the rolling/frequency/sequence window."""

    validate_feature_schema(schema)

    return schema.window


def get_feature_lag(
    schema: FeatureSchema,
) -> int | None:
    """Return the lag value."""

    validate_feature_schema(schema)

    return schema.lag


def get_feature_description(
    schema: FeatureSchema,
) -> str:
    """Return the feature description."""

    validate_feature_schema(schema)

    return schema.description


def get_feature_availability_rule(
    schema: FeatureSchema,
) -> str:
    """Return the point-in-time availability rule."""

    validate_feature_schema(schema)

    return schema.availability_rule


def get_feature_data_type(
    schema: FeatureSchema,
) -> str:
    """Return the declared data type."""

    validate_feature_schema(schema)

    return schema.data_type