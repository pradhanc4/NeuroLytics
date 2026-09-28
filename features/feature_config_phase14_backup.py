from __future__ import annotations

from dataclasses import dataclass


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
class FeatureConfig:
    """
    Configuration for leakage-safe feature generation.

    This configuration describes which historical feature families
    may be generated. It does not generate features itself.

    Phase 13:
        - lag
        - rolling
        - frequency
        - recency
        - position

    Phase 14:
        - time
        - cyclical time
        - historical intervals
        - observation density
        - expanded frequency
        - frequency change
        - frequency diversity
        - expanded recency
        - recency buckets
        - trend features
    """

    # ------------------------------------------------------------------
    # Core feature version
    # ------------------------------------------------------------------

    feature_version: str = "v1"

    # ------------------------------------------------------------------
    # Supported positions
    # ------------------------------------------------------------------

    positions: tuple[str, ...] = POSITIONS

    # ------------------------------------------------------------------
    # Phase 13 - Lag features
    # ------------------------------------------------------------------

    lag_windows: tuple[int, ...] = (1, 2, 3)

    # ------------------------------------------------------------------
    # Phase 13 - Rolling features
    # ------------------------------------------------------------------

    rolling_windows: tuple[int, ...] = (3, 5, 7)

    # ------------------------------------------------------------------
    # Phase 13 - Frequency features
    # ------------------------------------------------------------------

    frequency_enabled: bool = True

    frequency_window: int = 5

    # ------------------------------------------------------------------
    # Phase 13 - Recency features
    # ------------------------------------------------------------------

    recency_enabled: bool = True

    recency_lookback: int = 10

    # ------------------------------------------------------------------
    # Phase 13 - Position features
    # ------------------------------------------------------------------

    position_features_enabled: bool = True

    # ------------------------------------------------------------------
    # Phase 14 - Time features
    # ------------------------------------------------------------------

    time_features_enabled: bool = True

    cyclical_time_features_enabled: bool = True

    historical_interval_features_enabled: bool = True

    observation_density_features_enabled: bool = True

    observation_density_windows: tuple[int, ...] = (
        7,
        14,
        30,
        60,
        90,
    )

    # ------------------------------------------------------------------
    # Phase 14 - Frequency expansion
    # ------------------------------------------------------------------

    frequency_windows: tuple[int, ...] = (
        3,
        5,
        7,
        10,
        20,
    )

    frequency_change_enabled: bool = True

    frequency_comparison_windows: tuple[
        tuple[int, int], ...
    ] = (
        (3, 3),
        (5, 5),
    )

    frequency_diversity_enabled: bool = True

    # ------------------------------------------------------------------
    # Phase 14 - Recency expansion
    # ------------------------------------------------------------------

    recency_lookbacks: tuple[int, ...] = (
        3,
        5,
        7,
        10,
        20,
    )

    recency_calendar_enabled: bool = True

    recency_distribution_enabled: bool = True

    recency_buckets_enabled: bool = True

    recency_bucket_boundaries: tuple[int, ...] = (
        3,
        7,
        14,
    )

    # ------------------------------------------------------------------
    # Phase 14 - Change and trend features
    # ------------------------------------------------------------------

    change_features_enabled: bool = True

    trend_features_enabled: bool = True

    trend_windows: tuple[int, ...] = (
        3,
        5,
        7,
    )


