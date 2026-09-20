from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.data_quality_service import DataQualityService
from database.models import (
    HistoricalDataQuality,
    HistoricalResult,
    Market,
)


class HistoricalQualityChecker:
    """
    Performs dataset-level data-quality checks on historical results.

    This checker does not modify historical result data.
    It uses DataQualityService to validate individual records
    and then produces a historical dataset quality summary.
    """

    DEFAULT_VALIDATION_VERSION = "v1"

    def __init__(self, db: Session):
        self.db = db
        self.quality_service = DataQualityService(db)

    def get_historical_results(
        self,
        market_id: int,
    ) -> list[HistoricalResult]:
        """Return historical results for a market in date order."""

        if market_id <= 0:
            raise ValueError(
                "Market ID must be greater than zero."
            )

        statement = (
            select(HistoricalResult)
            .where(
                HistoricalResult.market_id == market_id,
            )
            .order_by(
                HistoricalResult.result_date,
                HistoricalResult.id,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )

    def validate_market_history(
        self,
        market_id: int,
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> dict:
        """
        Validate every historical result for a market and return
        a dataset-level quality summary.
        """

        if not validation_version.strip():
            raise ValueError(
                "Validation version is required."
            )

        market = self.db.get(
            Market,
            market_id,
        )

        if market is None:
            raise ValueError(
                "Market was not found."
            )

        historical_results = self.get_historical_results(
            market_id=market_id,
        )

        quality_records = []

        for historical_result in historical_results:
            quality_record = (
                self.quality_service.validate_historical_result(
                    historical_result_id=historical_result.id,
                    validation_version=validation_version,
                )
            )

            quality_records.append(
                quality_record
            )

        valid_count = sum(
            1
            for record in quality_records
            if record.status == "VALID"
        )

        warning_count = sum(
            1
            for record in quality_records
            if record.status == "WARNING"
        )

        invalid_count = sum(
            1
            for record in quality_records
            if record.status == "INVALID"
        )

        total_count = len(historical_results)

        quality_percentage = 0.0

        if total_count > 0:
            quality_percentage = (
                valid_count / total_count
            ) * 100

        invalid_record_ids = [
            record.historical_result_id
            for record in quality_records
            if record.status == "INVALID"
        ]

        warning_record_ids = [
            record.historical_result_id
            for record in quality_records
            if record.status == "WARNING"
        ]

        date_analysis = self.analyze_dates(
            historical_results=historical_results,
        )

        return {
            "market_id": market_id,
            "market_name": market.name,
            "validation_version": validation_version,
            "total_records": total_count,
            "valid_records": valid_count,
            "warning_records": warning_count,
            "invalid_records": invalid_count,
            "quality_percentage": quality_percentage,
            "invalid_record_ids": invalid_record_ids,
            "warning_record_ids": warning_record_ids,
            "date_analysis": date_analysis,
        }

    def analyze_dates(
        self,
        historical_results: list[HistoricalResult],
    ) -> dict:
        """
        Analyze historical dates.

        Missing calendar dates are reported separately and are not
        automatically treated as data-quality failures.
        """

        if not historical_results:
            return {
                "record_count": 0,
                "first_date": None,
                "last_date": None,
                "duplicate_dates": [],
                "missing_calendar_dates": [],
            }

        dates = [
            historical_result.result_date
            for historical_result in historical_results
        ]

        date_counts = Counter(dates)

        duplicate_dates = sorted(
            result_date
            for result_date, count in date_counts.items()
            if count > 1
        )

        first_date = min(dates)
        last_date = max(dates)

        existing_dates = set(dates)

        missing_calendar_dates = []

        current_date = first_date

        while current_date <= last_date:
            if current_date not in existing_dates:
                missing_calendar_dates.append(
                    current_date
                )

            current_date += timedelta(days=1)

        return {
            "record_count": len(historical_results),
            "first_date": first_date,
            "last_date": last_date,
            "duplicate_dates": duplicate_dates,
            "missing_calendar_dates": missing_calendar_dates,
        }

    def get_unchecked_results(
        self,
        market_id: int,
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> list[HistoricalResult]:
        """
        Return historical records that do not yet have a quality
        assessment for the requested validation version.
        """

        if market_id <= 0:
            raise ValueError(
                "Market ID must be greater than zero."
            )

        if not validation_version.strip():
            raise ValueError(
                "Validation version is required."
            )

        statement = (
            select(HistoricalResult)
            .outerjoin(
                HistoricalDataQuality,
                (
                    HistoricalDataQuality.historical_result_id
                    == HistoricalResult.id
                )
                & (
                    HistoricalDataQuality.validation_version
                    == validation_version
                ),
            )
            .where(
                HistoricalResult.market_id == market_id,
                HistoricalDataQuality.id.is_(None),
            )
            .order_by(
                HistoricalResult.result_date,
                HistoricalResult.id,
            )
        )

        return list(
            self.db.scalars(statement).all()
        )

    def get_quality_summary(
        self,
        market_id: int,
        validation_version: str = DEFAULT_VALIDATION_VERSION,
    ) -> dict:
        """
        Return a summary using already-stored quality records.

        Unlike validate_market_history(), this method does not
        revalidate historical records.
        """

        if market_id <= 0:
            raise ValueError(
                "Market ID must be greater than zero."
            )

        if not validation_version.strip():
            raise ValueError(
                "Validation version is required."
            )

        market = self.db.get(
            Market,
            market_id,
        )

        if market is None:
            raise ValueError(
                "Market was not found."
            )

        historical_results = self.get_historical_results(
            market_id=market_id,
        )

        historical_result_ids = [
            result.id
            for result in historical_results
        ]

        if not historical_result_ids:
            return {
                "market_id": market_id,
                "market_name": market.name,
                "validation_version": validation_version,
                "total_records": 0,
                "checked_records": 0,
                "unchecked_records": 0,
                "valid_records": 0,
                "warning_records": 0,
                "invalid_records": 0,
                "quality_percentage": 0.0,
            }

        statement = select(
            HistoricalDataQuality
        ).where(
            HistoricalDataQuality.historical_result_id.in_(
                historical_result_ids
            ),
            HistoricalDataQuality.validation_version
            == validation_version,
        )

        quality_records = list(
            self.db.scalars(statement).all()
        )

        valid_count = sum(
            1
            for record in quality_records
            if record.status == "VALID"
        )

        warning_count = sum(
            1
            for record in quality_records
            if record.status == "WARNING"
        )

        invalid_count = sum(
            1
            for record in quality_records
            if record.status == "INVALID"
        )

        checked_count = len(quality_records)

        unchecked_count = (
            len(historical_results)
            - checked_count
        )

        quality_percentage = 0.0

        if checked_count > 0:
            quality_percentage = (
                valid_count / checked_count
            ) * 100

        return {
            "market_id": market_id,
            "market_name": market.name,
            "validation_version": validation_version,
            "total_records": len(historical_results),
            "checked_records": checked_count,
            "unchecked_records": unchecked_count,
            "valid_records": valid_count,
            "warning_records": warning_count,
            "invalid_records": invalid_count,
            "quality_percentage": quality_percentage,
        }