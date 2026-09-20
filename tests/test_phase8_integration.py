from datetime import date

import pytest

from database.data_quality_rules import (
    DataQualityValidationError,
    validate_historical_record,
)
from database.data_quality_service import (
    DataQualityService,
)
from database.historical_quality_checker import (
    HistoricalQualityChecker,
)
from database.models import (
    HistoricalDataQuality,
    HistoricalResult,
    Market,
)
from database.quality_report_service import (
    QualityReportService,
)


def create_market(db, name="Integration Market"):
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


def test_phase8_valid_record_passes_complete_pipeline(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    columns = {
        "col1": result.col1,
        "col2": result.col2,
        "col3": result.col3,
        "col4": result.col4,
        "col5": result.col5,
        "col6": result.col6,
        "col7": result.col7,
        "col8": result.col8,
    }

    validate_historical_record(
        market_id=result.market_id,
        result_date=result.result_date,
        open_result=result.open_result,
        jodi_result=result.jodi_result,
        close_result=result.close_result,
        columns=columns,
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=result.id,
    )

    assert quality_record.status == "VALID"
    assert quality_record.issue_count == 0
    assert quality_record.issue_summary is None

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 1
    assert summary["valid_records"] == 1
    assert summary["invalid_records"] == 0
    assert summary["quality_percentage"] == 100.0

    report_service = QualityReportService(db)

    report = report_service.generate_market_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 1
    assert report["records"]["valid"] == 1
    assert report["records"]["invalid"] == 0
    assert report["quality"]["percentage"] == 100.0
    assert report["quality"]["status"] == "EXCELLENT"


def test_phase8_leading_zero_record_remains_valid(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 19),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=result.id,
    )

    assert quality_record.status == "VALID"

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
    ] == [
        0,
        0,
        5,
        0,
        5,
        0,
        0,
        7,
    ]


def test_phase8_actual_zero_values_remain_valid(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 20),
        open_result="000",
        jodi_result="00",
        close_result="000",
    )

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=result.id,
    )

    assert quality_record.status == "VALID"
    assert quality_record.issue_count == 0

    assert [
        result.col1,
        result.col2,
        result.col3,
        result.col4,
        result.col5,
        result.col6,
        result.col7,
        result.col8,
    ] == [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]


def test_phase8_invalid_derived_column_flows_to_report(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 21),
    )

    result.col4 = 9

    db.commit()

    service = DataQualityService(db)

    quality_record = service.validate_historical_result(
        historical_result_id=result.id,
    )

    assert quality_record.status == "INVALID"
    assert quality_record.issue_count == 1
    assert quality_record.issue_summary is not None

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 1
    assert summary["valid_records"] == 0
    assert summary["invalid_records"] == 1
    assert summary["quality_percentage"] == 0.0

    assert result.id in summary["invalid_record_ids"]

    report_service = QualityReportService(db)

    report = report_service.generate_market_report(
        market_id=market.id,
    )

    assert report["records"]["invalid"] == 1
    assert report["quality"]["percentage"] == 0.0
    assert report["quality"]["status"] == "NEEDS_REVIEW"

    assert (
        result.id
        in report["issues"]["invalid_record_ids"]
    )


def test_phase8_missing_calendar_date_is_reported_not_invalid(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 9, 22),
    )

    create_result(
        db,
        market.id,
        date(2026, 9, 24),
    )

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 2
    assert summary["valid_records"] == 2
    assert summary["invalid_records"] == 0

    assert summary["date_analysis"][
        "missing_calendar_dates"
    ] == [
        date(2026, 9, 23),
    ]

    report_service = QualityReportService(db)

    report = report_service.generate_display_report(
        market_id=market.id,
    )

    assert report["quality"]["percentage"] == 100.0

    assert report["dates"][
        "missing_calendar_dates"
    ] == [
        "2026-09-23",
    ]


def test_phase8_multiple_records_produce_correct_summary(db):
    market = create_market(db)

    valid_1 = create_result(
        db,
        market.id,
        date(2026, 9, 25),
    )

    valid_2 = create_result(
        db,
        market.id,
        date(2026, 9, 26),
    )

    invalid_1 = create_result(
        db,
        market.id,
        date(2026, 9, 27),
    )

    invalid_1.col8 = 9

    valid_3 = create_result(
        db,
        market.id,
        date(2026, 9, 28),
    )

    db.commit()

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 4
    assert summary["valid_records"] == 3
    assert summary["warning_records"] == 0
    assert summary["invalid_records"] == 1

    assert summary["quality_percentage"] == 75.0

    assert (
        invalid_1.id
        in summary["invalid_record_ids"]
    )

    assert (
        valid_1.id
        not in summary["invalid_record_ids"]
    )

    assert (
        valid_2.id
        not in summary["invalid_record_ids"]
    )

    assert (
        valid_3.id
        not in summary["invalid_record_ids"]
    )

    report_service = QualityReportService(db)

    report = report_service.generate_stored_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 4
    assert report["records"]["checked"] == 4
    assert report["records"]["unchecked"] == 0
    assert report["records"]["valid"] == 3
    assert report["records"]["invalid"] == 1
    assert report["quality"]["percentage"] == 75.0
    assert report["quality"]["status"] == "NEEDS_REVIEW"


