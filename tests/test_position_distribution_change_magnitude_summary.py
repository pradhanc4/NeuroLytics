from __future__ import annotations

import pytest

from analytics.position_distribution_change_magnitude_summary import (
    PositionDistributionChangeMagnitudeSummary,
    summarize_change_magnitudes,
)


def test_summary_counts_low_medium_and_high() -> None:
    result = summarize_change_magnitudes(
        position="col1",
        changes=(
            0.5,
            1.0,
            2.0,
            3.0,
            4.9,
            5.0,
            6.0,
            7.0,
            1.5,
            8.0,
        ),
    )

    assert result.low_count == 3
    assert result.medium_count == 3
    assert result.high_count == 4


def test_summary_digit_count_is_preserved() -> None:
    result = summarize_change_magnitudes(
        position="col2",
        changes=(
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
        ),
    )

    assert result.digit_count == 10


def test_summary_classified_count_matches_total() -> None:
    result = summarize_change_magnitudes(
        position="col3",
        changes=(
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
        ),
    )

    assert result.classified_count == 10


def test_summary_position_is_preserved() -> None:
    result = summarize_change_magnitudes(
        position="col4",
        changes=(1.0, 2.0, 5.0),
    )

    assert result.position == "col4"


def test_summary_thresholds_are_preserved() -> None:
    result = summarize_change_magnitudes(
        position="col5",
        changes=(1.0, 4.0, 8.0),
        low_threshold=3.0,
        high_threshold=7.0,
    )

    assert result.low_threshold == 3.0
    assert result.high_threshold == 7.0


def test_custom_thresholds_change_magnitude_counts() -> None:
    result = summarize_change_magnitudes(
        position="col6",
        changes=(
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
        ),
        low_threshold=2.0,
        high_threshold=4.0,
    )

    assert result.low_count == 1
    assert result.medium_count == 2
    assert result.high_count == 2


def test_zero_change_is_classified_as_low() -> None:
    result = summarize_change_magnitudes(
        position="col7",
        changes=(0.0,),
    )

    assert result.low_count == 1
    assert result.medium_count == 0
    assert result.high_count == 0


def test_boundary_values_are_classified_correctly() -> None:
    result = summarize_change_magnitudes(
        position="col8",
        changes=(
            1.999999,
            2.0,
            4.999999,
            5.0,
        ),
    )

    assert result.low_count == 1
    assert result.medium_count == 2
    assert result.high_count == 1


def test_classifications_are_returned() -> None:
    result = summarize_change_magnitudes(
        position="col1",
        changes=(1.0, 3.0, 6.0),
    )

    assert len(result.classifications) == 3
    assert tuple(
        item.magnitude
        for item in result.classifications
    ) == (
        "LOW",
        "MEDIUM",
        "HIGH",
    )


def test_classification_digits_are_preserved_in_order() -> None:
    result = summarize_change_magnitudes(
        position="col2",
        changes=(
            0.0,
            1.0,
            2.0,
            3.0,
        ),
    )

    assert tuple(
        item.digit
        for item in result.classifications
    ) == (
        0,
        1,
        2,
        3,
    )


def test_classification_position_is_preserved() -> None:
    result = summarize_change_magnitudes(
        position="col3",
        changes=(1.0, 3.0, 6.0),
    )

    assert all(
        item.position == "col3"
        for item in result.classifications
    )


def test_empty_changes_return_empty_summary() -> None:
    result = summarize_change_magnitudes(
        position="col4",
        changes=(),
    )

    assert result.digit_count == 0
    assert result.low_count == 0
    assert result.medium_count == 0
    assert result.high_count == 0
    assert result.classified_count == 0
    assert result.classifications == ()


def test_invalid_low_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_change_magnitudes(
            position="col5",
            changes=(1.0, 2.0),
            low_threshold=-1.0,
        )


def test_high_threshold_less_than_low_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_change_magnitudes(
            position="col6",
            changes=(1.0, 2.0),
            low_threshold=5.0,
            high_threshold=3.0,
        )


def test_invalid_negative_change_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_change_magnitudes(
            position="col7",
            changes=(1.0, -2.0, 5.0),
        )


def test_more_than_ten_changes_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_change_magnitudes(
            position="col8",
            changes=(
                0.0,
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
                7.0,
                8.0,
                9.0,
                10.0,
            ),
        )


def test_result_is_expected_dataclass_type() -> None:
    result = summarize_change_magnitudes(
        position="col1",
        changes=(1.0, 3.0, 6.0),
    )

    assert isinstance(
        result,
        PositionDistributionChangeMagnitudeSummary,
    )


def test_classified_count_equals_sum_of_magnitude_counts() -> None:
    result = summarize_change_magnitudes(
        position="col2",
        changes=(
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
        ),
    )

    assert result.classified_count == (
        result.low_count
        + result.medium_count
        + result.high_count
    )