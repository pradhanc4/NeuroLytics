import pytest

from database.models import (
    PanelFamily,
    PanelFamilyMember,
)
from database.panel_service import (
    PanelFamilyService,
)


# ============================================================
# Family Creation
# ============================================================


def test_create_panel_family(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A",
        "Test Panel family",
    )

    assert isinstance(
        family,
        PanelFamily,
    )

    assert family.family_name == "Family A"
    assert family.description == "Test Panel family"
    assert family.is_active is True


def test_create_panel_family_without_description(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    assert family.family_name == "Family A"
    assert family.description is None


def test_create_panel_family_normalizes_name(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "  Family A  "
    )

    assert family.family_name == "Family A"


def test_create_panel_family_normalizes_empty_description(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A",
        "   ",
    )

    assert family.description is None


def test_create_duplicate_panel_family_is_rejected(db):
    service = PanelFamilyService(db)

    service.create_family("Family A")

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.create_family("Family A")


def test_create_panel_family_requires_name(db):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Family name is required",
    ):
        service.create_family(None)


def test_create_panel_family_rejects_empty_name(db):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Family name is required",
    ):
        service.create_family("   ")


# ============================================================
# Family Lookup
# ============================================================


def test_get_panel_family(db):
    service = PanelFamilyService(db)

    created = service.create_family(
        "Family A"
    )

    family = service.get_family(
        "Family A"
    )

    assert family is not None
    assert family.id == created.id
    assert family.family_name == "Family A"


def test_get_missing_panel_family(db):
    service = PanelFamilyService(db)

    family = service.get_family(
        "Missing Family"
    )

    assert family is None


def test_get_panel_family_by_id(db):
    service = PanelFamilyService(db)

    created = service.create_family(
        "Family A"
    )

    family = service.get_family_by_id(
        created.id
    )

    assert family is not None
    assert family.id == created.id


def test_get_missing_panel_family_by_id(db):
    service = PanelFamilyService(db)

    family = service.get_family_by_id(
        999999
    )

    assert family is None


# ============================================================
# Family Listing
# ============================================================


def test_get_all_panel_families(db):
    service = PanelFamilyService(db)

    service.create_family(
        "Family B"
    )

    service.create_family(
        "Family A"
    )

    families = service.get_all_families()

    assert [
        family.family_name
        for family in families
    ] == [
        "Family A",
        "Family B",
    ]


def test_get_all_panel_families_excludes_inactive(
    db,
):
    service = PanelFamilyService(db)

    active_family = service.create_family(
        "Active Family"
    )

    inactive_family = service.create_family(
        "Inactive Family"
    )

    inactive_family.is_active = False
    db.commit()

    families = service.get_all_families()

    assert [
        family.id
        for family in families
    ] == [
        active_family.id,
    ]


def test_get_all_panel_families_can_include_inactive(
    db,
):
    service = PanelFamilyService(db)

    active_family = service.create_family(
        "Active Family"
    )

    inactive_family = service.create_family(
        "Inactive Family"
    )

    inactive_family.is_active = False
    db.commit()

    families = service.get_all_families(
        active_only=False
    )

    assert {
        family.id
        for family in families
    } == {
        active_family.id,
        inactive_family.id,
    }


# ============================================================
# Panel Member Creation
# ============================================================


