from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market
from database.parser import parse_results


class HistoricalResultService:
    """Service layer for historical result CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_market(self, name: str) -> Market:
        """Create a new market."""

        name = name.strip()

        if not name:
            raise ValueError("Market name is required.")

        existing_market = self.db.scalar(
            select(Market).where(Market.name == name)
        )

        if existing_market:
            raise ValueError(
                f"Market '{name}' already exists."
            )

        market = Market(name=name)

        self.db.add(market)
        self.db.commit()
        self.db.refresh(market)

        return market

    def get_market(self, name: str) -> Market | None:
        """Find a market by name."""

        return self.db.scalar(
            select(Market).where(Market.name == name)
        )

    def create_historical_result(
        self,
        market: Market,
        result_date: date,
        open_result: str,
        jodi_result: str,
        close_result: str,
    ) -> HistoricalResult:
        """Validate, parse, and save a historical result."""

        parsed = parse_results(
            open_result=open_result,
            jodi_result=jodi_result,
            close_result=close_result,
        )

        existing_result = self.db.scalar(
            select(HistoricalResult).where(
                HistoricalResult.market_id == market.id,
                HistoricalResult.result_date == result_date,
            )
        )

        if existing_result:
            raise ValueError(
                "A historical result already exists "
                "for this market and date."
            )

        historical_result = HistoricalResult(
            market_id=market.id,
            result_date=result_date,
            **parsed,
        )

        self.db.add(historical_result)
        self.db.commit()
        self.db.refresh(historical_result)

        return historical_result

    def get_result(
        self,
        result_id: int,
    ) -> HistoricalResult | None:
        """Get a historical result by ID."""

        return self.db.get(
            HistoricalResult,
            result_id,
        )

    def get_results_by_market(
        self,
        market: Market,
    ) -> list[HistoricalResult]:
        """Get all historical results for a market."""

        return list(
            self.db.scalars(
                select(HistoricalResult)
                .where(
                    HistoricalResult.market_id == market.id
                )
                .order_by(HistoricalResult.result_date)
            )
        )

    def get_result_by_date(
        self,
        market: Market,
        result_date: date,
    ) -> HistoricalResult | None:
        """Get a historical result for a market and specific date."""

        return self.db.scalar(
            select(HistoricalResult).where(
                HistoricalResult.market_id == market.id,
                HistoricalResult.result_date == result_date,
            )
        )

    def get_results_by_date_range(
        self,
        market: Market,
        start_date: date,
        end_date: date,
    ) -> list[HistoricalResult]:
        """Get historical results within an inclusive date range."""

        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date."
            )

        return list(
            self.db.scalars(
                select(HistoricalResult)
                .where(
                    HistoricalResult.market_id == market.id,
                    HistoricalResult.result_date >= start_date,
                    HistoricalResult.result_date <= end_date,
                )
                .order_by(HistoricalResult.result_date)
            )
        )

    def update_historical_result(
        self,
        result_id: int,
        result_date: date,
        open_result: str,
        jodi_result: str,
        close_result: str,
    ) -> HistoricalResult:
        """Validate and update an existing historical result."""

        historical_result = self.db.get(
            HistoricalResult,
            result_id,
        )

        if historical_result is None:
            raise ValueError(
                f"Historical result with ID {result_id} "
                "was not found."
            )

        parsed = parse_results(
            open_result=open_result,
            jodi_result=jodi_result,
            close_result=close_result,
        )

        duplicate_result = self.db.scalar(
            select(HistoricalResult).where(
                HistoricalResult.market_id
                == historical_result.market_id,
                HistoricalResult.result_date == result_date,
                HistoricalResult.id != result_id,
            )
        )

        if duplicate_result:
            raise ValueError(
                "Another historical result already exists "
                "for this market and date."
            )

        historical_result.result_date = result_date
        historical_result.open_result = parsed["open_result"]
        historical_result.jodi_result = parsed["jodi_result"]
        historical_result.close_result = parsed["close_result"]

        historical_result.col1 = parsed["col1"]
        historical_result.col2 = parsed["col2"]
        historical_result.col3 = parsed["col3"]
        historical_result.col4 = parsed["col4"]
        historical_result.col5 = parsed["col5"]
        historical_result.col6 = parsed["col6"]
        historical_result.col7 = parsed["col7"]
        historical_result.col8 = parsed["col8"]

        self.db.commit()
        self.db.refresh(historical_result)

        return historical_result

    def delete_historical_result(
        self,
        result_id: int,
    ) -> None:
        """Delete a historical result."""

        historical_result = self.db.get(
            HistoricalResult,
            result_id,
        )

        if historical_result is None:
            raise ValueError(
                f"Historical result with ID {result_id} "
                "was not found."
            )

        self.db.delete(historical_result)
        self.db.commit()