from dataclasses import dataclass

import pytest

from analytics.cross_position_relationship_change_detection import (
    build_cross_position_relationship_change_detection,
)
from analytics.cross_position_relationship_matrix import (
    build_cross_position_relationship_matrix,
)
from analytics.cross_position_relationship_overview import (
    CrossPositionRelationshipOverview,
    build_cross_position_relationship_overview,
    get_change_detection_result,
    get_stability_result,
    iter_change_detection_results,
    iter_stability_results,
)
from analytics.cross_position_relationship_stability import (
    build_cross_position_relationship_stability,
)
from analytics.cross_position_relationship_summary import (
    build_cross_position_relationship_summary,
)


@dataclass(frozen=True)
class Window:
    window_index: int
    correlation: float | None
    direction: str
    strength: str


def make_positions():
    return (
        "col1",
        "col2",
        "col3",
        "col4",
    )


def make_observations():
    return {
        ("col1", "col2"): (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (5, 0),
            (6, 2),
        ),
        ("col1", "col3"): (
            (1, 6),
            (2, 5),
            (3, 4),
            (4, 3),
            (5, 2),
            (6, 1),
        ),
        ("col1", "col4"): (
            (1, 1),
            (2, 1),
            (3, 1),
            (4, 1),
            (5, 1),
            (6, 1),
        ),
        ("col2", "col3"): (
            (2, 6),
            (4, 5),
            (6, 4),
            (8, 3),
            (0, 2),
            (2, 1),
        ),
        ("col2", "col4"): (
            (2, 1),
            (4, 1),
            (6, 1),
            (8, 1),
            (0, 1),
            (2, 1),
        ),
        ("col3", "col4"): (
            (6, 1),
            (5, 1),
            (4, 1),
            (3, 1),
            (2, 1),
            (1, 1),
        ),
    }


def make_matrix():
    return build_cross_position_relationship_matrix(
        make_positions(),
        make_observations(),
    )


def make_summary():
    return build_cross_position_relationship_summary(
        make_matrix()
    )


def make_stability_results():
    positive_observations = (
        (1, 2),
        (2, 4),
        (3, 6),
        (4, 8),
        (5, 10),
        (6, 12),
    )

    negative_observations = (
        (1, 6),
        (2, 5),
        (3, 4),
        (4, 3),
        (5, 2),
        (6, 1),
    )

    return (
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            positive_observations,
            window_size=2,
        ),
        build_cross_position_relationship_stability(
            "col1",
            "col3",
            negative_observations,
            window_size=2,
        ),
    )


def make_change_detection_results():
    return (
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            (
                Window(1, 0.80, "POSITIVE", "STRONG"),
                Window(2, 0.60, "POSITIVE", "MODERATE"),
                Window(3, 0.40, "POSITIVE", "MODERATE"),
            ),
        ),
        build_cross_position_relationship_change_detection(
            "col1",
            "col3",
            (
                Window(1, -0.80, "NEGATIVE", "STRONG"),
                Window(2, -0.40, "NEGATIVE", "MODERATE"),
                Window(3, 0.20, "POSITIVE", "WEAK"),
            ),
        ),
    )


def make_overview():
    matrix = make_matrix()
    summary = make_summary()

    return build_cross_position_relationship_overview(
        matrix,
        summary,
        make_stability_results(),
        make_change_detection_results(),
    )


def test_build_returns_expected_type():
    assert isinstance(
        make_overview(),
        CrossPositionRelationshipOverview,
    )


def test_positions_are_preserved():
    assert make_overview().positions == make_positions()


def test_position_count_is_preserved():
    assert make_overview().position_count == 4


def test_relationship_count_is_preserved():
    assert make_overview().relationship_count == 6


def test_matrix_relationship_count_is_preserved():
    assert make_overview().matrix_relationship_count == 6


def test_summary_relationship_count_is_preserved():
    assert make_overview().summary_relationship_count == 6


def test_valid_pair_count_is_preserved():
    assert make_overview().total_valid_pair_count == 36


def test_positive_count_is_preserved():
    assert make_overview().positive_count == 1


def test_negative_count_is_preserved():
    assert make_overview().negative_count == 2


def test_neutral_count_is_preserved():
    assert make_overview().neutral_count == 0


def test_insufficient_data_count_is_preserved():
    assert make_overview().insufficient_data_count == 3


def test_strength_counts_are_preserved():
    result = make_overview()

    assert result.none_count == 0
    assert result.weak_count == 2
    assert result.moderate_count == 0
    assert result.strong_count == 1


