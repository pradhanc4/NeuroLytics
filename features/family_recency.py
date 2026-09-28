"""
Phase 15.7 - Family Recency Features.

Provides point-in-time family recency features for
Panna, Jodi, and Panel families.

This module is intentionally standalone.

It does not:
    - perform prediction
    - calculate probabilities
    - calculate frequency
    - calculate transitions
    - calculate trends
    - modify the unified dataset
    - infer families from digit structure

Family identity always comes from the authoritative
database family mapping infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import distinct

from database.models import (
    JodiFamily,
    PannaReference,
    PanelFamily,
)
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
    HistoricalFeatureObservation,
    PointInTimeHistory,
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
class FamilyRecencyRecord:
    """
    One family-recency feature record.
    """

    feature_name: str
    value: int | bool | None
    feature_type: str
    source: str
    family_type: str
    family: str
    metric: str
    lookback: int | None


@dataclass(frozen=True)
class FamilyRecencyResult:
    """
    Complete Phase 15.7 family-recency result.
    """

    target_date: date
    records: tuple[FamilyRecencyRecord, ...]


def _validate_target_date(
    target_date: date,
) -> None:
    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a date instance."
        )


def _validate_history(
    history: PointInTimeHistory,
) -> None:
    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )


def _validate_db(db) -> None:
    if db is None:
        raise TypeError(
            "db is required."
        )

    if not hasattr(db, "query"):
        raise TypeError(
            "db must provide a query() method."
        )


def _get_prior_history(
    history: PointInTimeHistory,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Return only observations strictly before target_date.

    The explicit date filter is retained here even though
    PointInTimeHistory is expected to already be point-in-time
    filtered. This creates a defensive leakage boundary.
    """

    observations = tuple(
        observation
        for observation in history.observations
        if observation.result_date
        < history.target_date
    )

    return tuple(
        sorted(
            observations,
            key=lambda observation: (
                observation.result_date,
                observation.result_id,
            ),
        )
    )


def _build_panna_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return (
        f"{observation.positions[0]}"
        f"{observation.positions[1]}"
        f"{observation.positions[2]}"
    )


def _build_jodi_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return (
        f"{observation.positions[3]}"
        f"{observation.positions[4]}"
    )


def _build_panel_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return (
        f"{observation.positions[5]}"
        f"{observation.positions[6]}"
        f"{observation.positions[7]}"
    )


def _get_active_panna_families(
    db,
) -> tuple[str, ...]:
    rows = (
        db.query(
            distinct(PannaReference.panna_type)
        )
        .filter(
            PannaReference.is_active.is_(True),
            PannaReference.panna_type.isnot(None),
        )
        .all()
    )

    return tuple(
        sorted(
            {
                row[0]
                for row in rows
                if row[0] is not None
                and str(row[0]).strip()
            }
        )
    )


def _get_active_jodi_families(
    db,
) -> tuple[str, ...]:
    rows = (
        db.query(
            distinct(JodiFamily.family_name)
        )
        .filter(
            JodiFamily.is_active.is_(True),
        )
        .all()
    )

    return tuple(
        sorted(
            {
                row[0]
                for row in rows
                if row[0] is not None
                and str(row[0]).strip()
            }
        )
    )


def _get_active_panel_families(
    db,
) -> tuple[str, ...]:
    rows = (
        db.query(
            distinct(PanelFamily.family_name)
        )
        .filter(
            PanelFamily.is_active.is_(True),
        )
        .all()
    )

    return tuple(
        sorted(
            {
                row[0]
                for row in rows
                if row[0] is not None
                and str(row[0]).strip()
            }
        )
    )


def _get_family_universe(
    db,
) -> dict[str, tuple[str, ...]]:
    return {
        "panna": _get_active_panna_families(db),
        "jodi": _get_active_jodi_families(db),
        "panel": _get_active_panel_families(db),
    }


def _resolve_observation_families(
    db,
    observation: HistoricalFeatureObservation,
) -> dict[str, str | None]:
    """
    Resolve the authoritative family for one historical observation.

    Only active authoritative mappings are accepted.
    """

    panna_result = resolve_panna_family(
        db,
        _build_panna_value(observation),
    )

    jodi_result = resolve_jodi_family(
        db,
        _build_jodi_value(observation),
    )

    panel_result = resolve_panel_family(
        db,
        _build_panel_value(observation),
    )

    return {
        "panna": (
            panna_result["family"]
            if panna_result["is_mapped"]
            and panna_result["is_active"]
            else None
        ),
        "jodi": (
            jodi_result["family"]
            if jodi_result["is_mapped"]
            and jodi_result["is_active"]
            else None
        ),
        "panel": (
            panel_result["family"]
            if panel_result["is_mapped"]
            and panel_result["is_active"]
            else None
        ),
    }


