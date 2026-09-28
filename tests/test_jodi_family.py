from database.models import (
    JodiFamily,
    JodiFamilyMember,
)
from features.jodi_family import resolve_jodi_family


# ---------------------------------------------------------------------------
# Active Jodi family resolution
# ---------------------------------------------------------------------------


def test_resolve_active_jodi_family(db):
    family = JodiFamily(
        family_name="Family A",
        description="Test family",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="12",
        digit_1=1,
        digit_2=2,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, "12")

    assert result == {
        "jodi": "12",
        "family": "Family A",
        "family_id": family.id,
        "is_mapped": True,
        "is_active": True,
    }


def test_resolve_jodi_preserves_leading_zero(db):
    family = JodiFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="05",
        digit_1=0,
        digit_2=5,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, "05")

    assert result["jodi"] == "05"
    assert result["family"] == "Family A"
    assert result["family_id"] == family.id
    assert result["is_mapped"] is True
    assert result["is_active"] is True


def test_resolve_jodi_preserves_double_zero(db):
    family = JodiFamily(
        family_name="Family Zero",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="00",
        digit_1=0,
        digit_2=0,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, "00")

    assert result["jodi"] == "00"
    assert result["family"] == "Family Zero"
    assert result["is_mapped"] is True


def test_resolve_jodi_normalizes_whitespace(db):
    family = JodiFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="07",
        digit_1=0,
        digit_2=7,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, " 07 ")

    assert result["jodi"] == "07"
    assert result["family"] == "Family A"


# ---------------------------------------------------------------------------
# Missing / inactive mappings
# ---------------------------------------------------------------------------


def test_resolve_unmapped_jodi(db):
    result = resolve_jodi_family(db, "12")

    assert result == {
        "jodi": "12",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


def test_resolve_inactive_jodi_member_is_unmapped(db):
    family = JodiFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="12",
        digit_1=1,
        digit_2=2,
        is_active=False,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, "12")

    assert result == {
        "jodi": "12",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


def test_resolve_jodi_with_inactive_family_is_unmapped(db):
    family = JodiFamily(
        family_name="Family A",
        is_active=False,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="12",
        digit_1=1,
        digit_2=2,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_jodi_family(db, "12")

    assert result == {
        "jodi": "12",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


# ---------------------------------------------------------------------------
# No digit-based inference
# ---------------------------------------------------------------------------


def test_jodi_digits_do_not_create_family_mapping(db):
    result = resolve_jodi_family(db, "11")

    assert result["family"] is None
    assert result["family_id"] is None
    assert result["is_mapped"] is False


# ---------------------------------------------------------------------------
# Zero handling
# ---------------------------------------------------------------------------


def test_unmapped_zero_jodi_is_still_valid(db):
    result = resolve_jodi_family(db, "00")

    assert result == {
        "jodi": "00",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }