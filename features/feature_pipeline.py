from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.feature_schema import FeatureSchema
from features.feature_schema_builder import (
    build_feature_schemas,
)
from features.feature_validator import (
    FeatureValidationResult,
    validate_feature_dataset,
)
from features.feature_versioning import (
    FeatureVersionIdentity,
    build_feature_version_from_dataset,
)
from features.historical_data_loader import (
    HistoricalFeatureObservation,
    load_historical_observations,
)
from features.leakage_detector import (
    LeakageDetectionResult,
    detect_point_in_time_history_leakage,
)
from features.point_in_time import (
    PointInTimeHistory,
    build_point_in_time_history,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    build_unified_feature_dataset,
)

from database.models import Market
from database.services import HistoricalResultService


@dataclass(frozen=True)
class FeaturePipelineResult:
    """Complete output of the Phase 13 feature pipeline."""

    market_id: int
    target_date: date
    historical_observation_count: int
    point_in_time_observation_count: int
    dataset: UnifiedFeatureDataset
    schemas: tuple[FeatureSchema, ...]
    validation: FeatureValidationResult
    leakage: LeakageDetectionResult
    version_identity: FeatureVersionIdentity

    @property
    def feature_count(self) -> int:
        return self.dataset.feature_count

    @property
    def feature_version(self) -> str:
        return self.dataset.feature_version

    @property
    def is_valid(self) -> bool:
        return (
            self.validation.is_valid
            and self.leakage.is_clean
        )


def _validate_market(
    market: Market,
) -> None:
    if not isinstance(
        market,
        Market,
    ):
        raise TypeError(
            "market must be a Market instance."
        )

    if market.id is None:
        raise ValueError(
            "Market must have a database ID."
        )


def _validate_service(
    service: HistoricalResultService,
) -> None:
    if not isinstance(
        service,
        HistoricalResultService,
    ):
        raise TypeError(
            "service must be a HistoricalResultService instance."
        )


def _validate_target_date(
    target_date: date,
) -> None:
    if not isinstance(
        target_date,
        date,
    ):
        raise TypeError(
            "target_date must be a datetime.date instance."
        )


def _build_point_in_time_history(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
    target_date: date,
) -> PointInTimeHistory:
    return build_point_in_time_history(
        observations,
        target_date,
    )


def build_feature_pipeline(
    service: HistoricalResultService,
    market: Market,
    target_date: date,
    config: FeatureConfig,
) -> FeaturePipelineResult:
    """
    Execute the complete Phase 13 feature pipeline.

    Pipeline order:

    SQL historical data
        -> historical loader
        -> point-in-time history
        -> unified feature dataset
        -> feature schemas
        -> feature validation
        -> leakage validation
        -> reproducibility identity
    """

    _validate_service(
        service
    )

    _validate_market(
        market
    )

    _validate_target_date(
        target_date
    )

    validate_feature_config(
        config
    )

    observations = load_historical_observations(
        service,
        market,
    )

    history = _build_point_in_time_history(
        observations,
        target_date,
    )

    dataset = build_unified_feature_dataset(
        history,
        config,
    )

    schemas = build_feature_schemas(
        dataset
    )

    validation = validate_feature_dataset(
        dataset
    )

    leakage = detect_point_in_time_history_leakage(
        history
    )

    version_identity = (
        build_feature_version_from_dataset(
            dataset,
            schemas,
        )
    )

    return FeaturePipelineResult(
        market_id=market.id,
        target_date=target_date,
        historical_observation_count=len(
            observations
        ),
        point_in_time_observation_count=(
            history.observation_count
        ),
        dataset=dataset,
        schemas=schemas,
        validation=validation,
        leakage=leakage,
        version_identity=version_identity,
    )


def get_pipeline_dataset(
    result: FeaturePipelineResult,
) -> UnifiedFeatureDataset:
    """Return the unified feature dataset."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.dataset


def get_pipeline_schemas(
    result: FeaturePipelineResult,
) -> tuple[FeatureSchema, ...]:
    """Return feature schemas."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.schemas


def get_pipeline_validation(
    result: FeaturePipelineResult,
) -> FeatureValidationResult:
    """Return feature validation result."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.validation


def get_pipeline_leakage(
    result: FeaturePipelineResult,
) -> LeakageDetectionResult:
    """Return leakage detection result."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.leakage


def get_pipeline_version_identity(
    result: FeaturePipelineResult,
) -> FeatureVersionIdentity:
    """Return reproducibility identity."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.version_identity


def get_pipeline_feature_count(
    result: FeaturePipelineResult,
) -> int:
    """Return generated feature count."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.feature_count


def is_pipeline_valid(
    result: FeaturePipelineResult,
) -> bool:
    """Return whether validation and leakage checks both pass."""

    if not isinstance(
        result,
        FeaturePipelineResult,
    ):
        raise TypeError(
            "result must be a FeaturePipelineResult instance."
        )

    return result.is_valid