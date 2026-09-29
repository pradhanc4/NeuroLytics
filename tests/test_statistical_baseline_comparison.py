from analytics.statistical_baseline_comparison import (
    VALID,
    StatisticalBaselineComparison,
    compare_statistical_probability_baselines,
    get_probability_changes_for_position,
    validate_statistical_baseline_comparison,
    validate_statistical_baseline_comparison_result,
)
from analytics.statistical_probability_baseline import (
    PositionProbabilityBaseline,
    StatisticalProbabilityBaseline,
)


def baseline(version, probabilities):
    return StatisticalProbabilityBaseline(
        market_id=1,
        analysis_version="v1",
        baseline_version=version,
        positions=(
            PositionProbabilityBaseline("col1", probabilities),
        ),
    )


def test_comparison_detects_change():
    previous = baseline("old", (0.5, 0.5) + (0.0,) * 8)
    current = baseline("new", (0.25, 0.75) + (0.0,) * 8)
    result = compare_statistical_probability_baselines(previous, current)
    assert result.change_count == 2
    changes = get_probability_changes_for_position(result, "col1")
    assert changes[0].absolute_change == 0.25


def test_identical_baselines_have_no_changes():
    item = (0.5, 0.5) + (0.0,) * 8
    result = compare_statistical_probability_baselines(
        baseline("old", item), baseline("new", item)
    )
    assert result.change_count == 0


def test_tolerance():
    old = baseline("old", (0.5, 0.5) + (0.0,) * 8)
    new = baseline("new", (0.5000000000001, 0.4999999999999) + (0.0,) * 8)
    result = compare_statistical_probability_baselines(old, new)
    assert result.change_count == 0


def test_validation():
    result = compare_statistical_probability_baselines(
        baseline("old", (1.0,) + (0.0,) * 9),
        baseline("new", (0.9, 0.1) + (0.0,) * 8),
    )
    validate_statistical_baseline_comparison(result)
    validation = validate_statistical_baseline_comparison_result(result)
    assert validation.status == VALID
    assert validation.is_valid


def test_market_mismatch_rejected():
    old = baseline("old", (1.0,) + (0.0,) * 9)
    new = StatisticalProbabilityBaseline(
        2, "v1", "new",
        (PositionProbabilityBaseline("col1", (1.0,) + (0.0,) * 9),),
    )
    try:
        compare_statistical_probability_baselines(old, new)
        assert False
    except ValueError as exc:
        assert "market IDs" in str(exc)


def test_invalid_type_result():
    validation = validate_statistical_baseline_comparison_result(object())
    assert not validation.is_valid


def test_empty_comparison_validates():
    comparison = StatisticalBaselineComparison(1, "old", "new", ())
    validate_statistical_baseline_comparison(comparison)
