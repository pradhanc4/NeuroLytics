from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    PanelFamily,
    PanelFamilyMember,
)
from database.panel_validator import validate_panel


class PanelFamilyService:
    """Service layer for Panel family reference operations."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _validate_family_name(
        family_name: str,
    ) -> str:
        """Validate and normalize a family name."""

        if family_name is None:
            raise ValueError(
                "Family name is required."
            )

        family_name = str(family_name).strip()

        if not family_name:
            raise ValueError(
                "Family name is required."
            )

        return family_name

    def create_family(
        self,
        family_name: str,
        description: str | None = None,
    ) -> PanelFamily:
        """Create a new Panel family."""

        family_name = self._validate_family_name(
            family_name
        )

        existing_family = self.db.scalar(
            select(PanelFamily).where(
                PanelFamily.family_name
                == family_name
            )
        )

        if existing_family:
            raise ValueError(
                f"Panel family '{family_name}' "
                "already exists."
            )

        if description is not None:
            description = str(
                description
            ).strip()

            if not description:
                description = None

        family = PanelFamily(
            family_name=family_name,
            description=description,
        )

        self.db.add(family)
        self.db.commit()
        self.db.refresh(family)

        return family

    def get_family(
        self,
        family_name: str,
    ) -> PanelFamily | None:
        """Retrieve a Panel family by name."""

        family_name = self._validate_family_name(
            family_name
        )

        return self.db.scalar(
            select(PanelFamily).where(
                PanelFamily.family_name
                == family_name
            )
        )

    def get_family_by_id(
        self,
        family_id: int,
    ) -> PanelFamily | None:
        """Retrieve a Panel family by database ID."""

        return self.db.get(
            PanelFamily,
            family_id,
        )

    def get_all_families(
        self,
        active_only: bool = True,
    ) -> list[PanelFamily]:
        """
        Retrieve Panel families.

        By default, only active families are returned.
        Set active_only=False to retrieve all families.
        """

        statement = select(PanelFamily)

        if active_only:
            statement = statement.where(
                PanelFamily.is_active.is_(True)
            )

        statement = statement.order_by(
            PanelFamily.family_name
        )

        return list(
            self.db.scalars(statement)
        )

    def search_families(
        self,
        search_term: str,
        active_only: bool = True,
    ) -> list[PanelFamily]:
        """
        Search Panel families by partial family name.

        Search is case-insensitive and results are
        sorted alphabetically by family name.
        """

        if search_term is None:
            raise ValueError(
                "Search term is required."
            )

        search_term = str(search_term).strip()

        if not search_term:
            raise ValueError(
                "Search term is required."
            )

        statement = select(PanelFamily).where(
            PanelFamily.family_name.ilike(
                f"%{search_term}%"
            )
        )

        if active_only:
            statement = statement.where(
                PanelFamily.is_active.is_(True)
            )

        statement = statement.order_by(
            PanelFamily.family_name
        )

        return list(
            self.db.scalars(statement)
        )

    def add_member(
        self,
        family: PanelFamily,
        panel: str,
    ) -> PanelFamilyMember:
        """
        Validate and add a Panel member to a family.
        """

        if family is None:
            raise ValueError(
                "Panel family is required."
            )

        panel = validate_panel(panel)

        existing_member = self.db.scalar(
            select(PanelFamilyMember).where(
                PanelFamilyMember.family_id
                == family.id,
                PanelFamilyMember.panel
                == panel,
            )
        )

        if existing_member:
            raise ValueError(
                f"Panel '{panel}' already exists "
                "in this family."
            )

        member = PanelFamilyMember(
            family_id=family.id,
            panel=panel,
            digit_1=int(panel[0]),
            digit_2=int(panel[1]),
            digit_3=int(panel[2]),
        )

        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        return member

    def get_member(
        self,
        family: PanelFamily,
        panel: str,
    ) -> PanelFamilyMember | None:
        """Retrieve a Panel member from a specific family."""

        if family is None:
            raise ValueError(
                "Panel family is required."
            )

        panel = validate_panel(panel)

        return self.db.scalar(
            select(PanelFamilyMember).where(
                PanelFamilyMember.family_id
                == family.id,
                PanelFamilyMember.panel
                == panel,
            )
        )

    def get_members(
        self,
        family: PanelFamily,
        active_only: bool = True,
    ) -> list[PanelFamilyMember]:
        """
        Retrieve members belonging to a Panel family.

        By default, only active members are returned.
        """

        if family is None:
            raise ValueError(
                "Panel family is required."
            )

        statement = select(
            PanelFamilyMember
        ).where(
            PanelFamilyMember.family_id
            == family.id
        )

        if active_only:
            statement = statement.where(
                PanelFamilyMember.is_active.is_(True)
            )

        statement = statement.order_by(
            PanelFamilyMember.panel
        )

        return list(
            self.db.scalars(statement)
        )

    def search_members(
        self,
        search_term: str,
        family: PanelFamily | None = None,
        active_only: bool = True,
    ) -> list[PanelFamilyMember]:
        """
        Search Panel members by partial Panel value.

        Optionally restrict the search to one family.
        Results are sorted by Panel value.
        """

        if search_term is None:
            raise ValueError(
                "Search term is required."
            )

        search_term = str(search_term).strip()

        if not search_term:
            raise ValueError(
                "Search term is required."
            )

        statement = select(
            PanelFamilyMember
        ).where(
            PanelFamilyMember.panel.ilike(
                f"%{search_term}%"
            )
        )

        if family is not None:
            statement = statement.where(
                PanelFamilyMember.family_id
                == family.id
            )

        if active_only:
            statement = statement.where(
                PanelFamilyMember.is_active.is_(True)
            )

        statement = statement.order_by(
            PanelFamilyMember.panel
        )

        return list(
            self.db.scalars(statement)
        )