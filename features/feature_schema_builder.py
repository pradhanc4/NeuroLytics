from __future__ import annotations

from features.feature_schema import (
    FeatureSchema,
    build_feature_schema,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)


DEFAULT_AVAILABILITY_RULE = (
    "Uses only observations strictly before the target date."
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


def _extract_position(
    feature_name: str,
) -> str | None:
    """Extract col1-col8 when the feature belongs to a position."""

    first_part = feature_name.split("_", 1)[0]

    if first_part in POSITIONS:
        return first_part

    return None


def _extract_lag(
    feature_name: str,
) -> int | None:
    """Extract lag number from a lag feature name."""

    parts = feature_name.split("_")

    if len(parts) >= 3 and parts[1] == "lag":
        try:
            return int(parts[2])
        except ValueError:
            return None

    return None


def _safe_integer(
    value: str,
) -> int | None:
    """Convert a string to an integer when possible."""

    try:
        return int(value)
    except ValueError:
        return None


def _extract_window(
    feature_name: str,
    feature_type: str,
) -> int | None:
    """
    Extract a single meaningful window/lookback from a
    feature name.

    Feature families with multiple independent windows, such as
    frequency_change, intentionally return None because no single
    window accurately represents the feature.
    """

    parts = feature_name.split("_")

    if feature_type == "rolling":
        # Phase 13:
        # col1_rolling_5_mean
        if len(parts) >= 3:
            return _safe_integer(parts[2])

        return None

    if feature_type == "historical_frequency":
        # Phase 14:
        # col1_frequency_count_5_0
        # col1_frequency_percentage_5_0
        if len(parts) >= 4:
            return _safe_integer(parts[3])

        return None

    if feature_type == "rolling_frequency":
        # Phase 14:
        # col1_rolling_frequency_5_0
        if len(parts) >= 4:
            return _safe_integer(parts[3])

        return None

    if feature_type == "frequency_concentration":
        # Phase 14:
        # col1_frequency_dominant_digit_5
        # col1_frequency_entropy_5
        if len(parts) >= 5:
            return _safe_integer(parts[4])

        return None

    if feature_type == "observation_density":
        # Phase 14:
        # observation_density_count_7
        # observation_density_rate_7
        if len(parts) >= 4:
            return _safe_integer(parts[3])

        return None

    if feature_type == "recency_expansion":
        # Phase 14:
        # col1_digit_0_recency_expansion_count_3
        # col1_digit_0_recency_expansion_rate_3
        # col1_digit_0_recency_expansion_last_distance_3
        # col1_digit_0_recency_expansion_seen_3
        if parts:
            return _safe_integer(parts[-1])

        return None

    if feature_type == "recency_distribution":
        # Phase 14:
        # col1_digit_0_recency_distribution_count_3
        # col1_digit_0_recency_distribution_mean_distance_3
        if parts:
            return _safe_integer(parts[-1])

        return None

    if feature_type == "recency_bucket":
        # Phase 14:
        # col1_digit_0_recency_bucket_label_3
        # col1_digit_0_recency_bucket_index_3
        # col1_digit_0_recency_bucket_is_unseen_3
        if parts:
            return _safe_integer(parts[-1])

        return None

    if feature_type == "change_trend":
        # Change features have no window:
        # col1_change
        # col1_absolute_change
        # col1_change_direction
        #
        # Trend features do:
        # col1_trend_mean_3
        # col1_trend_std_5
        # col1_trend_slope_7
        if "trend" in parts:
            trend_index = parts.index("trend")

            if len(parts) > trend_index + 2:
                return _safe_integer(
                    parts[-1]
                )

        return None

    if feature_type == "historical_family_frequency":
        # Phase 15:
        # panna_family_frequency_count_5_FamilyA
        # panna_family_frequency_percentage_5_FamilyA
        # jodi_family_frequency_count_7_FamilyB
        # panel_family_frequency_percentage_10_FamilyC
        #
        # Structure:
        # family_type_family_frequency_metric_window_family
        #
        # Example:
        # panna_family_frequency_count_5_FamilyA
        # parts = [
        #     "panna",
        #     "family",
        #     "frequency",
        #     "count",
        #     "5",
        #     "FamilyA",
        # ]
        if len(parts) >= 5:
            return _safe_integer(parts[4])

        return None

    if feature_type == "family_recency":
        # Phase 15:
        #
        # Recency feature:
        # panna_family_recency_FamilyA
        #
        # Seen-within-lookback feature:
        # panna_family_seen_within_lookback_5_FamilyA
        #
        # Only the latter has a meaningful lookback.
        if (
            len(parts) >= 6
            and parts[1] == "family"
            and parts[2] == "seen"
            and parts[3] == "within"
            and parts[4] == "lookback"
        ):
            return _safe_integer(parts[5])

        return None

    # These feature families either do not have a single
    # window or their window is represented elsewhere.
    if feature_type in (
        "frequency",
        "time",
        "historical_interval",
        "frequency_change",
    ):
        return None

    return None


def _build_description(
    record: UnifiedFeatureRecord,
) -> str:
    """Build deterministic human-readable feature description."""

    return (
        f"{record.feature_type} feature generated by "
        f"{record.source}."
    )


def _infer_data_type(
    value,
) -> str:
    """Infer a controlled schema data type."""

    if value is None:
        return "unknown"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "float"

    if isinstance(value, str):
        return "string"

    raise TypeError(
        f"Unsupported feature value type: "
        f"{type(value).__name__}"
    )


def build_feature_schema_from_record(
    record: UnifiedFeatureRecord,
    feature_version: str,
) -> FeatureSchema:
    """Build schema metadata for one unified feature record."""

    if not isinstance(
        record,
        UnifiedFeatureRecord,
    ):
        raise TypeError(
            "record must be a UnifiedFeatureRecord instance."
        )

    if not isinstance(
        feature_version,
        str,
    ):
        raise TypeError(
            "feature_version must be a string."
        )

    position = _extract_position(
        record.feature_name
    )

    lag = _extract_lag(
        record.feature_name
    )

    window = _extract_window(
        record.feature_name,
        record.feature_type,
    )

    return build_feature_schema(
        feature_name=record.feature_name,
        feature_version=feature_version,
        feature_type=record.feature_type,
        source=record.source,
        position=position,
        window=window,
        lag=lag,
        description=_build_description(record),
        availability_rule=DEFAULT_AVAILABILITY_RULE,
        data_type=_infer_data_type(record.value),
    )


def build_feature_schemas(
    dataset: UnifiedFeatureDataset,
) -> tuple[FeatureSchema, ...]:
    """Build schema metadata for every feature in a dataset."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    schemas = tuple(
        build_feature_schema_from_record(
            record,
            dataset.feature_version,
        )
        for record in dataset.records
    )

    feature_names = tuple(
        schema.feature_name
        for schema in schemas
    )

    if len(feature_names) != len(
        set(feature_names)
    ):
        raise ValueError(
            "Duplicate feature names detected "
            "in generated feature schemas."
        )

    return schemas


def get_schema_by_feature_name(
    schemas: tuple[FeatureSchema, ...],
    feature_name: str,
) -> FeatureSchema:
    """Return one schema by feature name."""

    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple of FeatureSchema objects."
        )

    if not isinstance(
        feature_name,
        str,
    ):
        raise TypeError(
            "feature_name must be a string."
        )

    for schema in schemas:
        if not isinstance(
            schema,
            FeatureSchema,
        ):
            raise TypeError(
                "schemas must contain only FeatureSchema objects."
            )

        if schema.feature_name == feature_name:
            return schema

    raise ValueError(
        f"Feature schema not found: {feature_name}"
    )


def get_schema_feature_names(
    schemas: tuple[FeatureSchema, ...],
) -> tuple[str, ...]:
    """Return schema feature names in deterministic order."""

    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple of FeatureSchema objects."
        )

    for schema in schemas:
        if not isinstance(
            schema,
            FeatureSchema,
        ):
            raise TypeError(
                "schemas must contain only FeatureSchema objects."
            )

    return tuple(
        schema.feature_name
        for schema in schemas
    )


def get_schema_count(
    schemas: tuple[FeatureSchema, ...],
) -> int:
    """Return the number of generated schemas."""

    if not isinstance(
        schemas,
        tuple,
    ):
        raise TypeError(
            "schemas must be a tuple of FeatureSchema objects."
        )

    return len(schemas)