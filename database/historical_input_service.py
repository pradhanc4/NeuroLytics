from datetime import date

from sqlalchemy.orm import Session

from database.models import HistoricalResult
from database.services import HistoricalResultService


class HistoricalInputService:
    """Application service for entering historical results."""

    def __init__(self, db: Session):
        self.db = db
        self.result_service = HistoricalResultService(db)

    @staticmethod
    def _validate_market_name(market_name: str) -> str:
        """Validate and normalize the market name."""

        if market_name is None:
            raise ValueError("Market name is required.")

        market_name = market_name.strip()

        if not market_name:
            raise ValueError("Market name is required.")

        return market_name

    @staticmethod
    def _validate_result_date(result_date: date) -> date:
        """Validate the historical result date."""

        if result_date is None:
            raise ValueError("Result date is required.")

        if not isinstance(result_date, date):
            raise ValueError("Result date must be a valid date.")

        return result_date

    @staticmethod
    def _validate_result_input(
        value: str,
        field_name: str,
        expected_length: int,
    ) -> str:
        """Validate a result component before persistence."""

        if value is None:
            raise ValueError(
                f"{field_name} is required."
            )

        value = str(value).strip()

        if not value:
            raise ValueError(
                f"{field_name} is required."
            )

        if not value.isdigit():
            raise ValueError(
                f"{field_name} must contain digits only."
            )

        if len(value) != expected_length:
            raise ValueError(
                f"{field_name} must contain exactly "
                f"{expected_length} digits."
            )

        return value

    def add_historical_result(
        self,
        market_name: str,
        result_date: date,
        open_result: str,
        jodi_result: str,
        close_result: str,
    ) -> HistoricalResult:
        """
        Validate input, find the market, parse the result,
        and save the historical record.
        """

        market_name = self._validate_market_name(
            market_name
        )

        result_date = self._validate_result_date(
            result_date
        )

        open_result = self._validate_result_input(
            open_result,
            field_name="Open",
            expected_length=3,
        )

        jodi_result = self._validate_result_input(
            jodi_result,
            field_name="Jodi",
            expected_length=2,
        )

        close_result = self._validate_result_input(
            close_result,
            field_name="Close",
            expected_length=3,
        )

        market = self.result_service.get_market(
            market_name
        )

        if market is None:
            raise ValueError(
                f"Market '{market_name}' was not found."
            )

        return self.result_service.create_historical_result(
            market=market,
            result_date=result_date,
            open_result=open_result,
            jodi_result=jodi_result,
            close_result=close_result,
        )