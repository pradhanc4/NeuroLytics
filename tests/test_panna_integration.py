from database.models import PannaReference
from database.panna_relationship import analyze_panna_structure
from database.panna_service import PannaReferenceService
from database.panna_validator import validate_panna


def test_complete_panna_workflow(db):
    """Test validation, creation, persistence, lookup, and analysis."""

    panna = validate_panna("005")

    assert panna == "005"

    service = PannaReferenceService(db)

    created = service.create_panna(
        panna=panna,
        panna_type="test",
    )

    assert created.id is not None
    assert created.panna == "005"

    assert created.digit_1 == 0
    assert created.digit_2 == 0
    assert created.digit_3 == 5

    stored = db.get(
        PannaReference,
        created.id,
    )

    assert stored is not None
    assert stored.panna == "005"


def test_lookup_and_relationship_analysis_work_together(db):
    """Test Panna lookup followed by structural analysis."""

    service = PannaReferenceService(db)

    service.create_panna(
        panna="123",
        panna_type="standard",
    )

    result = service.get_panna("123")

    assert result is not None

    analysis = analyze_panna_structure(
        result.panna
    )

    assert analysis["panna"] == "123"
    assert analysis["digits"] == [1, 2, 3]
    assert analysis["unique_digits"] == [1, 2, 3]
    assert analysis["unique_digit_count"] == 3
    assert analysis["repeated_digit_count"] == 0
    assert analysis["has_repeated_digit"] is False


def test_repeated_digit_panna_workflow(db):
    """Test a Panna containing repeated digits."""

    service = PannaReferenceService(db)

    created = service.create_panna(
        panna="112",
        panna_type="repeated",
    )

    result = service.get_panna(
        created.panna
    )

    assert result is not None

    analysis = analyze_panna_structure(
        result.panna
    )

    assert analysis["digits"] == [1, 1, 2]
    assert analysis["sorted_digits"] == [1, 1, 2]
    assert analysis["unique_digits"] == [1, 2]
    assert analysis["unique_digit_count"] == 2
    assert analysis["repeated_digit_count"] == 1
    assert analysis["has_repeated_digit"] is True


def test_search_returns_persisted_records(db):
    """Test that search operates on persisted SQL records."""

    service = PannaReferenceService(db)

    service.create_panna(
        panna="123",
        panna_type="group_a",
    )

    service.create_panna(
        panna="124",
        panna_type="group_a",
    )

    service.create_panna(
        panna="456",
        panna_type="group_b",
    )

    db.expire_all()

    results = service.search_pannas(
        panna="12",
        panna_type="group_a",
    )

    assert [item.panna for item in results] == [
        "123",
        "124",
    ]


def test_inactive_panna_is_excluded_from_normal_workflow(db):
    """Test active/inactive filtering across the service."""

    service = PannaReferenceService(db)

    active = service.create_panna(
        panna="123",
    )

    inactive = service.create_panna(
        panna="456",
    )

    inactive.is_active = False
    db.commit()

    active_results = service.get_all_pannas()

    assert [item.panna for item in active_results] == [
        active.panna,
    ]

    all_results = service.get_all_pannas(
        active_only=False
    )

    assert [item.panna for item in all_results] == [
        active.panna,
        inactive.panna,
    ]


def test_multiple_panna_structures_can_be_analyzed(db):
    """Test structural analysis across multiple persisted Pannas."""

    service = PannaReferenceService(db)

    service.create_panna("123")
    service.create_panna("112")
    service.create_panna("111")
    service.create_panna("005")

    results = service.get_all_pannas()

    analyses = [
        analyze_panna_structure(
            result.panna
        )
        for result in results
    ]

    assert len(analyses) == 4

    assert analyses[0]["panna"] == "005"
    assert analyses[0]["has_repeated_digit"] is True

    assert analyses[1]["panna"] == "111"
    assert analyses[1]["repeated_digit_count"] == 2

    assert analyses[2]["panna"] == "112"
    assert analyses[2]["repeated_digit_count"] == 1

    assert analyses[3]["panna"] == "123"
    assert analyses[3]["repeated_digit_count"] == 0