from datetime import date

import pytest

from analytics.temporal_position_analysis import (
    build_temporal_position_analysis,
)
from analytics.temporal_position_summary import (
    TemporalPositionSummary,
    build_temporal_position_summary,
    build_temporal_position_summary_result,
    get_temporal_position_summary,
)


def make_analysis(
    position: str,
    values: tuple[int | None, ...],
):
    observations = tuple(
        (
            date(2026, 1, index + 1),
            value,
        )
        for index, value in enumerate(values)
    )

    result = build_temporal_position_analysis(
        {position: observations}
    )

    return result.analyses[0]


def test_basic_summary():
    analyses = (
        make_analysis("col1", (1, 3, 2)),
        make_analysis("col2", (2, 4, 6)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.position_count == 2
    assert summary.positions == ("col1", "col2")
    assert summary.total_observations == 6
    assert summary.total_change_count == 4
    assert summary.total_increase_count == 3
    assert summary.total_decrease_count == 1
    assert summary.total_unchanged_count == 0


def test_average_first_value():
    analyses = (
        make_analysis("col1", (2, 4)),
        make_analysis("col2", (4, 6)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_first_value == 3.0


def test_average_latest_value():
    analyses = (
        make_analysis("col1", (2, 4)),
        make_analysis("col2", (4, 8)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_latest_value == 6.0


def test_average_minimum_and_maximum():
    analyses = (
        make_analysis("col1", (1, 5, 3)),
        make_analysis("col2", (2, 7, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_minimum == 1.5
    assert summary.average_maximum == 6.0


def test_average_mean():
    analyses = (
        make_analysis("col1", (1, 3)),
        make_analysis("col2", (2, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_mean == 2.5


def test_average_first_to_latest_change():
    analyses = (
        make_analysis("col1", (1, 5)),
        make_analysis("col2", (8, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_first_to_latest_change == 0.0


def test_average_absolute_first_to_latest_change():
    analyses = (
        make_analysis("col1", (1, 5)),
        make_analysis("col2", (8, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_absolute_first_to_latest_change == 4.0


def test_average_absolute_step_change():
    analyses = (
        make_analysis("col1", (1, 4, 2)),
        make_analysis("col2", (2, 4, 6)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_absolute_step_change == 2.25


def test_maximum_absolute_step_change():
    analyses = (
        make_analysis("col1", (1, 4, 2)),
        make_analysis("col2", (2, 8, 3)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.maximum_absolute_step_change == 6


def test_movement_percentages_are_aggregated():
    analyses = (
        make_analysis("col1", (1, 2, 1)),
        make_analysis("col2", (3, 3, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.total_change_count == 4
    assert summary.total_increase_count == 2
    assert summary.total_decrease_count == 1
    assert summary.total_unchanged_count == 1

    assert summary.increase_percentage == 50.0
    assert summary.decrease_percentage == 25.0
    assert summary.unchanged_percentage == 25.0


def test_movement_percentages_sum_to_100():
    analyses = (
        make_analysis("col1", (1, 2, 3)),
        make_analysis("col2", (4, 3, 2)),
    )

    summary = build_temporal_position_summary(analyses)

    assert (
        summary.increase_percentage
        + summary.decrease_percentage
        + summary.unchanged_percentage
    ) == pytest.approx(100.0)


def test_empty_input():
    summary = build_temporal_position_summary([])

    assert summary.position_count == 0
    assert summary.positions == ()
    assert summary.total_observations == 0
    assert summary.total_change_count == 0
    assert summary.total_increase_count == 0
    assert summary.total_decrease_count == 0
    assert summary.total_unchanged_count == 0
    assert summary.average_first_value == 0.0
    assert summary.average_latest_value == 0.0
    assert summary.average_minimum == 0.0
    assert summary.average_maximum == 0.0
    assert summary.average_mean == 0.0
    assert summary.average_standard_deviation == 0.0
    assert summary.average_first_to_latest_change == 0.0
    assert summary.average_absolute_first_to_latest_change == 0.0
    assert summary.average_absolute_step_change == 0.0
    assert summary.maximum_absolute_step_change == 0
    assert summary.increase_percentage == 0.0
    assert summary.decrease_percentage == 0.0
    assert summary.unchanged_percentage == 0.0


def test_all_empty_analyses():
    analyses = (
        make_analysis("col1", ()),
        make_analysis("col2", ()),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.position_count == 2
    assert summary.positions == ("col1", "col2")
    assert summary.total_observations == 0
    assert summary.total_change_count == 0
    assert summary.average_mean == 0.0
    assert summary.maximum_absolute_step_change == 0


def test_none_values_are_not_counted_as_observations():
    analyses = (
        make_analysis("col1", (None, 0, 2)),
        make_analysis("col2", (None, None, 5)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.total_observations == 3


def test_zero_is_preserved():
    analyses = (
        make_analysis("col1", (0, 2)),
        make_analysis("col2", (0, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_first_value == 0.0
    assert summary.average_latest_value == 3.0
    assert summary.average_minimum == 0.0


def test_duplicate_positions_are_rejected():
    analyses = (
        make_analysis("col1", (1, 2)),
        make_analysis("col1", (3, 4)),
    )

    with pytest.raises(
        ValueError,
        match="duplicate positions",
    ):
        build_temporal_position_summary(analyses)


def test_invalid_analysis_item_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_summary(
            [object()]
        )


def test_string_input_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_summary("invalid")


def test_summary_is_frozen():
    summary = build_temporal_position_summary(
        [make_analysis("col1", (1, 2))]
    )

    with pytest.raises((AttributeError, TypeError)):
        summary.position_count = 99


def test_result_builder_matches_primary_builder():
    analyses = (
        make_analysis("col1", (1, 2)),
        make_analysis("col2", (3, 4)),
    )

    first = build_temporal_position_summary(analyses)
    second = build_temporal_position_summary_result(analyses)

    assert first == second


def test_getter_matches_primary_builder():
    analyses = (
        make_analysis("col1", (1, 2)),
        make_analysis("col2", (3, 4)),
    )

    first = build_temporal_position_summary(analyses)
    second = get_temporal_position_summary(analyses)

    assert first == second


def test_descriptive_only():
    summary = build_temporal_position_summary(
        [make_analysis("col1", (1, 2))]
    )

    assert not hasattr(summary, "prediction")
    assert not hasattr(summary, "score")
    assert not hasattr(summary, "rank")
    assert not hasattr(summary, "recommended_position")


def test_summary_type():
    summary = build_temporal_position_summary(
        [make_analysis("col1", (1, 2))]
    )

    assert isinstance(summary, TemporalPositionSummary)


def test_position_order_is_preserved():
    analyses = (
        make_analysis("col4", (4, 5)),
        make_analysis("col1", (1, 2)),
        make_analysis("col8", (8, 9)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.positions == ("col4", "col1", "col8")


def test_standard_deviation_average():
    analyses = (
        make_analysis("col1", (1, 2, 3)),
        make_analysis("col2", (2, 3, 4)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.average_standard_deviation == pytest.approx(
        (2 / 3) ** 0.5
    )


def test_total_change_counts_include_all_positions():
    analyses = (
        make_analysis("col1", (1, 2, 3)),
        make_analysis("col2", (5, 4, 4)),
        make_analysis("col3", (8, 8, 7)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.total_change_count == 6
    assert summary.total_increase_count == 2
    assert summary.total_decrease_count == 2
    assert summary.total_unchanged_count == 2


def test_maximum_absolute_step_change_with_single_observation():
    analyses = (
        make_analysis("col1", (5,)),
        make_analysis("col2", (1, 7)),
    )

    summary = build_temporal_position_summary(analyses)

    assert summary.maximum_absolute_step_change == 6