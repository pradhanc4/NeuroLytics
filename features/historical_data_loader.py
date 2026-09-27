from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from database.models import HistoricalResult, Market
from database.services import HistoricalResultService


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


@dataclass(frozen=True)
class HistoricalFeatureObservation:
    """Point-in-time-safe representation of one historical observation."""

    result_id: int
    market_id: int
    result_date: date
    positions: tuple[int, ...]


def _validate_historical_result(
    result: HistoricalResult,
) -> None:
    """Validate the structural requirements for one historical result."""

    if result.id is None:
        raise ValueError(
            "Historical result must have a database ID."
        )

    if result.market_id is None:
        raise ValueError(
            "Historical result must have a market ID."
        )

    if result.result_date is None:
        raise ValueError(
            "Historical result must have a result date."
        )

    values = tuple(
        getattr(result, position)
        for position in POSITIONS
    )

    if len(values) != len(POSITIONS):
        raise ValueError(
            "Historical result must contain exactly eight positions."
        )

    for position, value in zip(POSITIONS, values):
        if isinstance(value, bool):
            raise ValueError(
                f"{position} must be an integer digit."
            )

        if not isinstance(value, int):
            raise ValueError(
                f"{position} must be an integer digit."
            )

        if value < 0 or value > 9:
            raise ValueError(
                f"{position} must contain a digit from 0 to 9."
            )


def _convert_result(
    result: HistoricalResult,
) -> HistoricalFeatureObservation:
    """Convert one SQL historical result into an immutable observation."""

    _validate_historical_result(result)

    positions = tuple(
        getattr(result, position)
        for position in POSITIONS
    )

    return HistoricalFeatureObservation(
        result_id=result.id,
        market_id=result.market_id,
        result_date=result.result_date,
        positions=positions,
    )


def load_historical_observations(
    service: HistoricalResultService,
    market: Market,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Load historical observations for one market in chronological order.

    This loader only reads historical observations. It does not calculate
    features, predictions, rankings, or model outputs.
    """

    if not isinstance(service, HistoricalResultService):
        raise TypeError(
            "service must be a HistoricalResultService instance."
        )

    if not isinstance(market, Market):
        raise TypeError(
            "market must be a Market instance."
        )

    if market.id is None:
        raise ValueError(
            "Market must have a database ID."
        )

    results = service.get_results_by_market(
        market=market,
    )

    if not results:
        return ()

    observations = tuple(
        _convert_result(result)
        for result in results
    )

    previous_date: date | None = None

    for observation in observations:
        if (
            previous_date is not None
            and observation.result_date <= previous_date
        ):
            raise ValueError(
                "Historical observations must be strictly chronological."
            )

        previous_date = observation.result_date

    return observations