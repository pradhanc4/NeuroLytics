from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


RELATIONSHIP_DIRECTIONS: tuple[str, ...] = (
    "POSITIVE",
    "NEGATIVE",
    "NEUTRAL",
    "INSUFFICIENT_DATA",
)

RELATIONSHIP_STRENGTHS: tuple[str, ...] = (
    "NONE",
    "WEAK",
    "MODERATE",
    "STRONG",
    "INSUFFICIENT_DATA",
)


@dataclass(frozen=True)
class CrossPositionRelationship:
    position_a: str
    position_b: str
    valid_pair_count: int
    covariance: float | None
    correlation: float | None
    absolute_correlation: float | None
    direction: str
    strength: str


@dataclass(frozen=True)
class CrossPositionRelationshipMatrix:
    positions: tuple[str, ...]
    relationship_count: int
    relationships: tuple[CrossPositionRelationship, ...]


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError("position must be a string")

    if not position.strip():
        raise ValueError("position must not be empty")


def _validate_positions(
    positions: Iterable[str],
) -> tuple[str, ...]:
    if isinstance(positions, (str, bytes)):
        raise TypeError("positions must be an iterable of strings")

    try:
        materialized = tuple(positions)
    except TypeError as exc:
        raise TypeError(
            "positions must be an iterable of strings"
        ) from exc

    for position in materialized:
        _validate_position(position)

    if len(set(materialized)) != len(materialized):
        raise ValueError(
            "positions must not contain duplicates"
        )

    return materialized


def _validate_value(
    value: int | float | None,
) -> None:
    if value is None:
        return

    if isinstance(value, bool):
        raise TypeError(
            "position values must be numeric or None"
        )

    if not isinstance(value, (int, float)):
        raise TypeError(
            "position values must be numeric or None"
        )


def _validate_observations(
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
) -> tuple[
    tuple[int | float | None, int | float | None], ...
]:
    if isinstance(observations, (str, bytes)):
        raise TypeError(
            "observations must be an iterable of value pairs"
        )

    try:
        materialized = tuple(observations)
    except TypeError as exc:
        raise TypeError(
            "observations must be an iterable of value pairs"
        ) from exc

    validated = []

    for observation in materialized:
        if not isinstance(observation, (tuple, list)):
            raise TypeError(
                "each observation must contain two values"
            )

        if len(observation) != 2:
            raise ValueError(
                "each observation must contain exactly two values"
            )

        value_a, value_b = observation

        _validate_value(value_a)
        _validate_value(value_b)

        validated.append((value_a, value_b))

    return tuple(validated)


def _valid_pairs(
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
) -> tuple[tuple[float, float], ...]:
    pairs = []

    for value_a, value_b in observations:
        if value_a is None or value_b is None:
            continue

        pairs.append(
            (float(value_a), float(value_b))
        )

    return tuple(pairs)


def _covariance(
    pairs: tuple[tuple[float, float], ...],
) -> float | None:
    count = len(pairs)

    if count < 2:
        return None

    mean_a = sum(
        pair[0]
        for pair in pairs
    ) / count

    mean_b = sum(
        pair[1]
        for pair in pairs
    ) / count

    return sum(
        (value_a - mean_a) * (value_b - mean_b)
        for value_a, value_b in pairs
    ) / count


def _correlation(
    pairs: tuple[tuple[float, float], ...],
) -> float | None:
    count = len(pairs)

    if count < 2:
        return None

    mean_a = sum(
        pair[0]
        for pair in pairs
    ) / count

    mean_b = sum(
        pair[1]
        for pair in pairs
    ) / count

    deviations_a = tuple(
        value_a - mean_a
        for value_a, _ in pairs
    )

    deviations_b = tuple(
        value_b - mean_b
        for _, value_b in pairs
    )

    sum_squared_a = sum(
        deviation * deviation
        for deviation in deviations_a
    )

    sum_squared_b = sum(
        deviation * deviation
        for deviation in deviations_b
    )

    if sum_squared_a == 0.0 or sum_squared_b == 0.0:
        return None

    numerator = sum(
        deviation_a * deviation_b
        for deviation_a, deviation_b in zip(
            deviations_a,
            deviations_b,
        )
    )

    denominator = sqrt(
        sum_squared_a * sum_squared_b
    )

    if denominator == 0.0:
        return None

    return numerator / denominator


