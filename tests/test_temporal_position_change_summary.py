from datetime import date

import pytest

from analytics.temporal_position_change_classification import (
    build_temporal_position_change_classification,
)
from analytics.temporal_position_change_detection import (
    build_temporal_position_change_detection,
)
from analytics.temporal_position_change_summary import (
    TemporalPositionChangePositionSummary,
    TemporalPositionChangeSummary,
    build_temporal_position_change_summary,
    build_temporal_position_change_summary_result,
    get_temporal_position_change_position_summary,
    iter_temporal_position_change_position_summaries,
)


def make_result(
    position: str,
    pairs: tuple[tuple[int | None, int | None], ...],
):
    changes = []

    for index, (previous_value, current_value) in enumerate(pairs):
        detection = build_temporal_position_change_detection(
            position,
            (
                (date(2026, 1, index + 1), previous_value),
                (date(2026, 1, index + 2), current_value),
            ),
        )

        changes.append(detection.changes[0])

    return build_temporal_position_change_classification(
        position,
        tuple(changes),
    )


def test_basic_summary():
    result1 = make_result(
        "col1",
        (
            (1, 2),
            (2, 5),
            (5, 5),
        ),
    )

    result2 = make_result(
        "col2",
        (
            (8, 4),
            (4, 7),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result1, result2)
    )

    assert summary.position_count == 2
    assert summary.positions == ("col1", "col2")
    assert summary.total_change_count == 5
    assert summary.total_increase_count == 3
    assert summary.total_decrease_count == 1
    assert summary.total_unchanged_count == 1
    assert summary.total_missing_count == 0
    assert summary.total_valid_change_count == 5


def test_magnitude_counts():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 6),
            (6, 6),
            (6, 9),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.total_low_count == 1
    assert summary.total_medium_count == 2
    assert summary.total_high_count == 0


def test_missing_count():
    result = make_result(
        "col1",
        (
            (None, 2),
            (2, None),
            (2, 3),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.total_change_count == 3
    assert summary.total_missing_count == 2
    assert summary.total_valid_change_count == 1


def test_movement_percentages():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 1),
            (1, 1),
            (1, 4),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.increase_percentage == 50.0
    assert summary.decrease_percentage == 25.0
    assert summary.unchanged_percentage == 25.0
    assert summary.missing_percentage == 0.0


def test_missing_percentage():
    result = make_result(
        "col1",
        (
            (None, 2),
            (2, None),
            (2, 3),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.missing_percentage == pytest.approx(
        200 / 3
    )


def test_magnitude_percentages():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 4),
            (4, 9),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.low_percentage == pytest.approx(
        100 / 3
    )
    assert summary.medium_percentage == pytest.approx(
        100 / 3
    )
    assert summary.high_percentage == pytest.approx(
        100 / 3
    )


def test_position_summary_is_created():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 6),
            (6, 6),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    position_summary = summary.position_summaries[0]

    assert position_summary.position == "col1"
    assert position_summary.change_count == 3
    assert position_summary.increase_count == 2
    assert position_summary.unchanged_count == 1
    assert position_summary.low_count == 1
    assert position_summary.medium_count == 1
    assert position_summary.high_count == 0


def test_position_summary_percentages():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 5),
            (5, 5),
            (5, 4),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    position_summary = summary.position_summaries[0]

    assert position_summary.increase_percentage == 50.0
    assert position_summary.decrease_percentage == 25.0
    assert position_summary.unchanged_percentage == 25.0


def test_position_summary_getter():
    result1 = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    result2 = make_result(
        "col2",
        (
            (4, 8),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result1, result2)
    )

    position_summary = (
        get_temporal_position_change_position_summary(
            summary,
            "col2",
        )
    )

    assert position_summary.position == "col2"
    assert position_summary.increase_count == 1
    assert position_summary.high_count == 0


def test_unknown_position_getter_is_rejected():
    result = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    with pytest.raises(
        ValueError,
        match="Position summary not found",
    ):
        get_temporal_position_change_position_summary(
            summary,
            "col2",
        )


def test_iterator_returns_tuple():
    result1 = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    result2 = make_result(
        "col2",
        (
            (2, 3),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result1, result2)
    )

    summaries = (
        iter_temporal_position_change_position_summaries(
            summary
        )
    )

    assert isinstance(summaries, tuple)
    assert len(summaries) == 2


def test_position_order_is_preserved():
    result1 = make_result(
        "col4",
        (
            (1, 2),
        ),
    )

    result2 = make_result(
        "col1",
        (
            (2, 3),
        ),
    )

    result3 = make_result(
        "col8",
        (
            (3, 4),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result1, result2, result3)
    )

    assert summary.positions == (
        "col4",
        "col1",
        "col8",
    )


