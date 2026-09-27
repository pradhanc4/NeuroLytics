from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


@dataclass(frozen=True)
class CrossPositionFeatureRecord:
    """One cross-position relationship feature."""

    position_a: str
    position_b: str
    feature_name: str
    value: int | float | None


@dataclass(frozen=True)
class CrossPositionFeatureResult:
    """Complete cross-position feature output."""

    target_date: date
    records: tuple[CrossPositionFeatureRecord, ...]


def _build_feature_name(
    position_a: str,
    position_b: str,
    feature: str,
) -> str:
    """Build a deterministic cross-position feature name."""

    return f"{position_a}_{position_b}_{feature}"


def _get_position_index(position: str) -> int:
    """Convert col1-col8 into a zero-based index."""

    return int(
        position.replace("col", "")
    ) - 1


def _get_latest_values(
    history: PointInTimeHistory,
    position_a: str,
    position_b: str,
) -> tuple[int | None, int | None]:
    """Return the latest historical values for a position pair."""

    observations = get_point_in_time_observations(
        history
    )

    if not observations:
        return None, None

    latest = observations[-1]

    index_a = _get_position_index(position_a)
    index_b = _get_position_index(position_b)

    return (
        latest.positions[index_a],
        latest.positions[index_b],
    )


def _calculate_equality(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """Return whether two values are equal."""

    if value_a is None or value_b is None:
        return None

    return int(value_a == value_b)


def _calculate_absolute_difference(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """Return absolute digit difference."""

    if value_a is None or value_b is None:
        return None

    return abs(value_a - value_b)


def _calculate_sum(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """Return the sum of two position values."""

    if value_a is None or value_b is None:
        return None

    return value_a + value_b


def _calculate_order(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """
    Return relative ordering.

    1  -> A > B
    0  -> A == B
    -1 -> A < B
    """

    if value_a is None or value_b is None:
        return None

    if value_a > value_b:
        return 1

    if value_a < value_b:
        return -1

    return 0


def _calculate_same_parity(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """Return whether both digits have the same parity."""

    if value_a is None or value_b is None:
        return None

    return int(
        value_a % 2 == value_b % 2
    )


def _calculate_same_zero_state(
    value_a: int | None,
    value_b: int | None,
) -> int | None:
    """Return whether both digits share the same zero/non-zero state."""

    if value_a is None or value_b is None:
        return None

    return int(
        (value_a == 0)
        == (value_b == 0)
    )


def build_cross_position_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> CrossPositionFeatureResult:
    """
    Build leakage-safe relationships between position pairs.

    Only the latest historical observation strictly before
    the target date is used.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[
        CrossPositionFeatureRecord
    ] = []

    positions = config.positions

    for index_a, position_a in enumerate(positions):
        for position_b in positions[index_a + 1:]:
            value_a, value_b = (
                _get_latest_values(
                    history,
                    position_a,
                    position_b,
                )
            )

            features = (
                (
                    "equal",
                    _calculate_equality(
                        value_a,
                        value_b,
                    ),
                ),
                (
                    "absolute_difference",
                    _calculate_absolute_difference(
                        value_a,
                        value_b,
                    ),
                ),
                (
                    "sum",
                    _calculate_sum(
                        value_a,
                        value_b,
                    ),
                ),
                (
                    "order",
                    _calculate_order(
                        value_a,
                        value_b,
                    ),
                ),
                (
                    "same_parity",
                    _calculate_same_parity(
                        value_a,
                        value_b,
                    ),
                ),
                (
                    "same_zero_state",
                    _calculate_same_zero_state(
                        value_a,
                        value_b,
                    ),
                ),
            )

            for feature, value in features:
                records.append(
                    CrossPositionFeatureRecord(
                        position_a=position_a,
                        position_b=position_b,
                        feature_name=_build_feature_name(
                            position_a,
                            position_b,
                            feature,
                        ),
                        value=value,
                    )
                )

    return CrossPositionFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_cross_position_feature_value(
    result: CrossPositionFeatureResult,
    feature_name: str,
) -> int | float | None:
    """Return one cross-position feature value."""

    if not isinstance(
        result,
        CrossPositionFeatureResult,
    ):
        raise TypeError(
            "result must be a CrossPositionFeatureResult instance."
        )

    if not isinstance(
        feature_name,
        str,
    ):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Cross-position feature not found: {feature_name}"
    )


def get_cross_position_feature_names(
    result: CrossPositionFeatureResult,
) -> tuple[str, ...]:
    """Return all generated cross-position feature names."""

    if not isinstance(
        result,
        CrossPositionFeatureResult,
    ):
        raise TypeError(
            "result must be a CrossPositionFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )