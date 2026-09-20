from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import PannaReference
from database.panna_validator import validate_panna


class PannaReferenceService:
    """Service layer for Panna reference operations."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _validate_panna_type(
        panna_type: str | None,
    ) -> str | None:
        """Validate and normalize an optional Panna type."""

        if panna_type is None:
            return None

        panna_type = str(
            panna_type
        ).strip()

        if not panna_type:
            return None

        return panna_type

    def create_panna(
        self,
        panna: str,
        panna_type: str | None = None,
    ) -> PannaReference:
        """
        Create a new Panna reference.

        The Panna value is validated and normalized
        before persistence.
        """

        panna = validate_panna(panna)

        panna_type = self._validate_panna_type(
            panna_type
        )

        existing = self.db.scalar(
            select(PannaReference).where(
                PannaReference.panna == panna
            )
        )

        if existing:
            raise ValueError(
                f"Panna '{panna}' already exists."
            )

        reference = PannaReference(
            panna=panna,
            digit_1=int(panna[0]),
            digit_2=int(panna[1]),
            digit_3=int(panna[2]),
            panna_type=panna_type,
        )

        self.db.add(reference)
        self.db.commit()
        self.db.refresh(reference)

        return reference

    def get_panna(
        self,
        panna: str,
    ) -> PannaReference | None:
        """Retrieve a Panna reference by value."""

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

        By default, only active Pannas are returned.
        Set active_only=False to retrieve all Pannas.
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
        Search Panna references.

        Supports:
        - partial Panna value search
        - exact Panna type filtering
        - active/inactive filtering

        Both panna and panna_type are optional.
        At least one search criterion must be provided.
        """

        if panna is None and panna_type is None:
            raise ValueError(
                "At least one search criterion is required."
            )

        statement = select(PannaReference)

        if panna is not None:
            panna = str(panna).strip()

            if not panna:
                raise ValueError(
                    "Panna search value cannot be empty."
                )

            statement = statement.where(
                PannaReference.panna.ilike(
                    f"%{panna}%"
                )
            )

        if panna_type is not None:
            panna_type = self._validate_panna_type(
                panna_type
            )

            if panna_type is not None:
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