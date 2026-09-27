from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log
from typing import Iterable, Mapping


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

DEFAULT_WINDOW_SIZE = 5


@dataclass(frozen=True)
class DistributionRegimeWindow:
    position: str
    window_index: int
    start_date: date
    end_date: date
    observation_count: int
    frequency_total: int
    dominant_digit: int | None
    dominant_digit_percentage: float | None
    distribution_mean: float | None
    distribution_std: float | None
    entropy: float | None
    regime: str


@dataclass(frozen=True)
class DistributionRegimeDetection:
    position: str
    window_size: int
    window_count: int
    valid_window_count: int
    windows: tuple[DistributionRegimeWindow, ...]


@dataclass(frozen=True)
class DistributionRegimeDetectionResult:
    position_count: int
    positions: tuple[str, ...]
    detections: tuple[DistributionRegimeDetection, ...]


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError("position must be a string")

    if position not in POSITIONS:
        raise ValueError(
            f"unsupported position: {position}"
        )


def _validate_window_size(window_size: int) -> None:
    if isinstance(window_size, bool):
        raise TypeError("window_size must be an integer")

    if not isinstance(window_size, int):
        raise TypeError("window_size must be an integer")

    if window_size <= 0:
        raise ValueError(
            "window_size must be greater than zero"
        )


def _validate_observation(
    observation: tuple[date, int | None],
) -> None:
    if not isinstance(observation, (tuple, list)):
        raise TypeError(
            "each observation must contain a date and value"
        )

    if len(observation) != 2:
        raise ValueError(
            "each observation must contain exactly two values"
        )

    observation_date, value = observation

    if not isinstance(observation_date, date):
        raise TypeError(
            "observation date must be a date"
        )

    if value is not None:
        if isinstance(value, bool):
            raise TypeError(
                "observation value must be an integer or None"
            )

        if not isinstance(value, int):
            raise TypeError(
                "observation value must be an integer or None"
            )

        if value not in DIGITS:
            raise ValueError(
                "observation value must be between 0 and 9"
            )


def _validate_observations(
    observations: Iterable[tuple[date, int | None]],
) -> tuple[tuple[date, int | None], ...]:
    if isinstance(observations, (str, bytes)):
        raise TypeError(
            "observations must be an iterable of date/value pairs"
        )

    validated = []

    for observation in observations:
        _validate_observation(observation)
        validated.append(
            (
                observation[0],
                observation[1],
            )
        )

    validated.sort(key=lambda item: item[0])

    dates = [item[0] for item in validated]

    if len(dates) != len(set(dates)):
        raise ValueError(
            "duplicate observation dates are not allowed"
        )

    return tuple(validated)


def _frequency_counts(
    values: Iterable[int],
) -> tuple[int, ...]:
    counts = [0] * 10

    for value in values:
        counts[value] += 1

    return tuple(counts)


def _dominant_digit(
    counts: tuple[int, ...],
) -> int | None:
    total = sum(counts)

    if total == 0:
        return None

    return max(
        DIGITS,
        key=lambda digit: (
            counts[digit],
            -digit,
        ),
    )


def _distribution_mean(
    counts: tuple[int, ...],
) -> float | None:
    total = sum(counts)

    if total == 0:
        return None

    return sum(
        digit * counts[digit]
        for digit in DIGITS
    ) / total


def _distribution_std(
    counts: tuple[int, ...],
) -> float | None:
    total = sum(counts)

    if total == 0:
        return None

    mean = _distribution_mean(counts)

    if mean is None:
        return None

    variance = sum(
        ((digit - mean) ** 2) * counts[digit]
        for digit in DIGITS
    ) / total

    return variance ** 0.5


def _entropy(
    counts: tuple[int, ...],
) -> float | None:
    total = sum(counts)

    if total == 0:
        return None

    entropy = 0.0

    for count in counts:
        if count == 0:
            continue

        probability = count / total
        entropy -= probability * log(
            probability,
            2,
        )

    return entropy


def _classify_regime(
    counts: tuple[int, ...],
) -> str:
    total = sum(counts)

    if total == 0:
        return "INSUFFICIENT_DATA"

    dominant_count = max(counts)
    dominant_percentage = (
        dominant_count / total
    ) * 100.0

    entropy = _entropy(counts)

    if entropy is None:
        return "INSUFFICIENT_DATA"

    if dominant_percentage >= 60.0:
        return "CONCENTRATED"

    if entropy >= 2.75:
        return "DIVERSE"

    return "BALANCED"