def _validate_positive_integer(
    value: int,
    field_name: str,
) -> None:
    """Validate one positive integer configuration value."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )


def _validate_positive_integer_tuple(
    values: tuple[int, ...],
    field_name: str,
) -> None:
    """Validate a non-empty tuple of unique positive integers."""

    if not values:
        raise ValueError(
            f"At least one {field_name} value is required."
        )

    for value in values:
        _validate_positive_integer(
            value,
            field_name,
        )

    if len(set(values)) != len(values):
        raise ValueError(
            f"{field_name} must not contain duplicates."
        )


def _validate_boolean(
    value: bool,
    field_name: str,
) -> None:
    """Validate a boolean configuration value."""

    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a boolean."
        )


def _validate_comparison_windows(
    windows: tuple[tuple[int, int], ...],
) -> None:
    """Validate Phase 14 frequency comparison windows."""

    if not windows:
        raise ValueError(
            "At least one frequency comparison window is required."
        )

    for comparison in windows:
        if (
            not isinstance(comparison, tuple)
            or len(comparison) != 2
        ):
            raise ValueError(
                "frequency_comparison_windows must contain "
                "two-value tuples."
            )

        recent_window, previous_window = comparison

        _validate_positive_integer(
            recent_window,
            "frequency comparison recent window",
        )

        _validate_positive_integer(
            previous_window,
            "frequency comparison previous window",
        )

    if len(set(windows)) != len(windows):
        raise ValueError(
            "frequency_comparison_windows must not contain duplicates."
        )


def validate_feature_config(
    config: FeatureConfig,
) -> None:
    """Validate the complete Phase 13 and Phase 14 configuration."""

    if not isinstance(config, FeatureConfig):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )

    # ------------------------------------------------------------------
    # Core configuration
    # ------------------------------------------------------------------

    if not isinstance(config.feature_version, str):
        raise ValueError(
            "feature_version must be a string."
        )

    if not config.feature_version.strip():
        raise ValueError(
            "feature_version is required."
        )

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    if not config.positions:
        raise ValueError(
            "At least one position is required."
        )

    if len(set(config.positions)) != len(config.positions):
        raise ValueError(
            "positions must not contain duplicates."
        )

    for position in config.positions:
        if position not in POSITIONS:
            raise ValueError(
                f"Unsupported position: {position}."
            )

    # ------------------------------------------------------------------
    # Phase 13 - Lag
    # Preserve the existing Phase 13 validation/error contract.
    # ------------------------------------------------------------------

    if not config.lag_windows:
        raise ValueError(
            "At least one lag window is required."
        )

    for lag in config.lag_windows:
        if isinstance(lag, bool) or not isinstance(lag, int):
            raise ValueError(
                "lag_windows must contain integers."
            )

        if lag <= 0:
            raise ValueError(
                "lag windows must be greater than zero."
            )

    if len(set(config.lag_windows)) != len(
        config.lag_windows
    ):
        raise ValueError(
            "lag_windows must not contain duplicates."
        )

    # ------------------------------------------------------------------
    # Phase 13 - Rolling
    # Preserve the existing Phase 13 validation/error contract.
    # ------------------------------------------------------------------

    if not config.rolling_windows:
        raise ValueError(
            "At least one rolling window is required."
        )

    for window in config.rolling_windows:
        if isinstance(window, bool) or not isinstance(window, int):
            raise ValueError(
                "rolling_windows must contain integers."
            )

        if window <= 0:
            raise ValueError(
                "rolling windows must be greater than zero."
            )

    if len(set(config.rolling_windows)) != len(
        config.rolling_windows
    ):
        raise ValueError(
            "rolling_windows must not contain duplicates."
        )

    # ------------------------------------------------------------------
    # Phase 13 - Frequency
    # ------------------------------------------------------------------

    _validate_boolean(
        config.frequency_enabled,
        "frequency_enabled",
    )

    _validate_positive_integer(
        config.frequency_window,
        "frequency_window",
    )

    # ------------------------------------------------------------------
    # Phase 13 - Recency
    # ------------------------------------------------------------------

    _validate_boolean(
        config.recency_enabled,
        "recency_enabled",
    )

    _validate_positive_integer(
        config.recency_lookback,
        "recency_lookback",
    )

    # ------------------------------------------------------------------
    # Phase 13 - Position
    # ------------------------------------------------------------------

    _validate_boolean(
        config.position_features_enabled,
        "position_features_enabled",
    )

    # ------------------------------------------------------------------
    # Phase 14 - Time
    # ------------------------------------------------------------------

    _validate_boolean(
        config.time_features_enabled,
        "time_features_enabled",
    )

    _validate_boolean(
        config.cyclical_time_features_enabled,
        "cyclical_time_features_enabled",
    )

    _validate_boolean(
        config.historical_interval_features_enabled,
        "historical_interval_features_enabled",
    )

    _validate_boolean(
        config.observation_density_features_enabled,
        "observation_density_features_enabled",
    )

    _validate_positive_integer_tuple(
        config.observation_density_windows,
        "observation_density_windows",
    )

    # ------------------------------------------------------------------
    # Phase 14 - Frequency
    # ------------------------------------------------------------------

    _validate_positive_integer_tuple(
        config.frequency_windows,
        "frequency_windows",
    )

    _validate_boolean(
        config.frequency_change_enabled,
        "frequency_change_enabled",
    )

    _validate_comparison_windows(
        config.frequency_comparison_windows,
    )

    _validate_boolean(
        config.frequency_diversity_enabled,
        "frequency_diversity_enabled",
    )

    # ------------------------------------------------------------------
    # Phase 14 - Recency
    # ------------------------------------------------------------------

    _validate_positive_integer_tuple(
        config.recency_lookbacks,
        "recency_lookbacks",
    )

    _validate_boolean(
        config.recency_calendar_enabled,
        "recency_calendar_enabled",
    )

    _validate_boolean(
        config.recency_distribution_enabled,
        "recency_distribution_enabled",
    )

    _validate_boolean(
        config.recency_buckets_enabled,
        "recency_buckets_enabled",
    )

    _validate_positive_integer_tuple(
        config.recency_bucket_boundaries,
        "recency_bucket_boundaries",
    )

    if tuple(sorted(config.recency_bucket_boundaries)) != (
        config.recency_bucket_boundaries
    ):
        raise ValueError(
            "recency_bucket_boundaries must be in ascending order."
        )

    # ------------------------------------------------------------------
    # Phase 14 - Change and trend
    # ------------------------------------------------------------------

    _validate_boolean(
        config.change_features_enabled,
        "change_features_enabled",
    )

    _validate_boolean(
        config.trend_features_enabled,
        "trend_features_enabled",
    )

    _validate_positive_integer_tuple(
        config.trend_windows,
        "trend_windows",
    )


def get_feature_version(
    config: FeatureConfig,
) -> str:
    """Return the configured feature version."""

    validate_feature_config(config)

    return config.feature_version


def get_feature_positions(
    config: FeatureConfig,
) -> tuple[str, ...]:
    """Return the configured feature positions."""

    validate_feature_config(config)

    return config.positions


def get_lag_windows(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return configured lag windows."""

    validate_feature_config(config)

    return config.lag_windows


def get_rolling_windows(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return configured rolling windows."""

    validate_feature_config(config)

    return config.rolling_windows


def get_frequency_windows(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return Phase 14 frequency windows."""

    validate_feature_config(config)

    return config.frequency_windows


def get_frequency_comparison_windows(
    config: FeatureConfig,
) -> tuple[tuple[int, int], ...]:
    """Return Phase 14 frequency comparison windows."""

    validate_feature_config(config)

    return config.frequency_comparison_windows


def get_recency_lookbacks(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return Phase 14 recency lookback windows."""

    validate_feature_config(config)

    return config.recency_lookbacks


def get_recency_bucket_boundaries(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return Phase 14 recency bucket boundaries."""

    validate_feature_config(config)

    return config.recency_bucket_boundaries


def get_trend_windows(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return Phase 14 trend windows."""

    validate_feature_config(config)

    return config.trend_windows


def get_observation_density_windows(
    config: FeatureConfig,
) -> tuple[int, ...]:
    """Return Phase 14 observation density windows."""

    validate_feature_config(config)

    return config.observation_density_windows