def test_correlation_summary_values_are_preserved():
    result = make_overview()

    assert result.average_correlation == pytest.approx(
        -1 / 3
    )
    assert result.average_absolute_correlation == pytest.approx(
        0.4543788398670938
    )
    assert result.minimum_correlation == pytest.approx(-1.0)
    assert result.maximum_correlation == pytest.approx(
        0.1815682598006407
    )


def test_stability_results_are_preserved():
    result = make_overview()

    assert len(result.stability_results) == 2
    assert result.stability_results[0].position_a == "col1"
    assert result.stability_results[0].position_b == "col2"


def test_stability_pair_count_is_correct():
    assert make_overview().stability_pair_count == 2


def test_stability_high_count_is_correct():
    assert make_overview().stable_high_count == 2


def test_stability_medium_count_is_zero():
    assert make_overview().stable_medium_count == 0


def test_stability_low_count_is_zero():
    assert make_overview().stable_low_count == 0


def test_stability_insufficient_count_is_zero():
    assert make_overview().stable_insufficient_data_count == 0


def test_change_detection_results_are_preserved():
    assert len(make_overview().change_detection_results) == 2


def test_direction_change_count_is_aggregated():
    assert make_overview().total_direction_change_count == 1


def test_strength_change_count_is_aggregated():
    assert make_overview().total_strength_change_count == 3


def test_relationship_change_count_is_aggregated():
    assert make_overview().total_relationship_change_count == 4


def test_insufficient_data_change_count_is_aggregated():
    assert make_overview().total_insufficient_data_change_count == 0


def test_matrix_object_is_preserved():
    matrix = make_matrix()
    summary = make_summary()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        make_stability_results(),
        make_change_detection_results(),
    )

    assert result.matrix is matrix


def test_summary_object_is_preserved():
    matrix = make_matrix()
    summary = make_summary()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        make_stability_results(),
        make_change_detection_results(),
    )

    assert result.summary is summary


def test_get_stability_result_returns_forward_pair():
    result = make_overview()

    stability = get_stability_result(
        result,
        "col1",
        "col2",
    )

    assert stability.position_a == "col1"
    assert stability.position_b == "col2"


def test_get_stability_result_supports_reverse_pair():
    result = make_overview()

    stability = get_stability_result(
        result,
        "col2",
        "col1",
    )

    assert stability.position_a == "col1"
    assert stability.position_b == "col2"


def test_get_missing_stability_result_raises():
    result = make_overview()

    with pytest.raises(
        ValueError,
        match="Stability result not found",
    ):
        get_stability_result(
            result,
            "col3",
            "col4",
        )


def test_get_change_detection_result_returns_forward_pair():
    result = make_overview()

    detection = get_change_detection_result(
        result,
        "col1",
        "col2",
    )

    assert detection.position_a == "col1"
    assert detection.position_b == "col2"


def test_get_change_detection_result_supports_reverse_pair():
    result = make_overview()

    detection = get_change_detection_result(
        result,
        "col2",
        "col1",
    )

    assert detection.position_a == "col1"
    assert detection.position_b == "col2"


def test_get_missing_change_detection_result_raises():
    result = make_overview()

    with pytest.raises(
        ValueError,
        match="Change detection result not found",
    ):
        get_change_detection_result(
            result,
            "col3",
            "col4",
        )


def test_iter_stability_results_returns_all_results():
    result = make_overview()

    values = iter_stability_results(result)

    assert values == result.stability_results
    assert len(values) == 2


def test_iter_change_detection_results_returns_all_results():
    result = make_overview()

    values = iter_change_detection_results(result)

    assert values == result.change_detection_results
    assert len(values) == 2


def test_empty_stability_results_are_supported():
    matrix = make_matrix()
    summary = make_summary()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        (),
        make_change_detection_results(),
    )

    assert result.stability_pair_count == 0
    assert result.stability_results == ()


def test_empty_change_detection_results_are_supported():
    matrix = make_matrix()
    summary = make_summary()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        make_stability_results(),
        (),
    )

    assert result.change_detection_results == ()
    assert result.total_direction_change_count == 0
    assert result.total_strength_change_count == 0
    assert result.total_relationship_change_count == 0


def test_stability_generator_input_is_supported():
    matrix = make_matrix()
    summary = make_summary()
    stability_results = make_stability_results()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        (item for item in stability_results),
        make_change_detection_results(),
    )

    assert result.stability_results == stability_results


