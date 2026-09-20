from sqlalchemy import select
from sqlalchemy.orm import Session

from database.jodi_validator import validate_jodi
from database.models import JodiFamily, JodiFamilyMember


class JodiFamilyService:
    """Service layer for Jodi family reference operations."""

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
    ) -> JodiFamily:
        """Create a new Jodi family."""

        family_name = self._validate_family_name(
            family_name
        )

        existing_family = self.db.scalar(
            select(JodiFamily).where(
                JodiFamily.family_name
                == family_name
            )
        )

        if existing_family:
            raise ValueError(
                f"Jodi family '{family_name}' "
                "already exists."
            )

        if description is not None:
            description = str(
                description
            ).strip()

            if not description:
                description = None

        family = JodiFamily(
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
    ) -> JodiFamily | None:
        """Retrieve a Jodi family by name."""

        family_name = self._validate_family_name(
            family_name
        )

        return self.db.scalar(
            select(JodiFamily).where(
                JodiFamily.family_name
                == family_name
            )
        )

    def get_family_by_id(
        self,
        family_id: int,
    ) -> JodiFamily | None:
        """Retrieve a Jodi family by database ID."""

        return self.db.get(
            JodiFamily,
            family_id,
        )

    def get_all_families(
        self,
        active_only: bool = True,
    ) -> list[JodiFamily]:
        """
        Retrieve Jodi families.

        By default, only active families are returned.
        Set active_only=False to retrieve all families.
        """

        statement = select(JodiFamily)

        if active_only:
            statement = statement.where(
                JodiFamily.is_active.is_(True)
            )

        statement = statement.order_by(
            JodiFamily.family_name
        )

        return list(
            self.db.scalars(statement)
        )

    def search_families(
        self,
        search_term: str,
        active_only: bool = True,
    ) -> list[JodiFamily]:
        """
        Search Jodi families by partial family name.

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

        statement = select(JodiFamily).where(
            JodiFamily.family_name.ilike(
                f"%{search_term}%"
            )
        )

        if active_only:
            statement = statement.where(
                JodiFamily.is_active.is_(True)
            )

        statement = statement.order_by(
            JodiFamily.family_name
        )

        return list(
            self.db.scalars(statement)
        )

    def add_member(
        self,
        family: JodiFamily,
        jodi: str,
    ) -> JodiFamilyMember:
        """
        Validate and add a Jodi member to a family.
        """

        if family is None:
            raise ValueError(
                "Jodi family is required."
            )

        jodi = validate_jodi(jodi)

        existing_member = self.db.scalar(
            select(JodiFamilyMember).where(
                JodiFamilyMember.family_id
                == family.id,
                JodiFamilyMember.jodi
                == jodi,
            )
        )

        if existing_member:
            raise ValueError(
                f"Jodi '{jodi}' already exists "
                "in this family."
            )

        member = JodiFamilyMember(
            family_id=family.id,
            jodi=jodi,
            digit_1=int(jodi[0]),
            digit_2=int(jodi[1]),
        )

        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        return member

    def get_member(
        self,
        family: JodiFamily,
        jodi: str,
    ) -> JodiFamilyMember | None:
        """Retrieve a Jodi member from a specific family."""

        if family is None:
            raise ValueError(
                "Jodi family is required."
            )

        jodi = validate_jodi(jodi)

        return self.db.scalar(
            select(JodiFamilyMember).where(
                JodiFamilyMember.family_id
                == family.id,
                JodiFamilyMember.jodi
                == jodi,
            )
        )

    def get_members(
        self,
        family: JodiFamily,
        active_only: bool = True,
    ) -> list[JodiFamilyMember]:
        """
        Retrieve members belonging to a family.

        By default, only active members are returned.
        """

        if family is None:
            raise ValueError(
                "Jodi family is required."
            )

        statement = select(
            JodiFamilyMember
        ).where(
            JodiFamilyMember.family_id
            == family.id
        )

        if active_only:
            statement = statement.where(
                JodiFamilyMember.is_active.is_(True)
            )

        statement = statement.order_by(
            JodiFamilyMember.jodi
        )

        return list(
            self.db.scalars(statement)
        )

    def search_members(
        self,
        search_term: str,
        family: JodiFamily | None = None,
        active_only: bool = True,
    ) -> list[JodiFamilyMember]:
        """
        Search Jodi members by partial Jodi value.

        Optionally restrict the search to one family.
        Results are sorted by Jodi value.
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
            JodiFamilyMember
        ).where(
            JodiFamilyMember.jodi.ilike(
                f"%{search_term}%"
            )
        )

        if family is not None:
            statement = statement.where(
                JodiFamilyMember.family_id
                == family.id
            )

        if active_only:
            statement = statement.where(
                JodiFamilyMember.is_active.is_(True)
            )

        statement = statement.order_by(
            JodiFamilyMember.jodi
        )

        return list(
            self.db.scalars(statement)
        )