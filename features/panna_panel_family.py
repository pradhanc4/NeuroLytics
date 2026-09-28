"""
Panna / Panel family resolution features.

Phase 15.2
-----------
Provides point-in-time-safe reference resolution for Panna and Panel
family classifications.

Design principles
-----------------
- Reuse existing database reference models.
- Reuse existing validators.
- Preserve leading-zero identifiers such as "005".
- Only active reference mappings are considered mapped.
- Missing or inactive mappings are represented explicitly.
- Never infer a family from digit structure.
- Do not perform historical frequency, recency, or transition analysis.
  Those belong to later Phase 15 milestones.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)
from database.panel_validator import validate_panel
from database.panna_validator import validate_panna


def resolve_panna_family(
    db: Session,
    panna: str,
) -> dict:
    """
    Resolve the active family/type classification for a Panna.

    Parameters
    ----------
    db:
        SQLAlchemy database session.

    panna:
        Three-digit Panna identifier.

    Returns
    -------
    dict
        A normalized Panna family-resolution record.

    Example
    -------
    {
        "panna": "005",
        "family": "family_a",
        "is_mapped": True,
        "is_active": True,
    }

    Notes
    -----
    - Panna values are normalized through the existing validator.
    - Leading zeros are preserved.
    - Only an active PannaReference can be mapped.
    - A missing panna_type means the Panna is explicitly unmapped.
    - No family is inferred from digit structure.
    """

    panna = validate_panna(panna)

    reference = db.scalar(
        select(PannaReference).where(
            PannaReference.panna == panna,
        )
    )

    if reference is None:
        return {
            "panna": panna,
            "family": None,
            "is_mapped": False,
            "is_active": False,
        }

    if not reference.is_active:
        return {
            "panna": panna,
            "family": None,
            "is_mapped": False,
            "is_active": False,
        }

    if reference.panna_type is None:
        return {
            "panna": panna,
            "family": None,
            "is_mapped": False,
            "is_active": True,
        }

    return {
        "panna": reference.panna,
        "family": reference.panna_type,
        "is_mapped": True,
        "is_active": True,
    }


def resolve_panel_family(
    db: Session,
    panel: str,
) -> dict:
    """
    Resolve the active family classification for a Panel.

    Parameters
    ----------
    db:
        SQLAlchemy database session.

    panel:
        Three-digit Panel identifier.

    Returns
    -------
    dict
        A normalized Panel family-resolution record.

    Example
    -------
    {
        "panel": "005",
        "family": "Family A",
        "family_id": 1,
        "is_mapped": True,
        "is_active": True,
    }

    Notes
    -----
    - Panel values are normalized through the existing validator.
    - Leading zeros are preserved.
    - Both the Panel member and its family must be active.
    - Missing family membership is explicitly unmapped.
    - No family is inferred from digit structure.
    """

    panel = validate_panel(panel)

    statement = (
        select(
            PanelFamilyMember,
            PanelFamily,
        )
        .join(
            PanelFamily,
            PanelFamily.id == PanelFamilyMember.family_id,
        )
        .where(
            PanelFamilyMember.panel == panel,
            PanelFamilyMember.is_active.is_(True),
            PanelFamily.is_active.is_(True),
        )
    )

    result = db.execute(statement).first()

    if result is None:
        return {
            "panel": panel,
            "family": None,
            "family_id": None,
            "is_mapped": False,
            "is_active": False,
        }

    member, family = result

    return {
        "panel": member.panel,
        "family": family.family_name,
        "family_id": family.id,
        "is_mapped": True,
        "is_active": True,
    }


__all__ = [
    "resolve_panna_family",
    "resolve_panel_family",
]