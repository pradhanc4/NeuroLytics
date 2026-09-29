from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    build_statistical_baseline_contract,
)
from analytics.statistical_baseline_dataset import (
    build_statistical_baseline_dataset,
)
from analytics.statistical_distribution_baseline import (
    INVALID,
    VALID,
    StatisticalDistributionBaseline,
    StatisticalDistributionBaselineValidationResult,
    build_statistical_distribution_baseline,
    get_distribution_baseline,
    get_distribution_baseline_percentage,
    get_distribution_baseline_positions,
    is_statistical_distribution_baseline_valid,
    validate_statistical_distribution_baseline,
    validate_statistical_distribution_baseline_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisResult,
    StatisticalObservation,
)


def build_dataset():
    observations = (
        StatisticalObservation(date(2026, 1, 1), "col1", 0),
        StatisticalObservation(date(2026, 1, 2), "col1", 1),
        StatisticalObservation(date(2026, 1, 3), "col1", 1),
        StatisticalObservation(date(2026, 1, 4), "col1", 5),
        StatisticalObservation(date(2026, 1, 1), "col2", 2),
        StatisticalObservation(date(2026, 1, 2), "col2", 2),
    )
    result = StatisticalAnalysisResult(
        market_id=1,
        analysis_version="v1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        observation_count=len(observations),
    )
    contract = build_statistical_baseline_contract(
        result,
        observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v1",
    )
    return build_statistical_baseline_dataset(
        contract,
        observations,
    )


def test_build_distribution_baseline():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    assert baseline.market_id == 1
    assert baseline.analysis_version == "v1"
    assert baseline.baseline_version == "v1"
    assert baseline.positions == ("col1", "col2")
    assert baseline.position_count == 2


def test_distribution_reuses_existing_position_distribution_engine():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    col1 = get_distribution_baseline(
        baseline,
        "col1",
    )
    assert col1.total_observations == 4
    assert col1.percentages[0] == pytest.approx(25.0)
    assert col1.percentages[1] == pytest.approx(50.0)
    assert col1.percentages[5] == pytest.approx(25.0)


def test_zero_is_preserved():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    assert get_distribution_baseline_percentage(
        baseline,
        "col1",
        0,
    ) == pytest.approx(25.0)


def test_empty_declared_position_is_supported():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    col2 = get_distribution_baseline(
        baseline,
        "col2",
    )
    assert col2.total_observations == 2
    assert col2.percentages[2] == pytest.approx(100.0)


def test_all_digits_are_represented():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    for distribution in baseline.distributions:
        assert len(distribution.percentages) == 10


def test_percentages_sum_to_100_for_non_empty_positions():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    for distribution in baseline.distributions:
        assert sum(distribution.percentages) == pytest.approx(100.0)


def test_positions_are_deterministic():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    assert get_distribution_baseline_positions(
        baseline
    ) == ("col1", "col2")


def test_validation_accepts_valid_baseline():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    validate_statistical_distribution_baseline(baseline)
    assert is_statistical_distribution_baseline_valid(
        baseline
    )


def test_validation_result_accepts_valid_baseline():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    result = validate_statistical_distribution_baseline_result(
        baseline
    )
    assert result.status == VALID
    assert result.is_valid
    assert result.issue_count == 0


def test_validation_result_rejects_wrong_type():
    result = validate_statistical_distribution_baseline_result(
        object()
    )
    assert result.status == INVALID
    assert not result.is_valid
    assert result.issue_count == 1
    assert result.issues[0].code == "INVALID_BASELINE_TYPE"


def test_validation_rejects_wrong_distribution_type():
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=(object(),),
    )
    with pytest.raises(
        TypeError,
        match="PositionDistribution",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_validation_rejects_duplicate_positions():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=(
            baseline.distributions[0],
            baseline.distributions[0],
        ),
    )
    with pytest.raises(
        ValueError,
        match="unique",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_validation_rejects_bad_percentage_count():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    original = baseline.distributions[0]
    invalid_distribution = type(original)(
        position=original.position,
        total_observations=original.total_observations,
        percentages=(25.0,),
    )
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=(invalid_distribution,),
    )
    with pytest.raises(
        ValueError,
        match="exactly 10",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_validation_rejects_percentage_out_of_range():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    original = baseline.distributions[0]
    percentages = list(original.percentages)
    percentages[0] = 101.0
    invalid_distribution = type(original)(
        position=original.position,
        total_observations=original.total_observations,
        percentages=tuple(percentages),
    )
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=(invalid_distribution,),
    )
    with pytest.raises(
        ValueError,
        match="between 0 and 100",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_validation_rejects_percentage_sum_mismatch():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    original = baseline.distributions[0]
    percentages = list(original.percentages)
    percentages[0] += 1.0
    invalid_distribution = type(original)(
        position=original.position,
        total_observations=original.total_observations,
        percentages=tuple(percentages),
    )
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=(invalid_distribution,),
    )
    with pytest.raises(
        ValueError,
        match="sum to 100",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_validation_rejects_non_deterministic_position_order():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    invalid = StatisticalDistributionBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        distributions=tuple(
            reversed(baseline.distributions)
        ),
    )
    with pytest.raises(
        ValueError,
        match="deterministic order",
    ):
        validate_statistical_distribution_baseline(invalid)


def test_get_missing_position_raises():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    with pytest.raises(
        ValueError,
        match="not found",
    ):
        get_distribution_baseline(
            baseline,
            "col8",
        )


def test_get_invalid_digit_raises():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    with pytest.raises(
        ValueError,
        match="between 0 and 9",
    ):
        get_distribution_baseline_percentage(
            baseline,
            "col1",
            10,
        )


def test_get_boolean_digit_raises():
    baseline = build_statistical_distribution_baseline(
        build_dataset()
    )
    with pytest.raises(
        ValueError,
        match="between 0 and 9",
    ):
        get_distribution_baseline_percentage(
            baseline,
            "col1",
            True,
        )


def test_validation_result_is_immutable():
    result = StatisticalDistributionBaselineValidationResult(
        status=VALID,
        issues=(),
    )
    with pytest.raises(AttributeError):
        result.status = INVALID
