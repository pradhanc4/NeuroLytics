from database.models import PanelFamily
from database.panel_relationship import (
    analyze_panel_relationship,
)
from database.panel_service import PanelFamilyService


class PanelFamilyRelationshipService:
    """
    Service for analyzing structural relationships
    between members of a Panel family.

    This service is descriptive only.
    It does not generate predictions.
    """

    def __init__(self, db):
        self.db = db
        self.family_service = PanelFamilyService(db)

    @staticmethod
    def categorize_relationship(
        relationship: dict,
    ) -> list[str]:
        """
        Convert relationship flags into descriptive
        relationship categories.

        Multiple categories may apply to one pair.
        """

        categories = []

        if relationship["same_panel"]:
            categories.append("same")

        if relationship["reversed_panel"]:
            categories.append("reverse")

        if relationship["same_first_digit"]:
            categories.append("same_first_digit")

        if relationship["same_second_digit"]:
            categories.append("same_second_digit")

        if relationship["same_third_digit"]:
            categories.append("same_third_digit")

        if relationship["same_digit_sum"]:
            categories.append("same_digit_sum")

        if not categories:
            categories.append("different")

        return categories

    def analyze_family(
        self,
        family: PanelFamily,
        active_only: bool = True,
    ) -> list[dict]:
        """
        Analyze every unique Panel pair within a family.

        Each pair is analyzed only once.
        A Panel is never compared with itself.
        """

        if family is None:
            raise ValueError(
                "Panel family is required."
            )

        members = self.family_service.get_members(
            family=family,
            active_only=active_only,
        )

        relationships = []

        for index, member_a in enumerate(members):
            for member_b in members[index + 1:]:
                relationship = analyze_panel_relationship(
                    member_a.panel,
                    member_b.panel,
                )

                relationship["family_id"] = family.id
                relationship["family_name"] = (
                    family.family_name
                )
                relationship["categories"] = (
                    self.categorize_relationship(
                        relationship
                    )
                )

                relationships.append(
                    relationship
                )

        return relationships

    def summarize_family(
        self,
        family: PanelFamily,
        active_only: bool = True,
    ) -> dict:
        """
        Return summary statistics for relationships
        within a Panel family.
        """

        if family is None:
            raise ValueError(
                "Panel family is required."
            )

        members = self.family_service.get_members(
            family=family,
            active_only=active_only,
        )

        relationships = self.analyze_family(
            family=family,
            active_only=active_only,
        )

        total_pairs = len(relationships)

        if total_pairs:
            average_digit_difference = (
                sum(
                    relationship[
                        "total_digit_difference"
                    ]
                    for relationship in relationships
                )
                / total_pairs
            )
        else:
            average_digit_difference = 0.0

        category_counts = {
            "same": 0,
            "reverse": 0,
            "same_first_digit": 0,
            "same_second_digit": 0,
            "same_third_digit": 0,
            "same_digit_sum": 0,
            "different": 0,
        }

        for relationship in relationships:
            for category in relationship[
                "categories"
            ]:
                category_counts[category] += 1

        return {
            "family_id": family.id,
            "family_name": family.family_name,
            "member_count": len(members),
            "pair_count": total_pairs,
            "average_digit_difference": (
                average_digit_difference
            ),
            "reverse_pair_count": (
                category_counts["reverse"]
            ),
            "same_digit_sum_pair_count": (
                category_counts["same_digit_sum"]
            ),
            "category_counts": category_counts,
        }