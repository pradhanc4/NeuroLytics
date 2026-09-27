from datetime import date

import pytest

from database.services import HistoricalResultService
from features.historical_data_loader import (
    HistoricalFeatureObservation,
    POSITIONS,
    load_historical_observations,
)


def test_load_historical_observations_in_chronological_order(db):
    service = HistoricalResultService(db)

    market = service.create_market("Loader Test Market")

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 22),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 20),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 21),
        open_result="987",
        jodi_result="65",
        close_result="432",
    )

    observations = load_historical_observations(
        service=service,
        market=market,
    )

    assert isinstance(
        observations,
        tuple,
    )

    assert len(observations) == 3

    assert all(
        isinstance(
            observation,
            HistoricalFeatureObservation,
        )
        for observation in observations
    )

    assert [
        observation.result_date
        for observation in observations
    ] == [
        date(2026, 9, 20),
        date(2026, 9, 21),
        date(2026, 9, 22),
    ]


def test_loader_preserves_eight_positions(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Position Loader Market"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 20),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    observations = load_historical_observations(
        service=service,
        market=market,
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.positions == (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    )

    assert len(observation.positions) == len(POSITIONS)


def test_loader_preserves_zero_values(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Zero Loader Market"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 20),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    observations = load_historical_observations(
        service=service,
        market=market,
    )

    assert observations[0].positions == (
        0,
        0,
        5,
        0,
        5,
        0,
        0,
        7,
    )


def test_loader_returns_empty_tuple_for_market_without_history(
    db,
):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Empty Loader Market"
    )

    observations = load_historical_observations(
        service=service,
        market=market,
    )

    assert observations == ()


def test_loader_preserves_result_and_market_identity(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Identity Loader Market"
    )

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 20),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    observations = load_historical_observations(
        service=service,
        market=market,
    )

    observation = observations[0]

    assert observation.result_id == result.id
    assert observation.market_id == market.id
    assert observation.result_date == result.result_date


def test_loader_requires_historical_result_service(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Type Validation Market"
    )

    with pytest.raises(
        TypeError,
        match="HistoricalResultService",
    ):
        load_historical_observations(
            service=object(),
            market=market,
        )


def test_loader_requires_market_instance(db):
    service = HistoricalResultService(db)

    with pytest.raises(
        TypeError,
        match="Market",
    ):
        load_historical_observations(
            service=service,
            market=object(),
        )


def test_loader_requires_persisted_market(db):
    service = HistoricalResultService(db)

    from database.models import Market

    unsaved_market = Market(
        name="Unsaved Loader Market",
    )

    with pytest.raises(
        ValueError,
        match="database ID",
    ):
        load_historical_observations(
            service=service,
            market=unsaved_market,
        )