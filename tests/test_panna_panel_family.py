from database.models import (
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)
from features.panna_panel_family import (
    resolve_panna_family,
    resolve_panel_family,
)


# ---------------------------------------------------------------------------
# Panna family resolution
# ---------------------------------------------------------------------------


def test_resolve_active_panna_family(db):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="family_a",
        is_active=True,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, "123")

    assert result == {
        "panna": "123",
        "family": "family_a",
        "is_mapped": True,
        "is_active": True,
    }


def test_resolve_panna_preserves_leading_zeros(db):
    panna = PannaReference(
        panna="005",
        digit_1=0,
        digit_2=0,
        digit_3=5,
        panna_type="family_a",
        is_active=True,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, "005")

    assert result["panna"] == "005"
    assert result["family"] == "family_a"
    assert result["is_mapped"] is True
    assert result["is_active"] is True


def test_resolve_panna_with_whitespace_preserves_normalized_value(db):
    panna = PannaReference(
        panna="005",
        digit_1=0,
        digit_2=0,
        digit_3=5,
        panna_type="family_a",
        is_active=True,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, " 005 ")

    assert result["panna"] == "005"
    assert result["family"] == "family_a"


def test_resolve_panna_without_family_is_unmapped(db):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type=None,
        is_active=True,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, "123")

    assert result == {
        "panna": "123",
        "family": None,
        "is_mapped": False,
        "is_active": True,
    }


def test_resolve_inactive_panna_is_not_mapped(db):
    panna = PannaReference(
        panna="456",
        digit_1=4,
        digit_2=5,
        digit_3=6,
        panna_type="family_a",
        is_active=False,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, "456")

    assert result == {
        "panna": "456",
        "family": None,
        "is_mapped": False,
        "is_active": False,
    }


def test_resolve_missing_panna_returns_unmapped_result(db):
    result = resolve_panna_family(db, "789")

    assert result == {
        "panna": "789",
        "family": None,
        "is_mapped": False,
        "is_active": False,
    }


# ---------------------------------------------------------------------------
# Panel family resolution
# ---------------------------------------------------------------------------


def test_resolve_active_panel_family(db):
    family = PanelFamily(
        family_name="Family A",
        description="Test family",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_panel_family(db, "123")

    assert result == {
        "panel": "123",
        "family": "Family A",
        "family_id": family.id,
        "is_mapped": True,
        "is_active": True,
    }


def test_resolve_panel_preserves_leading_zeros(db):
    family = PanelFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="005",
        digit_1=0,
        digit_2=0,
        digit_3=5,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_panel_family(db, "005")

    assert result["panel"] == "005"
    assert result["family"] == "Family A"
    assert result["family_id"] == family.id
    assert result["is_mapped"] is True
    assert result["is_active"] is True


def test_resolve_panel_with_whitespace_preserves_normalized_value(db):
    family = PanelFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="007",
        digit_1=0,
        digit_2=0,
        digit_3=7,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_panel_family(db, " 007 ")

    assert result["panel"] == "007"
    assert result["family"] == "Family A"


def test_resolve_unmapped_panel(db):
    result = resolve_panel_family(db, "123")

    assert result == {
        "panel": "123",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


def test_resolve_inactive_panel_member_is_unmapped(db):
    family = PanelFamily(
        family_name="Family A",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        is_active=False,
    )

    db.add(member)
    db.commit()

    result = resolve_panel_family(db, "123")

    assert result == {
        "panel": "123",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


def test_resolve_panel_with_inactive_family_is_unmapped(db):
    family = PanelFamily(
        family_name="Family A",
        is_active=False,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        is_active=True,
    )

    db.add(member)
    db.commit()

    result = resolve_panel_family(db, "123")

    assert result == {
        "panel": "123",
        "family": None,
        "family_id": None,
        "is_mapped": False,
        "is_active": False,
    }


# ---------------------------------------------------------------------------
# No inference from digit structure
# ---------------------------------------------------------------------------


def test_panel_digits_do_not_create_family_mapping(db):
    result = resolve_panel_family(db, "111")

    assert result["family"] is None
    assert result["family_id"] is None
    assert result["is_mapped"] is False


def test_panna_digits_do_not_create_family_mapping(db):
    panna = PannaReference(
        panna="111",
        digit_1=1,
        digit_2=1,
        digit_3=1,
        panna_type=None,
        is_active=True,
    )

    db.add(panna)
    db.commit()

    result = resolve_panna_family(db, "111")

    assert result["family"] is None
    assert result["is_mapped"] is False
    assert result["is_active"] is True