def _calculate_family_recency(
    db,
    observations: tuple[HistoricalFeatureObservation, ...],
    family_type: str,
    family: str,
) -> int | None:
    """
    Return the number of prior observations since the family
    was last seen.

    Example:

        Family seen at:
            observation 1
            observation 2
            observation 5

        Target follows observation 5.

        Recency = 0.

    If the family was last seen at observation 2
    and observations 3, 4, and 5 followed it:

        Recency = 3.

    None means the family has never been observed in the
    available point-in-time history.
    """

    if family_type not in FAMILY_TYPES:
        raise ValueError(
            f"Unsupported family_type: {family_type}"
        )

    for index in range(
        len(observations) - 1,
        -1,
        -1,
    ):
        resolved = _resolve_observation_families(
            db,
            observations[index],
        )

        if resolved[family_type] == family:
            return (
                len(observations)
                - 1
                - index
            )

    return None


def _build_recency_feature_name(
    family_type: str,
    family: str,
) -> str:
    return (
        f"{family_type}_family_recency_{family}"
    )


def _build_seen_within_feature_name(
    family_type: str,
    lookback: int,
    family: str,
) -> str:
    return (
        f"{family_type}_family_seen_within_"
        f"lookback_{lookback}_{family}"
    )


def _build_family_recency_records(
    db,
    observations: tuple[HistoricalFeatureObservation, ...],
    family_universe: dict[str, tuple[str, ...]],
    lookbacks: tuple[int, ...],
) -> tuple[FamilyRecencyRecord, ...]:
    records: list[FamilyRecencyRecord] = []

    for family_type in FAMILY_TYPES:
        for family in family_universe[family_type]:
            recency = _calculate_family_recency(
                db,
                observations,
                family_type,
                family,
            )

            records.append(
                FamilyRecencyRecord(
                    feature_name=(
                        _build_recency_feature_name(
                            family_type,
                            family,
                        )
                    ),
                    value=recency,
                    feature_type="family_recency",
                    source="features.family_recency",
                    family_type=family_type,
                    family=family,
                    metric=(
                        "observations_since_last_seen"
                    ),
                    lookback=None,
                )
            )

            for lookback in lookbacks:
                seen_within = (
                    recency is not None
                    and recency < lookback
                )

                records.append(
                    FamilyRecencyRecord(
                        feature_name=(
                            _build_seen_within_feature_name(
                                family_type,
                                lookback,
                                family,
                            )
                        ),
                        value=seen_within,
                        feature_type="family_recency",
                        source="features.family_recency",
                        family_type=family_type,
                        family=family,
                        metric="seen_within_lookback",
                        lookback=lookback,
                    )
                )

    return tuple(records)


def build_family_recency_features(
    db,
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> FamilyRecencyResult:
    """
    Build point-in-time family recency features.

    Only observations strictly before the target date are used.

    Recency is measured in historical observations, matching
    the existing NeuroLytics recency convention.

    Active authoritative families are represented even when
    they have never appeared in the available history.

    A never-seen family receives:

        observations_since_last_seen = None

    and:

        seen_within_lookback = False

    for every configured lookback.

    No prediction or future information is used.
    """

    _validate_db(db)
    _validate_history(history)

    if not isinstance(config, FeatureConfig):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )

    validate_feature_config(config)

    target_date = history.target_date

    _validate_target_date(target_date)

    if not config.family_recency_features_enabled:
        return FamilyRecencyResult(
            target_date=target_date,
            records=(),
        )

    observations = _get_prior_history(
        history,
    )

    family_universe = _get_family_universe(
        db,
    )

    records = _build_family_recency_records(
        db=db,
        observations=observations,
        family_universe=family_universe,
        lookbacks=config.recency_lookbacks,
    )

    return FamilyRecencyResult(
        target_date=target_date,
        records=records,
    )


def get_family_recency_record(
    result: FamilyRecencyResult,
    feature_name: str,
) -> FamilyRecencyRecord:
    if not isinstance(
        result,
        FamilyRecencyResult,
    ):
        raise TypeError(
            "result must be a FamilyRecencyResult instance."
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
        f"Family recency feature not found: "
        f"{feature_name}"
    )


def get_family_recency_value(
    result: FamilyRecencyResult,
    feature_name: str,
):
    return get_family_recency_record(
        result,
        feature_name,
    ).value


def get_family_recency_feature_names(
    result: FamilyRecencyResult,
) -> tuple[str, ...]:
    if not isinstance(
        result,
        FamilyRecencyResult,
    ):
        raise TypeError(
            "result must be a FamilyRecencyResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_family_recency_records(
    result: FamilyRecencyResult,
) -> tuple[FamilyRecencyRecord, ...]:
    if not isinstance(
        result,
        FamilyRecencyResult,
    ):
        raise TypeError(
            "result must be a FamilyRecencyResult instance."
        )

    return result.records