from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.data_quality_rules import (
    DataQualityValidationError,
    validate_historical_record,
)
from database.models import (
    HistoricalDataQuality,
    HistoricalResult,
)


class DataQualityService:
    """
    Service for validating historical records and storing
    their data-quality results.

    The original HistoricalResult is never modified.
    """

    DEFAULT_VALIDATION_VERSION = "v1"

    def __init__(self, db: Session):
        self.db = db

    def get_quality_record(
        self,
        historical_result_id: int,
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> HistoricalDataQuality | None:
        """
        Retrieve an existing quality record for a historical result.
        """

        if historical_result_id <= 0:
            raise ValueError(
                "Historical result ID must be greater than zero."
            )

        if not validation_version.strip():
            raise ValueError(
                "Validation version is required."
            )

        statement = select(HistoricalDataQuality).where(
            HistoricalDataQuality.historical_result_id
            == historical_result_id,
            HistoricalDataQuality.validation_version
            == validation_version,
        )

        return self.db.scalar(statement)

    def get_quality_record_by_id(
        self,
        quality_record_id: int,
    ) -> HistoricalDataQuality | None:
        """Retrieve a quality record by its primary key."""

        if quality_record_id <= 0:
            raise ValueError(
                "Quality record ID must be greater than zero."
            )

        statement = select(HistoricalDataQuality).where(
            HistoricalDataQuality.id == quality_record_id
        )

        return self.db.scalar(statement)

    def validate_historical_result(
        self,
        historical_result_id: int,
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> HistoricalDataQuality:
        """
        Validate one historical result and persist its quality status.

        Existing quality records for the same result/version are updated
        rather than duplicated.
        """

        if historical_result_id <= 0:
            raise ValueError(
                "Historical result ID must be greater than zero."
            )

        if not validation_version.strip():
            raise ValueError(
                "Validation version is required."
            )

        historical_result = self.db.get(
            HistoricalResult,
            historical_result_id,
        )

        if historical_result is None:
            raise ValueError(
                "Historical result was not found."
            )

        columns = {
            "col1": historical_result.col1,
            "col2": historical_result.col2,
            "col3": historical_result.col3,
            "col4": historical_result.col4,
            "col5": historical_result.col5,
            "col6": historical_result.col6,
            "col7": historical_result.col7,
            "col8": historical_result.col8,
        }

        try:
            validate_historical_record(
                market_id=historical_result.market_id,
                result_date=historical_result.result_date,
                open_result=historical_result.open_result,
                jodi_result=historical_result.jodi_result,
                close_result=historical_result.close_result,
                columns=columns,
            )

            status = "VALID"
            issue_count = 0
            issue_summary = None

        except DataQualityValidationError as exc:
            status = "INVALID"
            issue_count = 1
            issue_summary = str(exc)

        quality_record = self.get_quality_record(
            historical_result_id=historical_result_id,
            validation_version=validation_version,
        )

        if quality_record is None:
            quality_record = HistoricalDataQuality(
                historical_result_id=historical_result_id,
                validation_version=validation_version,
                status=status,
                issue_count=issue_count,
                issue_summary=issue_summary,
            )

            self.db.add(quality_record)

        else:
            quality_record.status = status
            quality_record.issue_count = issue_count
            quality_record.issue_summary = issue_summary

        self.db.commit()
        self.db.refresh(quality_record)

        return quality_record

    def validate_historical_results(
        self,
        historical_result_ids: list[int],
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> list[HistoricalDataQuality]:
        """
        Validate multiple historical results.

        Results are processed in the order supplied.
        """

        if not historical_result_ids:
            raise ValueError(
                "At least one historical result ID is required."
            )

        results = []

        for historical_result_id in historical_result_ids:
            quality_record = self.validate_historical_result(
                historical_result_id=historical_result_id,
                validation_version=validation_version,
            )

            results.append(quality_record)

        return results

    def get_quality_records_by_status(
        self,
        status: str,
        validation_version: str | None = None,
    ) -> list[HistoricalDataQuality]:
        """
        Retrieve quality records by status.

        Supported statuses:
        VALID
        WARNING
        INVALID
        """

        status = status.strip().upper()

        allowed_statuses = {
            "VALID",
            "WARNING",
            "INVALID",
        }

        if status not in allowed_statuses:
            raise ValueError(
                "Status must be VALID, WARNING, or INVALID."
            )

        statement = select(HistoricalDataQuality).where(
            HistoricalDataQuality.status == status
        )

        if validation_version is not None:
            validation_version = validation_version.strip()

            if not validation_version:
                raise ValueError(
                    "Validation version cannot be empty."
                )

            statement = statement.where(
                HistoricalDataQuality.validation_version
                == validation_version
            )

        statement = statement.order_by(
            HistoricalDataQuality.historical_result_id
        )

        return list(self.db.scalars(statement).all())

    def get_quality_records_by_date_range(
        self,
        start_date: date,
        end_date: date,
        validation_version: str | None = None,
    ) -> list[HistoricalDataQuality]:
        """
        Retrieve quality records for historical results within
        an inclusive date range.
        """

        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date."
            )

        statement = (
            select(HistoricalDataQuality)
            .join(
                HistoricalResult,
                HistoricalDataQuality.historical_result_id
                == HistoricalResult.id,
            )
            .where(
                HistoricalResult.result_date >= start_date,
                HistoricalResult.result_date <= end_date,
            )
            .order_by(
                HistoricalResult.result_date,
                HistoricalResult.id,
            )
        )

        if validation_version is not None:
            validation_version = validation_version.strip()

            if not validation_version:
                raise ValueError(
                    "Validation version cannot be empty."
                )

            statement = statement.where(
                HistoricalDataQuality.validation_version
                == validation_version
            )

        return list(self.db.scalars(statement).all())

    def count_by_status(
        self,
        validation_version: str | None = None,
    ) -> dict[str, int]:
        """
        Return the number of quality records for each status.
        """

        records = self.get_quality_records_by_status(
            status="VALID",
            validation_version=validation_version,
        )

        valid_count = len(records)

        warning_records = self.get_quality_records_by_status(
            status="WARNING",
            validation_version=validation_version,
        )

        warning_count = len(warning_records)

        invalid_records = self.get_quality_records_by_status(
            status="INVALID",
            validation_version=validation_version,
        )

        invalid_count = len(invalid_records)

        return {
            "VALID": valid_count,
            "WARNING": warning_count,
            "INVALID": invalid_count,
        }