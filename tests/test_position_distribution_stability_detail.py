from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_detail import (
    PositionDistributionStabilityDetail,
    build_all_position_distribution_stability_details,
    build_position_distribution_stability_detail,
    get_position_distribution_stability_detail,
)
from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


def make_result(
    position="col1",
    digit=0,
    window_count=4,
    change_count=3,
    total_absolute_change=3.0,
    mean_absolute_change=1.0,
    maximum_absolute_change=2.0,
    minimum_absolute_change=0.5,
):
    return PositionDistributionVolatility(
        position=position,
        digit=digit,
        window_count=window_count,
        change_count=change_count,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=mean_absolute_change,
        maximum_absolute_change=maximum_absolute_change,
        minimum_absolute_change=minimum_absolute_change,
        volatility_level="LOW",
    )


def test_stable_result_is_classified_correctly():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            digit=5,
            mean_absolute_change=1.5,
        ),
    )

    assert result.position == "col1"
    assert result.digit == 5
    assert result.stability_level == "STABLE"


def test_low_threshold_boundary_is_moderate():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            digit=5,
            mean_absolute_change=2.0,
        ),
    )

    assert result.stability_level == "MODERATE"


def test_moderate_result_is_classified_correctly():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            digit=5,
            mean_absolute_change=3.5,
        ),
    )

    assert result.stability_level == "MODERATE"


def test_high_threshold_boundary_is_unstable():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            digit=5,
            mean_absolute_change=5.0,
        ),
    )

    assert result.stability_level == "UNSTABLE"


def test_unstable_result_is_classified_correctly():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            digit=5,
            mean_absolute_change=8.0,
        ),
    )

    assert result.stability_level == "UNSTABLE"


def test_all_source_fields_are_preserved():
    source = make_result(
        position="col3",
        digit=7,
        window_count=8,
        change_count=7,
        total_absolute_change=28.5,
        mean_absolute_change=4.0714285714,
        maximum_absolute_change=8.0,
        minimum_absolute_change=1.5,
    )

    result = build_position_distribution_stability_detail(
        position="col3",
        result=source,
    )

    assert result.position == "col3"
    assert result.digit == 7
    assert result.window_count == 8
    assert result.change_count == 7
    assert result.total_absolute_change == 28.5
    assert result.mean_absolute_change == pytest.approx(
        4.0714285714
    )
    assert result.maximum_absolute_change == 8.0
    assert result.minimum_absolute_change == 1.5


def test_position_mismatch_is_rejected():
    source = make_result(
        position="col2",
        digit=1,
    )

    with pytest.raises(
        ValueError,
        match="Volatility result position does not match",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_digit_is_rejected():
    source = make_result(
        digit=-1,
    )

    with pytest.raises(
        ValueError,
        match="digit must be between 0 and 9",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_digit_above_nine_is_rejected():
    source = make_result(
        digit=10,
    )

    with pytest.raises(
        ValueError,
        match="digit must be between 0 and 9",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_window_count_is_rejected():
    source = make_result(
        window_count=-1,
    )

    with pytest.raises(
        ValueError,
        match="Window count must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_change_count_is_rejected():
    source = make_result(
        change_count=-1,
    )

    with pytest.raises(
        ValueError,
        match="Change count must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_total_absolute_change_is_rejected():
    source = make_result(
        total_absolute_change=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Total absolute change must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_mean_absolute_change_is_rejected():
    source = make_result(
        mean_absolute_change=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Mean absolute change must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_maximum_absolute_change_is_rejected():
    source = make_result(
        maximum_absolute_change=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Maximum absolute change must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_minimum_absolute_change_is_rejected():
    source = make_result(
        minimum_absolute_change=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Minimum absolute change must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=source,
        )


def test_negative_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="Low threshold must be greater than or equal to zero",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=make_result(),
            low_threshold=-1.0,
        )


def test_high_threshold_below_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="High threshold must be greater than or equal to",
    ):
        build_position_distribution_stability_detail(
            position="col1",
            result=make_result(),
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_custom_thresholds_are_supported():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(
            mean_absolute_change=6.0,
        ),
        low_threshold=4.0,
        high_threshold=7.0,
    )

    assert result.stability_level == "MODERATE"


def test_all_digits_are_supported():
    results = tuple(
        make_result(
            digit=digit,
            mean_absolute_change=1.0,
        )
        for digit in range(10)
    )

    details = build_all_position_distribution_stability_details(
        position="col1",
        results=results,
    )

    assert len(details) == 10
    assert [detail.digit for detail in details] == list(range(10))


def test_all_details_preserve_input_order():
    results = (
        make_result(digit=7),
        make_result(digit=2),
        make_result(digit=9),
    )

    details = build_all_position_distribution_stability_details(
        position="col1",
        results=results,
    )

    assert [detail.digit for detail in details] == [7, 2, 9]


def test_all_details_preserve_positions():
    results = (
        make_result(
            position="col4",
            digit=0,
        ),
        make_result(
            position="col4",
            digit=1,
        ),
    )

    details = build_all_position_distribution_stability_details(
        position="col4",
        results=results,
    )

    assert all(
        detail.position == "col4"
        for detail in details
    )


def test_all_details_empty_input_returns_empty_tuple():
    result = build_all_position_distribution_stability_details(
        position="col1",
        results=(),
    )

    assert result == ()


def test_all_details_mismatched_position_is_rejected():
    results = (
        make_result(
            position="col2",
            digit=0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Volatility result position does not match",
    ):
        build_all_position_distribution_stability_details(
            position="col1",
            results=results,
        )


def test_get_detail_returns_matching_digit():
    details = (
        build_position_distribution_stability_detail(
            position="col1",
            result=make_result(
                digit=2,
                mean_absolute_change=1.0,
            ),
        ),
        build_position_distribution_stability_detail(
            position="col1",
            result=make_result(
                digit=7,
                mean_absolute_change=6.0,
            ),
        ),
    )

    result = get_position_distribution_stability_detail(
        results=details,
        digit=7,
    )

    assert result is not None
    assert result.digit == 7
    assert result.stability_level == "UNSTABLE"


def test_get_detail_returns_none_when_digit_is_missing():
    details = (
        build_position_distribution_stability_detail(
            position="col1",
            result=make_result(
                digit=2,
            ),
        ),
    )

    result = get_position_distribution_stability_detail(
        results=details,
        digit=8,
    )

    assert result is None


def test_get_detail_rejects_negative_digit():
    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        get_position_distribution_stability_detail(
            results=(),
            digit=-1,
        )


def test_get_detail_rejects_digit_above_nine():
    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        get_position_distribution_stability_detail(
            results=(),
            digit=10,
        )


def test_detail_dataclass_is_frozen():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"


def test_result_type_is_correct():
    result = build_position_distribution_stability_detail(
        position="col1",
        result=make_result(),
    )

    assert isinstance(
        result,
        PositionDistributionStabilityDetail,
    )


def test_all_detail_results_have_correct_type():
    results = (
        make_result(digit=0),
        make_result(digit=1),
        make_result(digit=2),
    )

    details = build_all_position_distribution_stability_details(
        position="col1",
        results=results,
    )

    assert all(
        isinstance(
            detail,
            PositionDistributionStabilityDetail,
        )
        for detail in details
    )