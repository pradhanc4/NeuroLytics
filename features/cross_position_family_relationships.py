"""
Cross-position family relationship features.

Phase 15.5
-----------
Provides point-in-time-safe relationships between the three
authoritative position-family groups:

    col1-col3 -> Panna
    col4-col5 -> Jodi
    col6-col8 -> Panel

This module does not perform:
- historical frequency analysis,
- recency analysis,
- transition analysis,
- probability calculation,
- prediction scoring,
- trend analysis,
- family inference.

It only exposes the family classifications that coexist across
different position groups for the latest historical observation
strictly before the target date.

Design principles
-----------------
- Reuse the Phase 15.4 position-family resolver.
- Preserve leading-zero identifiers.
- Preserve explicit unmapped states.
- Never infer family identity from digit structure.
- Use only point-in-time-safe historical observations.
- Generate deterministic cross-position pair ordering.
- Do not modify the existing Phase 13 digit-level cross-position
  feature layer.
"""

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
from features.position_family import (
    PositionFamilyRecord,
    build_position_family_features,
)


@dataclass(frozen=True)
class CrossPositionFamilyRelationshipRecord:
    """Relationship between two position-family classifications."""

    left_position_group: str
    left_family_type: str
    left_value: str | None
    left_family: str | None
    left_family_id: int | None
    left_is_mapped: bool
    left_is_active: bool

    right_position_group: str
    right_family_type: str
    right_value: str | None
    right_family: str | None
    right_family_id: int | None
    right_is_mapped: bool
    right_is_active: bool


@dataclass(frozen=True)
class CrossPositionFamilyRelationshipResult:
    """Complete cross-position family relationship output."""

    target_date: date
    records: tuple[
        CrossPositionFamilyRelationshipRecord,
        ...,
    ]


_POSITION_GROUP_ORDER = (
    "col1-col3",
    "col4-col5",
    "col6-col8",
)


def _build_relationship_record(
    left: PositionFamilyRecord,
    right: PositionFamilyRecord,
) -> CrossPositionFamilyRelationshipRecord:
    """Build one deterministic cross-position family relationship."""

    return CrossPositionFamilyRelationshipRecord(
        left_position_group=left.position_group,
        left_family_type=left.family_type,
        left_value=left.value,
        left_family=left.family,
        left_family_id=left.family_id,
        left_is_mapped=left.is_mapped,
        left_is_active=left.is_active,
        right_position_group=right.position_group,
        right_family_type=right.family_type,
        right_value=right.value,
        right_family=right.family,
        right_family_id=right.family_id,
        right_is_mapped=right.is_mapped,
        right_is_active=right.is_active,
    )


def _build_empty_relationship_records(
    target_date: date,
) -> CrossPositionFamilyRelationshipResult:
    """
    Return explicit empty-state relationships.

    When no point-in-time observation exists, all three position
    groups remain present with None values and unmapped states.
    """

    panna = PositionFamilyRecord(
        position_group="col1-col3",
        family_type="panna",
        value=None,
        family=None,
        family_id=None,
        is_mapped=False,
        is_active=False,
    )

    jodi = PositionFamilyRecord(
        position_group="col4-col5",
        family_type="jodi",
        value=None,
        family=None,
        family_id=None,
        is_mapped=False,
        is_active=False,
    )

    panel = PositionFamilyRecord(
        position_group="col6-col8",
        family_type="panel",
        value=None,
        family=None,
        family_id=None,
        is_mapped=False,
        is_active=False,
    )

    return CrossPositionFamilyRelationshipResult(
        target_date=target_date,
        records=(
            _build_relationship_record(
                panna,
                jodi,
            ),
            _build_relationship_record(
                panna,
                panel,
            ),
            _build_relationship_record(
                jodi,
                panel,
            ),
        ),
    )


def _validate_position_family_records(
    records: tuple[PositionFamilyRecord, ...],
) -> None:
    """Validate the expected Phase 15.4 position-family groups."""

    if len(records) != 3:
        raise ValueError(
            "Position-family resolution must contain exactly "
            "three position groups."
        )

    actual_groups = tuple(
        record.position_group
        for record in records
    )

    if actual_groups != _POSITION_GROUP_ORDER:
        raise ValueError(
            "Position-family records must contain the groups "
            "in deterministic order: "
            "col1-col3, col4-col5, col6-col8."
        )


def build_cross_position_family_relationships(
    db,
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> CrossPositionFamilyRelationshipResult:
    """
    Build family-aware relationships across position groups.

    The latest observation strictly before history.target_date is
    used through the Phase 15.4 position-family feature layer.

    Three deterministic relationships are produced:

        col1-col3 <-> col4-col5
        col1-col3 <-> col6-col8
        col4-col5 <-> col6-col8

    Missing or inactive family mappings remain explicit and are not
    inferred.
    """

    if db is None:
        raise ValueError(
            "db is required."
        )

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    observations = get_point_in_time_observations(
        history
    )

    if not observations:
        return _build_empty_relationship_records(
            target_date=history.target_date,
        )

    position_family_result = (
        build_position_family_features(
            db=db,
            history=history,
            config=config,
        )
    )

    records = position_family_result.records

    _validate_position_family_records(
        records
    )

    panna = records[0]
    jodi = records[1]
    panel = records[2]

    relationship_records = (
        _build_relationship_record(
            panna,
            jodi,
        ),
        _build_relationship_record(
            panna,
            panel,
        ),
        _build_relationship_record(
            jodi,
            panel,
        ),
    )

    return CrossPositionFamilyRelationshipResult(
        target_date=history.target_date,
        records=relationship_records,
    )


def get_cross_position_family_relationships(
    result: CrossPositionFamilyRelationshipResult,
) -> tuple[
    CrossPositionFamilyRelationshipRecord,
    ...,
]:
    """Return all cross-position family relationships."""

    if not isinstance(
        result,
        CrossPositionFamilyRelationshipResult,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionFamilyRelationshipResult instance."
        )

    return result.records


def get_cross_position_family_relationship(
    result: CrossPositionFamilyRelationshipResult,
    left_position_group: str,
    right_position_group: str,
) -> CrossPositionFamilyRelationshipRecord:
    """
    Return one deterministic cross-position family relationship.

    The pair is order-sensitive for lookup and must match the
    deterministic ordering produced by the builder.
    """

    if not isinstance(
        result,
        CrossPositionFamilyRelationshipResult,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionFamilyRelationshipResult instance."
        )

    if not isinstance(
        left_position_group,
        str,
    ):
        raise TypeError(
            "left_position_group must be a string."
        )

    if not isinstance(
        right_position_group,
        str,
    ):
        raise TypeError(
            "right_position_group must be a string."
        )

    for record in result.records:
        if (
            record.left_position_group
            == left_position_group
            and record.right_position_group
            == right_position_group
        ):
            return record

    raise ValueError(
        "Cross-position family relationship not found: "
        f"{left_position_group} -> {right_position_group}"
    )


__all__ = [
    "CrossPositionFamilyRelationshipRecord",
    "CrossPositionFamilyRelationshipResult",
    "build_cross_position_family_relationships",
    "get_cross_position_family_relationships",
    "get_cross_position_family_relationship",
]