from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.cross_position_relationship_change_detection import (
    CrossPositionRelationshipChangeDetection,
)
from analytics.cross_position_relationship_matrix import (
    CrossPositionRelationshipMatrix,
)
from analytics.cross_position_relationship_stability import (
    CrossPositionRelationshipStability,
)
from analytics.cross_position_relationship_summary import (
    CrossPositionRelationshipSummary,
)


@dataclass(frozen=True)
class CrossPositionRelationshipOverview:
    position_count: int
    positions: tuple[str, ...]
    relationship_count: int

    matrix_relationship_count: int
    summary_relationship_count: int

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

    stability_pair_count: int
    stable_high_count: int
    stable_medium_count: int
    stable_low_count: int
    stable_insufficient_data_count: int

    total_direction_change_count: int
    total_strength_change_count: int
    total_relationship_change_count: int
    total_insufficient_data_change_count: int

    matrix: CrossPositionRelationshipMatrix
    summary: CrossPositionRelationshipSummary
    stability_results: tuple[CrossPositionRelationshipStability, ...]
    change_detection_results: tuple[
        CrossPositionRelationshipChangeDetection, ...
    ]


def _validate_matrix(
    matrix: CrossPositionRelationshipMatrix,
) -> None:
    if not isinstance(matrix, CrossPositionRelationshipMatrix):
        raise TypeError(
            "matrix must be a CrossPositionRelationshipMatrix"
        )


def _validate_summary(
    summary: CrossPositionRelationshipSummary,
) -> None:
    if not isinstance(summary, CrossPositionRelationshipSummary):
        raise TypeError(
            "summary must be a CrossPositionRelationshipSummary"
        )


def _validate_stability_result(
    result: CrossPositionRelationshipStability,
) -> None:
    if not isinstance(result, CrossPositionRelationshipStability):
        raise TypeError(
            "each stability result must be a "
            "CrossPositionRelationshipStability"
        )


def _validate_change_detection_result(
    result: CrossPositionRelationshipChangeDetection,
) -> None:
    if not isinstance(
        result,
        CrossPositionRelationshipChangeDetection,
    ):
        raise TypeError(
            "each change detection result must be a "
            "CrossPositionRelationshipChangeDetection"
        )


def _validate_stability_results(
    results: Iterable[CrossPositionRelationshipStability],
) -> tuple[CrossPositionRelationshipStability, ...]:
    if isinstance(results, (str, bytes)):
        raise TypeError(
            "stability_results must be an iterable"
        )

    try:
        materialized = tuple(results)
    except TypeError as exc:
        raise TypeError(
            "stability_results must be an iterable"
        ) from exc

    for result in materialized:
        _validate_stability_result(result)

    return materialized


def _validate_change_detection_results(
    results: Iterable[CrossPositionRelationshipChangeDetection],
) -> tuple[CrossPositionRelationshipChangeDetection, ...]:
    if isinstance(results, (str, bytes)):
        raise TypeError(
            "change_detection_results must be an iterable"
        )

    try:
        materialized = tuple(results)
    except TypeError as exc:
        raise TypeError(
            "change_detection_results must be an iterable"
        ) from exc

    for result in materialized:
        _validate_change_detection_result(result)

    return materialized


def _count_stability_levels(
    results: tuple[CrossPositionRelationshipStability, ...],
) -> tuple[int, int, int, int]:
    high_count = 0
    medium_count = 0
    low_count = 0
    insufficient_count = 0

    for result in results:
        level = result.stability_level

        if level == "HIGH":
            high_count += 1
        elif level == "MEDIUM":
            medium_count += 1
        elif level == "LOW":
            low_count += 1
        elif level == "INSUFFICIENT_DATA":
            insufficient_count += 1

    return (
        high_count,
        medium_count,
        low_count,
        insufficient_count,
    )


def _sum_direction_changes(
    results: tuple[CrossPositionRelationshipChangeDetection, ...],
) -> int:
    return sum(result.direction_change_count for result in results)


def _sum_strength_changes(
    results: tuple[CrossPositionRelationshipChangeDetection, ...],
) -> int:
    return sum(result.strength_change_count for result in results)


def _sum_relationship_changes(
    results: tuple[CrossPositionRelationshipChangeDetection, ...],
) -> int:
    return sum(
        result.relationship_change_count
        for result in results
    )


def _sum_insufficient_data_changes(
    results: tuple[CrossPositionRelationshipChangeDetection, ...],
) -> int:
    return sum(
        result.insufficient_data_change_count
        for result in results
    )


