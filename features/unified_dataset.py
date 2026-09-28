from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from features.change_trend_features import (
    build_change_trend_features,
)
from features.cross_position_features import (
    build_cross_position_features,
)
from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.frequency_concentration_features import (
    build_frequency_concentration_features,
)
from features.frequency_change_features import (
    build_frequency_change_features,
)
from features.frequency_features import (
    build_frequency_features,
)
from features.family_recency import (
    build_family_recency_features,
)
from features.historical_family_frequency import (
    build_historical_family_frequency_features,
)
from features.historical_frequency_features import (
    build_historical_frequency_features,
)
from features.historical_interval_features import (
    build_historical_interval_features,
)
from features.lag_features import (
    build_lag_features,
)
from features.observation_density_features import (
    build_observation_density_features,
)
from features.point_in_time import (
    PointInTimeHistory,
)
from features.position_features import (
    build_position_features,
)
from features.recency_bucket_features import (
    build_recency_bucket_features,
)
from features.recency_distribution_features import (
    build_recency_distribution_features,
)
from features.recency_expansion_features import (
    build_recency_expansion_features,
)
from features.recency_features import (
    build_recency_features,
)
from features.rolling_features import (
    build_rolling_features,
)
from features.rolling_frequency_features import (
    build_rolling_frequency_features,
)
from features.sequence_features import (
    build_sequence_features,
)
from features.time_features import (
    build_time_features,
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
    def values(
        self,
    ) -> Mapping[
        str,
        int | float | str | bool | None,
    ]:
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
    """Append specialized feature records."""

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


def _extract_feature_value(
    record,
) -> int | float | str | bool | None:
    """Extract a value from specialized feature records."""

    if hasattr(record, "count") and hasattr(
        record,
        "percentage",
    ):
        if record.feature_name.endswith("_count"):
            return record.count

        if record.feature_name.endswith("_percentage"):
            return record.percentage

    if hasattr(
        record,
        "observations_since_last_seen",
    ):
        return record.observations_since_last_seen

    if hasattr(record, "mean"):
        if record.feature_name.endswith("_mean"):
            return record.mean

    if hasattr(record, "minimum"):
        if record.feature_name.endswith("_min"):
            return record.minimum

    if hasattr(record, "maximum"):
        if record.feature_name.endswith("_max"):
            return record.maximum

    if hasattr(record, "stability_percentage"):
        if record.feature_name.endswith("_stability_percentage"):
            return record.stability_percentage

    if hasattr(record, "trend_direction"):
        return record.trend_direction

    raise ValueError(
        "Unable to extract feature value: "
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
    db=None,
) -> UnifiedFeatureDataset:
    """
    Build the complete point-in-time feature dataset.

    Phase 13 features receive the canonical PointInTimeHistory.

    Phase 14 features that currently operate on historical
    observations receive the already-filtered history.observations.
    Therefore they cannot access the target-date or future rows.

    Phase 14 features that require PointInTimeHistory receive the
    canonical history object directly.

    Phase 15.6/15.7 family features require the SQLAlchemy session
    because authoritative family mappings are database-backed. They
    are integrated when ``db`` is supplied.

    Phase 15.11/15.12 scalar transition/relationship summaries are
    integrated directly. Event-level transition and relationship
    records remain standalone until their explicit schema/aggregation
    contract is introduced.

    No feature performs prediction.
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

    # ------------------------------------------------------------
    # Phase 13 - Leakage-safe foundation
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # Phase 14.2 / 14.3 - Time and cyclical time
    # ------------------------------------------------------------

    time_result = build_time_features(
        history.target_date,
    )

    _append_records(
        records,
        time_result,
        "time",
        "time_features",
    )

    # ------------------------------------------------------------
    # Phase 14.4 - Historical intervals
    # ------------------------------------------------------------

    historical_interval_result = (
        build_historical_interval_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        historical_interval_result,
        "historical_interval",
        "historical_interval_features",
    )

    # ------------------------------------------------------------
    # Phase 14.5 - Observation density
    # ------------------------------------------------------------

    observation_density_result = (
        build_observation_density_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        observation_density_result,
        "observation_density",
        "observation_density_features",
    )

    # ------------------------------------------------------------
    # Phase 14.6 - Historical frequency expansion
    # ------------------------------------------------------------

    historical_frequency_result = (
        build_historical_frequency_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        historical_frequency_result,
        "historical_frequency",
        "historical_frequency_features",
    )

    # ------------------------------------------------------------
    # Phase 14.7 - Rolling frequency
    # ------------------------------------------------------------

    rolling_frequency_result = (
        build_rolling_frequency_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        rolling_frequency_result,
        "rolling_frequency",
        "rolling_frequency_features",
    )

    # ------------------------------------------------------------
    # Phase 14.8 - Frequency change
    # ------------------------------------------------------------

    frequency_change_result = (
        build_frequency_change_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        frequency_change_result,
        "frequency_change",
        "frequency_change_features",
    )

    # ------------------------------------------------------------
    # Phase 14.9 - Frequency concentration/diversity
    # ------------------------------------------------------------

    frequency_concentration_result = (
        build_frequency_concentration_features(
            target_date=history.target_date,
            history=history.observations,
            config=config,
        )
    )

    _append_records(
        records,
        frequency_concentration_result,
        "frequency_concentration",
        "frequency_concentration_features",
    )

    # ------------------------------------------------------------
    # Phase 14.10 - Recency expansion
    # ------------------------------------------------------------

    recency_expansion_result = (
        build_recency_expansion_features(
            history,
            config,
        )
    )

    _append_records(
        records,
        recency_expansion_result,
        "recency_expansion",
        "recency_expansion_features",
    )

    # ------------------------------------------------------------
    # Phase 14.11 - Recency distribution
    # ------------------------------------------------------------

    recency_distribution_result = (
        build_recency_distribution_features(
            history,
            config,
        )
    )

    _append_records(
        records,
        recency_distribution_result,
        "recency_distribution",
        "recency_distribution_features",
    )

    # ------------------------------------------------------------
    # Phase 14.12 - Recency buckets
    # ------------------------------------------------------------

    recency_bucket_result = (
        build_recency_bucket_features(
            history.observations,
            history.target_date,
            config,
        )
    )

    _append_records(
        records,
        recency_bucket_result,
        "recency_bucket",
        "recency_bucket_features",
    )

    # ------------------------------------------------------------
    # Phase 14.13 - Change and trend
    # ------------------------------------------------------------

    change_trend_result = (
        build_change_trend_features(
            history.observations,
            history.target_date,
            config,
        )
    )

    _append_records(
        records,
        change_trend_result,
        "change_trend",
        "change_trend_features",
    )

    # ------------------------------------------------------------
    # Phase 15.6 / 15.7 - Family frequency and recency
    # ------------------------------------------------------------

    if db is not None:
        historical_family_frequency_result = (
            build_historical_family_frequency_features(
                db,
                history,
                history.target_date,
                config,
            )
        )

        _append_records(
            records,
            historical_family_frequency_result,
            "historical_family_frequency",
            "historical_family_frequency",
        )

        family_recency_result = build_family_recency_features(
            db,
            history,
            config,
        )

        _append_records(
            records,
            family_recency_result,
            "family_recency",
            "family_recency",
        )

    # ------------------------------------------------------------
    # Unified validation
    # ------------------------------------------------------------

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