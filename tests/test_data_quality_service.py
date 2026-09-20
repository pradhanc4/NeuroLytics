from datetime import date

import pytest

from database.data_quality_service import DataQualityService
from database.models import (
    HistoricalDataQuality,
    HistoricalResult,
    Market,
)


def create_market(
    db,
    name="Test Market",
):
    """Create a test market."""

    market = Market(
        name=name,
        is_active=True,
    )

    db.add(market)
    db.commit()
    db.refresh(market)

    return market


def create_historical_result(
    db,
    market,
    result_date=date(2026, 9, 19),
    open_result="123",
    jodi_result="45",
    close_result="678",
):
    """Create a historical result with correctly derived columns."""

    result = HistoricalResult(
        market_id=market.id,
        result_date=result_date,
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
        col1=int(open_result[0]),
        col2=int(open_result[1]),
        col3=int(open_result[2]),
        col4=int(jodi_result[0]),
        col5=int(jodi_result[1]),
        col6=int(close_result[0]),
        col7=int(close_result[1]),
        col8=int(close_result[2]),
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result


def test_validate_valid_historical_result(db):
    """A valid historical result should receive VALID status."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert quality_record.status == "VALID"
    assert quality_record.issue_count == 0
    assert quality_record.issue_summary is None
    assert quality_record.validation_version == "v1"
    assert (
        quality_record.historical_result_id
        == historical_result.id
    )


def test_validate_leading_zero_historical_result(db):
    """Leading-zero historical results should remain VALID."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert quality_record.status == "VALID"
    assert quality_record.issue_count == 0

    db.refresh(historical_result)

    assert historical_result.open_result == "005"
    assert historical_result.jodi_result == "05"
    assert historical_result.close_result == "007"


def test_validate_actual_zero_digits(db):
    """Actual zero digits must be accepted as valid data."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        open_result="000",
        jodi_result="00",
        close_result="000",
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert quality_record.status == "VALID"
    assert quality_record.issue_count == 0


def test_invalid_derived_column_is_saved_as_invalid(db):
    """An inconsistent derived column should produce INVALID status."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
    )

    historical_result.col8 = 9

    db.commit()
    db.refresh(historical_result)

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert quality_record.status == "INVALID"
    assert quality_record.issue_count == 1
    assert quality_record.issue_summary is not None
    assert "col8" in quality_record.issue_summary


def test_invalid_market_id_is_saved_as_invalid(db):
    """An invalid market reference should produce INVALID status."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
    )

    historical_result.market_id = 0

    db.commit()
    db.refresh(historical_result)

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert quality_record.status == "INVALID"
    assert quality_record.issue_count == 1
    assert "Market ID" in quality_record.issue_summary


def test_missing_historical_result_raises_error(db):
    """A nonexistent historical result should raise an error."""

    service = DataQualityService(db)

    with pytest.raises(
        ValueError,
        match="Historical result was not found",
    ):
        service.validate_historical_result(
            historical_result_id=999999,
        )


def test_invalid_historical_result_id_is_rejected(db):
    """Historical result IDs must be positive."""

    service = DataQualityService(db)

    with pytest.raises(
        ValueError,
        match="Historical result ID must be greater than zero",
    ):
        service.validate_historical_result(
            historical_result_id=0,
        )


def test_get_quality_record(db):
    """A saved quality record should be retrievable."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
    )

    service = DataQualityService(db)

    created = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    retrieved = service.get_quality_record(
        historical_result_id=historical_result.id,
    )

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.status == "VALID"


def test_quality_record_is_updated_not_duplicated(db):
    """Revalidating the same result/version should update one record."""

    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
    )

    service = DataQualityService(db)

    first = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    historical_result.col8 = 9

    db.commit()

    second = service.validate_historical_result(
        historical_result_id=historical_result.id,
    )

    assert second.id == first.id
    assert second.status == "INVALID"
    assert second.issue_count == 1

    records = (
        db.query(HistoricalDataQuality)
        .filter(
            HistoricalDataQuality.historical_result_id
            == historical_result.id
        )
        .all()
    )

    assert len(records) == 1


def test_validate_multiple_historical_results(db):
    """Multiple historical results should be validated in order."""

    market = create_market(db)

    first_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 18),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    second_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 19),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    service = DataQualityService(db)

    records = service.validate_historical_results(
        historical_result_ids=[
            first_result.id,
            second_result.id,
        ],
    )

    assert len(records) == 2
    assert records[0].historical_result_id == first_result.id
    assert records[1].historical_result_id == second_result.id
    assert records[0].status == "VALID"
    assert records[1].status == "VALID"


def test_validate_multiple_requires_ids(db):
    """An empty historical-result list should be rejected."""

    service = DataQualityService(db)

    with pytest.raises(
        ValueError,
        match="At least one historical result ID is required",
    ):
        service.validate_historical_results([])


def test_get_quality_records_by_status(db):
    """Quality records can be filtered by status."""

    market = create_market(db)

    valid_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 18),
    )

    invalid_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 19),
    )

    invalid_result.col8 = 9
    db.commit()

    service = DataQualityService(db)

    service.validate_historical_result(
        historical_result_id=valid_result.id,
    )

    service.validate_historical_result(
        historical_result_id=invalid_result.id,
    )

    valid_records = service.get_quality_records_by_status(
        status="VALID",
    )

    invalid_records = service.get_quality_records_by_status(
        status="INVALID",
    )

    assert len(valid_records) == 1
    assert valid_records[0].historical_result_id == valid_result.id

    assert len(invalid_records) == 1
    assert (
        invalid_records[0].historical_result_id
        == invalid_result.id
    )


def test_invalid_quality_status_is_rejected(db):
    """Unsupported quality statuses should be rejected."""

    service = DataQualityService(db)

    with pytest.raises(
        ValueError,
        match="Status must be VALID, WARNING, or INVALID",
    ):
        service.get_quality_records_by_status(
            status="UNKNOWN",
        )


def test_get_quality_records_by_date_range(db):
    """Quality records can be filtered by historical date range."""

    market = create_market(db)

    first_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 10),
    )

    second_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 15),
    )

    third_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 20),
    )

    service = DataQualityService(db)

    service.validate_historical_results(
        historical_result_ids=[
            first_result.id,
            second_result.id,
            third_result.id,
        ],
    )

    records = service.get_quality_records_by_date_range(
        start_date=date(2026, 9, 12),
        end_date=date(2026, 9, 18),
    )

    assert len(records) == 1
    assert (
        records[0].historical_result_id
        == second_result.id
    )


def test_invalid_date_range_is_rejected(db):
    """Start date cannot be after end date."""

    service = DataQualityService(db)

    with pytest.raises(
        ValueError,
        match="Start date cannot be after end date",
    ):
        service.get_quality_records_by_date_range(
            start_date=date(2026, 9, 20),
            end_date=date(2026, 9, 10),
        )


def test_count_by_status(db):
    """Status counts should correctly summarize quality records."""

    market = create_market(db)

    first_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 18),
    )

    second_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 9, 19),
    )

    second_result.col8 = 9
    db.commit()

    service = DataQualityService(db)

    service.validate_historical_results(
        historical_result_ids=[
            first_result.id,
            second_result.id,
        ],
    )

    counts = service.count_by_status()

    assert counts["VALID"] == 1
    assert counts["WARNING"] == 0
    assert counts["INVALID"] == 1