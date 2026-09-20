from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.classification_rules import (
    classify_historical_result,
)
from database.models import (
    HistoricalClassification,
    HistoricalResult,
)


class ClassificationService:
    """Service for creating and retrieving historical classifications."""

    def __init__(self, db: Session):
        self.db = db

    def get_classification(
        self,
        historical_result_id: int,
        classification_version: str,
    ) -> HistoricalClassification | None:
        """
        Return a classification for a historical result
        and classification version.
        """

        if historical_result_id is None:
            raise ValueError(
                "Historical result ID is required."
            )

        if not classification_version:
            raise ValueError(
                "Classification version is required."
            )

        statement = select(
            HistoricalClassification
        ).where(
            HistoricalClassification.historical_result_id
            == historical_result_id,
            HistoricalClassification.classification_version
            == classification_version,
        )

        return self.db.scalar(statement)

    def get_classification_by_id(
        self,
        classification_id: int,
    ) -> HistoricalClassification | None:
        """Return one classification by its database ID."""

        if classification_id is None:
            raise ValueError(
                "Classification ID is required."
            )

        return self.db.get(
            HistoricalClassification,
            classification_id,
        )

    def classify_result(
        self,
        historical_result_id: int,
        classification_version: str = "v1",
    ) -> HistoricalClassification:
        """
        Classify one historical result and persist
        the classification in SQL.
        """

        if historical_result_id is None:
            raise ValueError(
                "Historical result ID is required."
            )

        if not classification_version:
            raise ValueError(
                "Classification version is required."
            )

        historical_result = self.db.get(
            HistoricalResult,
            historical_result_id,
        )

        if historical_result is None:
            raise ValueError(
                "Historical result not found."
            )

        existing = self.get_classification(
            historical_result_id=historical_result_id,
            classification_version=classification_version,
        )

        if existing is not None:
            return existing

        classification_data = classify_historical_result(
            historical_result=historical_result,
            classification_version=classification_version,
        )

        classification = HistoricalClassification(
            historical_result_id=historical_result.id,
            classification_version=classification_version,
            open_class=classification_data["open_class"],
            jodi_class=classification_data["jodi_class"],
            close_class=classification_data["close_class"],
            overall_class=classification_data["overall_class"],
        )

        self.db.add(classification)
        self.db.commit()
        self.db.refresh(classification)

        return classification

    def classify_results(
        self,
        historical_result_ids: list[int],
        classification_version: str = "v1",
    ) -> list[HistoricalClassification]:
        """
        Classify multiple historical results.

        Existing classifications for the same result/version
        are reused instead of creating duplicates.
        """

        if not historical_result_ids:
            raise ValueError(
                "At least one historical result ID is required."
            )

        if not classification_version:
            raise ValueError(
                "Classification version is required."
            )

        classifications = []

        for historical_result_id in historical_result_ids:
            classification = self.classify_result(
                historical_result_id=historical_result_id,
                classification_version=classification_version,
            )

            classifications.append(classification)

        return classifications

    def get_classifications_for_result(
        self,
        historical_result_id: int,
    ) -> list[HistoricalClassification]:
        """Return all classification versions for a result."""

        if historical_result_id is None:
            raise ValueError(
                "Historical result ID is required."
            )

        statement = (
            select(HistoricalClassification)
            .where(
                HistoricalClassification.historical_result_id
                == historical_result_id
            )
            .order_by(
                HistoricalClassification.classification_version
            )
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_version(
        self,
        classification_version: str,
    ) -> list[HistoricalClassification]:
        """Return all classifications for a specific version."""

        if not classification_version:
            raise ValueError(
                "Classification version is required."
            )

        statement = (
            select(HistoricalClassification)
            .where(
                HistoricalClassification.classification_version
                == classification_version
            )
            .order_by(
                HistoricalClassification.historical_result_id
            )
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_open_class(
        self,
        open_class: str,
        classification_version: str | None = None,
    ) -> list[HistoricalClassification]:
        """Return classifications matching an Open classification."""

        if not open_class:
            raise ValueError(
                "Open classification is required."
            )

        statement = select(
            HistoricalClassification
        ).where(
            HistoricalClassification.open_class
            == open_class
        )

        if classification_version:
            statement = statement.where(
                HistoricalClassification.classification_version
                == classification_version
            )

        statement = statement.order_by(
            HistoricalClassification.historical_result_id
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_jodi_class(
        self,
        jodi_class: str,
        classification_version: str | None = None,
    ) -> list[HistoricalClassification]:
        """Return classifications matching a Jodi classification."""

        if not jodi_class:
            raise ValueError(
                "Jodi classification is required."
            )

        statement = select(
            HistoricalClassification
        ).where(
            HistoricalClassification.jodi_class
            == jodi_class
        )

        if classification_version:
            statement = statement.where(
                HistoricalClassification.classification_version
                == classification_version
            )

        statement = statement.order_by(
            HistoricalClassification.historical_result_id
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_close_class(
        self,
        close_class: str,
        classification_version: str | None = None,
    ) -> list[HistoricalClassification]:
        """Return classifications matching a Close classification."""

        if not close_class:
            raise ValueError(
                "Close classification is required."
            )

        statement = select(
            HistoricalClassification
        ).where(
            HistoricalClassification.close_class
            == close_class
        )

        if classification_version:
            statement = statement.where(
                HistoricalClassification.classification_version
                == classification_version
            )

        statement = statement.order_by(
            HistoricalClassification.historical_result_id
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_overall_class(
        self,
        overall_class: str,
        classification_version: str | None = None,
    ) -> list[HistoricalClassification]:
        """Return classifications matching an overall classification."""

        if not overall_class:
            raise ValueError(
                "Overall classification is required."
            )

        statement = select(
            HistoricalClassification
        ).where(
            HistoricalClassification.overall_class
            == overall_class
        )

        if classification_version:
            statement = statement.where(
                HistoricalClassification.classification_version
                == classification_version
            )

        statement = statement.order_by(
            HistoricalClassification.historical_result_id
        )

        return list(
            self.db.scalars(statement)
        )

    def get_classifications_by_date_range(
        self,
        start_date: date,
        end_date: date,
        classification_version: str | None = None,
    ) -> list[HistoricalClassification]:
        """
        Return classifications for historical results
        within an inclusive date range.
        """

        if start_date is None:
            raise ValueError(
                "Start date is required."
            )

        if end_date is None:
            raise ValueError(
                "End date is required."
            )

        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date."
            )

        statement = (
            select(HistoricalClassification)
            .join(
                HistoricalResult,
                HistoricalClassification.historical_result_id
                == HistoricalResult.id,
            )
            .where(
                HistoricalResult.result_date >= start_date,
                HistoricalResult.result_date <= end_date,
            )
        )

        if classification_version:
            statement = statement.where(
                HistoricalClassification.classification_version
                == classification_version
            )

        statement = statement.order_by(
            HistoricalResult.result_date,
            HistoricalClassification.historical_result_id,
            HistoricalClassification.classification_version,
        )

        return list(
            self.db.scalars(statement)
        )