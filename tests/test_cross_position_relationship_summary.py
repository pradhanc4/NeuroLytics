import pytest

from analytics.cross_position_relationship_matrix import (
    build_cross_position_relationship_matrix,
)
from analytics.cross_position_relationship_summary import (
    CrossPositionRelationshipPositionSummary,
    CrossPositionRelationshipSummary,
    build_cross_position_relationship_summary,
    build_cross_position_relationship_summary_result,
    get_cross_position_relationship_position_summary,
    iter_cross_position_relationship_position_summaries,
)


def build_matrix():
    return build_cross_position_relationship_matrix(
        (
            "col1",
            "col2",
            "col3",
            "col4",
        ),
        {
            (
                "col1",
                "col2",
            ): (
                (1, 2),
                (2, 4),
                (3, 6),
            ),
            (
                "col1",
                "col3",
            ): (
                (1, 3),
                (2, 2),
                (3, 1),
            ),
            (
                "col1",
                "col4",
            ): (
                (1, 1),
                (2, 1),
                (3, 1),
            ),
            (
                "col2",
                "col3",
            ): (
                (2, 3),
                (4, 2),
                (6, 1),
            ),
            (
                "col2",
                "col4",
            ): (
                (2, 1),
                (4, 2),
                (6, 3),
            ),
            (
                "col3",
                "col4",
            ): (
                (1, 3),
                (2, 3),
                (3, 3),
            ),
        },
    )


def test_basic_summary():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.position_count == 4
    assert summary.positions == (
        "col1",
        "col2",
        "col3",
        "col4",
    )
    assert summary.relationship_count == 6


def test_direction_counts():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.positive_count == 2
    assert summary.negative_count == 2
    assert summary.neutral_count == 0
    assert summary.insufficient_data_count == 2


def test_strength_counts():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.strong_count == 4
    assert summary.none_count == 0
    assert summary.weak_count == 0
    assert summary.moderate_count == 0
    assert summary.insufficient_data_count == 2


def test_total_valid_pair_count():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.total_valid_pair_count == 18


def test_correlation_statistics():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.average_correlation == pytest.approx(
        0.0
    )

    assert summary.average_absolute_correlation == pytest.approx(
        1.0
    )

    assert summary.minimum_correlation == pytest.approx(
        -1.0
    )

    assert summary.maximum_correlation == pytest.approx(
        1.0
    )


def test_position_summaries_count():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert len(summary.position_summaries) == 4


def test_position_summary_col1():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    col1 = (
        get_cross_position_relationship_position_summary(
            summary,
            "col1",
        )
    )

    assert col1.position == "col1"
    assert col1.relationship_count == 3
    assert col1.positive_count == 1
    assert col1.negative_count == 1
    assert col1.neutral_count == 0
    assert col1.insufficient_data_count == 1
    assert col1.valid_pair_count == 9


def test_position_summary_col2():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    col2 = (
        get_cross_position_relationship_position_summary(
            summary,
            "col2",
        )
    )

    assert col2.position == "col2"
    assert col2.relationship_count == 3
    assert col2.positive_count == 2
    assert col2.negative_count == 1
    assert col2.insufficient_data_count == 0
    assert col2.valid_pair_count == 9


def test_position_summary_order_is_preserved():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert tuple(
        item.position
        for item in summary.position_summaries
    ) == (
        "col1",
        "col2",
        "col3",
        "col4",
    )


def test_iterator_returns_tuple():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    result = (
        iter_cross_position_relationship_position_summaries(
            summary
        )
    )

    assert isinstance(result, tuple)
    assert len(result) == 4


def test_unknown_position_is_rejected():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    with pytest.raises(
        ValueError,
        match="Position summary not found",
    ):
        get_cross_position_relationship_position_summary(
            summary,
            "col9",
        )


def test_invalid_summary_for_getter():
    with pytest.raises(TypeError):
        get_cross_position_relationship_position_summary(
            object(),
            "col1",
        )


def test_invalid_summary_for_iterator():
    with pytest.raises(TypeError):
        iter_cross_position_relationship_position_summaries(
            object()
        )


def test_invalid_matrix_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_summary(
            object()
        )


def test_result_builder_matches_primary_builder():
    matrix = build_matrix()

    first = build_cross_position_relationship_summary(
        matrix
    )

    second = (
        build_cross_position_relationship_summary_result(
            matrix
        )
    )

    assert first == second