def test_empty_input():
    summary = build_temporal_position_change_summary(
        ()
    )

    assert summary.position_count == 0
    assert summary.positions == ()
    assert summary.total_change_count == 0
    assert summary.total_increase_count == 0
    assert summary.total_decrease_count == 0
    assert summary.total_unchanged_count == 0
    assert summary.total_missing_count == 0
    assert summary.total_low_count == 0
    assert summary.total_medium_count == 0
    assert summary.total_high_count == 0
    assert summary.total_valid_change_count == 0
    assert summary.increase_percentage == 0.0
    assert summary.decrease_percentage == 0.0
    assert summary.unchanged_percentage == 0.0
    assert summary.missing_percentage == 0.0
    assert summary.position_summaries == ()


def test_empty_position_result():
    result = build_temporal_position_change_classification(
        "col1",
        (),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.position_count == 1
    assert summary.total_change_count == 0
    assert summary.position_summaries[0].change_count == 0
    assert summary.position_summaries[0].increase_percentage == 0.0


def test_duplicate_positions_are_rejected():
    result1 = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    result2 = make_result(
        "col1",
        (
            (3, 4),
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate positions",
    ):
        build_temporal_position_change_summary(
            (result1, result2)
        )


def test_invalid_result_item_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_summary(
            (object(),)
        )


def test_invalid_results_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_summary(
            "invalid"
        )


def test_invalid_getter_result_is_rejected():
    with pytest.raises(TypeError):
        get_temporal_position_change_position_summary(
            object(),
            "col1",
        )


def test_invalid_iterator_result_is_rejected():
    with pytest.raises(TypeError):
        iter_temporal_position_change_position_summaries(
            object()
        )


def test_summary_is_frozen():
    result = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    with pytest.raises((AttributeError, TypeError)):
        summary.total_change_count = 99


def test_position_summary_is_frozen():
    result = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    with pytest.raises((AttributeError, TypeError)):
        summary.position_summaries[0].change_count = 99


def test_result_builder_matches_primary_builder():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 4),
        ),
    )

    first = build_temporal_position_change_summary(
        (result,)
    )

    second = build_temporal_position_change_summary_result(
        (result,)
    )

    assert first == second


def test_valid_change_count_equals_direction_counts():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 1),
            (1, 1),
            (None, 4),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.total_valid_change_count == (
        summary.total_increase_count
        + summary.total_decrease_count
        + summary.total_unchanged_count
    )


def test_movement_percentages_sum_to_100_without_missing():
    result = make_result(
        "col1",
        (
            (1, 2),
            (2, 1),
            (1, 1),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert (
        summary.increase_percentage
        + summary.decrease_percentage
        + summary.unchanged_percentage
    ) == pytest.approx(100.0)


def test_magnitude_counts_exclude_unchanged_and_missing():
    result = make_result(
        "col1",
        (
            (1, 1),
            (1, 2),
            (2, 6),
            (6, 9),
            (None, 4),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.total_change_count == 5
    assert summary.total_low_count == 1
    assert summary.total_medium_count == 2
    assert summary.total_high_count == 0
    assert summary.total_unchanged_count == 1
    assert summary.total_missing_count == 1


def test_dataclass_types():
    result = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert isinstance(
        summary,
        TemporalPositionChangeSummary,
    )

    assert isinstance(
        summary.position_summaries[0],
        TemporalPositionChangePositionSummary,
    )


def test_descriptive_only():
    result = make_result(
        "col1",
        (
            (1, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert not hasattr(summary, "prediction")
    assert not hasattr(summary, "score")
    assert not hasattr(summary, "rank")
    assert not hasattr(summary, "recommended_position")


def test_zero_is_valid_in_change_summary():
    result = make_result(
        "col1",
        (
            (0, 0),
            (0, 2),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result,)
    )

    assert summary.total_unchanged_count == 1
    assert summary.total_increase_count == 1
    assert summary.total_change_count == 2


def test_multiple_positions_aggregate_correctly():
    result1 = make_result(
        "col1",
        (
            (1, 2),
            (2, 5),
        ),
    )

    result2 = make_result(
        "col2",
        (
            (8, 3),
            (3, 3),
        ),
    )

    summary = build_temporal_position_change_summary(
        (result1, result2)
    )

    assert summary.total_change_count == 4
    assert summary.total_increase_count == 2
    assert summary.total_decrease_count == 1
    assert summary.total_unchanged_count == 1