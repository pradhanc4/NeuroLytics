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
    """

    feature_version: str = "v1"

    positions: tuple[str, ...] = POSITIONS

    lag_windows: tuple[int, ...] = (1, 2, 3)

    rolling_windows: tuple[int, ...] = (3, 5, 7)

    frequency_enabled: bool = True

    frequency_window: int = 5

    recency_enabled: bool = True

    recency_lookback: int = 10

    position_features_enabled: bool = True


def validate_feature_config(
    config: FeatureConfig,
) -> None:
    """Validate the complete Phase 13 feature configuration."""

    if not isinstance(config, FeatureConfig):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )

    if not isinstance(config.feature_version, str):
        raise ValueError(
            "feature_version must be a string."
        )

    if not config.feature_version.strip():
        raise ValueError(
            "feature_version is required."
        )

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

    if isinstance(config.frequency_enabled, bool) is False:
        raise ValueError(
            "frequency_enabled must be a boolean."
        )

    if isinstance(config.frequency_window, bool):
        raise ValueError(
            "frequency_window must be an integer."
        )

    if not isinstance(config.frequency_window, int):
        raise ValueError(
            "frequency_window must be an integer."
        )

    if config.frequency_window <= 0:
        raise ValueError(
            "frequency_window must be greater than zero."
        )

    if isinstance(config.recency_enabled, bool) is False:
        raise ValueError(
            "recency_enabled must be a boolean."
        )

    if isinstance(config.recency_lookback, bool):
        raise ValueError(
            "recency_lookback must be an integer."
        )

    if not isinstance(config.recency_lookback, int):
        raise ValueError(
            "recency_lookback must be an integer."
        )

    if config.recency_lookback <= 0:
        raise ValueError(
            "recency_lookback must be greater than zero."
        )

    if isinstance(config.position_features_enabled, bool) is False:
        raise ValueError(
            "position_features_enabled must be a boolean."
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