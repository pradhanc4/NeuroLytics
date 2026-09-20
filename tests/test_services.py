from datetime import date

import pytest
from sqlalchemy import delete

from database.engine import Base, SessionLocal, engine
from database.models import HistoricalResult, Market
from database.services import HistoricalResultService


@pytest.fixture
def db():
    """Create an isolated database session for each test."""

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()

        session.execute(delete(HistoricalResult))
        session.execute(delete(Market))

        session.commit()
        session.close()


def test_create_and_read_historical_result(db):
    service = HistoricalResultService(db)

    market = service.create_market("Test Market")

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 20),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    assert result.id is not None
    assert result.market_id == market.id
    assert result.result_date == date(2026, 9, 20)

    assert result.open_result == "123"
    assert result.jodi_result == "45"
    assert result.close_result == "678"

    assert [
        result.col1,
        result.col2,
        result.col3,
        result.col4,
        result.col5,
        result.col6,
        result.col7,
        result.col8,
    ] == [1, 2, 3, 4, 5, 6, 7, 8]

    retrieved = service.get_result(result.id)

    assert retrieved is not None
    assert retrieved.id == result.id
    assert retrieved.open_result == "123"


def test_leading_zeros_are_preserved(db):
    service = HistoricalResultService(db)

    market = service.create_market("Zero Test Market")

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 21),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    assert result.open_result == "005"
    assert result.jodi_result == "05"
    assert result.close_result == "007"

    assert [
        result.col1,
        result.col2,
        result.col3,
        result.col4,
        result.col5,
        result.col6,
        result.col7,
        result.col8,
    ] == [0, 0, 5, 0, 5, 0, 0, 7]


def test_duplicate_market_date_is_rejected(db):
    service = HistoricalResultService(db)

    market = service.create_market("Duplicate Test Market")

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 22),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.create_historical_result(
            market=market,
            result_date=date(2026, 9, 22),
            open_result="987",
            jodi_result="65",
            close_result="432",
        )


def test_update_historical_result(db):
    service = HistoricalResultService(db)

    market = service.create_market("Update Test Market")

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 23),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    updated = service.update_historical_result(
        result_id=result.id,
        result_date=date(2026, 9, 24),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    assert updated.result_date == date(2026, 9, 24)

    assert updated.open_result == "005"
    assert updated.jodi_result == "05"
    assert updated.close_result == "007"

    assert [
        updated.col1,
        updated.col2,
        updated.col3,
        updated.col4,
        updated.col5,
        updated.col6,
        updated.col7,
        updated.col8,
    ] == [0, 0, 5, 0, 5, 0, 0, 7]


def test_delete_historical_result(db):
    service = HistoricalResultService(db)

    market = service.create_market("Delete Test Market")

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 25),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    result_id = result.id

    assert service.get_result(result_id) is not None

    service.delete_historical_result(result_id)

    assert service.get_result(result_id) is None


def test_update_rejects_duplicate_market_date(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Update Duplicate Test Market"
    )

    first = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 26),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    second = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 27),
        open_result="987",
        jodi_result="65",
        close_result="432",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.update_historical_result(
            result_id=second.id,
            result_date=first.result_date,
            open_result="111",
            jodi_result="22",
            close_result="333",
        )


def test_get_result_by_date(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Get By Date Test Market"
    )

    result = service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 28),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    found = service.get_result_by_date(
        market=market,
        result_date=date(2026, 9, 28),
    )

    assert found is not None
    assert found.id == result.id
    assert found.result_date == date(2026, 9, 28)


def test_get_results_by_date_range(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Date Range Test Market"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 28),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 29),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 9, 30),
        open_result="987",
        jodi_result="65",
        close_result="432",
    )

    results = service.get_results_by_date_range(
        market=market,
        start_date=date(2026, 9, 28),
        end_date=date(2026, 9, 29),
    )

    assert len(results) == 2

    assert results[0].result_date == date(2026, 9, 28)
    assert results[1].result_date == date(2026, 9, 29)


def test_invalid_date_range_is_rejected(db):
    service = HistoricalResultService(db)

    market = service.create_market(
        "Invalid Date Range Test Market"
    )

    with pytest.raises(
        ValueError,
        match="Start date cannot be after end date",
    ):
        service.get_results_by_date_range(
            market=market,
            start_date=date(2026, 9, 30),
            end_date=date(2026, 9, 28),
        )