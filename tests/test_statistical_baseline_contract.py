from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    ANALYSIS_COLUMNS,
    INVALID,
    VALID,
    StatisticalBaselineContract,
    StatisticalBaselineValidationResult,
    build_statistical_baseline_contract,
    build_statistical_baseline_contract_from_observations,
    get_baseline_analysis_columns,
    get_baseline_analysis_version,
    get_baseline_column_observation_counts,
    get_baseline_market_id,
    get_baseline_observation_count,
    get_baseline_validation_issues,
    get_baseline_validation_status,
    get_baseline_version,
    is_statistical_baseline_contract_valid,
    validate_statistical_baseline_contract,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def build_result():
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
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col2",
            value=7,
        ),
    ]

    return build_analysis_result(
        request,
        observations,
    )


def build_observations():
    return [
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
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col2",
            value=7,
        ),
    ]


def test_build_baseline_contract():
    contract = build_statistical_baseline_contract(
        result=build_result(),
        observations=build_observations(),
        analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )

    assert contract.market_id == 1
    assert contract.analysis_version == "v1"
    assert contract.baseline_version == "v1"
    assert contract.start_date == date(2026, 1, 1)
    assert contract.end_date == date(2026, 1, 10)
    assert contract.analysis_columns == (
        "col1",
        "col2",
    )
    assert contract.observation_count == 3
    assert contract.column_observation_counts == (
        ("col1", 2),
        ("col2", 1),
    )


def test_zero_is_counted_as_observation():
    contract = build_statistical_baseline_contract(
        result=build_result(),
        observations=build_observations(),
        analysis_columns=("col1", "col2"),
    )

    counts = dict(
        contract.column_observation_counts
    )

    assert counts["col1"] == 2


def test_default_builder_uses_all_analysis_columns():
    contract = build_statistical_baseline_contract_from_observations(
        result=build_result(),
        observations=build_observations(),
    )

    assert contract.analysis_columns == ANALYSIS_COLUMNS
    assert contract.observation_count == 3


def test_default_builder_preserves_zero():
    contract = build_statistical_baseline_contract_from_observations(
        result=build_result(),
        observations=build_observations(),
    )

    counts = dict(
        contract.column_observation_counts
    )

    assert counts["col1"] == 2


def test_valid_contract():
    contract = build_statistical_baseline_contract(
        result=build_result(),
        observations=build_observations(),
        analysis_columns=("col1", "col2"),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == VALID
    assert validation.is_valid
    assert validation.issue_count == 0


def test_invalid_market_id():
    contract = StatisticalBaselineContract(
        market_id=0,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1",),
        observation_count=1,
        column_observation_counts=(("col1", 1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "INVALID_MARKET_ID"
        for issue in validation.issues
    )


def test_invalid_analysis_version():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1",),
        observation_count=1,
        column_observation_counts=(("col1", 1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "INVALID_ANALYSIS_VERSION"
        for issue in validation.issues
    )


def test_invalid_baseline_version():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="",
        start_date=None,
        end_date=None,
        analysis_columns=("col1",),
        observation_count=1,
        column_observation_counts=(("col1", 1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "INVALID_BASELINE_VERSION"
        for issue in validation.issues
    )


def test_invalid_date_range():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 1, 1),
        analysis_columns=("col1",),
        observation_count=1,
        column_observation_counts=(("col1", 1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "INVALID_DATE_RANGE"
        for issue in validation.issues
    )


def test_unsupported_analysis_column():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("invalid",),
        observation_count=1,
        column_observation_counts=(("invalid", 1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "UNSUPPORTED_ANALYSIS_COLUMN"
        for issue in validation.issues
    )


def test_duplicate_analysis_columns():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1", "col1"),
        observation_count=2,
        column_observation_counts=(
            ("col1", 1),
            ("col1", 1),
        ),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "DUPLICATE_ANALYSIS_COLUMNS"
        for issue in validation.issues
    )


def test_negative_observation_count():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1",),
        observation_count=-1,
        column_observation_counts=(("col1", -1),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "INVALID_OBSERVATION_COUNT"
        for issue in validation.issues
    )


def test_observation_count_mismatch():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1",),
        observation_count=5,
        column_observation_counts=(("col1", 2),),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "OBSERVATION_COUNT_MISMATCH"
        for issue in validation.issues
    )


def test_column_order_mismatch():
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=None,
        end_date=None,
        analysis_columns=("col1", "col2"),
        observation_count=3,
        column_observation_counts=(
            ("col2", 1),
            ("col1", 2),
        ),
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert validation.status == INVALID
    assert any(
        issue.code == "COLUMN_COUNT_ALIGNMENT_MISMATCH"
        for issue in validation.issues
    )


def test_builder_rejects_unknown_observation_column():
    observations = [
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col3",
            value=5,
        ),
    ]

    with pytest.raises(ValueError, match="not included"):
        build_statistical_baseline_contract(
            result=build_result(),
            observations=observations,
            analysis_columns=("col1",),
        )


def test_builder_rejects_wrong_observation_type():
    with pytest.raises(
        TypeError,
        match="StatisticalObservation",
    ):
        build_statistical_baseline_contract(
            result=build_result(),
            observations=[object()],
            analysis_columns=("col1",),
        )


def test_builder_rejects_invalid_result_type():
    with pytest.raises(
        TypeError,
        match="StatisticalAnalysisResult",
    ):
        build_statistical_baseline_contract(
            result=object(),
            observations=[],
        )


def test_baseline_version_is_preserved():
    contract = build_statistical_baseline_contract(
        result=build_result(),
        observations=build_observations(),
        analysis_columns=("col1", "col2"),
        baseline_version="v18.1",
    )

    assert contract.baseline_version == "v18.1"


def test_getters():
    contract = build_statistical_baseline_contract(
        result=build_result(),
        observations=build_observations(),
        analysis_columns=("col1", "col2"),
        baseline_version="v18.1",
    )

    validation = validate_statistical_baseline_contract(
        contract
    )

    assert get_baseline_market_id(contract) == 1
    assert get_baseline_analysis_version(contract) == "v1"
    assert get_baseline_version(contract) == "v18.1"
    assert get_baseline_analysis_columns(contract) == (
        "col1",
        "col2",
    )
    assert get_baseline_observation_count(contract) == 3
    assert get_baseline_column_observation_counts(
        contract
    ) == (
        ("col1", 2),
        ("col2", 1),
    )
    assert get_baseline_validation_status(validation) == VALID
    assert get_baseline_validation_issues(validation) == ()
    assert is_statistical_baseline_contract_valid(
        validation
    )


def test_validation_result_is_immutable():
    result = StatisticalBaselineValidationResult(
        status=VALID,
        issues=(),
    )

    with pytest.raises(
        AttributeError
    ):
        result.status = INVALID