def _classify_direction(
    correlation: float | None,
) -> str:
    if correlation is None:
        return "INSUFFICIENT_DATA"

    if correlation > 0:
        return "POSITIVE"

    if correlation < 0:
        return "NEGATIVE"

    return "NEUTRAL"


def _classify_strength(
    correlation: float | None,
) -> str:
    if correlation is None:
        return "INSUFFICIENT_DATA"

    absolute_correlation = abs(correlation)

    if absolute_correlation == 0:
        return "NONE"

    if absolute_correlation < 0.30:
        return "WEAK"

    if absolute_correlation < 0.70:
        return "MODERATE"

    return "STRONG"


def build_cross_position_relationship(
    position_a: str,
    position_b: str,
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
) -> CrossPositionRelationship:
    _validate_position(position_a)
    _validate_position(position_b)

    if position_a == position_b:
        raise ValueError(
            "position_a and position_b must be different"
        )

    validated_observations = _validate_observations(
        observations
    )

    pairs = _valid_pairs(
        validated_observations
    )

    covariance = _covariance(pairs)
    correlation = _correlation(pairs)

    absolute_correlation = (
        abs(correlation)
        if correlation is not None
        else None
    )

    return CrossPositionRelationship(
        position_a=position_a,
        position_b=position_b,
        valid_pair_count=len(pairs),
        covariance=covariance,
        correlation=correlation,
        absolute_correlation=absolute_correlation,
        direction=_classify_direction(
            correlation
        ),
        strength=_classify_strength(
            correlation
        ),
    )


def build_cross_position_relationship_matrix(
    positions: Iterable[str],
    observations: dict[
        tuple[str, str],
        Iterable[
            tuple[int | float | None, int | float | None]
        ],
    ],
) -> CrossPositionRelationshipMatrix:
    validated_positions = _validate_positions(
        positions
    )

    if not isinstance(observations, dict):
        raise TypeError(
            "observations must be a dictionary keyed by position pairs"
        )

    relationships = []

    for index, position_a in enumerate(
        validated_positions
    ):
        for position_b in validated_positions[index + 1:]:
            key = (position_a, position_b)
            reverse_key = (position_b, position_a)

            if key in observations:
                pair_observations = observations[key]
            elif reverse_key in observations:
                original = _validate_observations(
                    observations[reverse_key]
                )
                pair_observations = tuple(
                    (value_b, value_a)
                    for value_a, value_b in original
                )
            else:
                pair_observations = ()

            relationship = (
                build_cross_position_relationship(
                    position_a,
                    position_b,
                    pair_observations,
                )
            )

            relationships.append(
                relationship
            )

    return CrossPositionRelationshipMatrix(
        positions=validated_positions,
        relationship_count=len(relationships),
        relationships=tuple(relationships),
    )


def get_cross_position_relationship(
    matrix: CrossPositionRelationshipMatrix,
    position_a: str,
    position_b: str,
) -> CrossPositionRelationship:
    if not isinstance(
        matrix,
        CrossPositionRelationshipMatrix,
    ):
        raise TypeError(
            "matrix must be a CrossPositionRelationshipMatrix"
        )

    for relationship in matrix.relationships:
        if (
            relationship.position_a == position_a
            and relationship.position_b == position_b
        ):
            return relationship

        if (
            relationship.position_a == position_b
            and relationship.position_b == position_a
        ):
            return relationship

    raise ValueError(
        f"Relationship not found: "
        f"{position_a} / {position_b}"
    )


def iter_cross_position_relationships(
    matrix: CrossPositionRelationshipMatrix,
) -> tuple[CrossPositionRelationship, ...]:
    if not isinstance(
        matrix,
        CrossPositionRelationshipMatrix,
    ):
        raise TypeError(
            "matrix must be a CrossPositionRelationshipMatrix"
        )

    return matrix.relationships