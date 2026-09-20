import pytest

from database.models import PannaReference
from database.panna_service import PannaReferenceService


def test_create_panna(db):
    service = PannaReferenceService(db)

    result = service.create_panna(
        panna="123",
        panna_type="example",
    )

    assert result.id is not None
    assert result.panna == "123"

    assert result.digit_1 == 1
    assert result.digit_2 == 2
    assert result.digit_3 == 3

    assert result.panna_type == "example"
    assert result.is_active is True


def test_create_panna_preserves_leading_zeros(db):
    service = PannaReferenceService(db)

    result = service.create_panna(
        panna="005",
    )

    assert result.panna == "005"

    assert result.digit_1 == 0
    assert result.digit_2 == 0
    assert result.digit_3 == 5


def test_duplicate_panna_is_rejected(db):
    service = PannaReferenceService(db)

    service.create_panna(
        panna="123",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.create_panna(
            panna="123",
        )


def test_get_panna(db):
    service = PannaReferenceService(db)

    service.create_panna(
        panna="456",
    )

    result = service.get_panna("456")

    assert result is not None
    assert result.panna == "456"

    assert result.digit_1 == 4
    assert result.digit_2 == 5
    assert result.digit_3 == 6


def test_get_missing_panna_returns_none(db):
    service = PannaReferenceService(db)

    result = service.get_panna("789")

    assert result is None


def test_get_panna_by_id(db):
    service = PannaReferenceService(db)

    created = service.create_panna(
        panna="789",
    )

    result = service.get_panna_by_id(
        created.id
    )

    assert result is not None
    assert result.id == created.id
    assert result.panna == "789"


def test_invalid_panna_is_rejected_by_service(db):
    service = PannaReferenceService(db)

    with pytest.raises(
        ValueError,
        match="exactly 3 digits",
    ):
        service.create_panna(
            panna="12",
        )

    results = db.query(PannaReference).all()

    assert results == []


def test_get_all_pannas_returns_active_pannas_sorted(db):
    service = PannaReferenceService(db)

    service.create_panna("456")
    service.create_panna("123")
    service.create_panna("789")

    results = service.get_all_pannas()

    assert [item.panna for item in results] == [
        "123",
        "456",
        "789",
    ]


def test_get_all_pannas_excludes_inactive_by_default(db):
    service = PannaReferenceService(db)

    active = service.create_panna("123")
    inactive = service.create_panna("456")

    inactive.is_active = False
    db.commit()

    results = service.get_all_pannas()

    assert [item.panna for item in results] == [
        active.panna,
    ]


def test_get_all_pannas_can_include_inactive(db):
    service = PannaReferenceService(db)

    active = service.create_panna("123")
    inactive = service.create_panna("456")

    inactive.is_active = False
    db.commit()

    results = service.get_all_pannas(
        active_only=False
    )

    assert [item.panna for item in results] == [
        active.panna,
        inactive.panna,
    ]


def test_search_pannas_by_partial_value(db):
    service = PannaReferenceService(db)

    service.create_panna("123")
    service.create_panna("124")
    service.create_panna("125")
    service.create_panna("223")

    results = service.search_pannas(
        panna="12"
    )

    assert [item.panna for item in results] == [
        "123",
        "124",
        "125",
    ]


def test_search_pannas_by_type(db):
    service = PannaReferenceService(db)

    service.create_panna(
        "123",
        panna_type="family_a",
    )

    service.create_panna(
        "456",
        panna_type="family_b",
    )

    service.create_panna(
        "789",
        panna_type="family_a",
    )

    results = service.search_pannas(
        panna_type="family_a"
    )

    assert [item.panna for item in results] == [
        "123",
        "789",
    ]


def test_search_pannas_by_value_and_type(db):
    service = PannaReferenceService(db)

    service.create_panna(
        "123",
        panna_type="family_a",
    )

    service.create_panna(
        "124",
        panna_type="family_b",
    )

    service.create_panna(
        "125",
        panna_type="family_a",
    )

    results = service.search_pannas(
        panna="12",
        panna_type="family_a",
    )

    assert [item.panna for item in results] == [
        "123",
        "125",
    ]


def test_search_pannas_excludes_inactive_by_default(db):
    service = PannaReferenceService(db)

    active = service.create_panna(
        "123",
        panna_type="family_a",
    )

    inactive = service.create_panna(
        "124",
        panna_type="family_a",
    )

    inactive.is_active = False
    db.commit()

    results = service.search_pannas(
        panna_type="family_a"
    )

    assert [item.panna for item in results] == [
        active.panna,
    ]


def test_search_pannas_can_include_inactive(db):
    service = PannaReferenceService(db)

    active = service.create_panna("123")
    inactive = service.create_panna("124")

    inactive.is_active = False
    db.commit()

    results = service.search_pannas(
        panna="12",
        active_only=False,
    )

    assert [item.panna for item in results] == [
        active.panna,
        inactive.panna,
    ]