def test_empty_matrix():
    matrix = build_cross_position_relationship_matrix(
        (),
        {},
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.position_count == 0
    assert summary.positions == ()
    assert summary.relationship_count == 0
    assert summary.total_valid_pair_count == 0
    assert summary.positive_count == 0
    assert summary.negative_count == 0
    assert summary.neutral_count == 0
    assert summary.insufficient_data_count == 0
    assert summary.none_count == 0
    assert summary.weak_count == 0
    assert summary.moderate_count == 0
    assert summary.strong_count == 0
    assert summary.average_correlation is None
    assert summary.average_absolute_correlation is None
    assert summary.minimum_correlation is None
    assert summary.maximum_correlation is None
    assert summary.position_summaries == ()


def test_single_position_matrix():
    matrix = build_cross_position_relationship_matrix(
        ("col1",),
        {},
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.position_count == 1
    assert summary.relationship_count == 0
    assert summary.position_summaries[0].position == "col1"
    assert summary.position_summaries[0].relationship_count == 0


def test_all_missing_relationships():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            (
                "col1",
                "col2",
            ): (
                (None, 1),
                (2, None),
            ),
        },
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.relationship_count == 1
    assert summary.total_valid_pair_count == 0
    assert summary.insufficient_data_count == 1
    assert summary.average_correlation is None
    assert summary.average_absolute_correlation is None
    assert summary.minimum_correlation is None
    assert summary.maximum_correlation is None


def test_zero_values_are_valid():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            (
                "col1",
                "col2",
            ): (
                (0, 0),
                (1, 1),
                (2, 2),
            ),
        },
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.relationship_count == 1
    assert summary.total_valid_pair_count == 3
    assert summary.positive_count == 1
    assert summary.strong_count == 1
    assert summary.average_correlation == pytest.approx(
        1.0
    )


def test_summary_is_frozen():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    with pytest.raises((AttributeError, TypeError)):
        summary.relationship_count = 99


def test_position_summary_is_frozen():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    with pytest.raises((AttributeError, TypeError)):
        summary.position_summaries[0].relationship_count = 99


def test_dataclass_types():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert isinstance(
        summary,
        CrossPositionRelationshipSummary,
    )

    assert isinstance(
        summary.position_summaries[0],
        CrossPositionRelationshipPositionSummary,
    )


def test_descriptive_only():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert not hasattr(
        summary,
        "prediction",
    )

    assert not hasattr(
        summary,
        "score",
    )

    assert not hasattr(
        summary,
        "rank",
    )

    assert not hasattr(
        summary,
        "recommended_position",
    )


def test_direction_counts_equal_relationship_count_when_no_missing():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            (
                "col1",
                "col2",
            ): (
                (1, 2),
                (2, 4),
                (3, 6),
            ),
        },
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert (
        summary.positive_count
        + summary.negative_count
        + summary.neutral_count
        + summary.insufficient_data_count
    ) == summary.relationship_count


def test_strength_counts_equal_relationship_count():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert (
        summary.none_count
        + summary.weak_count
        + summary.moderate_count
        + summary.strong_count
        + summary.insufficient_data_count
    ) == summary.relationship_count


def test_position_relationship_counts_match_matrix():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    for position_summary in summary.position_summaries:
        assert (
            position_summary.relationship_count
            == 3
        )


def test_position_valid_pair_totals():
    matrix = build_matrix()

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert sum(
        item.valid_pair_count
        for item in summary.position_summaries
    ) == (
        summary.total_valid_pair_count * 2
    )


def test_average_uses_only_valid_correlations():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {
            (
                "col1",
                "col2",
            ): (
                (1, 2),
                (2, 4),
            ),
            (
                "col1",
                "col3",
            ): (
                (1, 1),
            ),
            (
                "col2",
                "col3",
            ): (
                (None, 2),
            ),
        },
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.average_correlation == pytest.approx(
        1.0
    )

    assert summary.insufficient_data_count == 2


def test_negative_and_positive_are_preserved():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {
            (
                "col1",
                "col2",
            ): (
                (1, 1),
                (2, 2),
                (3, 3),
            ),
            (
                "col1",
                "col3",
            ): (
                (1, 3),
                (2, 2),
                (3, 1),
            ),
            (
                "col2",
                "col3",
            ): (
                (1, 3),
                (2, 2),
                (3, 1),
            ),
        },
    )

    summary = build_cross_position_relationship_summary(
        matrix
    )

    assert summary.positive_count == 1
    assert summary.negative_count == 2
    assert summary.strong_count == 3