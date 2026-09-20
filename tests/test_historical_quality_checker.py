from datetime import date

import pytest

from database.historical_quality_checker import (
    HistoricalQualityChecker,
)
from database.models import (
    HistoricalDataQuality,
    HistoricalResult,
    Market,
)


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


def test_get_historical_results_returns_records_in_date_order(db):
    market = create_market(db)

    create_result(
        db,
        market.id,
        date(2026, 9, 20),
    )

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

    checker = HistoricalQualityChecker(db)

    results = checker.get_historical_results(
        market_id=market.id,
    )

    assert len(results) == 3

    assert [
        result.result_date
        for result in results
    ] == [
        date(2026, 9, 18),
        date(2026, 9, 19),
        date(2026, 9, 20),
    ]


def test_get_historical_results_rejects_invalid_market_id(db):
    checker = HistoricalQualityChecker(db)

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        checker.get_historical_results(
            market_id=0,
        )


def test_validate_market_history_marks_valid_records(db):
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
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 2
    assert summary["valid_records"] == 2
    assert summary["warning_records"] == 0
    assert summary["invalid_records"] == 0
    assert summary["quality_percentage"] == 100.0
    assert summary["invalid_record_ids"] == []

    quality_records = (
        db.query(HistoricalDataQuality)
        .all()
    )

    assert len(quality_records) == 2


def test_validate_market_history_detects_invalid_record(db):
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

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["total_records"] == 2
    assert summary["valid_records"] == 1
    assert summary["invalid_records"] == 1
    assert summary["quality_percentage"] == 50.0

    assert (
        invalid_result.id
        in summary["invalid_record_ids"]
    )

    assert (
        valid_result.id
        not in summary["invalid_record_ids"]
    )


def test_validate_market_history_revalidation_does_not_create_duplicates(db):
    market = create_market(db)

    result = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    checker = HistoricalQualityChecker(db)

    checker.validate_market_history(
        market_id=market.id,
    )

    checker.validate_market_history(
        market_id=market.id,
    )

    quality_records = (
        db.query(HistoricalDataQuality)
        .filter(
            HistoricalDataQuality.historical_result_id
            == result.id
        )
        .all()
    )

    assert len(quality_records) == 1


def test_analyze_dates_detects_missing_calendar_dates(db):
    market = create_market(db)

    result_1 = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    result_2 = create_result(
        db,
        market.id,
        date(2026, 9, 20),
    )

    checker = HistoricalQualityChecker(db)

    analysis = checker.analyze_dates(
        [
            result_1,
            result_2,
        ]
    )

    assert analysis["record_count"] == 2

    assert (
        analysis["first_date"]
        == date(2026, 9, 18)
    )

    assert (
        analysis["last_date"]
        == date(2026, 9, 20)
    )

    assert analysis["missing_calendar_dates"] == [
        date(2026, 9, 19),
    ]


def test_analyze_dates_does_not_mark_missing_dates_as_invalid(db):
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

    checker = HistoricalQualityChecker(db)

    summary = checker.validate_market_history(
        market_id=market.id,
    )

    assert summary["invalid_records"] == 0

    assert (
        summary["date_analysis"][
            "missing_calendar_dates"
        ]
        == [
            date(2026, 9, 19),
        ]
    )


def test_analyze_dates_handles_empty_history(db):
    checker = HistoricalQualityChecker(db)

    analysis = checker.analyze_dates([])

    assert analysis == {
        "record_count": 0,
        "first_date": None,
        "last_date": None,
        "duplicate_dates": [],
        "missing_calendar_dates": [],
    }


def test_get_unchecked_results_returns_unvalidated_records(db):
    market = create_market(db)

    result_1 = create_result(
        db,
        market.id,
        date(2026, 9, 18),
    )

    result_2 = create_result(
        db,
        market.id,
        date(2026, 9, 19),
    )

    checker = HistoricalQualityChecker(db)

    unchecked = checker.get_unchecked_results(
        market_id=market.id,
    )

    assert [
        result.id
        for result in unchecked
    ] == [
        result_1.id,
        result_2.id,
    ]

    checker.validate_market_history(
        market_id=market.id,
    )

    unchecked_after_validation = (
        checker.get_unchecked_results(
            market_id=market.id,
        )
    )

    assert unchecked_after_validation == []


def test_get_quality_summary_works_without_revalidation(db):
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

    checker = HistoricalQualityChecker(db)

    before_validation = checker.get_quality_summary(
        market_id=market.id,
    )

    assert before_validation["total_records"] == 2
    assert before_validation["checked_records"] == 0
    assert before_validation["unchecked_records"] == 2

    checker.validate_market_history(
        market_id=market.id,
    )

    after_validation = checker.get_quality_summary(
        market_id=market.id,
    )

    assert after_validation["total_records"] == 2
    assert after_validation["checked_records"] == 2
    assert after_validation["unchecked_records"] == 0
    assert after_validation["valid_records"] == 2
    assert after_validation["warning_records"] == 0
    assert after_validation["invalid_records"] == 0
    assert after_validation["quality_percentage"] == 100.0


def test_validate_market_history_rejects_unknown_market(db):
    checker = HistoricalQualityChecker(db)

    with pytest.raises(
        ValueError,
        match="Market was not found",
    ):
        checker.validate_market_history(
            market_id=999999,
        )


def test_validate_market_history_rejects_empty_version(db):
    market = create_market(db)

    checker = HistoricalQualityChecker(db)

    with pytest.raises(
        ValueError,
        match="Validation version is required",
    ):
        checker.validate_market_history(
            market_id=market.id,
            validation_version="   ",
        )
