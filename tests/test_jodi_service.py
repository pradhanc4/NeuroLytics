import pytest

from database.jodi_service import JodiFamilyService
from database.models import JodiFamily, JodiFamilyMember


def test_create_family(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        family_name="Family A",
        description="Test family",
    )

    assert family.id is not None
    assert family.family_name == "Family A"
    assert family.description == "Test family"
    assert family.is_active is True


def test_create_family_with_blank_description(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        family_name="Family A",
        description="   ",
    )

    assert family.description is None


def test_duplicate_family_is_rejected(db):
    service = JodiFamilyService(db)

    service.create_family("Family A")

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.create_family("Family A")


def test_family_lookup(db):
    service = JodiFamilyService(db)

    created = service.create_family("Family A")

    result = service.get_family("Family A")

    assert result is not None
    assert result.id == created.id


def test_family_id_lookup(db):
    service = JodiFamilyService(db)

    created = service.create_family("Family A")

    result = service.get_family_by_id(
        created.id
    )

    assert result is not None
    assert result.family_name == "Family A"


def test_missing_family_lookup(db):
    service = JodiFamilyService(db)

    result = service.get_family(
        "Missing Family"
    )

    assert result is None


def test_get_all_families_sorted(db):
    service = JodiFamilyService(db)

    service.create_family("Family C")
    service.create_family("Family A")
    service.create_family("Family B")

    results = service.get_all_families()

    assert [
        family.family_name
        for family in results
    ] == [
        "Family A",
        "Family B",
        "Family C",
    ]


def test_inactive_family_filter(db):
    service = JodiFamilyService(db)

    active = service.create_family(
        "Family A"
    )

    inactive = service.create_family(
        "Family B"
    )

    inactive.is_active = False
    db.commit()

    active_results = (
        service.get_all_families()
    )

    assert [
        family.family_name
        for family in active_results
    ] == [
        active.family_name,
    ]

    all_results = (
        service.get_all_families(
            active_only=False
        )
    )

    assert [
        family.family_name
        for family in all_results
    ] == [
        "Family A",
        "Family B",
    ]


def test_add_member(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.add_member(
        family=family,
        jodi="05",
    )

    assert member.id is not None
    assert member.family_id == family.id
    assert member.jodi == "05"
    assert member.digit_1 == 0
    assert member.digit_2 == 5
    assert member.is_active is True


def test_add_member_leading_zero_is_preserved(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    member = service.add_member(
        family=family,
        jodi="05",
    )

    assert member.jodi == "05"
    assert member.digit_1 == 0
    assert member.digit_2 == 5


def test_duplicate_member_is_rejected(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family=family,
        jodi="05",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.add_member(
            family=family,
            jodi="05",
        )


def test_member_lookup(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    created = service.add_member(
        family=family,
        jodi="05",
    )

    result = service.get_member(
        family=family,
        jodi="05",
    )

    assert result is not None
    assert result.id == created.id


def test_missing_member_lookup(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    result = service.get_member(
        family=family,
        jodi="05",
    )

    assert result is None


def test_get_members_sorted(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family=family,
        jodi="25",
    )

    service.add_member(
        family=family,
        jodi="05",
    )

    service.add_member(
        family=family,
        jodi="12",
    )

    results = service.get_members(
        family
    )

    assert [
        member.jodi
        for member in results
    ] == [
        "05",
        "12",
        "25",
    ]


def test_inactive_member_filter(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active = service.add_member(
        family=family,
        jodi="05",
    )

    inactive = service.add_member(
        family=family,
        jodi="12",
    )

    inactive.is_active = False
    db.commit()

    active_results = service.get_members(
        family
    )

    assert [
        member.jodi
        for member in active_results
    ] == [
        active.jodi,
    ]

    all_results = service.get_members(
        family,
        active_only=False,
    )

    assert [
        member.jodi
        for member in all_results
    ] == [
        "05",
        "12",
    ]


def test_missing_family_is_rejected_when_adding_member(db):
    service = JodiFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Jodi family is required",
    ):
        service.add_member(
            family=None,
            jodi="05",
        )


def test_missing_family_is_rejected_when_getting_member(db):
    service = JodiFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Jodi family is required",
    ):
        service.get_member(
            family=None,
            jodi="05",
        )


def test_missing_family_is_rejected_when_getting_members(db):
    service = JodiFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Jodi family is required",
    ):
        service.get_members(
            family=None,
        )
def test_search_families_by_partial_name(db):
    service = JodiFamilyService(db)

    service.create_family("Alpha Family")
    service.create_family("Beta Family")
    service.create_family("Alpha Group")

    results = service.search_families("Alpha")

    assert [
        family.family_name
        for family in results
    ] == [
        "Alpha Family",
        "Alpha Group",
    ]


def test_search_families_is_case_insensitive(db):
    service = JodiFamilyService(db)

    service.create_family("Alpha Family")
    service.create_family("Beta Family")

    results = service.search_families("alpha")

    assert [
        family.family_name
        for family in results
    ] == [
        "Alpha Family",
    ]


def test_search_families_excludes_inactive(db):
    service = JodiFamilyService(db)

    active = service.create_family(
        "Alpha Active"
    )

    inactive = service.create_family(
        "Alpha Inactive"
    )

    inactive.is_active = False
    db.commit()

    results = service.search_families("Alpha")

    assert [
        family.family_name
        for family in results
    ] == [
        active.family_name,
    ]

    all_results = service.search_families(
        "Alpha",
        active_only=False,
    )

    assert [
        family.family_name
        for family in all_results
    ] == [
        "Alpha Active",
        "Alpha Inactive",
    ]


def test_search_families_requires_search_term(db):
    service = JodiFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Search term is required",
    ):
        service.search_families("")


def test_search_members_by_partial_jodi(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    service.add_member(
        family=family,
        jodi="05",
    )

    service.add_member(
        family=family,
        jodi="12",
    )

    service.add_member(
        family=family,
        jodi="25",
    )

    service.add_member(
        family=family,
        jodi="50",
    )

    results = service.search_members("5")

    assert [
        member.jodi
        for member in results
    ] == [
        "05",
        "25",
        "50",
    ]


def test_search_members_can_filter_by_family(db):
    service = JodiFamilyService(db)

    family_a = service.create_family(
        "Family A"
    )

    family_b = service.create_family(
        "Family B"
    )

    service.add_member(
        family=family_a,
        jodi="05",
    )

    service.add_member(
        family=family_b,
        jodi="15",
    )

    service.add_member(
        family=family_b,
        jodi="25",
    )

    results = service.search_members(
        "5",
        family=family_b,
    )

    assert [
        member.jodi
        for member in results
    ] == [
        "15",
        "25",
    ]


def test_search_members_excludes_inactive(db):
    service = JodiFamilyService(db)

    family = service.create_family(
        "Family A"
    )

    active = service.add_member(
        family=family,
        jodi="05",
    )

    inactive = service.add_member(
        family=family,
        jodi="15",
    )

    inactive.is_active = False
    db.commit()

    results = service.search_members("5")

    assert [
        member.jodi
        for member in results
    ] == [
        active.jodi,
    ]

    all_results = service.search_members(
        "5",
        active_only=False,
    )

    assert [
        member.jodi
        for member in all_results
    ] == [
        "05",
        "15",
    ]


def test_search_members_requires_search_term(db):
    service = JodiFamilyService(db)

    with pytest.raises(
        ValueError,
        match="Search term is required",
    ):
        service.search_members("")