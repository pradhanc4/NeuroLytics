from datetime import date

from database.historical_quality_checker import (
    HistoricalQualityChecker,
)


class QualityReportService:
    """
    Builds human-readable data-quality reports from the
    HistoricalQualityChecker results.

    This service does not perform validation itself.
    It only organizes and formats quality information.
    """

    def __init__(self, db):
        self.checker = HistoricalQualityChecker(db)

    def generate_market_report(
        self,
        market_id: int,
        validation_version: str = "v1",
    ) -> dict:
        """
        Validate a market's historical data and return
        a structured quality report.
        """

        summary = self.checker.validate_market_history(
            market_id=market_id,
            validation_version=validation_version,
        )

        date_analysis = summary["date_analysis"]

        return {
            "market": {
                "id": summary["market_id"],
                "name": summary["market_name"],
            },
            "validation": {
                "version": summary["validation_version"],
            },
            "records": {
                "total": summary["total_records"],
                "valid": summary["valid_records"],
                "warning": summary["warning_records"],
                "invalid": summary["invalid_records"],
            },
            "quality": {
                "percentage": summary["quality_percentage"],
                "status": self._get_quality_status(
                    summary["quality_percentage"]
                ),
            },
            "dates": {
                "first": date_analysis["first_date"],
                "last": date_analysis["last_date"],
                "duplicate_dates": date_analysis[
                    "duplicate_dates"
                ],
                "missing_calendar_dates": date_analysis[
                    "missing_calendar_dates"
                ],
            },
            "issues": {
                "invalid_record_ids": summary[
                    "invalid_record_ids"
                ],
                "warning_record_ids": summary[
                    "warning_record_ids"
                ],
            },
        }

    def generate_stored_report(
        self,
        market_id: int,
        validation_version: str = "v1",
    ) -> dict:
        """
        Generate a report using already-stored quality
        records without re-running validation.
        """

        summary = self.checker.get_quality_summary(
            market_id=market_id,
            validation_version=validation_version,
        )

        return {
            "market": {
                "id": summary["market_id"],
                "name": summary["market_name"],
            },
            "validation": {
                "version": summary["validation_version"],
            },
            "records": {
                "total": summary["total_records"],
                "checked": summary["checked_records"],
                "unchecked": summary["unchecked_records"],
                "valid": summary["valid_records"],
                "warning": summary["warning_records"],
                "invalid": summary["invalid_records"],
            },
            "quality": {
                "percentage": summary["quality_percentage"],
                "status": self._get_quality_status(
                    summary["quality_percentage"]
                ),
            },
        }

    @staticmethod
    def _get_quality_status(
        quality_percentage: float,
    ) -> str:
        """
        Convert a quality percentage into a descriptive
        reporting status.

        These are reporting categories only and do not
        change the underlying validation result.
        """

        if quality_percentage >= 99:
            return "EXCELLENT"

        if quality_percentage >= 95:
            return "GOOD"

        if quality_percentage >= 90:
            return "FAIR"

        return "NEEDS_REVIEW"

    @staticmethod
    def format_date(
        value: date | None,
    ) -> str | None:
        """
        Convert a date object into ISO format for reports.
        """

        if value is None:
            return None

        return value.isoformat()

    def generate_display_report(
        self,
        market_id: int,
        validation_version: str = "v1",
    ) -> dict:
        """
        Generate a frontend-friendly report with dates
        represented as strings.
        """

        report = self.generate_market_report(
            market_id=market_id,
            validation_version=validation_version,
        )

        report["dates"]["first"] = self.format_date(
            report["dates"]["first"]
        )

        report["dates"]["last"] = self.format_date(
            report["dates"]["last"]
        )

        report["dates"]["duplicate_dates"] = [
            self.format_date(value)
            for value in report["dates"][
                "duplicate_dates"
            ]
        ]

        report["dates"]["missing_calendar_dates"] = [
            self.format_date(value)
            for value in report["dates"][
                "missing_calendar_dates"
            ]
        ]

        return report