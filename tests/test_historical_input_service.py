from datetime import date

import pytest

from database.engine import Base, SessionLocal, engine
from database.historical_input_service import HistoricalInputService
from database.models import HistoricalResult, Market
from sqlalchemy import delete


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


def test_add_historical_result(db):
    service = HistoricalInputService(db)

    market = Market(name="Phase 3 Test Market")

    db.add(market)
    db.commit()
    db.refresh(market)

    result = service.add_historical_result(
        market_name="Phase 3 Test Market",
        result_date=date(2026, 10, 1),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    assert result.id is not None
    assert result.market_id == market.id
    assert result.result_date == date(2026, 10, 1)

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


def test_add_historical_result_preserves_leading_zeros(db):
    service = HistoricalInputService(db)

    market = Market(name="Phase 3 Zero Test Market")

    db.add(market)
    db.commit()

    result = service.add_historical_result(
        market_name="Phase 3 Zero Test Market",
        result_date=date(2026, 10, 2),
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


def test_unknown_market_is_rejected(db):
    service = HistoricalInputService(db)

    with pytest.raises(
        ValueError,
        match="Market 'Unknown Market' was not found",
    ):
        service.add_historical_result(
            market_name="Unknown Market",
            result_date=date(2026, 10, 3),
            open_result="123",
            jodi_result="45",
            close_result="678",
        )


def test_empty_market_name_is_rejected(db):
    service = HistoricalInputService(db)

    with pytest.raises(
        ValueError,
        match="Market name is required",
    ):
        service.add_historical_result(
            market_name="",
            result_date=date(2026, 10, 4),
            open_result="123",
            jodi_result="45",
            close_result="678",
        )
def test_empty_open_is_rejected(db):
    service = HistoricalInputService(db)

    market = Market(name="Open Validation Market")
    db.add(market)
    db.commit()

    with pytest.raises(
        ValueError,
        match="Open is required",
    ):
        service.add_historical_result(
            market_name="Open Validation Market",
            result_date=date(2026, 10, 5),
            open_result="",
            jodi_result="45",
            close_result="678",
        )


def test_invalid_open_length_is_rejected(db):
    service = HistoricalInputService(db)

    market = Market(name="Open Length Market")
    db.add(market)
    db.commit()

    with pytest.raises(
        ValueError,
        match="Open must contain exactly 3 digits",
    ):
        service.add_historical_result(
            market_name="Open Length Market",
            result_date=date(2026, 10, 6),
            open_result="12",
            jodi_result="45",
            close_result="678",
        )


def test_non_numeric_jodi_is_rejected(db):
    service = HistoricalInputService(db)

    market = Market(name="Jodi Validation Market")
    db.add(market)
    db.commit()

    with pytest.raises(
        ValueError,
        match="Jodi must contain digits only",
    ):
        service.add_historical_result(
            market_name="Jodi Validation Market",
            result_date=date(2026, 10, 7),
            open_result="123",
            jodi_result="4A",
            close_result="678",
        )


def test_invalid_close_length_is_rejected(db):
    service = HistoricalInputService(db)

    market = Market(name="Close Length Market")
    db.add(market)
    db.commit()

    with pytest.raises(
        ValueError,
        match="Close must contain exactly 3 digits",
    ):
        service.add_historical_result(
            market_name="Close Length Market",
            result_date=date(2026, 10, 8),
            open_result="123",
            jodi_result="45",
            close_result="67",
        )


def test_missing_result_date_is_rejected(db):
    service = HistoricalInputService(db)

    market = Market(name="Date Validation Market")
    db.add(market)
    db.commit()

    with pytest.raises(
        ValueError,
        match="Result date is required",
    ):
        service.add_historical_result(
            market_name="Date Validation Market",
            result_date=None,
            open_result="123",
            jodi_result="45",
            close_result="678",
        )
def test_parser_integration_generates_all_columns(db):
    service = HistoricalInputService(db)

    market = Market(name="Parser Integration Market")
    db.add(market)
    db.commit()

    result = service.add_historical_result(
        market_name="Parser Integration Market",
        result_date=date(2026, 10, 9),
        open_result="321",
        jodi_result="54",
        close_result="876",
    )

    assert result.open_result == "321"
    assert result.jodi_result == "54"
    assert result.close_result == "876"

    assert result.col1 == 3
    assert result.col2 == 2
    assert result.col3 == 1
    assert result.col4 == 5
    assert result.col5 == 4
    assert result.col6 == 8
    assert result.col7 == 7
    assert result.col8 == 6


def test_parser_integration_preserves_leading_zeros(db):
    service = HistoricalInputService(db)

    market = Market(name="Parser Zero Integration Market")
    db.add(market)
    db.commit()

    result = service.add_historical_result(
        market_name="Parser Zero Integration Market",
        result_date=date(2026, 10, 10),
        open_result="001",
        jodi_result="02",
        close_result="003",
    )

    assert result.open_result == "001"
    assert result.jodi_result == "02"
    assert result.close_result == "003"

    assert result.col1 == 0
    assert result.col2 == 0
    assert result.col3 == 1
    assert result.col4 == 0
    assert result.col5 == 2
    assert result.col6 == 0
    assert result.col7 == 0
    assert result.col8 == 3
def test_historical_input_is_persisted_to_sql(db):
    service = HistoricalInputService(db)

    market = Market(name="SQL Persistence Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    result = service.add_historical_result(
        market_name="SQL Persistence Market",
        result_date=date(2026, 10, 11),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    result_id = result.id

    db.expire_all()

    stored_result = db.get(
        HistoricalResult,
        result_id,
    )

    assert stored_result is not None
    assert stored_result.id == result_id
    assert stored_result.market_id == market.id
    assert stored_result.result_date == date(2026, 10, 11)

    assert stored_result.open_result == "123"
    assert stored_result.jodi_result == "45"
    assert stored_result.close_result == "678"

    assert [
        stored_result.col1,
        stored_result.col2,
        stored_result.col3,
        stored_result.col4,
        stored_result.col5,
        stored_result.col6,
        stored_result.col7,
        stored_result.col8,
    ] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_leading_zeros_survive_sql_persistence(db):
    service = HistoricalInputService(db)

    market = Market(name="SQL Zero Persistence Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    result = service.add_historical_result(
        market_name="SQL Zero Persistence Market",
        result_date=date(2026, 10, 12),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    result_id = result.id

    db.expire_all()

    stored_result = db.get(
        HistoricalResult,
        result_id,
    )

    assert stored_result is not None

    assert stored_result.open_result == "005"
    assert stored_result.jodi_result == "05"
    assert stored_result.close_result == "007"

    assert [
        stored_result.col1,
        stored_result.col2,
        stored_result.col3,
        stored_result.col4,
        stored_result.col5,
        stored_result.col6,
        stored_result.col7,
        stored_result.col8,
    ] == [0, 0, 5, 0, 5, 0, 0, 7]


def test_persisted_result_can_be_retrieved_by_date(db):
    service = HistoricalInputService(db)

    market = Market(name="SQL Retrieval Persistence Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    service.add_historical_result(
        market_name="SQL Retrieval Persistence Market",
        result_date=date(2026, 10, 13),
        open_result="987",
        jodi_result="65",
        close_result="432",
    )

    stored_result = service.result_service.get_result_by_date(
        market=market,
        result_date=date(2026, 10, 13),
    )

    assert stored_result is not None
    assert stored_result.result_date == date(2026, 10, 13)

    assert stored_result.open_result == "987"
    assert stored_result.jodi_result == "65"
    assert stored_result.close_result == "432"

    assert [
        stored_result.col1,
        stored_result.col2,
        stored_result.col3,
        stored_result.col4,
        stored_result.col5,
        stored_result.col6,
        stored_result.col7,
        stored_result.col8,
    ] == [9, 8, 7, 6, 5, 4, 3, 2]
def test_duplicate_historical_result_is_rejected_without_creating_extra_record(
    db,
):
    service = HistoricalInputService(db)

    market = Market(name="Duplicate Error Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    service.add_historical_result(
        market_name="Duplicate Error Market",
        result_date=date(2026, 10, 14),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.add_historical_result(
            market_name="Duplicate Error Market",
            result_date=date(2026, 10, 14),
            open_result="987",
            jodi_result="65",
            close_result="432",
        )

    results = service.result_service.get_results_by_market(
        market
    )

    assert len(results) == 1

    assert results[0].open_result == "123"
    assert results[0].jodi_result == "45"
    assert results[0].close_result == "678"


def test_unknown_market_does_not_create_historical_result(db):
    service = HistoricalInputService(db)

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        service.add_historical_result(
            market_name="Unknown Error Market",
            result_date=date(2026, 10, 15),
            open_result="123",
            jodi_result="45",
            close_result="678",
        )

    results = db.query(HistoricalResult).all()

    assert results == []


def test_invalid_input_does_not_create_historical_result(db):
    service = HistoricalInputService(db)

    market = Market(name="Invalid Input Error Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    with pytest.raises(
        ValueError,
        match="Open must contain exactly 3 digits",
    ):
        service.add_historical_result(
            market_name="Invalid Input Error Market",
            result_date=date(2026, 10, 16),
            open_result="12",
            jodi_result="45",
            close_result="678",
        )

    results = service.result_service.get_results_by_market(
        market
    )

    assert results == []


def test_missing_date_does_not_create_historical_result(db):
    service = HistoricalInputService(db)

    market = Market(name="Missing Date Error Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    with pytest.raises(
        ValueError,
        match="Result date is required",
    ):
        service.add_historical_result(
            market_name="Missing Date Error Market",
            result_date=None,
            open_result="123",
            jodi_result="45",
            close_result="678",
        )

    results = service.result_service.get_results_by_market(
        market
    )

    assert results == []