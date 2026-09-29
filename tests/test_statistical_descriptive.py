from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    build_statistical_baseline_contract,
)
from analytics.statistical_baseline_dataset import (
    build_statistical_baseline_dataset,
)
from analytics.statistical_descriptive import (
    INVALID,
    VALID,
    DescriptiveStatistics,
    StatisticalDescriptiveResult,
    StatisticalDescriptiveValidationResult,
    build_statistical_descriptive_result,
    build_statistical_descriptive_result_from_observations,
    get_column_descriptive_statistics,
    get_descriptive_column_names,
    get_descriptive_statistics,
    is_statistical_descriptive_result_valid,
    validate_descriptive_statistics,
    validate_statistical_descriptive_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def build_observations():
    return (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=1,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=2,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col1",
            value=2,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 4),
            column_name="col1",
            value=3,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 5),
            column_name="col1",
            value=0,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col2",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col2",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col2",
            value=7,
        ),
    )


def build_dataset():
    observations = build_observations()

    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        analysis_version="v1",
    )

    result = build_analysis_result(
        request,
        observations,
    )

    contract = build_statistical_baseline_contract(
        result=result,
        observations=observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v18.2",
    )

    return build_statistical_baseline_dataset(
        contract=contract,
        observations=observations,
    )


def test_build_descriptive_result():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    assert isinstance(
        result,
        StatisticalDescriptiveResult,
    )

    assert result.market_id == 1
    assert result.analysis_version == "v1"
    assert result.baseline_version == "v18.2"
    assert result.column_count == 2


def test_columns_are_deterministic():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    assert result.columns == (
        "col1",
        "col2",
    )


def test_col1_count():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.count == 5


def test_col1_minimum():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.minimum == 0


def test_col1_maximum():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.maximum == 3


def test_col1_range():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.range == 3


def test_col1_mean():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.mean == pytest.approx(1.6)


def test_col1_median():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.median == 2.0


def test_col1_mode():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.mode == (2,)


def test_col1_population_variance():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.variance == pytest.approx(
        1.04
    )


def test_col1_population_standard_deviation():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.standard_deviation == pytest.approx(
        1.019803902718557
    )


def test_zero_is_included_in_statistics():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.minimum == 0
    assert statistic.count == 5


def test_multiple_modes_are_deterministic():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=1,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=2,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col1",
            value=1,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 4),
            column_name="col1",
            value=2,
        ),
    )

    result = build_statistical_descriptive_result_from_observations(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        observations=observations,
        columns=("col1",),
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.mode == (
        1,
        2,
    )


def test_all_values_equal():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col1",
            value=5,
        ),
    )

    result = build_statistical_descriptive_result_from_observations(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        observations=observations,
        columns=("col1",),
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.count == 3
    assert statistic.minimum == 5
    assert statistic.maximum == 5
    assert statistic.range == 0
    assert statistic.mean == 5.0
    assert statistic.median == 5.0
    assert statistic.mode == (5,)
    assert statistic.variance == 0.0
    assert statistic.standard_deviation == 0.0


def test_empty_column_statistics():
    result = build_statistical_descriptive_result_from_observations(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        observations=(),
        columns=("col1",),
    )

    statistic = get_column_descriptive_statistics(
        result,
        "col1",
    )

    assert statistic.count == 0
    assert statistic.minimum is None
    assert statistic.maximum is None
    assert statistic.range is None
    assert statistic.mean is None
    assert statistic.median is None
    assert statistic.mode == ()
    assert statistic.variance is None
    assert statistic.standard_deviation is None


def test_get_all_statistics():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    statistics = get_descriptive_statistics(
        result
    )

    assert len(statistics) == 2
    assert all(
        isinstance(
            statistic,
            DescriptiveStatistics,
        )
        for statistic in statistics
    )


def test_get_column_names():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    assert get_descriptive_column_names(
        result
    ) == (
        "col1",
        "col2",
    )


def test_valid_result():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    validate_descriptive_statistics(
        result
    )

    assert is_statistical_descriptive_result_valid(
        result
    )


def test_validation_result_is_valid():
    result = build_statistical_descriptive_result(
        build_dataset()
    )

    validation = validate_statistical_descriptive_result(
        result
    )

    assert validation.status == VALID
    assert validation.is_valid
    assert validation.issue_count == 0


def test_invalid_result_type():
    validation = validate_statistical_descriptive_result(
        object()
    )

    assert validation.status == INVALID
    assert not validation.is_valid
    assert validation.issue_count == 1
    assert (
        validation.issues[0].code
        == "INVALID_RESULT_TYPE"
    )


def test_invalid_market_id():
    result = StatisticalDescriptiveResult(
        market_id=0,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(),
    )

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        validate_descriptive_statistics(
            result
        )


def test_invalid_analysis_version():
    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="",
        baseline_version="v18.2",
        statistics=(),
    )

    with pytest.raises(
        ValueError,
        match="analysis_version",
    ):
        validate_descriptive_statistics(
            result
        )


