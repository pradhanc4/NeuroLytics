from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Literal

FAMILY_MASTER_VERSION = "1.0.0"
PANEL_TYPES = ("single", "double", "triple")
MASTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "reference"
    / "family_master.json"
)


class FamilyMasterError(ValueError):
    """Raised when the authoritative family master is invalid."""


def _normalize_jodi(value: str) -> str:
    value = str(value).strip()
    if len(value) != 2 or not value.isdigit():
        raise FamilyMasterError("Jodi must contain exactly 2 digits.")
    return value


def _normalize_panel(value: str) -> str:
    value = str(value).strip()
    if len(value) != 3 or not value.isdigit():
        raise FamilyMasterError("Panel must contain exactly 3 digits.")
    return value


def _normalize_digit(value: int | str) -> str:
    text = str(value).strip()
    if len(text) != 1 or not text.isdigit():
        raise FamilyMasterError("Digit must be one digit from 0 through 9.")
    return text


def load_family_master(path: Path | None = None) -> dict:
    source = path or MASTER_PATH
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FamilyMasterError(
            f"Family master file not found: {source}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise FamilyMasterError(
            f"Family master JSON is invalid: {source}"
        ) from exc

    validate_family_master(payload)
    return payload


def validate_family_master(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise FamilyMasterError("Family master must be an object.")

    if payload.get("version") != FAMILY_MASTER_VERSION:
        raise FamilyMasterError("Unsupported family master version.")

    jodi = payload.get("jodi_families")
    panel = payload.get("panel_families")

    if not isinstance(jodi, dict) or not isinstance(panel, dict):
        raise FamilyMasterError(
            "Family master must contain jodi_families and panel_families."
        )

    expected_jodi_families = {
        "12", "13", "14", "15", "23", "24",
        "25", "34", "35", "45", "HALF_RED", "FULL_RED",
    }
    if set(jodi) != expected_jodi_families:
        raise FamilyMasterError("Jodi family IDs do not match the authoritative chart.")

    expected_panel_families = set("0123456789")
    if set(panel) != expected_panel_families:
        raise FamilyMasterError("Panel family IDs must contain digits 0 through 9.")

    all_jodis: list[str] = []
    for family_id, members in jodi.items():
        if not isinstance(members, list) or not members:
            raise FamilyMasterError(f"Jodi family {family_id} is empty.")
        normalized = [_normalize_jodi(item) for item in members]
        if len(normalized) != len(set(normalized)):
            raise FamilyMasterError(f"Duplicate Jodi inside family {family_id}.")
        all_jodis.extend(normalized)

    if len(all_jodis) != 100 or set(all_jodis) != {
        f"{value:02d}" for value in range(100)
    }:
        raise FamilyMasterError(
            "Jodi chart must contain every Jodi 00 through 99 exactly once."
        )

    all_panels: list[str] = []
    for family_id, family in panel.items():
        if not isinstance(family, dict) or set(family) != set(PANEL_TYPES):
            raise FamilyMasterError(
                f"Panel family {family_id} must contain Single, Double and Triple sets."
            )
        for panel_type in PANEL_TYPES:
            members = family[panel_type]
            if not isinstance(members, list) or not members:
                raise FamilyMasterError(
                    f"Panel family {family_id}/{panel_type} is empty."
                )
            normalized = [_normalize_panel(item) for item in members]
            if len(normalized) != len(set(normalized)):
                raise FamilyMasterError(
                    f"Duplicate panel inside family {family_id}/{panel_type}."
                )
            all_panels.extend(normalized)

    if len(all_panels) != 220 or len(set(all_panels)) != 220:
        raise FamilyMasterError(
            "Panel chart must contain exactly 220 unique panels."
        )


def jodi_family_for(jodi: str) -> str:
    value = _normalize_jodi(jodi)
    master = load_family_master()
    for family_id, members in master["jodi_families"].items():
        if value in members:
            return family_id
    raise FamilyMasterError(f"No Jodi family mapping exists for {value}.")


def jodis_in_family(family_id: str) -> tuple[str, ...]:
    master = load_family_master()
    if family_id not in master["jodi_families"]:
        raise FamilyMasterError(f"Unknown Jodi family: {family_id}")
    return tuple(master["jodi_families"][family_id])


def panel_family_for_digit(digit: int | str) -> str:
    return _normalize_digit(digit)


def panel_family_for_panel(panel: str) -> str:
    value = _normalize_panel(panel)
    master = load_family_master()
    matches = [
        family_id
        for family_id, family in master["panel_families"].items()
        if any(value in family[panel_type] for panel_type in PANEL_TYPES)
    ]
    if len(matches) != 1:
        raise FamilyMasterError(
            f"Panel {value} must belong to exactly one panel family; found {matches}."
        )
    return matches[0]


def panel_type_for(panel: str) -> Literal["single", "double", "triple"]:
    value = _normalize_panel(panel)
    master = load_family_master()
    matches = [
        panel_type
        for panel_type in PANEL_TYPES
        if value in master["panel_families"][panel_family_for_panel(value)][panel_type]
    ]
    if len(matches) != 1:
        raise FamilyMasterError(
            f"Panel {value} must have exactly one panel type; found {matches}."
        )
    return matches[0]  # type: ignore[return-value]


def panels_for_digit(
    digit: int | str,
    panel_types: Iterable[str] | None = None,
) -> tuple[str, ...]:
    family_id = panel_family_for_digit(digit)
    master = load_family_master()
    selected_types = tuple(panel_types or PANEL_TYPES)
    invalid = set(selected_types) - set(PANEL_TYPES)
    if invalid:
        raise FamilyMasterError(
            f"Unknown panel types: {sorted(invalid)}."
        )

    result: list[str] = []
    for panel_type in selected_types:
        result.extend(master["panel_families"][family_id][panel_type])
    return tuple(result)


def is_panel_valid_for_digit(panel: str, digit: int | str) -> bool:
    value = _normalize_panel(panel)
    expected_family = panel_family_for_digit(digit)
    return panel_family_for_panel(value) == expected_family


def jodi_family_summary() -> dict[str, int]:
    master = load_family_master()
    return {
        family_id: len(members)
        for family_id, members in master["jodi_families"].items()
    }


def panel_family_summary() -> dict[str, dict[str, int]]:
    master = load_family_master()
    return {
        family_id: {
            panel_type: len(family[panel_type])
            for panel_type in PANEL_TYPES
        }
        for family_id, family in master["panel_families"].items()
    }


__all__ = [
    "FAMILY_MASTER_VERSION",
    "PANEL_TYPES",
    "MASTER_PATH",
    "FamilyMasterError",
    "load_family_master",
    "validate_family_master",
    "jodi_family_for",
    "jodis_in_family",
    "panel_family_for_digit",
    "panel_family_for_panel",
    "panel_type_for",
    "panels_for_digit",
    "is_panel_valid_for_digit",
    "jodi_family_summary",
    "panel_family_summary",
]