def test_add_panel_member(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.add_member(
        family,
        "123",
    )

    assert isinstance(
        member,
        PanelFamilyMember,
    )

    assert member.family_id == family.id
    assert member.panel == "123"
    assert member.digit_1 == 1
    assert member.digit_2 == 2
    assert member.digit_3 == 3
    assert member.is_active is True


def test_add_panel_member_preserves_leading_zero(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.add_member(
        family,
        "005",
    )

    assert member.panel == "005"
    assert member.digit_1 == 0
    assert member.digit_2 == 0
    assert member.digit_3 == 5


def test_add_zero_panel_member(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.add_member(
        family,
        "000",
    )

    assert member.panel == "000"
    assert member.digit_1 == 0
    assert member.digit_2 == 0
    assert member.digit_3 == 0


def test_duplicate_panel_member_is_rejected(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family,
        "123",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.add_member(
            family,
            "123",
        )


def test_same_panel_can_exist_in_different_families(
    db,
):
    service = PanelFamilyService(db)

    family_a = service.create_family(
        "Family A"
    )

    family_b = service.create_family(
        "Family B"
    )

    member_a = service.add_member(
        family_a,
        "123",
    )

    member_b = service.add_member(
        family_b,
        "123",
    )

    assert member_a.panel == "123"
    assert member_b.panel == "123"
    assert member_a.family_id != member_b.family_id


def test_add_panel_member_requires_family(db):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Panel family is required",
    ):
        service.add_member(
            None,
            "123",
        )


# ============================================================
# Panel Member Lookup
# ============================================================


def test_get_panel_member(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    created = service.add_member(
        family,
        "123",
    )

    member = service.get_member(
        family,
        "123",
    )

    assert member is not None
    assert member.id == created.id
    assert member.panel == "123"


def test_get_missing_panel_member(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.get_member(
        family,
        "999",
    )

    assert member is None


def test_get_panel_members(db):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family,
        "456",
    )

    service.add_member(
        family,
        "123",
    )

    members = service.get_members(
        family
    )

    assert [
        member.panel
        for member in members
    ] == [
        "123",
        "456",
    ]


def test_get_panel_members_excludes_inactive(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active_member = service.add_member(
        family,
        "123",
    )

    inactive_member = service.add_member(
        family,
        "124",
    )

    inactive_member.is_active = False
    db.commit()

    members = service.get_members(
        family
    )

    assert [
        member.id
        for member in members
    ] == [
        active_member.id,
    ]


def test_get_panel_members_can_include_inactive(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active_member = service.add_member(
        family,
        "123",
    )

    inactive_member = service.add_member(
        family,
        "124",
    )

    inactive_member.is_active = False
    db.commit()

    members = service.get_members(
        family,
        active_only=False,
    )

    assert {
        member.id
        for member in members
    } == {
        active_member.id,
        inactive_member.id,
    }


def test_get_panel_member_requires_family(db):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Panel family is required",
    ):
        service.get_member(
            None,
            "123",
        )


def test_get_panel_members_requires_family(db):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Panel family is required",
    ):
        service.get_members(
            None
        )


# ============================================================
# Panel Validation Integration
# ============================================================


def test_add_panel_member_rejects_invalid_panel(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    with pytest.raises(
        ValueError,
        match="digits only",
    ):
        service.add_member(
            family,
            "12A",
        )


# ============================================================
# Phase 6.4 — Family Search
# ============================================================


def test_search_panel_families_by_partial_name(
    db,
):
    service = PanelFamilyService(db)

    service.create_family(
        "Morning Family"
    )

    service.create_family(
        "Evening Family"
    )

    service.create_family(
        "Night Group"
    )

    families = service.search_families(
        "family"
    )

    assert [
        family.family_name
        for family in families
    ] == [
        "Evening Family",
        "Morning Family",
    ]


def test_search_panel_families_is_case_insensitive(
    db,
):
    service = PanelFamilyService(db)

    service.create_family(
        "Morning Family"
    )

    service.create_family(
        "Evening Group"
    )

    families = service.search_families(
        "MORNING"
    )

    assert [
        family.family_name
        for family in families
    ] == [
        "Morning Family",
    ]


def test_search_panel_families_excludes_inactive(
    db,
):
    service = PanelFamilyService(db)

    active_family = service.create_family(
        "Active Family"
    )

    inactive_family = service.create_family(
        "Inactive Family"
    )

    inactive_family.is_active = False
    db.commit()

    families = service.search_families(
        "Family"
    )

    assert [
        family.id
        for family in families
    ] == [
        active_family.id,
    ]


def test_search_panel_families_can_include_inactive(
    db,
):
    service = PanelFamilyService(db)

    active_family = service.create_family(
        "Active Family"
    )

    inactive_family = service.create_family(
        "Inactive Family"
    )

    inactive_family.is_active = False
    db.commit()

    families = service.search_families(
        "Family",
        active_only=False,
    )

    assert {
        family.id
        for family in families
    } == {
        active_family.id,
        inactive_family.id,
    }


def test_search_panel_families_requires_search_term(
    db,
):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Search term is required",
    ):
        service.search_families("   ")


# ============================================================
# Phase 6.4 — Panel Member Search
# ============================================================


def test_search_panel_members_by_partial_panel(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family,
        "123",
    )

    service.add_member(
        family,
        "124",
    )

    service.add_member(
        family,
        "456",
    )

    members = service.search_members(
        "12"
    )

    assert [
        member.panel
        for member in members
    ] == [
        "123",
        "124",
    ]


def test_search_panel_members_preserves_leading_zero(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family,
        "005",
    )

    service.add_member(
        family,
        "105",
    )

    members = service.search_members(
        "05"
    )

    assert [
        member.panel
        for member in members
    ] == [
        "005",
        "105",
    ]


def test_search_panel_members_can_filter_by_family(
    db,
):
    service = PanelFamilyService(db)

    family_a = service.create_family(
        "Family A"
    )

    family_b = service.create_family(
        "Family B"
    )

    service.add_member(
        family_a,
        "123",
    )

    service.add_member(
        family_b,
        "123",
    )

    service.add_member(
        family_b,
        "124",
    )

    members = service.search_members(
        "12",
        family=family_b,
    )

    assert [
        member.panel
        for member in members
    ] == [
        "123",
        "124",
    ]


def test_search_panel_members_excludes_inactive(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active_member = service.add_member(
        family,
        "123",
    )

    inactive_member = service.add_member(
        family,
        "124",
    )

    inactive_member.is_active = False
    db.commit()

    members = service.search_members(
        "12"
    )

    assert [
        member.id
        for member in members
    ] == [
        active_member.id,
    ]


def test_search_panel_members_can_include_inactive(
    db,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active_member = service.add_member(
        family,
        "123",
    )

    inactive_member = service.add_member(
        family,
        "124",
    )

    inactive_member.is_active = False
    db.commit()

    members = service.search_members(
        "12",
        active_only=False,
    )

    assert {
        member.id
        for member in members
    } == {
        active_member.id,
        inactive_member.id,
    }


def test_search_panel_members_requires_search_term(
    db,
):
    service = PanelFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Search term is required",
    ):
        service.search_members("   ")