def test_invalid_baseline_version():
    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="",
        statistics=(),
    )

    with pytest.raises(
        ValueError,
        match="baseline_version",
    ):
        validate_descriptive_statistics(
            result
        )


def test_negative_count():
    statistic = DescriptiveStatistics(
        column_name="col1",
        count=-1,
        minimum=None,
        maximum=None,
        range=None,
        mean=None,
        median=None,
        mode=(),
        variance=None,
        standard_deviation=None,
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(statistic,),
    )

    with pytest.raises(
        ValueError,
        match="count cannot be negative",
    ):
        validate_descriptive_statistics(
            result
        )


def test_non_empty_statistics_require_minimum():
    statistic = DescriptiveStatistics(
        column_name="col1",
        count=1,
        minimum=None,
        maximum=5,
        range=0,
        mean=5.0,
        median=5.0,
        mode=(5,),
        variance=0.0,
        standard_deviation=0.0,
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(statistic,),
    )

    with pytest.raises(
        ValueError,
        match="require a minimum",
    ):
        validate_descriptive_statistics(
            result
        )


def test_range_must_match_minimum_and_maximum():
    statistic = DescriptiveStatistics(
        column_name="col1",
        count=2,
        minimum=1,
        maximum=5,
        range=99,
        mean=3.0,
        median=3.0,
        mode=(1, 5),
        variance=4.0,
        standard_deviation=2.0,
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(statistic,),
    )

    with pytest.raises(
        ValueError,
        match="range must equal",
    ):
        validate_descriptive_statistics(
            result
        )


def test_negative_variance_rejected():
    statistic = DescriptiveStatistics(
        column_name="col1",
        count=2,
        minimum=1,
        maximum=5,
        range=4,
        mean=3.0,
        median=3.0,
        mode=(1, 5),
        variance=-1.0,
        standard_deviation=0.0,
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(statistic,),
    )

    with pytest.raises(
        ValueError,
        match="variance cannot be negative",
    ):
        validate_descriptive_statistics(
            result
        )


def test_non_empty_statistics_require_mode():
    statistic = DescriptiveStatistics(
        column_name="col1",
        count=2,
        minimum=1,
        maximum=5,
        range=4,
        mean=3.0,
        median=3.0,
        mode=(),
        variance=4.0,
        standard_deviation=2.0,
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=(statistic,),
    )

    with pytest.raises(
        ValueError,
        match="require at least one mode",
    ):
        validate_descriptive_statistics(
            result
        )


def test_statistics_columns_must_be_deterministically_ordered():
    statistics = (
        DescriptiveStatistics(
            column_name="col2",
            count=1,
            minimum=5,
            maximum=5,
            range=0,
            mean=5.0,
            median=5.0,
            mode=(5,),
            variance=0.0,
            standard_deviation=0.0,
        ),
        DescriptiveStatistics(
            column_name="col1",
            count=1,
            minimum=1,
            maximum=1,
            range=0,
            mean=1.0,
            median=1.0,
            mode=(1,),
            variance=0.0,
            standard_deviation=0.0,
        ),
    )

    result = StatisticalDescriptiveResult(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.2",
        statistics=statistics,
    )

    with pytest.raises(
        ValueError,
        match="deterministic order",
    ):
        validate_descriptive_statistics(
            result
        )


def test_invalid_observation_type_in_direct_builder():
    with pytest.raises(
        TypeError,
        match="StatisticalObservation",
    ):
        build_statistical_descriptive_result_from_observations(
            market_id=1,
            analysis_version="v1",
            baseline_version="v18.2",
            observations=(object(),),
            columns=("col1",),
        )


def test_unknown_observation_column_in_direct_builder():
    observation = StatisticalObservation(
        record_date=date(2026, 1, 1),
        column_name="col2",
        value=5,
    )

    with pytest.raises(
        ValueError,
        match="not included",
    ):
        build_statistical_descriptive_result_from_observations(
            market_id=1,
            analysis_version="v1",
            baseline_version="v18.2",
            observations=(observation,),
            columns=("col1",),
        )


def test_validation_result_is_immutable():
    result = StatisticalDescriptiveValidationResult(
        status=VALID,
        issues=(),
    )

    with pytest.raises(
        AttributeError
    ):
        result.status = INVALID