def _build_window(
    position: str,
    window_index: int,
    observations: tuple[
        tuple[date, int | None],
        ...,
    ],
) -> DistributionRegimeWindow:
    start_date = observations[0][0]
    end_date = observations[-1][0]

    values = tuple(
        value
        for _, value in observations
        if value is not None
    )

    counts = _frequency_counts(values)
    frequency_total = sum(counts)

    dominant_digit = _dominant_digit(counts)

    dominant_digit_percentage = None

    if frequency_total > 0:
        dominant_digit_percentage = (
            counts[dominant_digit]
            / frequency_total
        ) * 100.0

    return DistributionRegimeWindow(
        position=position,
        window_index=window_index,
        start_date=start_date,
        end_date=end_date,
        observation_count=len(values),
        frequency_total=frequency_total,
        dominant_digit=dominant_digit,
        dominant_digit_percentage=dominant_digit_percentage,
        distribution_mean=_distribution_mean(counts),
        distribution_std=_distribution_std(counts),
        entropy=_entropy(counts),
        regime=_classify_regime(counts),
    )


def build_distribution_regime_detection(
    position: str,
    observations: Iterable[
        tuple[date, int | None]
    ],
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> DistributionRegimeDetection:
    _validate_position(position)
    _validate_window_size(window_size)

    validated = _validate_observations(
        observations
    )

    windows = []

    for start in range(
        0,
        len(validated),
        window_size,
    ):
        window_observations = validated[
            start:start + window_size
        ]

        if not window_observations:
            continue

        windows.append(
            _build_window(
                position,
                len(windows) + 1,
                window_observations,
            )
        )

    valid_window_count = sum(
        1
        for window in windows
        if window.regime != "INSUFFICIENT_DATA"
    )

    return DistributionRegimeDetection(
        position=position,
        window_size=window_size,
        window_count=len(windows),
        valid_window_count=valid_window_count,
        windows=tuple(windows),
    )


def build_distribution_regime_detection_result(
    observations_by_position: Mapping[
        str,
        Iterable[tuple[date, int | None]],
    ],
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> DistributionRegimeDetectionResult:
    if not isinstance(
        observations_by_position,
        Mapping,
    ):
        raise TypeError(
            "observations_by_position must be a mapping"
        )

    _validate_window_size(window_size)

    positions = tuple(
        observations_by_position.keys()
    )

    for position in positions:
        _validate_position(position)

    detections = tuple(
        build_distribution_regime_detection(
            position,
            observations_by_position[position],
            window_size=window_size,
        )
        for position in positions
    )

    return DistributionRegimeDetectionResult(
        position_count=len(positions),
        positions=positions,
        detections=detections,
    )


def get_distribution_regime_detection(
    result: DistributionRegimeDetectionResult,
    position: str,
) -> DistributionRegimeDetection:
    if not isinstance(
        result,
        DistributionRegimeDetectionResult,
    ):
        raise TypeError(
            "result must be a DistributionRegimeDetectionResult"
        )

    _validate_position(position)

    for detection in result.detections:
        if detection.position == position:
            return detection

    raise ValueError(
        f"Distribution regime detection not found for {position}"
    )


def iter_distribution_regime_detections(
    result: DistributionRegimeDetectionResult,
) -> tuple[DistributionRegimeDetection, ...]:
    if not isinstance(
        result,
        DistributionRegimeDetectionResult,
    ):
        raise TypeError(
            "result must be a DistributionRegimeDetectionResult"
        )

    return result.detections


def get_distribution_regime_window(
    detection: DistributionRegimeDetection,
    window_index: int,
) -> DistributionRegimeWindow:
    if not isinstance(
        detection,
        DistributionRegimeDetection,
    ):
        raise TypeError(
            "detection must be a DistributionRegimeDetection"
        )

    if isinstance(window_index, bool):
        raise TypeError(
            "window_index must be an integer"
        )

    if not isinstance(window_index, int):
        raise TypeError(
            "window_index must be an integer"
        )

    for window in detection.windows:
        if window.window_index == window_index:
            return window

    raise ValueError(
        f"Distribution regime window not found: {window_index}"
    )


def iter_distribution_regime_windows(
    detection: DistributionRegimeDetection,
) -> tuple[DistributionRegimeWindow, ...]:
    if not isinstance(
        detection,
        DistributionRegimeDetection,
    ):
        raise TypeError(
            "detection must be a DistributionRegimeDetection"
        )

    return detection.windows