"""
Jodi family resolution features.

Phase 15.3
-----------
Provides reference-based resolution for Jodi family classifications.

Design principles
-----------------
- Reuse the existing Jodi family reference infrastructure.
- Reuse the existing Jodi validator.
- Preserve leading-zero identifiers such as "05" and "00".
- Only active Jodi members belonging to active families are mapped.
- Missing or inactive mappings are represented explicitly.
- Never infer a family from Jodi digit structure.
- Historical frequency, recency, and transition analysis belong
  to later Phase 15 milestones.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.jodi_validator import validate_jodi
from database.models import (
    JodiFamily,
    JodiFamilyMember,
)


def resolve_jodi_family(
    db: Session,
    jodi: str,
) -> dict:
    """
    Resolve the active family classification for a Jodi.

    Parameters
    ----------
    db:
        SQLAlchemy database session.

    jodi:
        Two-digit Jodi identifier.

    Returns
    -------
    dict
        Normalized Jodi family-resolution record.

    Example
    -------
    {
        "jodi": "05",
        "family": "Family A",
        "family_id": 1,
        "is_mapped": True,
        "is_active": True,
    }

    Notes
    -----
    - Jodi values are normalized through the existing validator.
    - Leading zeros are preserved.
    - Both the Jodi member and its family must be active.
    - Missing family membership is explicitly unmapped.
    - No family is inferred from digit structure.
    """

    jodi = validate_jodi(jodi)

    statement = (
        select(
            JodiFamilyMember,
            JodiFamily,
        )
        .join(
            JodiFamily,
            JodiFamily.id == JodiFamilyMember.family_id,
        )
        .where(
            JodiFamilyMember.jodi == jodi,
            JodiFamilyMember.is_active.is_(True),
            JodiFamily.is_active.is_(True),
        )
    )

    result = db.execute(statement).first()

    if result is None:
        return {
            "jodi": jodi,
            "family": None,
            "family_id": None,
            "is_mapped": False,
            "is_active": False,
        }

    member, family = result

    return {
        "jodi": member.jodi,
        "family": family.family_name,
        "family_id": family.id,
        "is_mapped": True,
        "is_active": True,
    }


__all__ = [
    "resolve_jodi_family",
]