def test_change_detection_generator_input_is_supported():
    matrix = make_matrix()
    summary = make_summary()
    change_results = make_change_detection_results()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        make_stability_results(),
        (item for item in change_results),
    )

    assert result.change_detection_results == change_results


def test_invalid_matrix_type_raises():
    with pytest.raises(
        TypeError,
        match="matrix must be a CrossPositionRelationshipMatrix",
    ):
        build_cross_position_relationship_overview(
            None,
            make_summary(),
            make_stability_results(),
            make_change_detection_results(),
        )


def test_invalid_summary_type_raises():
    with pytest.raises(
        TypeError,
        match="summary must be a CrossPositionRelationshipSummary",
    ):
        build_cross_position_relationship_overview(
            make_matrix(),
            None,
            make_stability_results(),
            make_change_detection_results(),
        )


def test_invalid_stability_result_type_raises():
    with pytest.raises(
        TypeError,
        match="each stability result must be",
    ):
        build_cross_position_relationship_overview(
            make_matrix(),
            make_summary(),
            (None,),
            make_change_detection_results(),
        )


def test_invalid_change_detection_result_type_raises():
    with pytest.raises(
        TypeError,
        match="each change detection result must be",
    ):
        build_cross_position_relationship_overview(
            make_matrix(),
            make_summary(),
            make_stability_results(),
            (None,),
        )


def test_string_stability_results_raise():
    with pytest.raises(
        TypeError,
        match="stability_results must be an iterable",
    ):
        build_cross_position_relationship_overview(
            make_matrix(),
            make_summary(),
            "invalid",
            make_change_detection_results(),
        )


def test_string_change_detection_results_raise():
    with pytest.raises(
        TypeError,
        match="change_detection_results must be an iterable",
    ):
        build_cross_position_relationship_overview(
            make_matrix(),
            make_summary(),
            make_stability_results(),
            "invalid",
        )


def test_matrix_and_summary_positions_must_match():
    matrix = make_matrix()
    summary = make_summary()

    modified_summary = summary.__class__(
        position_count=summary.position_count,
        positions=("col1", "col2"),
        relationship_count=summary.relationship_count,
        total_valid_pair_count=summary.total_valid_pair_count,
        positive_count=summary.positive_count,
        negative_count=summary.negative_count,
        neutral_count=summary.neutral_count,
        insufficient_data_count=summary.insufficient_data_count,
        none_count=summary.none_count,
        weak_count=summary.weak_count,
        moderate_count=summary.moderate_count,
        strong_count=summary.strong_count,
        average_correlation=summary.average_correlation,
        average_absolute_correlation=(
            summary.average_absolute_correlation
        ),
        minimum_correlation=summary.minimum_correlation,
        maximum_correlation=summary.maximum_correlation,
        position_summaries=summary.position_summaries,
    )

    with pytest.raises(
        ValueError,
        match="matrix and summary positions must match",
    ):
        build_cross_position_relationship_overview(
            matrix,
            modified_summary,
            (),
            (),
        )


def test_matrix_and_summary_relationship_counts_must_match():
    matrix = make_matrix()
    summary = make_summary()

    modified_summary = summary.__class__(
        position_count=summary.position_count,
        positions=summary.positions,
        relationship_count=999,
        total_valid_pair_count=summary.total_valid_pair_count,
        positive_count=summary.positive_count,
        negative_count=summary.negative_count,
        neutral_count=summary.neutral_count,
        insufficient_data_count=summary.insufficient_data_count,
        none_count=summary.none_count,
        weak_count=summary.weak_count,
        moderate_count=summary.moderate_count,
        strong_count=summary.strong_count,
        average_correlation=summary.average_correlation,
        average_absolute_correlation=(
            summary.average_absolute_correlation
        ),
        minimum_correlation=summary.minimum_correlation,
        maximum_correlation=summary.maximum_correlation,
        position_summaries=summary.position_summaries,
    )

    with pytest.raises(
        ValueError,
        match="matrix and summary relationship counts must match",
    ):
        build_cross_position_relationship_overview(
            matrix,
            modified_summary,
            (),
            (),
        )


def test_overview_is_immutable():
    result = make_overview()

    with pytest.raises(AttributeError):
        result.position_count = 999


def test_overview_contains_original_matrix_and_summary():
    matrix = make_matrix()
    summary = make_summary()

    result = build_cross_position_relationship_overview(
        matrix,
        summary,
        (),
        (),
    )

    assert result.matrix is matrix
    assert result.summary is summary