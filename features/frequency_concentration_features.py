from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log2
from typing import Iterable

from analytics.distribution_regime_detection import (
    DistributionRegimeWindow,
    build_distribution_regime_detection,
)
from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
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

DIGITS = tuple(range(10))

REGIMES = (
    "CONCENTRATED",
    "BALANCED",
    "DIVERSE",
    "INSUFFICIENT_DATA",
)


@dataclass(frozen=True)
class FrequencyConcentrationFeatureRecord:
    """One frequency concentration/diversity feature."""

    feature_name: str
    value: float | int | str | None
    feature_type: str
    position: str
    window: int
    digit: int | None
    source: str


@dataclass(frozen=True)
class FrequencyConcentrationFeatureResult:
    """Point-in-time frequency concentration/diversity feature result."""

    target_date: date
    records: tuple[FrequencyConcentrationFeatureRecord, ...]


def _validate_target_date(target_date: date) -> None:
    if not isinstance(target_date, date):
        raise TypeError("target_date must be a date.")


def _validate_history(
    history: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    if isinstance(history, (str, bytes)):
        raise TypeError(
            "history must be an iterable of HistoricalFeatureObservation."
        )

    validated = []

    for observation in history:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "history must contain HistoricalFeatureObservation objects."
            )

        validated.append(observation)

    return tuple(validated)


def _validate_config(config: FeatureConfig) -> None:
    if not isinstance(config, FeatureConfig):
        raise TypeError("config must be a FeatureConfig instance.")


def _position_index(position: str) -> int:
    if position not in POSITIONS:
        raise ValueError(
            f"unsupported position: {position}"
        )

    return POSITIONS.index(position)


def _point_in_time_history(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
) -> tuple[HistoricalFeatureObservation, ...]:
    """Return only observations strictly before target_date."""

    filtered = tuple(
        observation
        for observation in history
        if observation.result_date < target_date
    )

    return tuple(
        sorted(
            filtered,
            key=lambda observation: observation.result_date,
        )
    )


def _window_observations(
    history: tuple[HistoricalFeatureObservation, ...],
    position: str,
    window: int,
) -> tuple[tuple[date, int | None], ...]:
    """Build the trailing observation-count window for one position."""

    index = _position_index(position)

    observations = tuple(
        (
            observation.result_date,
            observation.positions[index],
        )
        for observation in history
    )

    return observations[-window:]


def _build_regime_window(
    observations: tuple[tuple[date, int | None], ...],
    position: str,
    window: int,
) -> DistributionRegimeWindow | None:
    if not observations:
        return None

    detection = build_distribution_regime_detection(
        position=position,
        observations=observations,
        window_size=window,
    )

    if not detection.windows:
        return None

    return detection.windows[-1]


def _normalized_entropy(
    entropy: float | None,
) -> float | None:
    if entropy is None:
        return None

    maximum_entropy = log2(10)

    if maximum_entropy == 0:
        return None

    return entropy / maximum_entropy


def _feature_name(
    position: str,
    metric: str,
    window: int,
) -> str:
    return f"{position}_frequency_{metric}_{window}"


def _append_record(
    records: list[FrequencyConcentrationFeatureRecord],
    feature_name: str,
    value: float | int | str | None,
    position: str,
    window: int,
    digit: int | None = None,
) -> None:
    records.append(
        FrequencyConcentrationFeatureRecord(
            feature_name=feature_name,
            value=value,
            feature_type="frequency_concentration",
            position=position,
            window=window,
            digit=digit,
            source="analytics.distribution_regime_detection",
        )
    )


def _build_position_window_features(
    records: list[FrequencyConcentrationFeatureRecord],
    position: str,
    window: int,
    history: tuple[HistoricalFeatureObservation, ...],
) -> None:
    observations = _window_observations(
        history=history,
        position=position,
        window=window,
    )

    regime_window = _build_regime_window(
        observations=observations,
        position=position,
        window=window,
    )

    dominant_digit: int | None = None
    dominant_percentage: float | None = None
    entropy: float | None = None
    normalized_entropy: float | None = None
    regime = "INSUFFICIENT_DATA"

    if regime_window is not None:
        dominant_digit = regime_window.dominant_digit
        dominant_percentage = regime_window.dominant_digit_percentage
        entropy = regime_window.entropy
        normalized_entropy = _normalized_entropy(entropy)
        regime = regime_window.regime

    _append_record(
        records,
        _feature_name(
            position,
            "dominant_digit",
            window,
        ),
        dominant_digit,
        position,
        window,
        dominant_digit,
    )

    _append_record(
        records,
        _feature_name(
            position,
            "dominant_percentage",
            window,
        ),
        dominant_percentage,
        position,
        window,
    )

    _append_record(
        records,
        _feature_name(
            position,
            "entropy",
            window,
        ),
        entropy,
        position,
        window,
    )

    _append_record(
        records,
        _feature_name(
            position,
            "normalized_entropy",
            window,
        ),
        normalized_entropy,
        position,
        window,
    )

    _append_record(
        records,
        _feature_name(
            position,
            "concentration_level",
            window,
        ),
        regime,
        position,
        window,
    )

    _append_record(
        records,
        _feature_name(
            position,
            "diversity_level",
            window,
        ),
        regime,
        position,
        window,
    )


def build_frequency_concentration_features(
    target_date: date,
    history: Iterable[HistoricalFeatureObservation],
    config: FeatureConfig,
) -> FrequencyConcentrationFeatureResult:
    """
    Build point-in-time frequency concentration and diversity features.

    Only observations strictly before target_date are used.

    The configured frequency windows are observation-count windows.
    Existing Phase 9.3 distribution-regime logic is reused for
    dominant digit, dominant percentage, entropy, and regime
    classification.
    """

    _validate_target_date(target_date)
    validated_history = _validate_history(history)
    _validate_config(config)

    point_in_time_history = _point_in_time_history(
        history=validated_history,
        target_date=target_date,
    )

    records: list[FrequencyConcentrationFeatureRecord] = []

    if not config.frequency_diversity_enabled:
        return FrequencyConcentrationFeatureResult(
            target_date=target_date,
            records=(),
        )

    for position in config.positions:
        for window in config.frequency_windows:
            _build_position_window_features(
                records=records,
                position=position,
                window=window,
                history=point_in_time_history,
            )

    return FrequencyConcentrationFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_frequency_concentration_feature_value(
    result: FrequencyConcentrationFeatureResult,
    feature_name: str,
) -> float | int | str | None:
    if not isinstance(
        result,
        FrequencyConcentrationFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyConcentrationFeatureResult."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Frequency concentration feature not found: {feature_name}"
    )


def get_frequency_concentration_feature_names(
    result: FrequencyConcentrationFeatureResult,
) -> tuple[str, ...]:
    if not isinstance(
        result,
        FrequencyConcentrationFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyConcentrationFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_frequency_concentration_records(
    result: FrequencyConcentrationFeatureResult,
) -> tuple[FrequencyConcentrationFeatureRecord, ...]:
    if not isinstance(
        result,
        FrequencyConcentrationFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyConcentrationFeatureResult."
        )

    return result.records