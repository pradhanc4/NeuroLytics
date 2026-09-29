from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    build_statistical_baseline_contract,
)
from analytics.statistical_baseline_dataset import (
    build_statistical_baseline_dataset,
)
from analytics.statistical_central_tendency_dispersion import (
    INVALID,
    VALID,
    CentralTendencyDispersion,
    StatisticalCentralTendencyDispersionBaseline,
    build_statistical_central_tendency_dispersion_baseline,
    get_central_tendency_dispersion,
    get_central_tendency_dispersion_positions,
    get_position_mean,
    get_position_median,
    get_position_standard_deviation,
    get_position_variance,
    is_statistical_central_tendency_dispersion_baseline_valid,
    validate_statistical_central_tendency_dispersion_baseline,
    validate_statistical_central_tendency_dispersion_baseline_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def build_dataset():
    observations = tuple(
        StatisticalObservation(
            record_date=date(2026, 1, day),
            column_name="col1",
            value=value,
        )
        for day, value in enumerate(
            (0, 1, 2, 2, 3),
            start=1,
        )
    )

    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        analysis_version="v1",
    )
    result = build_analysis_result(request, observations)

    contract = build_statistical_baseline_contract(
        result=result,
        observations=observations,
        analysis_columns=("col1",),
        baseline_version="v18.7",
    )

    return build_statistical_baseline_dataset(
        contract=contract,
        observations=observations,
    )


def test_builds_from_existing_descriptive_engine():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    assert isinstance(
        baseline,
        StatisticalCentralTendencyDispersionBaseline,
    )
    assert baseline.market_id == 1
    assert baseline.analysis_version == "v1"
    assert baseline.baseline_version == "v18.7"
    assert baseline.positions == ("col1",)


def test_values_are_reused_from_phase_18_3():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )
    item = get_central_tendency_dispersion(
        baseline,
        "col1",
    )

    assert item.count == 5
    assert item.minimum == 0
    assert item.maximum == 3
    assert item.range == 3
    assert item.mean == pytest.approx(1.6)
    assert item.median == 2.0
    assert item.mode == (2,)
    assert item.variance == pytest.approx(1.04)
    assert item.standard_deviation == pytest.approx(
        1.019803902718557
    )


def test_zero_is_preserved():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    assert get_central_tendency_dispersion(
        baseline,
        "col1",
    ).minimum == 0


def test_getters_return_expected_values():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    assert get_position_mean(baseline, "col1") == pytest.approx(1.6)
    assert get_position_median(baseline, "col1") == 2.0
    assert get_position_variance(baseline, "col1") == pytest.approx(1.04)
    assert get_position_standard_deviation(
        baseline,
        "col1",
    ) == pytest.approx(1.019803902718557)


def test_positions_are_deterministic():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    assert get_central_tendency_dispersion_positions(
        baseline
    ) == ("col1",)


def test_validation_accepts_valid_baseline():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    validate_statistical_central_tendency_dispersion_baseline(
        baseline
    )

    validation = (
        validate_statistical_central_tendency_dispersion_baseline_result(
            baseline
        )
    )

    assert validation.status == VALID
    assert validation.is_valid
    assert validation.issue_count == 0
    assert is_statistical_central_tendency_dispersion_baseline_valid(
        baseline
    )


def test_invalid_type_returns_validation_issue():
    validation = (
        validate_statistical_central_tendency_dispersion_baseline_result(
            object()
        )
    )

    assert validation.status == INVALID
    assert not validation.is_valid
    assert validation.issue_count == 1
    assert validation.issues[0].code == "INVALID_BASELINE_TYPE"


def test_negative_count_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=-1,
        mean=None,
        median=None,
        mode=(),
        minimum=None,
        maximum=None,
        range=None,
        variance=None,
        standard_deviation=None,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    with pytest.raises(
        ValueError,
        match="count cannot be negative",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )
def test_empty_statistics_are_valid():
    item = CentralTendencyDispersion(
        position="col1",
        count=0,
        mean=None,
        median=None,
        mode=(),
        minimum=None,
        maximum=None,
        range=None,
        variance=None,
        standard_deviation=None,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    validate_statistical_central_tendency_dispersion_baseline(
        baseline
    )


def test_duplicate_positions_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=0,
        mean=None,
        median=None,
        mode=(),
        minimum=None,
        maximum=None,
        range=None,
        variance=None,
        standard_deviation=None,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item, item),
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_invalid_range_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=1,
        mean=5.0,
        median=5.0,
        mode=(5,),
        minimum=1,
        maximum=5,
        range=99,
        variance=0.0,
        standard_deviation=0.0,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    with pytest.raises(
        ValueError,
        match="range must equal",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_invalid_mode_digit_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=1,
        mean=5.0,
        median=5.0,
        mode=(10,),
        minimum=5,
        maximum=5,
        range=0,
        variance=0.0,
        standard_deviation=0.0,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    with pytest.raises(
        ValueError,
        match="within 0-9",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_invalid_order_rejected():
    first = CentralTendencyDispersion(
        position="col2",
        count=0,
        mean=None,
        median=None,
        mode=(),
        minimum=None,
        maximum=None,
        range=None,
        variance=None,
        standard_deviation=None,
    )
    second = CentralTendencyDispersion(
        position="col1",
        count=0,
        mean=None,
        median=None,
        mode=(),
        minimum=None,
        maximum=None,
        range=None,
        variance=None,
        standard_deviation=None,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(first, second),
    )

    with pytest.raises(
        ValueError,
        match="deterministic order",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_missing_non_empty_measure_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=1,
        mean=None,
        median=5.0,
        mode=(5,),
        minimum=5,
        maximum=5,
        range=0,
        variance=0.0,
        standard_deviation=0.0,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    with pytest.raises(
        ValueError,
        match="require all measures",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_negative_variance_rejected():
    item = CentralTendencyDispersion(
        position="col1",
        count=1,
        mean=5.0,
        median=5.0,
        mode=(5,),
        minimum=5,
        maximum=5,
        range=0,
        variance=-1.0,
        standard_deviation=0.0,
    )
    baseline = StatisticalCentralTendencyDispersionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v18.7",
        statistics=(item,),
    )

    with pytest.raises(
        ValueError,
        match="variance cannot be negative",
    ):
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )


def test_unknown_position_getter_rejected():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        get_central_tendency_dispersion(
            baseline,
            "col8",
        )


def test_result_is_immutable():
    baseline = (
        build_statistical_central_tendency_dispersion_baseline(
            build_dataset()
        )
    )

    with pytest.raises(AttributeError):
        baseline.market_id = 2
