import pytest

from database.models import PanelFamily
from database.panel_family_relationship import (
    PanelFamilyRelationshipService,
)
from database.panel_service import PanelFamilyService


def create_family_with_panels(
    db,
    family_name: str,
    panels: list[str],
) -> PanelFamily:
    family_service = PanelFamilyService(db)

    family = family_service.create_family(
        family_name
    )

    for panel in panels:
        family_service.add_member(
            family,
            panel,
        )

    return family


def test_categorize_same_panel():
    relationship = {
        "same_panel": True,
        "reversed_panel": False,
        "same_first_digit": True,
        "same_second_digit": True,
        "same_third_digit": True,
        "same_digit_sum": True,
    }

    categories = (
        PanelFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert "same" in categories
    assert "same_first_digit" in categories
    assert "same_second_digit" in categories
    assert "same_third_digit" in categories
    assert "same_digit_sum" in categories


def test_categorize_reverse_panel():
    relationship = {
        "same_panel": False,
        "reversed_panel": True,
        "same_first_digit": False,
        "same_second_digit": True,
        "same_third_digit": False,
        "same_digit_sum": True,
    }

    categories = (
        PanelFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert "reverse" in categories
    assert "same_second_digit" in categories
    assert "same_digit_sum" in categories


def test_categorize_different_panel():
    relationship = {
        "same_panel": False,
        "reversed_panel": False,
        "same_first_digit": False,
        "same_second_digit": False,
        "same_third_digit": False,
        "same_digit_sum": False,
    }

    categories = (
        PanelFamilyRelationshipService
        .categorize_relationship(
            relationship
        )
    )

    assert categories == ["different"]


def test_analyze_family_creates_unique_pairs(db):
    family = create_family_with_panels(
        db,
        "Family A",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 3


def test_analyze_family_never_compares_panel_with_itself(
    db,
):
    family = create_family_with_panels(
        db,
        "Family B",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    for relationship in relationships:
        assert (
            relationship["panel_a"]
            != relationship["panel_b"]
        )


def test_analyze_family_contains_family_information(
    db,
):
    family = create_family_with_panels(
        db,
        "Family C",
        [
            "123",
            "321",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 1

    relationship = relationships[0]

    assert relationship["family_id"] == family.id
    assert (
        relationship["family_name"]
        == "Family C"
    )


def test_analyze_family_detects_reverse_relationship(
    db,
):
    family = create_family_with_panels(
        db,
        "Family D",
        [
            "123",
            "321",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 1

    assert relationships[0][
        "reversed_panel"
    ] is True

    assert "reverse" in relationships[0][
        "categories"
    ]


def test_analyze_family_active_only(
    db,
):
    family = create_family_with_panels(
        db,
        "Family E",
        [
            "123",
            "321",
            "456",
        ],
    )

    family_service = PanelFamilyService(db)

    inactive_member = family_service.get_member(
        family,
        "456",
    )

    inactive_member.is_active = False
    db.commit()

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family,
        active_only=True,
    )

    assert len(relationships) == 1

    panels = {
        relationships[0]["panel_a"],
        relationships[0]["panel_b"],
    }

    assert panels == {"123", "321"}


def test_analyze_family_can_include_inactive(
    db,
):
    family = create_family_with_panels(
        db,
        "Family F",
        [
            "123",
            "321",
            "456",
        ],
    )

    family_service = PanelFamilyService(db)

    inactive_member = family_service.get_member(
        family,
        "456",
    )

    inactive_member.is_active = False
    db.commit()

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family,
        active_only=False,
    )

    assert len(relationships) == 3


def test_analyze_family_requires_family(
    db,
):
    service = PanelFamilyRelationshipService(db)

    with pytest.raises(ValueError):
        service.analyze_family(None)


def test_summarize_empty_family(
    db,
):
    family_service = PanelFamilyService(db)

    family = family_service.create_family(
        "Empty Family"
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    assert summary["family_id"] == family.id
    assert summary["family_name"] == (
        "Empty Family"
    )
    assert summary["member_count"] == 0
    assert summary["pair_count"] == 0
    assert summary[
        "average_digit_difference"
    ] == 0.0


def test_summarize_family_member_and_pair_count(
    db,
):
    family = create_family_with_panels(
        db,
        "Family G",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    assert summary["member_count"] == 3
    assert summary["pair_count"] == 3


def test_summarize_reverse_pair_count(
    db,
):
    family = create_family_with_panels(
        db,
        "Family H",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    assert summary[
        "reverse_pair_count"
    ] == 1


def test_summarize_same_digit_sum_count(
    db,
):
    family = create_family_with_panels(
        db,
        "Family I",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    assert summary[
        "same_digit_sum_pair_count"
    ] == 1


def test_summarize_contains_category_counts(
    db,
):
    family = create_family_with_panels(
        db,
        "Family J",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    category_counts = summary[
        "category_counts"
    ]

    assert "same" in category_counts
    assert "reverse" in category_counts
    assert "same_first_digit" in category_counts
    assert "same_second_digit" in category_counts
    assert "same_third_digit" in category_counts
    assert "same_digit_sum" in category_counts
    assert "different" in category_counts


def test_summarize_requires_family(
    db,
):
    service = PanelFamilyRelationshipService(db)

    with pytest.raises(ValueError):
        service.summarize_family(None)

def test_analyze_family_preserves_leading_zero_panels(
    db,
):
    family = create_family_with_panels(
        db,
        "Leading Zero Family",
        [
            "005",
            "050",
            "500",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 3

    panels = set()

    for relationship in relationships:
        panels.add(relationship["panel_a"])
        panels.add(relationship["panel_b"])

    assert panels == {
        "005",
        "050",
        "500",
    }


def test_analyze_family_detects_reverse_with_leading_zero(
    db,
):
    family = create_family_with_panels(
        db,
        "Reverse Zero Family",
        [
            "005",
            "500",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 1

    relationship = relationships[0]

    assert relationship["panel_a"] == "005"
    assert relationship["panel_b"] == "500"
    assert relationship["reversed_panel"] is True
    assert "reverse" in relationship["categories"]


def test_analyze_family_detects_multiple_categories(
    db,
):
    family = create_family_with_panels(
        db,
        "Multiple Category Family",
        [
            "123",
            "321",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    relationship = relationships[0]

    assert relationship["reversed_panel"] is True
    assert relationship["same_second_digit"] is True
    assert relationship["same_digit_sum"] is True

    assert "reverse" in relationship["categories"]
    assert "same_second_digit" in relationship[
        "categories"
    ]
    assert "same_digit_sum" in relationship[
        "categories"
    ]


def test_repeated_digit_panel_relationship(
    db,
):
    family = create_family_with_panels(
        db,
        "Repeated Digit Family",
        [
            "111",
            "121",
            "131",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    assert len(relationships) == 3

    for relationship in relationships:
        assert (
            len(relationship["digit_differences"])
            == 3
        )


def test_family_pair_count_formula(
    db,
):
    family = create_family_with_panels(
        db,
        "Pair Count Family",
        [
            "123",
            "234",
            "345",
            "456",
            "567",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    summary = service.summarize_family(
        family
    )

    assert len(relationships) == 10
    assert summary["pair_count"] == 10


def test_average_digit_difference(
    db,
):
    family = create_family_with_panels(
        db,
        "Average Difference Family",
        [
            "123",
            "124",
            "125",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    assert summary[
        "average_digit_difference"
    ] == pytest.approx(
        1.3333333333,
        rel=1e-6,
    )


def test_all_relationship_categories_can_be_counted(
    db,
):
    family = create_family_with_panels(
        db,
        "Category Count Family",
        [
            "123",
            "321",
            "456",
        ],
    )

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family
    )

    category_counts = summary[
        "category_counts"
    ]

    total_category_entries = sum(
        category_counts.values()
    )

    assert total_category_entries > 0


def test_inactive_member_is_excluded_from_summary(
    db,
):
    family = create_family_with_panels(
        db,
        "Inactive Summary Family",
        [
            "123",
            "321",
            "456",
        ],
    )

    family_service = PanelFamilyService(db)

    inactive_member = family_service.get_member(
        family,
        "456",
    )

    inactive_member.is_active = False
    db.commit()

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family,
        active_only=True,
    )

    assert summary["member_count"] == 2
    assert summary["pair_count"] == 1


def test_inactive_member_can_be_included_in_summary(
    db,
):
    family = create_family_with_panels(
        db,
        "Inactive Included Family",
        [
            "123",
            "321",
            "456",
        ],
    )

    family_service = PanelFamilyService(db)

    inactive_member = family_service.get_member(
        family,
        "456",
    )

    inactive_member.is_active = False
    db.commit()

    service = PanelFamilyRelationshipService(db)

    summary = service.summarize_family(
        family,
        active_only=False,
    )

    assert summary["member_count"] == 3
    assert summary["pair_count"] == 3


def test_large_family_pair_generation(
    db,
):
    panels = [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
        "007",
        "008",
        "009",
        "010",
    ]

    family = create_family_with_panels(
        db,
        "Large Family",
        panels,
    )

    service = PanelFamilyRelationshipService(db)

    relationships = service.analyze_family(
        family
    )

    # 10 members produce 10 * 9 / 2 = 45
    # unique pairs.
    assert len(relationships) == 45