"""
Family transition features.

Phase 15.8
-----------

Builds authoritative family-to-family transitions between consecutive
historical observations.

Position groups
---------------
    col1-col3 -> Panna family
    col4-col5 -> Jodi family
    col6-col8 -> Panel family

Design principles
-----------------
- Reuse existing Panna, Jodi, and Panel family resolvers.
- Use only observations strictly before the target date.
- Only consecutive historical observations may form a transition.
- Both sides of a transition must resolve to active authoritative
  families.
- An unmapped observation breaks the transition chain.
- Never bridge across an unmapped observation.
- Preserve leading-zero identifiers.
- Do not calculate transition counts, percentages, stability,
  probability, trends, or predictions.
- Do not infer family membership from digit structure.
- Keep this layer standalone until the planned Phase 15.13 integration.
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


POSITION_GROUPS = (
    "col1-col3",
    "col4-col5",
    "col6-col8",
)

FAMILY_TYPES = (
    "panna",
    "jodi",
    "panel",
)


@dataclass(frozen=True)
class FamilyTransitionRecord:
    """One valid family-to-family transition."""

    position_group: str
    family_type: str

    from_family: str
    from_family_id: int | None

    to_family: str
    to_family_id: int | None

    from_is_mapped: bool
    to_is_mapped: bool

    from_is_active: bool
    to_is_active: bool

    feature_name: str


@dataclass(frozen=True)
class FamilyTransitionResult:
    """Complete family-transition output for one target date."""

    target_date: date
    records: tuple[FamilyTransitionRecord, ...]


def _get_position_index(
    position_group: str,
) -> tuple[int, int]:
    """Return the zero-based slice boundaries for a position group."""

    mapping = {
        "col1-col3": (0, 3),
        "col4-col5": (3, 5),
        "col6-col8": (5, 8),
    }

    try:
        return mapping[position_group]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported position group: {position_group}"
        ) from exc


def _build_position_value(
    positions: tuple[int, ...],
    position_group: str,
) -> str:
    """Build the authoritative Panna/Jodi/Panel identifier."""

    start, end = _get_position_index(
        position_group
    )

    return "".join(
        str(value)
        for value in positions[start:end]
    )


def _resolve_family(
    db,
    family_type: str,
    value: str,
) -> dict:
    """Resolve one family through the existing authoritative resolver."""

    if family_type == "panna":
        return resolve_panna_family(
            db=db,
            panna=value,
        )

    if family_type == "jodi":
        return resolve_jodi_family(
            db=db,
            jodi=value,
        )

    if family_type == "panel":
        return resolve_panel_family(
            db=db,
            panel=value,
        )

    raise ValueError(
        f"Unsupported family type: {family_type}"
    )


def _get_family_metadata(
    resolution: dict,
    family_type: str,
) -> tuple[str | None, int | None, bool, bool]:
    """Extract normalized family metadata from a resolver result."""

    family = resolution.get("family")

    family_id = resolution.get(
        "family_id"
    )

    is_mapped = bool(
        resolution.get(
            "is_mapped",
            False,
        )
    )

    is_active = bool(
        resolution.get(
            "is_active",
            False,
        )
    )

    if family_type == "panna":
        family_id = None

    return (
        family,
        family_id,
        is_mapped,
        is_active,
    )


def _resolve_observation_family(
    db,
    observation,
    position_group: str,
    family_type: str,
) -> dict:
    """Resolve one observation's family classification."""

    if len(observation.positions) != 8:
        raise ValueError(
            "Historical observation must contain exactly eight positions."
        )

    value = _build_position_value(
        observation.positions,
        position_group,
    )

    resolution = _resolve_family(
        db=db,
        family_type=family_type,
        value=value,
    )

    family, family_id, is_mapped, is_active = (
        _get_family_metadata(
            resolution,
            family_type,
        )
    )

    return {
        "value": value,
        "family": family,
        "family_id": family_id,
        "is_mapped": is_mapped,
        "is_active": is_active,
    }


def _build_feature_name(
    family_type: str,
    from_family: str,
    to_family: str,
) -> str:
    """Build a deterministic family-transition feature name."""

    return (
        f"{family_type}_family_transition_"
        f"{from_family}_to_{to_family}"
    )