def test_phase8_revalidation_preserves_single_quality_record(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 29),
    )

    service = DataQualityService(db)

    first = service.validate_historical_result(
        historical_result_id=result.id,
    )

    second = service.validate_historical_result(
        historical_result_id=result.id,
    )

    records = (
        db.query(HistoricalDataQuality)
        .filter(
            HistoricalDataQuality.historical_result_id
            == result.id
        )
        .all()
    )

    assert first.id == second.id
    assert len(records) == 1


def test_phase8_validation_version_creates_independent_quality_records(
    db,
):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 30),
    )

    service = DataQualityService(db)

    first = service.validate_historical_result(
        historical_result_id=result.id,
        validation_version="v1",
    )

    second = service.validate_historical_result(
        historical_result_id=result.id,
        validation_version="v2",
    )

    assert first.id != second.id

    records = (
        db.query(HistoricalDataQuality)
        .filter(
            HistoricalDataQuality.historical_result_id
            == result.id
        )
        .order_by(
            HistoricalDataQuality.validation_version
        )
        .all()
    )

    assert len(records) == 2

    assert [
        record.validation_version
        for record in records
    ] == [
        "v1",
        "v2",
    ]


def test_phase8_unchecked_records_disappear_after_validation(
    db,
):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 10, 1),
    )

    create_result(
        db,
        market.id,
        date(2026, 10, 2),
    )

    checker = HistoricalQualityChecker(db)

    unchecked_before = checker.get_unchecked_results(
        market_id=market.id,
    )

    assert len(unchecked_before) == 2

    checker.validate_market_history(
        market_id=market.id,
    )

    unchecked_after = checker.get_unchecked_results(
        market_id=market.id,
    )

    assert unchecked_after == []


def test_phase8_display_report_is_frontend_friendly(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 10, 3),
    )

    service = QualityReportService(db)

    report = service.generate_display_report(
        market_id=market.id,
    )

    assert isinstance(
        report["dates"]["first"],
        str,
    )

    assert isinstance(
        report["dates"]["last"],
        str,
    )

    assert report["dates"]["first"] == "2026-10-03"
    assert report["dates"]["last"] == "2026-10-03"


def test_phase8_invalid_rule_input_raises_expected_error():
    with pytest.raises(
        DataQualityValidationError
    ):
        validate_historical_record(
            market_id=1,
            result_date=date(2026, 10, 4),
            open_result="12",
            jodi_result="45",
            close_result="678",
            columns={
                "col1": 1,
                "col2": 2,
                "col3": 3,
                "col4": 4,
                "col5": 5,
                "col6": 6,
                "col7": 7,
                "col8": 8,
            },
        )


def test_phase8_unknown_market_fails_through_checker(db):
    checker = HistoricalQualityChecker(db)

    with pytest.raises(
        ValueError,
        match="Market was not found",
    ):
        checker.validate_market_history(
            market_id=999999,
        )


def test_phase8_empty_history_produces_zero_quality_report(db):
    market = create_market(db)

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 0
    assert summary["valid_records"] == 0
    assert summary["warning_records"] == 0
    assert summary["invalid_records"] == 0
    assert summary["quality_percentage"] == 0.0

    report_service = QualityReportService(db)

    report = report_service.generate_market_report(
        market_id=market.id,
    )

    assert report["records"]["total"] == 0
    assert report["records"]["valid"] == 0
    assert report["records"]["invalid"] == 0
    assert report["quality"]["percentage"] == 0.0
    assert report["quality"]["status"] == "NEEDS_REVIEW"


def test_phase8_quality_report_does_not_modify_historical_values(
    db,
):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 10, 5),
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    original_values = {
        "open": result.open_result,
        "jodi": result.jodi_result,
        "close": result.close_result,
        "cols": [
            result.col1,
            result.col2,
            result.col3,
            result.col4,
            result.col5,
            result.col6,
            result.col7,
            result.col8,
        ],
    }

    report_service = QualityReportService(db)

    report_service.generate_market_report(
        market_id=market.id,
    )

    db.refresh(result)

    assert result.open_result == original_values["open"]
    assert result.jodi_result == original_values["jodi"]
    assert result.close_result == original_values["close"]

    assert [
        result.col1,
        result.col2,
        result.col3,
        result.col4,
        result.col5,
        result.col6,
        result.col7,
        result.col8,
    ] == original_values["cols"]