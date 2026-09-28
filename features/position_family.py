"""
Position-family relationship features.

Phase 15.4
-----------
Resolves the family classification associated with each historical
position group:

    col1-col3 -> Panna family
    col4-col5 -> Jodi family
    col6-col8 -> Panel family

Design principles
-----------------
- Reuse the existing Panna, Jodi, and Panel family resolvers.
- Use only the latest observation strictly before the target date.
- Preserve leading-zero identifiers.
- Never infer a family from digit structure.
- Inactive or missing mappings remain explicitly unmapped.
- Do not calculate historical frequency, recency, transitions,
  probabilities, or predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.jodi_family import resolve_jodi_family
from features.panna_panel_family import (
    resolve_panel_family,
    resolve_panna_family,
)
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


@dataclass(frozen=True)
class PositionFamilyRecord:
    """Family classification for one position group."""

    position_group: str
    family_type: str
    value: str | None
    family: str | None
    family_id: int | None
    is_mapped: bool
    is_active: bool


@dataclass(frozen=True)
class PositionFamilyResult:
    """Complete position-family output for one target date."""

    target_date: date
    records: tuple[PositionFamilyRecord, ...]


def _build_panna_value(
    positions: tuple[int, ...],
) -> str:
    """Build the three-digit Panna identifier from col1-col3."""

    return "".join(
        str(value)
        for value in positions[0:3]
    )


def _build_jodi_value(
    positions: tuple[int, ...],
) -> str:
    """Build the two-digit Jodi identifier from col4-col5."""

    return "".join(
        str(value)
        for value in positions[3:5]
    )


def _build_panel_value(
    positions: tuple[int, ...],
) -> str:
    """Build the three-digit Panel identifier from col6-col8."""

    return "".join(
        str(value)
        for value in positions[5:8]
    )


def _build_unmapped_record(
    position_group: str,
    family_type: str,
    value: str | None,
) -> PositionFamilyRecord:
    """Build an explicit unmapped family record."""

    return PositionFamilyRecord(
        position_group=position_group,
        family_type=family_type,
        value=value,
        family=None,
        family_id=None,
        is_mapped=False,
        is_active=False,
    )


def _resolve_panna_record(
    db,
    positions: tuple[int, ...],
) -> PositionFamilyRecord:
    """Resolve the Panna family for col1-col3."""

    value = _build_panna_value(positions)

    resolution = resolve_panna_family(
        db=db,
        panna=value,
    )

    return PositionFamilyRecord(
        position_group="col1-col3",
        family_type="panna",
        value=resolution["panna"],
        family=resolution["family"],
        family_id=None,
        is_mapped=resolution["is_mapped"],
        is_active=resolution["is_active"],
    )


def _resolve_jodi_record(
    db,
    positions: tuple[int, ...],
) -> PositionFamilyRecord:
    """Resolve the Jodi family for col4-col5."""

    value = _build_jodi_value(positions)

    resolution = resolve_jodi_family(
        db=db,
        jodi=value,
    )

    return PositionFamilyRecord(
        position_group="col4-col5",
        family_type="jodi",
        value=resolution["jodi"],
        family=resolution["family"],
        family_id=resolution["family_id"],
        is_mapped=resolution["is_mapped"],
        is_active=resolution["is_active"],
    )


def _resolve_panel_record(
    db,
    positions: tuple[int, ...],
) -> PositionFamilyRecord:
    """Resolve the Panel family for col6-col8."""

    value = _build_panel_value(positions)

    resolution = resolve_panel_family(
        db=db,
        panel=value,
    )

    return PositionFamilyRecord(
        position_group="col6-col8",
        family_type="panel",
        value=resolution["panel"],
        family=resolution["family"],
        family_id=resolution["family_id"],
        is_mapped=resolution["is_mapped"],
        is_active=resolution["is_active"],
    )


def build_position_family_features(
    db,
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> PositionFamilyResult:
    """
    Build position-family features from the latest historical observation.

    Only observations strictly before history.target_date are used.

    The latest available historical observation supplies:

        col1-col3 -> Panna
        col4-col5 -> Jodi
        col6-col8 -> Panel
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
        records = (
            _build_unmapped_record(
                "col1-col3",
                "panna",
                None,
            ),
            _build_unmapped_record(
                "col4-col5",
                "jodi",
                None,
            ),
            _build_unmapped_record(
                "col6-col8",
                "panel",
                None,
            ),
        )

        return PositionFamilyResult(
            target_date=history.target_date,
            records=records,
        )

    latest = observations[-1]
    positions = latest.positions

    if len(positions) != 8:
        raise ValueError(
            "Historical observation must contain exactly eight positions."
        )

    records = (
        _resolve_panna_record(
            db=db,
            positions=positions,
        ),
        _resolve_jodi_record(
            db=db,
            positions=positions,
        ),
        _resolve_panel_record(
            db=db,
            positions=positions,
        ),
    )

    return PositionFamilyResult(
        target_date=history.target_date,
        records=records,
    )


def get_position_family_record(
    result: PositionFamilyResult,
    position_group: str,
) -> PositionFamilyRecord:
    """Return one position-family record."""

    if not isinstance(
        result,
        PositionFamilyResult,
    ):
        raise TypeError(
            "result must be a PositionFamilyResult instance."
        )

    if not isinstance(
        position_group,
        str,
    ):
        raise TypeError(
            "position_group must be a string."
        )

    for record in result.records:
        if record.position_group == position_group:
            return record

    raise ValueError(
        f"Position-family record not found: {position_group}"
    )


def get_position_family_records(
    result: PositionFamilyResult,
) -> tuple[PositionFamilyRecord, ...]:
    """Return all position-family records."""

    if not isinstance(
        result,
        PositionFamilyResult,
    ):
        raise TypeError(
            "result must be a PositionFamilyResult instance."
        )

    return result.records


__all__ = [
    "PositionFamilyRecord",
    "PositionFamilyResult",
    "build_position_family_features",
    "get_position_family_record",
    "get_position_family_records",
]