def _build_transition_record(
    db,
    previous_observation,
    current_observation,
    position_group: str,
    family_type: str,
) -> FamilyTransitionRecord | None:
    """
    Build one transition when both consecutive observations are mapped.

    If either observation is unmapped or inactive, no transition is
    returned. This prevents an unmapped observation from being bridged.
    """

    previous = _resolve_observation_family(
        db=db,
        observation=previous_observation,
        position_group=position_group,
        family_type=family_type,
    )

    current = _resolve_observation_family(
        db=db,
        observation=current_observation,
        position_group=position_group,
        family_type=family_type,
    )

    if not (
        previous["is_mapped"]
        and previous["is_active"]
        and current["is_mapped"]
        and current["is_active"]
    ):
        return None

    previous_family = previous["family"]
    current_family = current["family"]

    if previous_family is None or current_family is None:
        return None

    feature_name = _build_feature_name(
        family_type=family_type,
        from_family=previous_family,
        to_family=current_family,
    )

    return FamilyTransitionRecord(
        position_group=position_group,
        family_type=family_type,
        from_family=previous_family,
        from_family_id=previous["family_id"],
        to_family=current_family,
        to_family_id=current["family_id"],
        from_is_mapped=True,
        to_is_mapped=True,
        from_is_active=True,
        to_is_active=True,
        feature_name=feature_name,
    )


def _build_family_transition_records(
    db,
    observations,
) -> list[FamilyTransitionRecord]:
    """Build all valid consecutive family transitions."""

    records: list[FamilyTransitionRecord] = []

    if len(observations) < 2:
        return records

    for index in range(1, len(observations)):
        previous_observation = observations[index - 1]
        current_observation = observations[index]

        for position_group, family_type in zip(
            POSITION_GROUPS,
            FAMILY_TYPES,
        ):
            record = _build_transition_record(
                db=db,
                previous_observation=previous_observation,
                current_observation=current_observation,
                position_group=position_group,
                family_type=family_type,
            )

            if record is not None:
                records.append(record)

    return records


def build_family_transition_features(
    db,
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> FamilyTransitionResult:
    """
    Build leakage-safe family transitions.

    Only observations strictly before history.target_date are used.

    Each transition is formed only between consecutive historical
    observations. Unmapped observations break the transition chain.
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

    validate_feature_config(
        config
    )

    if not config.family_transition_features_enabled:
        return FamilyTransitionResult(
            target_date=history.target_date,
            records=(),
        )

    observations = tuple(
        observation
        for observation in get_point_in_time_observations(history)
        if observation.result_date < history.target_date
    )

    records = _build_family_transition_records(
        db=db,
        observations=observations,
    )

    return FamilyTransitionResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_family_transition_record(
    result: FamilyTransitionResult,
    position_group: str,
    from_family: str,
    to_family: str,
) -> FamilyTransitionRecord:
    """Return one family transition record."""

    if not isinstance(
        result,
        FamilyTransitionResult,
    ):
        raise TypeError(
            "result must be a FamilyTransitionResult instance."
        )

    if not isinstance(
        position_group,
        str,
    ):
        raise TypeError(
            "position_group must be a string."
        )

    if not isinstance(
        from_family,
        str,
    ):
        raise TypeError(
            "from_family must be a string."
        )

    if not isinstance(
        to_family,
        str,
    ):
        raise TypeError(
            "to_family must be a string."
        )

    for record in result.records:
        if (
            record.position_group == position_group
            and record.from_family == from_family
            and record.to_family == to_family
        ):
            return record

    raise ValueError(
        "Family transition not found: "
        f"{position_group} -> "
        f"{from_family} -> "
        f"{to_family}"
    )


def get_family_transition_records(
    result: FamilyTransitionResult,
) -> tuple[FamilyTransitionRecord, ...]:
    """Return all family transition records."""

    if not isinstance(
        result,
        FamilyTransitionResult,
    ):
        raise TypeError(
            "result must be a FamilyTransitionResult instance."
        )

    return result.records


def get_family_transition_feature_names(
    result: FamilyTransitionResult,
) -> tuple[str, ...]:
    """Return all generated family-transition feature names."""

    if not isinstance(
        result,
        FamilyTransitionResult,
    ):
        raise TypeError(
            "result must be a FamilyTransitionResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_family_transition_value(
    result: FamilyTransitionResult,
    feature_name: str,
) -> FamilyTransitionRecord:
    """Return the transition record associated with a feature name."""

    if not isinstance(
        result,
        FamilyTransitionResult,
    ):
        raise TypeError(
            "result must be a FamilyTransitionResult instance."
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
            return record

    raise ValueError(
        f"Family transition feature not found: {feature_name}"
    )


__all__ = [
    "FamilyTransitionRecord",
    "FamilyTransitionResult",
    "build_family_transition_features",
    "get_family_transition_record",
    "get_family_transition_records",
    "get_family_transition_feature_names",
    "get_family_transition_value",
]