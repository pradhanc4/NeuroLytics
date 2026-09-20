from datetime import date

import pytest

from database.models import HistoricalDataQuality, HistoricalResult, Market
from database.quality_report_service import QualityReportService


def create_market(db, name="Test Market"):
    market = Market(
        name=name,
        is_active=True,
    )

    db.add(market)
    db.commit()
    db.refresh(market)

    return market


def create_result(
    db,
    market_id,
    result_date,
    open_result="123",
    jodi_result="45",
    close_result="678",
):
    digits = (
        open_result
        + jodi_result
        + close_result
    )

    result = HistoricalResult(
        market_id=market_id,
        result_date=result_date,
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
        col1=int(digits[0]),
        col2=int(digits[1]),
        col3=int(digits[2]),
        col4=int(digits[3]),
        col5=int(digits[4]),
        col6=int(digits[5]),
        col7=int(digits[6]),
        col8=int(digits[7]),
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result


def test_generate_market_report_returns_structured_report(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    create_result(
        db,
        market.id,
        date(2026, 9, 20),
    )

    service = QualityReportService(db)

    report = service.generate_market_report(
        market_id=market.id,
    )

    assert report["market"]["id"] == market.id
    assert report["market"]["name"] == "Test Market"

    assert report["validation"]["version"] == "v1"

    assert report["records"]["total"] == 2
    assert report["records"]["valid"] == 2
    assert report["records"]["warning"] == 0
    assert report["records"]["invalid"] == 0

    assert report["quality"]["percentage"] == 100.0
    assert report["quality"]["status"] == "EXCELLENT"

    assert report["dates"]["first"] == date(2026, 9, 18)
    assert report["dates"]["last"] == date(2026, 9, 20)

    assert report["dates"]["missing_calendar_dates"] == [
        date(2026, 9, 19),
    ]


def test_generate_market_report_detects_invalid_record(db):
    market = create_market(db)

    valid_result = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    invalid_result = create_result(
        db,
        market.id,
        date(2026, 9, 19),
    )

    invalid_result.col8 = 9

    db.commit()

    service = QualityReportService(db)

    report = service.generate_market_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 2
    assert report["records"]["valid"] == 1
    assert report["records"]["invalid"] == 1

    assert report["quality"]["percentage"] == 50.0
    assert report["quality"]["status"] == "NEEDS_REVIEW"

    assert (
        invalid_result.id
        in report["issues"]["invalid_record_ids"]
    )

    assert (
        valid_result.id
        not in report["issues"]["invalid_record_ids"]
    )


def test_generate_stored_report_returns_unchecked_records(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    create_result(
        db,
        market.id,
        date(2026, 9, 19),
    )

    service = QualityReportService(db)

    report = service.generate_stored_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 2
    assert report["records"]["checked"] == 0
    assert report["records"]["unchecked"] == 2
    assert report["records"]["valid"] == 0
    assert report["records"]["invalid"] == 0
    assert report["quality"]["percentage"] == 0.0
    assert report["quality"]["status"] == "NEEDS_REVIEW"


def test_generate_stored_report_uses_existing_quality_records(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    quality_record = HistoricalDataQuality(
        historical_result_id=result.id,
        validation_version="v1",
        status="VALID",
        issue_count=0,
        issue_summary=None,
    )

    db.add(quality_record)
    db.commit()

    service = QualityReportService(db)

    report = service.generate_stored_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 1
    assert report["records"]["checked"] == 1
    assert report["records"]["unchecked"] == 0
    assert report["records"]["valid"] == 1
    assert report["records"]["invalid"] == 0
    assert report["quality"]["percentage"] == 100.0
    assert report["quality"]["status"] == "EXCELLENT"


@pytest.mark.parametrize(
    "percentage, expected_status",
    [
        (100.0, "EXCELLENT"),
        (99.0, "EXCELLENT"),
        (98.99, "GOOD"),
        (95.0, "GOOD"),
        (94.99, "FAIR"),
        (90.0, "FAIR"),
        (89.99, "NEEDS_REVIEW"),
        (50.0, "NEEDS_REVIEW"),
        (0.0, "NEEDS_REVIEW"),
    ],
)
def test_quality_status_categories(
    percentage,
    expected_status,
):
    assert (
        QualityReportService._get_quality_status(
            percentage
        )
        == expected_status
    )


def test_format_date():
    assert (
        QualityReportService.format_date(
            date(2026, 9, 20)
        )
        == "2026-09-20"
    )


def test_format_date_handles_none():
    assert (
        QualityReportService.format_date(None)
        is None
    )


def test_generate_display_report_converts_dates_to_strings(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    create_result(
        db,
        market.id,
        date(2026, 9, 20),
    )

    service = QualityReportService(db)

    report = service.generate_display_report(
        market_id=market.id,
    )

    assert report["dates"]["first"] == "2026-09-18"
    assert report["dates"]["last"] == "2026-09-20"

    assert report["dates"]["missing_calendar_dates"] == [
        "2026-09-19",
    ]


def test_generate_market_report_rejects_unknown_market(db):
    service = QualityReportService(db)

    with pytest.raises(
        ValueError,
        match="Market was not found",
    ):
        service.generate_market_report(
            market_id=999999,
        )


def test_generate_market_report_rejects_empty_version(db):
    market = create_market(db)

    service = QualityReportService(db)

    with pytest.raises(
        ValueError,
        match="Validation version is required",
    ):
        service.generate_market_report(
            market_id=market.id,
            validation_version="   ",
        )