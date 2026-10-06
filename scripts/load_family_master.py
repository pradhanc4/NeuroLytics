from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.engine import SessionLocal
from database.jodi_service import JodiFamilyService
from database.models import JodiFamily, JodiFamilyMember, PannaReference, PanelFamily, PanelFamilyMember
from database.panel_service import PanelFamilyService
from analytics.family_master import load_family_master


def seed_family_master() -> dict[str, int]:
    master = load_family_master()
    db = SessionLocal()
    try:
        jodi_service = JodiFamilyService(db)
        panel_service = PanelFamilyService(db)

        jodi_members_added = 0
        panel_members_added = 0
        panna_added = 0

        for family_name, members in master["jodi_families"].items():
            family = db.query(JodiFamily).filter_by(family_name=family_name).one_or_none()
            if family is None:
                family = jodi_service.create_family(
                    family_name,
                    description="Authoritative user-supplied Jodi family master.",
                )
            for value in members:
                existing = (
                    db.query(JodiFamilyMember)
                    .filter_by(family_id=family.id, jodi=value)
                    .one_or_none()
                )
                if existing is None:
                    jodi_service.add_member(family, value)
                    jodi_members_added += 1

        for family_name, family_data in master["panel_families"].items():
            family = db.query(PanelFamily).filter_by(family_name=family_name).one_or_none()
            if family is None:
                family = panel_service.create_family(
                    family_name,
                    description="Authoritative user-supplied Panel family master.",
                )
            for panel_type, members in family_data.items():
                for value in members:
                    existing = (
                        db.query(PanelFamilyMember)
                        .filter_by(family_id=family.id, panel=value)
                        .one_or_none()
                    )
                    if existing is None:
                        panel_service.add_member(family, value)
                        panel_members_added += 1

                    panna = db.query(PannaReference).filter_by(panna=value).one_or_none()
                    if panna is None:
                        from database.panna_service import PannaReferenceService
                        PannaReferenceService(db).create_panna(value, panna_type=panel_type)
                        panna_added += 1

        return {
            "jodi_families": len(master["jodi_families"]),
            "jodi_members_added": jodi_members_added,
            "panel_families": len(master["panel_families"]),
            "panel_members_added": panel_members_added,
            "panna_added": panna_added,
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(seed_family_master())
