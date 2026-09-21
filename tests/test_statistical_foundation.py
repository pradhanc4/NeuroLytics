from datetime import date

import pytest

from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
    extract_observations,
    validate_analysis_column,
    validate_analysis_request,
)


class MockHistoricalRecord:
    def __init__(
        self,
        result_date,
        col1=None,
        col2=None,
        col3=None,
        col4=None,
        col5=None,
        col6=None,
        col7=None,
        col8=None,
    ):
        self.result_date = result_date
        self.col1 = col1
        self.col2 = col2
        self.col3 = col3
        self.col4 = col4
        self.col5 = col5
        self.col6 = col6
        self.col7 = col7
        self.col8 = col8


def test_analysis_columns_are_defined():
    assert ANALYSIS_COLUMNS == (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    )


def test_valid_analysis_request():
    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    validate_analysis_request(request)


def test_market_id_must_be_positive():
    request = StatisticalAnalysisRequest(
        market_id=0,
    )

    with pytest.raises(ValueError, match="greater than zero"):
        validate_analysis_request(request)


def test_analysis_version_is_required():
    request = StatisticalAnalysisRequest(
        market_id=1,
        analysis_version="",
    )

    with pytest.raises(ValueError, match="analysis_version"):
        validate_analysis_request(request)


def test_start_date_cannot_be_after_end_date():
    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 1, 1),
    )

    with pytest.raises(ValueError, match="later than"):
        validate_analysis_request(request)


def test_supported_analysis_column():
    validate_analysis_column("col1")
    validate_analysis_column("col8")


def test_unsupported_analysis_column():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_analysis_column("open_result")


def test_extract_integer_observations():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=1,
        ),
        MockHistoricalRecord(
            result_date=date(2026, 1, 2),
            col1=7,
        ),
    ]

    observations = extract_observations(
        records,
        "col1",
    )

    assert observations == [
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=1,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=7,
        ),
    ]


def test_actual_zero_is_preserved():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=0,
        ),
    ]

    observations = extract_observations(
        records,
        "col1",
    )

    assert len(observations) == 1
    assert observations[0].value == 0


def test_null_is_not_converted_to_zero():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=None,
        ),
    ]

    observations = extract_observations(
        records,
        "col1",
    )

    assert observations == []


def test_invalid_digit_value_is_rejected():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=10,
        ),
    ]

    with pytest.raises(ValueError, match="0-9"):
        extract_observations(records, "col1")


def test_negative_digit_value_is_rejected():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=-1,
        ),
    ]

    with pytest.raises(ValueError, match="0-9"):
        extract_observations(records, "col1")


def test_boolean_value_is_rejected():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1=True,
        ),
    ]

    with pytest.raises(ValueError, match="boolean"):
        extract_observations(records, "col1")


def test_non_integer_value_is_rejected():
    records = [
        MockHistoricalRecord(
            result_date=date(2026, 1, 1),
            col1="5",
        ),
    ]

    with pytest.raises(ValueError, match="integer"):
        extract_observations(records, "col1")


def test_missing_record_date_is_rejected():
    records = [
        MockHistoricalRecord(
            result_date=None,
            col1=5,
        ),
    ]

    with pytest.raises(ValueError, match="result_date"):
        extract_observations(records, "col1")


def test_build_analysis_result():
    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        analysis_version="v1",
    )

    observations = [
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=0,
        ),
    ]

    result = build_analysis_result(
        request,
        observations,
    )

    assert result.market_id == 1
    assert result.analysis_version == "v1"
    assert result.start_date == date(2026, 1, 1)
    assert result.end_date == date(2026, 1, 10)
    assert result.observation_count == 2


def test_empty_observations_are_supported():
    request = StatisticalAnalysisRequest(
        market_id=1,
    )

    result = build_analysis_result(
        request,
        [],
    )

    assert result.observation_count == 0
