"""
Historical family frequency features.

Phase 15.6
-----------
Calculates point-in-time-safe historical frequency for authoritative
Panna, Jodi, and Panel families.

Design principles
-----------------
- Reuse existing family-resolution infrastructure.
- Reuse FeatureConfig.frequency_windows.
- Use observation-count windows.
- Exclude target-date and future observations.
- Count only active authoritative family mappings.
- Do not infer family identity from digit structure.
- Unmapped observations do not contribute to family counts or
  family-frequency denominators.
- Preserve deterministic family ordering.
- Do not calculate predictions, probabilities, recency, transitions,
  stability, or trends.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    JodiFamily,
    PannaReference,
    PanelFamily,
)
from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.panna_panel_family import (
    resolve_panel_family,
    resolve_panna_family,
)
from features.jodi_family import resolve_jodi_family


POSITION_GROUPS = (
    "col1-col3",
    "col4-col5",
    "col6-col8",
)


@dataclass(frozen=True)
class HistoricalFamilyFrequencyRecord:
    """One historical family-frequency feature."""

    feature_name: str
    value: float | int
    feature_type: str
    source: str
    family_type: str
    family: str
    window: int


@dataclass(frozen=True)
class HistoricalFamilyFrequencyResult:
    """Historical family-frequency output for one target date."""

    target_date: date
    records: tuple[
        HistoricalFamilyFrequencyRecord,
        ...
    ]


def _validate_target_date(
    target_date: date,
) -> None:
    if not isinstance(
        target_date,
        date,
    ):
        raise TypeError(
            "target_date must be a date instance."
        )


def _validate_history(
    history: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    if history is None:
        raise TypeError(
            "history must be an iterable of "
            "HistoricalFeatureObservation."
        )

    try:
        observations = tuple(history)
    except TypeError as exc:
        raise TypeError(
            "history must be an iterable of "
            "HistoricalFeatureObservation."
        ) from exc

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "history must contain only "
                "HistoricalFeatureObservation values."
            )

    return observations


def _validate_config(
    config: FeatureConfig,
) -> None:
    if not isinstance(
        config,
        FeatureConfig,
    ):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )


def _validate_db(
    db: Session,
) -> None:
    if db is None:
        raise ValueError(
            "db is required."
        )


def _get_prior_history(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
) -> tuple[HistoricalFeatureObservation, ...]:
    """Return observations strictly before target_date."""

    observations = _validate_history(
        history
    )

    prior = [
        observation
        for observation in observations
        if observation.result_date < target_date
    ]

    return tuple(
        sorted(
            prior,
            key=lambda observation: observation.result_date,
        )
    )


def _get_window_history(
    history: tuple[HistoricalFeatureObservation, ...],
    window: int,
) -> tuple[HistoricalFeatureObservation, ...]:
    """Return the latest observation-count window."""

    return tuple(
        history[-window:]
    )


def _build_panna_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return "".join(
        str(value)
        for value in observation.positions[0:3]
    )


def _build_jodi_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return "".join(
        str(value)
        for value in observation.positions[3:5]
    )


def _build_panel_value(
    observation: HistoricalFeatureObservation,
) -> str:
    return "".join(
        str(value)
        for value in observation.positions[5:8]
    )


def _get_active_panna_families(
    db: Session,
) -> tuple[str, ...]:
    """Return distinct active Panna family names."""

    rows = db.execute(
        select(
            PannaReference.panna_type
        )
        .where(
            PannaReference.is_active.is_(True),
            PannaReference.panna_type.is_not(None),
        )
        .distinct()
        .order_by(
            PannaReference.panna_type
        )
    ).all()

    return tuple(
        row[0]
        for row in rows
        if row[0] is not None
    )


def _get_active_jodi_families(
    db: Session,
) -> tuple[str, ...]:
    """Return active Jodi family names."""

    rows = db.execute(
        select(
            JodiFamily.family_name
        )
        .where(
            JodiFamily.is_active.is_(True),
        )
        .order_by(
            JodiFamily.family_name
        )
    ).all()

    return tuple(
        row[0]
        for row in rows
    )


def _get_active_panel_families(
    db: Session,
) -> tuple[str, ...]:
    """Return active Panel family names."""

    rows = db.execute(
        select(
            PanelFamily.family_name
        )
        .where(
            PanelFamily.is_active.is_(True),
        )
        .order_by(
            PanelFamily.family_name
        )
    ).all()

    return tuple(
        row[0]
        for row in rows
    )


def _get_family_universe(
    db: Session,
) -> dict[str, tuple[str, ...]]:
    """Return the authoritative active family universe."""

    return {
        "panna": _get_active_panna_families(db),
        "jodi": _get_active_jodi_families(db),
        "panel": _get_active_panel_families(db),
    }


def _resolve_observation_families(
    db: Session,
    observation: HistoricalFeatureObservation,
) -> dict[str, str | None]:
    """Resolve all three authoritative families for one observation."""

    panna_resolution = resolve_panna_family(
        db=db,
        panna=_build_panna_value(observation),
    )

    jodi_resolution = resolve_jodi_family(
        db=db,
        jodi=_build_jodi_value(observation),
    )

    panel_resolution = resolve_panel_family(
        db=db,
        panel=_build_panel_value(observation),
    )

    return {
        "panna": (
            panna_resolution["family"]
            if panna_resolution["is_mapped"]
            else None
        ),
        "jodi": (
            jodi_resolution["family"]
            if jodi_resolution["is_mapped"]
            else None
        ),
        "panel": (
            panel_resolution["family"]
            if panel_resolution["is_mapped"]
            else None
        ),
    }


def _count_family_occurrences(
    db: Session,
    history: tuple[HistoricalFeatureObservation, ...],
) -> dict[str, dict[str, int]]:
    """
    Count mapped family occurrences.

    Unmapped observations are deliberately excluded.
    """

    counts: dict[str, dict[str, int]] = {
        "panna": {},
        "jodi": {},
        "panel": {},
    }

    for observation in history:
        resolved = _resolve_observation_families(
            db=db,
            observation=observation,
        )

        for family_type in (
            "panna",
            "jodi",
            "panel",
        ):
            family = resolved[family_type]

            if family is None:
                continue

            counts[family_type][family] = (
                counts[family_type].get(
                    family,
                    0,
                )
                + 1
            )

    return counts


def _build_frequency_records(
    family_universe: dict[str, tuple[str, ...]],
    counts: dict[str, dict[str, int]],
    window: int,
    target_date: date,
) -> tuple[
    HistoricalFamilyFrequencyRecord,
    ...
]:
    records: list[
        HistoricalFamilyFrequencyRecord
    ] = []

    for family_type in (
        "panna",
        "jodi",
        "panel",
    ):
        families = family_universe[family_type]

        total_mapped = sum(
            counts[family_type].values()
        )

        for family in families:
            count = counts[
                family_type
            ].get(
                family,
                0,
            )

            percentage = (
                (count / total_mapped) * 100.0
                if total_mapped > 0
                else 0.0
            )

            records.append(
                HistoricalFamilyFrequencyRecord(
                    feature_name=(
                        f"{family_type}_family_"
                        f"frequency_count_"
                        f"{window}_{family}"
                    ),
                    value=count,
                    feature_type="historical_family_frequency",
                    source=(
                        "features.historical_family_frequency"
                    ),
                    family_type=family_type,
                    family=family,
                    window=window,
                )
            )

            records.append(
                HistoricalFamilyFrequencyRecord(
                    feature_name=(
                        f"{family_type}_family_"
                        f"frequency_percentage_"
                        f"{window}_{family}"
                    ),
                    value=percentage,
                    feature_type="historical_family_frequency",
                    source=(
                        "features.historical_family_frequency"
                    ),
                    family_type=family_type,
                    family=family,
                    window=window,
                )
            )

    return tuple(records)


def build_historical_family_frequency_features(
    db: Session,
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
    config: FeatureConfig,
) -> HistoricalFamilyFrequencyResult:
    """
    Build historical family-frequency features.

    Only observations strictly before target_date are considered.

    Each configured frequency window selects the latest N prior
    observations.

    The denominator for percentage is the number of mapped
    observations for the corresponding family type within that
    window. Unmapped observations do not contribute to any family.
    """

    _validate_db(db)
    _validate_target_date(target_date)
    _validate_config(config)

    observations = _get_prior_history(
        history=history,
        target_date=target_date,
    )

    family_universe = _get_family_universe(
        db
    )

    records: list[
        HistoricalFamilyFrequencyRecord
    ] = []

    for window in config.frequency_windows:
        window_history = _get_window_history(
            observations,
            window,
        )

        counts = _count_family_occurrences(
            db=db,
            history=window_history,
        )

        records.extend(
            _build_frequency_records(
                family_universe=family_universe,
                counts=counts,
                window=window,
                target_date=target_date,
            )
        )

    return HistoricalFamilyFrequencyResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_historical_family_frequency_feature_value(
    result: HistoricalFamilyFrequencyResult,
    feature_name: str,
) -> float | int:
    """Return one historical family-frequency feature value."""

    if not isinstance(
        result,
        HistoricalFamilyFrequencyResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFamilyFrequencyResult instance."
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
        "Historical family frequency feature not found: "
        f"{feature_name}"
    )


def get_historical_family_frequency_feature_names(
    result: HistoricalFamilyFrequencyResult,
) -> tuple[str, ...]:
    """Return all historical family-frequency feature names."""

    if not isinstance(
        result,
        HistoricalFamilyFrequencyResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFamilyFrequencyResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_historical_family_frequency_feature_values(
    result: HistoricalFamilyFrequencyResult,
) -> dict[str, float | int]:
    """Return historical family-frequency features as a mapping."""

    if not isinstance(
        result,
        HistoricalFamilyFrequencyResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFamilyFrequencyResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }


__all__ = [
    "HistoricalFamilyFrequencyRecord",
    "HistoricalFamilyFrequencyResult",
    "build_historical_family_frequency_features",
    "get_historical_family_frequency_feature_value",
    "get_historical_family_frequency_feature_names",
    "get_historical_family_frequency_feature_values",
]