from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.cross_position_relationship_matrix import (
    CrossPositionRelationship,
    CrossPositionRelationshipMatrix,
)


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
class CrossPositionRelationshipPositionSummary:
    position: str
    relationship_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    insufficient_data_count: int
    valid_pair_count: int


@dataclass(frozen=True)
class CrossPositionRelationshipSummary:
    position_count: int
    positions: tuple[str, ...]
    relationship_count: int
    total_valid_pair_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    insufficient_data_count: int
    none_count: int
    weak_count: int
    moderate_count: int
    strong_count: int
    average_correlation: float | None
    average_absolute_correlation: float | None
    minimum_correlation: float | None
    maximum_correlation: float | None
    position_summaries: tuple[
        CrossPositionRelationshipPositionSummary, ...
    ]


def _validate_relationship(
    relationship: CrossPositionRelationship,
) -> None:
    if not isinstance(
        relationship,
        CrossPositionRelationship,
    ):
        raise TypeError(
            "relationships must contain only "
            "CrossPositionRelationship instances"
        )


def _validate_matrix(
    matrix: CrossPositionRelationshipMatrix,
) -> None:
    if not isinstance(
        matrix,
        CrossPositionRelationshipMatrix,
    ):
        raise TypeError(
            "matrix must be a CrossPositionRelationshipMatrix"
        )

    for relationship in matrix.relationships:
        _validate_relationship(relationship)


def _validate_relationships(
    relationships: Iterable[CrossPositionRelationship],
) -> tuple[CrossPositionRelationship, ...]:
    if isinstance(relationships, (str, bytes)):
        raise TypeError(
            "relationships must be an iterable of "
            "CrossPositionRelationship instances"
        )

    try:
        materialized = tuple(relationships)
    except TypeError as exc:
        raise TypeError(
            "relationships must be an iterable of "
            "CrossPositionRelationship instances"
        ) from exc

    for relationship in materialized:
        _validate_relationship(relationship)

    return materialized


def _average(
    values: Iterable[float],
) -> float | None:
    materialized = tuple(values)

    if not materialized:
        return None

    return sum(materialized) / len(materialized)


def _build_position_summaries(
    relationships: tuple[CrossPositionRelationship, ...],
    positions: tuple[str, ...],
) -> tuple[CrossPositionRelationshipPositionSummary, ...]:
    summaries = []

    for position in positions:
        position_relationships = tuple(
            relationship
            for relationship in relationships
            if (
                relationship.position_a == position
                or relationship.position_b == position
            )
        )

        summaries.append(
            CrossPositionRelationshipPositionSummary(
                position=position,
                relationship_count=len(
                    position_relationships
                ),
                positive_count=sum(
                    1
                    for relationship in position_relationships
                    if relationship.direction == "POSITIVE"
                ),
                negative_count=sum(
                    1
                    for relationship in position_relationships
                    if relationship.direction == "NEGATIVE"
                ),
                neutral_count=sum(
                    1
                    for relationship in position_relationships
                    if relationship.direction == "NEUTRAL"
                ),
                insufficient_data_count=sum(
                    1
                    for relationship in position_relationships
                    if (
                        relationship.direction
                        == "INSUFFICIENT_DATA"
                    )
                ),
                valid_pair_count=sum(
                    relationship.valid_pair_count
                    for relationship in position_relationships
                ),
            )
        )

    return tuple(summaries)


def build_cross_position_relationship_summary(
    matrix: CrossPositionRelationshipMatrix,
) -> CrossPositionRelationshipSummary:
    _validate_matrix(matrix)

    relationships = matrix.relationships
    positions = matrix.positions

    valid_correlations = tuple(
        relationship.correlation
        for relationship in relationships
        if relationship.correlation is not None
    )

    absolute_correlations = tuple(
        relationship.absolute_correlation
        for relationship in relationships
        if relationship.absolute_correlation is not None
    )

    position_summaries = _build_position_summaries(
        relationships,
        positions,
    )

    return CrossPositionRelationshipSummary(
        position_count=len(positions),
        positions=positions,
        relationship_count=len(relationships),
        total_valid_pair_count=sum(
            relationship.valid_pair_count
            for relationship in relationships
        ),
        positive_count=sum(
            1
            for relationship in relationships
            if relationship.direction == "POSITIVE"
        ),
        negative_count=sum(
            1
            for relationship in relationships
            if relationship.direction == "NEGATIVE"
        ),
        neutral_count=sum(
            1
            for relationship in relationships
            if relationship.direction == "NEUTRAL"
        ),
        insufficient_data_count=sum(
            1
            for relationship in relationships
            if relationship.direction == "INSUFFICIENT_DATA"
        ),
        none_count=sum(
            1
            for relationship in relationships
            if relationship.strength == "NONE"
        ),
        weak_count=sum(
            1
            for relationship in relationships
            if relationship.strength == "WEAK"
        ),
        moderate_count=sum(
            1
            for relationship in relationships
            if relationship.strength == "MODERATE"
        ),
        strong_count=sum(
            1
            for relationship in relationships
            if relationship.strength == "STRONG"
        ),
        average_correlation=_average(
            value
            for value in valid_correlations
            if value is not None
        ),
        average_absolute_correlation=_average(
            value
            for value in absolute_correlations
            if value is not None
        ),
        minimum_correlation=(
            min(valid_correlations)
            if valid_correlations
            else None
        ),
        maximum_correlation=(
            max(valid_correlations)
            if valid_correlations
            else None
        ),
        position_summaries=position_summaries,
    )


def build_cross_position_relationship_summary_result(
    matrix: CrossPositionRelationshipMatrix,
) -> CrossPositionRelationshipSummary:
    return build_cross_position_relationship_summary(
        matrix
    )


def get_cross_position_relationship_position_summary(
    summary: CrossPositionRelationshipSummary,
    position: str,
) -> CrossPositionRelationshipPositionSummary:
    if not isinstance(
        summary,
        CrossPositionRelationshipSummary,
    ):
        raise TypeError(
            "summary must be a CrossPositionRelationshipSummary"
        )

    for position_summary in summary.position_summaries:
        if position_summary.position == position:
            return position_summary

    raise ValueError(
        f"Position summary not found: {position}"
    )


def iter_cross_position_relationship_position_summaries(
    summary: CrossPositionRelationshipSummary,
) -> tuple[CrossPositionRelationshipPositionSummary, ...]:
    if not isinstance(
        summary,
        CrossPositionRelationshipSummary,
    ):
        raise TypeError(
            "summary must be a CrossPositionRelationshipSummary"
        )

    return summary.position_summaries