def build_cross_position_relationship_overview(
    matrix: CrossPositionRelationshipMatrix,
    summary: CrossPositionRelationshipSummary,
    stability_results: Iterable[
        CrossPositionRelationshipStability
    ],
    change_detection_results: Iterable[
        CrossPositionRelationshipChangeDetection
    ],
) -> CrossPositionRelationshipOverview:
    _validate_matrix(matrix)
    _validate_summary(summary)

    validated_stability_results = _validate_stability_results(
        stability_results
    )

    validated_change_detection_results = (
        _validate_change_detection_results(
            change_detection_results
        )
    )

    if matrix.positions != summary.positions:
        raise ValueError(
            "matrix and summary positions must match"
        )

    if matrix.relationship_count != summary.relationship_count:
        raise ValueError(
            "matrix and summary relationship counts must match"
        )

    (
        high_count,
        medium_count,
        low_count,
        insufficient_stability_count,
    ) = _count_stability_levels(
        validated_stability_results
    )

    return CrossPositionRelationshipOverview(
        position_count=summary.position_count,
        positions=summary.positions,
        relationship_count=summary.relationship_count,
        matrix_relationship_count=matrix.relationship_count,
        summary_relationship_count=summary.relationship_count,
        total_valid_pair_count=summary.total_valid_pair_count,
        positive_count=summary.positive_count,
        negative_count=summary.negative_count,
        neutral_count=summary.neutral_count,
        insufficient_data_count=summary.insufficient_data_count,
        none_count=summary.none_count,
        weak_count=summary.weak_count,
        moderate_count=summary.moderate_count,
        strong_count=summary.strong_count,
        average_correlation=summary.average_correlation,
        average_absolute_correlation=(
            summary.average_absolute_correlation
        ),
        minimum_correlation=summary.minimum_correlation,
        maximum_correlation=summary.maximum_correlation,
        stability_pair_count=len(
            validated_stability_results
        ),
        stable_high_count=high_count,
        stable_medium_count=medium_count,
        stable_low_count=low_count,
        stable_insufficient_data_count=(
            insufficient_stability_count
        ),
        total_direction_change_count=_sum_direction_changes(
            validated_change_detection_results
        ),
        total_strength_change_count=_sum_strength_changes(
            validated_change_detection_results
        ),
        total_relationship_change_count=_sum_relationship_changes(
            validated_change_detection_results
        ),
        total_insufficient_data_change_count=(
            _sum_insufficient_data_changes(
                validated_change_detection_results
            )
        ),
        matrix=matrix,
        summary=summary,
        stability_results=validated_stability_results,
        change_detection_results=(
            validated_change_detection_results
        ),
    )


def get_stability_result(
    overview: CrossPositionRelationshipOverview,
    position_a: str,
    position_b: str,
) -> CrossPositionRelationshipStability:
    if not isinstance(
        overview,
        CrossPositionRelationshipOverview,
    ):
        raise TypeError(
            "overview must be a CrossPositionRelationshipOverview"
        )

    for result in overview.stability_results:
        if (
            result.position_a == position_a
            and result.position_b == position_b
        ):
            return result

        if (
            result.position_a == position_b
            and result.position_b == position_a
        ):
            return result

    raise ValueError(
        "Stability result not found for "
        f"{position_a} and {position_b}"
    )


def get_change_detection_result(
    overview: CrossPositionRelationshipOverview,
    position_a: str,
    position_b: str,
) -> CrossPositionRelationshipChangeDetection:
    if not isinstance(
        overview,
        CrossPositionRelationshipOverview,
    ):
        raise TypeError(
            "overview must be a CrossPositionRelationshipOverview"
        )

    for result in overview.change_detection_results:
        if (
            result.position_a == position_a
            and result.position_b == position_b
        ):
            return result

        if (
            result.position_a == position_b
            and result.position_b == position_a
        ):
            return result

    raise ValueError(
        "Change detection result not found for "
        f"{position_a} and {position_b}"
    )


def iter_stability_results(
    overview: CrossPositionRelationshipOverview,
) -> tuple[CrossPositionRelationshipStability, ...]:
    if not isinstance(
        overview,
        CrossPositionRelationshipOverview,
    ):
        raise TypeError(
            "overview must be a CrossPositionRelationshipOverview"
        )

    return overview.stability_results


def iter_change_detection_results(
    overview: CrossPositionRelationshipOverview,
) -> tuple[CrossPositionRelationshipChangeDetection, ...]:
    if not isinstance(
        overview,
        CrossPositionRelationshipOverview,
    ):
        raise TypeError(
            "overview must be a CrossPositionRelationshipOverview"
        )

    return overview.change_detection_results