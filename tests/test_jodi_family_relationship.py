import pytest

from database.jodi_family_relationship import (
    JodiFamilyRelationshipService,
)
from database.jodi_service import (
    JodiFamilyService,
)


def test_analyze_family_returns_unique_pairs(db):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="12",
    )

    family_service.add_member(
        family=family,
        jodi="50",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert len(results) == 3

    pairs = {
        (
            result["jodi_a"],
            result["jodi_b"],
        )
        for result in results
    }

    assert pairs == {
        ("05", "12"),
        ("05", "50"),
        ("12", "50"),
    }


def test_analyze_family_does_not_compare_member_with_itself(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert results == []


def test_analyze_family_detects_reverse_relationship(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="50",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert len(results) == 1

    result = results[0]

    assert result["jodi_a"] == "05"
    assert result["jodi_b"] == "50"
    assert result["reversed_jodi"] is True


def test_analyze_family_preserves_leading_zero(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="06",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert len(results) == 1

    result = results[0]

    assert result["jodi_a"] == "05"
    assert result["jodi_b"] == "06"


def test_analyze_family_includes_family_information(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="12",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert len(results) == 1

    result = results[0]

    assert result["family_id"] == family.id
    assert result["family_name"] == "Family A"


def test_analyze_family_excludes_inactive_members(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    active = family_service.add_member(
        family=family,
        jodi="05",
    )

    inactive = family_service.add_member(
        family=family,
        jodi="12",
    )

    family_service.add_member(
        family=family,
        jodi="25",
    )

    inactive.is_active = False
    db.commit()

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    pairs = {
        (
            result["jodi_a"],
            result["jodi_b"],
        )
        for result in results
    }

    assert pairs == {
        (active.jodi, "25"),
    }


def test_analyze_family_can_include_inactive_members(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    active = family_service.add_member(
        family=family,
        jodi="05",
    )

    inactive = family_service.add_member(
        family=family,
        jodi="12",
    )

    inactive.is_active = False
    db.commit()

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family,
        active_only=False,
    )

    assert len(results) == 1

    result = results[0]

    assert result["jodi_a"] == active.jodi
    assert result["jodi_b"] == inactive.jodi


def test_missing_family_is_rejected(db):
    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    with pytest.raises(
        ValueError,
        match="Jodi family is required",
    ):
        relationship_service.analyze_family(
            None
        )


def test_empty_family_returns_empty_relationships(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert results == []


def test_categorize_reverse_relationship():
    relationship = {
        "same_jodi": False,
        "reversed_jodi": True,
        "same_first_digit": False,
        "same_second_digit": False,
        "same_digit_sum": True,
    }

    categories = (
        JodiFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert categories == [
        "reverse",
        "same_digit_sum",
    ]


def test_categorize_same_jodi():
    relationship = {
        "same_jodi": True,
        "reversed_jodi": False,
        "same_first_digit": True,
        "same_second_digit": True,
        "same_digit_sum": True,
    }

    categories = (
        JodiFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert categories == [
        "same",
        "same_first_digit",
        "same_second_digit",
        "same_digit_sum",
    ]


def test_categorize_different_relationship():
    relationship = {
        "same_jodi": False,
        "reversed_jodi": False,
        "same_first_digit": False,
        "same_second_digit": False,
        "same_digit_sum": False,
    }

    categories = (
        JodiFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert categories == [
        "different",
    ]


def test_analyze_family_adds_relationship_categories(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="50",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    results = relationship_service.analyze_family(
        family
    )

    assert len(results) == 1

    result = results[0]

    assert result["categories"] == [
        "reverse",
        "same_digit_sum",
    ]


def test_summarize_family(db):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    family_service.add_member(
        family=family,
        jodi="50",
    )

    family_service.add_member(
        family=family,
        jodi="12",
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    summary = (
        relationship_service.summarize_family(
            family
        )
    )

    assert summary["family_id"] == family.id
    assert summary["family_name"] == "Family A"
    assert summary["member_count"] == 3
    assert summary["pair_count"] == 3
    assert summary["reverse_pair_count"] == 1
    assert summary["same_digit_sum_pair_count"] == 1

    assert summary[
        "average_digit_difference"
    ] == pytest.approx(
        6.6666666667,
        rel=1e-6,
    )


def test_summarize_empty_family(db):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    summary = (
        relationship_service.summarize_family(
            family
        )
    )

    assert summary["member_count"] == 0
    assert summary["pair_count"] == 0
    assert summary["average_digit_difference"] == 0.0
    assert summary["reverse_pair_count"] == 0
    assert summary["same_digit_sum_pair_count"] == 0


def test_summarize_family_can_include_inactive_members(
    db,
):
    family_service = JodiFamilyService(db)

    family = family_service.create_family(
        "Family A"
    )

    family_service.add_member(
        family=family,
        jodi="05",
    )

    inactive = family_service.add_member(
        family=family,
        jodi="50",
    )

    inactive.is_active = False
    db.commit()

    relationship_service = (
        JodiFamilyRelationshipService(db)
    )

    summary = (
        relationship_service.summarize_family(
            family,
            active_only=False,
        )
    )

    assert summary["member_count"] == 2
    assert summary["pair_count"] == 1
    assert summary["reverse_pair_count"] == 1