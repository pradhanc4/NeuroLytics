from __future__ import annotations

import pytest

from analytics.position_distribution_change import (
    PositionDistributionDigitChange,
)
from analytics.position_distribution_change_summary import (
    PositionDistributionChangeSummary,
    summarize_position_distribution_changes,
)


def make_change(
    digit: int,
    absolute_change: float,
    direction: str,
    position: str = "col1",
) -> PositionDistributionDigitChange:
    return PositionDistributionDigitChange(
        position=position,
        digit=digit,
        percentage_a=10.0,
        percentage_b=10.0,
        absolute_change=absolute_change,
        direction=direction,
    )


def test_empty_changes_return_empty_summary() -> None:
    result = summarize_position_distribution_changes(
        position="col1",
        changes=(),
    )

    assert isinstance(
        result,
        PositionDistributionChangeSummary,
    )
    assert result.position == "col1"
    assert result.threshold == 0.0
    assert result.digit_count == 0
    assert result.increased_digits == 0
    assert result.decreased_digits == 0
    assert result.unchanged_digits == 0
    assert result.total_absolute_change == 0.0
    assert result.mean_absolute_change == 0.0
    assert result.classified_changes == ()


def test_summary_counts_increased_decreased_and_unchanged() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=5.0,
            direction="increased",
        ),
        make_change(
            digit=1,
            absolute_change=3.0,
            direction="decreased",
        ),
        make_change(
            digit=2,
            absolute_change=0.0,
            direction="unchanged",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
    )

    assert result.digit_count == 3
    assert result.increased_digits == 1
    assert result.decreased_digits == 1
    assert result.unchanged_digits == 1


def test_summary_calculates_total_absolute_change() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=5.0,
            direction="increased",
        ),
        make_change(
            digit=1,
            absolute_change=3.0,
            direction="decreased",
        ),
        make_change(
            digit=2,
            absolute_change=2.0,
            direction="increased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
    )

    assert result.total_absolute_change == pytest.approx(10.0)


def test_summary_calculates_mean_absolute_change() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=5.0,
            direction="increased",
        ),
        make_change(
            digit=1,
            absolute_change=3.0,
            direction="decreased",
        ),
        make_change(
            digit=2,
            absolute_change=2.0,
            direction="increased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
    )

    assert result.mean_absolute_change == pytest.approx(10.0 / 3.0)


def test_threshold_is_preserved() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=5.0,
            direction="increased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
        threshold=2.0,
    )

    assert result.threshold == 2.0


def test_threshold_changes_classification() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=1.0,
            direction="increased",
        ),
        make_change(
            digit=1,
            absolute_change=3.0,
            direction="decreased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
        threshold=2.0,
    )

    assert result.increased_digits == 0
    assert result.decreased_digits == 1
    assert result.unchanged_digits == 1

    assert result.classified_changes[0].classification == "unchanged"
    assert result.classified_changes[1].classification == "decreased"


def test_change_equal_to_threshold_is_unchanged() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=2.0,
            direction="increased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
        threshold=2.0,
    )

    assert result.unchanged_digits == 1
    assert result.increased_digits == 0
    assert result.classified_changes[0].classification == "unchanged"


def test_change_above_threshold_remains_classified() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=2.1,
            direction="increased",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
        threshold=2.0,
    )

    assert result.increased_digits == 1
    assert result.unchanged_digits == 0
    assert result.classified_changes[0].classification == "increased"


def test_negative_threshold_is_rejected() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=1.0,
            direction="increased",
        ),
    )

    with pytest.raises(
        ValueError,
        match="greater than or equal to zero",
    ):
        summarize_position_distribution_changes(
            position="col1",
            changes=changes,
            threshold=-1.0,
        )


def test_position_mismatch_is_rejected() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=1.0,
            direction="increased",
            position="col2",
        ),
    )

    with pytest.raises(
        ValueError,
        match="All changes must belong",
    ):
        summarize_position_distribution_changes(
            position="col1",
            changes=changes,
        )


def test_classified_changes_preserve_input_order() -> None:
    changes = (
        make_change(
            digit=7,
            absolute_change=4.0,
            direction="increased",
        ),
        make_change(
            digit=2,
            absolute_change=3.0,
            direction="decreased",
        ),
        make_change(
            digit=5,
            absolute_change=0.0,
            direction="unchanged",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
    )

    assert tuple(
        item.digit
        for item in result.classified_changes
    ) == (7, 2, 5)


def test_summary_contains_all_classified_changes() -> None:
    changes = tuple(
        make_change(
            digit=digit,
            absolute_change=float(digit),
            direction=(
                "unchanged"
                if digit == 0
                else "increased"
            ),
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_changes(
        position="col1",
        changes=changes,
    )

    assert result.digit_count == 10
    assert len(result.classified_changes) == 10


def test_summary_preserves_position() -> None:
    changes = (
        make_change(
            digit=4,
            absolute_change=6.0,
            direction="increased",
            position="col8",
        ),
    )

    result = summarize_position_distribution_changes(
        position="col8",
        changes=changes,
    )

    assert result.position == "col8"
    assert result.classified_changes[0].position == "col8"