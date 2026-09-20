from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import PannaReference
from database.panna_validator import validate_panna


class PannaReferenceService:
    """Service layer for Panna/Panel reference operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_panna(
        self,
        panna: str,
        panna_type: str | None = None,
    ) -> PannaReference:
        """Validate and create a Panna reference."""

        panna = validate_panna(panna)

        existing_panna = self.db.scalar(
            select(PannaReference).where(
                PannaReference.panna == panna
            )
        )

        if existing_panna:
            raise ValueError(
                f"Panna '{panna}' already exists."
            )

        panna_reference = PannaReference(
            panna=panna,
            digit_1=int(panna[0]),
            digit_2=int(panna[1]),
            digit_3=int(panna[2]),
            panna_type=panna_type,
        )

        self.db.add(panna_reference)
        self.db.commit()
        self.db.refresh(panna_reference)

        return panna_reference

    def get_panna(
        self,
        panna: str,
    ) -> PannaReference | None:
        """Retrieve a Panna reference by its exact value."""

        panna = validate_panna(panna)

        return self.db.scalar(
            select(PannaReference).where(
                PannaReference.panna == panna
            )
        )

    def get_panna_by_id(
        self,
        panna_id: int,
    ) -> PannaReference | None:
        """Retrieve a Panna reference by database ID."""

        return self.db.get(
            PannaReference,
            panna_id,
        )

    def get_all_pannas(
        self,
        active_only: bool = True,
    ) -> list[PannaReference]:
        """
        Retrieve Panna references.

        By default, only active Panna references are returned.
        Set active_only=False to retrieve both active and inactive
        references.
        """

        statement = select(PannaReference)

        if active_only:
            statement = statement.where(
                PannaReference.is_active.is_(True)
            )

        statement = statement.order_by(
            PannaReference.panna
        )

        return list(
            self.db.scalars(statement)
        )

    def search_pannas(
        self,
        panna: str | None = None,
        panna_type: str | None = None,
        active_only: bool = True,
    ) -> list[PannaReference]:
        """
        Search Panna references using optional filters.

        Search behavior:
        - panna: partial text match
        - panna_type: exact type match
        - active_only: return only active references by default
        """

        statement = select(PannaReference)

        if panna is not None:
            panna = str(panna).strip()

            if panna:
                statement = statement.where(
                    PannaReference.panna.like(
                        f"%{panna}%"
                    )
                )

        if panna_type is not None:
            panna_type = panna_type.strip()

            if panna_type:
                statement = statement.where(
                    PannaReference.panna_type
                    == panna_type
                )

        if active_only:
            statement = statement.where(
                PannaReference.is_active.is_(True)
            )

        statement = statement.order_by(
            PannaReference.panna
        )

        return list(
            self.db.scalars(statement)
        )