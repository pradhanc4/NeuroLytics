from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from features.cross_position_features import (
    build_cross_position_features,
)
from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.frequency_features import (
    build_frequency_features,
)
from features.lag_features import (
    build_lag_features,
)
from features.point_in_time import (
    PointInTimeHistory,
)
from features.position_features import (
    build_position_features,
)
from features.recency_features import (
    build_recency_features,
)
from features.rolling_features import (
    build_rolling_features,
)
from features.sequence_features import (
    build_sequence_features,
)


@dataclass(frozen=True)
class UnifiedFeatureRecord:
    """One feature in the unified feature dataset."""

    feature_name: str
    value: int | float | str | bool | None
    feature_type: str
    source: str


@dataclass(frozen=True)
class UnifiedFeatureDataset:
    """Complete feature dataset for one target date."""

    target_date: date
    feature_version: str
    records: tuple[UnifiedFeatureRecord, ...]

    @property
    def feature_count(self) -> int:
        """Return the number of generated features."""

        return len(self.records)

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Return feature names in deterministic order."""

        return tuple(
            record.feature_name
            for record in self.records
        )

    @property
    def values(self) -> Mapping[str, int | float | str | bool | None]:
        """Return feature values keyed by feature name."""

        return {
            record.feature_name: record.value
            for record in self.records
        }


def _append_records(
    records: list[UnifiedFeatureRecord],
    source_result,
    feature_type: str,
    source: str,
) -> None:
    """Append feature-engine records to the unified dataset."""

    for record in source_result.records:
        records.append(
            UnifiedFeatureRecord(
                feature_name=record.feature_name,
                value=(
                    record.value
                    if hasattr(record, "value")
                    else _extract_feature_value(record)
                ),
                feature_type=feature_type,
                source=source,
            )
        )


def _extract_feature_value(record) -> int | float | str | bool | None:
    """Extract a value from specialized feature records."""

    if hasattr(record, "count") and hasattr(
        record,
        "percentage",
    ):
        if record.feature_name.endswith(
            "_count"
        ):
            return record.count

        if record.feature_name.endswith(
            "_percentage"
        ):
            return record.percentage

    if hasattr(
        record,
        "observations_since_last_seen",
    ):
        return record.observations_since_last_seen

    if hasattr(
        record,
        "mean",
    ):
        if record.feature_name.endswith(
            "_mean"
        ):
            return record.mean

    if hasattr(
        record,
        "minimum",
    ):
        if record.feature_name.endswith(
            "_min"
        ):
            return record.minimum

    if hasattr(
        record,
        "maximum",
    ):
        if record.feature_name.endswith(
            "_max"
        ):
            return record.maximum

    raise ValueError(
        f"Unable to extract feature value: "
        f"{record.feature_name}"
    )


def _validate_unique_feature_names(
    records: list[UnifiedFeatureRecord],
) -> None:
    """Reject duplicate feature names."""

    names = [
        record.feature_name
        for record in records
    ]

    if len(names) != len(set(names)):
        duplicates = sorted(
            {
                name
                for name in names
                if names.count(name) > 1
            }
        )

        raise ValueError(
            "Duplicate feature names detected: "
            + ", ".join(duplicates)
        )


def _validate_feature_records(
    records: list[UnifiedFeatureRecord],
) -> None:
    """Validate unified feature records."""

    for record in records:
        if not isinstance(
            record,
            UnifiedFeatureRecord,
        ):
            raise TypeError(
                "records must contain only "
                "UnifiedFeatureRecord objects."
            )

        if not isinstance(
            record.feature_name,
            str,
        ) or not record.feature_name:
            raise ValueError(
                "Feature name must be a non-empty string."
            )

        if not isinstance(
            record.feature_type,
            str,
        ) or not record.feature_type:
            raise ValueError(
                "Feature type must be a non-empty string."
            )

        if not isinstance(
            record.source,
            str,
        ) or not record.source:
            raise ValueError(
                "Feature source must be a non-empty string."
            )


def build_unified_feature_dataset(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> UnifiedFeatureDataset:
    """
    Build the complete point-in-time feature dataset.

    No target-date or future observation is accessed directly.
    Every component receives the same PointInTimeHistory object.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[UnifiedFeatureRecord] = []

    lag_result = build_lag_features(
        history,
        config,
    )

    _append_records(
        records,
        lag_result,
        "lag",
        "lag_features",
    )

    rolling_result = build_rolling_features(
        history,
        config,
    )

    _append_records(
        records,
        rolling_result,
        "rolling",
        "rolling_features",
    )

    recency_result = build_recency_features(
        history,
        config,
    )

    _append_records(
        records,
        recency_result,
        "recency",
        "recency_features",
    )

    position_result = build_position_features(
        history,
        config,
    )

    _append_records(
        records,
        position_result,
        "position",
        "position_features",
    )

    frequency_result = build_frequency_features(
        history,
        config,
    )

    _append_records(
        records,
        frequency_result,
        "frequency",
        "frequency_features",
    )

    sequence_result = build_sequence_features(
        history,
        config,
    )

    _append_records(
        records,
        sequence_result,
        "sequence",
        "sequence_features",
    )

    cross_position_result = (
        build_cross_position_features(
            history,
            config,
        )
    )

    _append_records(
        records,
        cross_position_result,
        "cross_position",
        "cross_position_features",
    )

    _validate_feature_records(records)
    _validate_unique_feature_names(records)

    return UnifiedFeatureDataset(
        target_date=history.target_date,
        feature_version=config.feature_version,
        records=tuple(records),
    )


def get_unified_feature_value(
    dataset: UnifiedFeatureDataset,
    feature_name: str,
):
    """Return one feature value."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    if not isinstance(
        feature_name,
        str,
    ):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in dataset.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Feature not found: {feature_name}"
    )


def get_unified_feature_names(
    dataset: UnifiedFeatureDataset,
) -> tuple[str, ...]:
    """Return all unified feature names."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    return dataset.feature_names


def get_unified_feature_values(
    dataset: UnifiedFeatureDataset,
) -> Mapping[
    str,
    int | float | str | bool | None,
]:
    """Return all feature values."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    return dataset.values


def get_unified_feature_count(
    dataset: UnifiedFeatureDataset,
) -> int:
    """Return the total number of unified features."""

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    return dataset.feature_count