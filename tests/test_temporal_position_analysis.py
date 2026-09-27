from datetime import date

import pytest

from analytics.temporal_position_analysis import (
    TemporalPositionAnalysis,
    TemporalPositionAnalysisResult,
    build_temporal_position_analysis,
    get_temporal_position_analysis,
    iter_temporal_position_analyses,
)


def test_basic_temporal_analysis():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 3),
                (date(2026, 1, 3), 2),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.observation_count == 3
    assert analysis.first_date == date(2026, 1, 1)
    assert analysis.latest_date == date(2026, 1, 3)
    assert analysis.first_value == 1
    assert analysis.latest_value == 2
    assert analysis.minimum == 1
    assert analysis.maximum == 3
    assert analysis.mean == 2.0
    assert analysis.first_to_latest_change == 1
    assert analysis.absolute_first_to_latest_change == 1


def test_observations_are_sorted_chronologically():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 3), 5),
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 3),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.first_date == date(2026, 1, 1)
    assert analysis.latest_date == date(2026, 1, 3)
    assert analysis.first_value == 1
    assert analysis.latest_value == 5


def test_increase_decrease_unchanged_counts():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 3),
                (date(2026, 1, 3), 3),
                (date(2026, 1, 4), 2),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.change_count == 3
    assert analysis.increase_count == 1
    assert analysis.decrease_count == 1
    assert analysis.unchanged_count == 1
    assert analysis.increase_percentage == pytest.approx(100 / 3)
    assert analysis.decrease_percentage == pytest.approx(100 / 3)
    assert analysis.unchanged_percentage == pytest.approx(100 / 3)


def test_average_absolute_step_change():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 4),
                (date(2026, 1, 3), 2),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.average_absolute_step_change == 2.5
    assert analysis.maximum_absolute_step_change == 3


def test_single_observation_has_no_step_changes():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 7),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.observation_count == 1
    assert analysis.change_count == 0
    assert analysis.increase_count == 0
    assert analysis.decrease_count == 0
    assert analysis.unchanged_count == 0
    assert analysis.average_absolute_step_change == 0.0
    assert analysis.maximum_absolute_step_change == 0
    assert analysis.increase_percentage == 0.0
    assert analysis.decrease_percentage == 0.0
    assert analysis.unchanged_percentage == 0.0


def test_empty_position():
    result = build_temporal_position_analysis(
        {
            "col1": (),
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.observation_count == 0
    assert analysis.first_date is None
    assert analysis.latest_date is None
    assert analysis.first_value is None
    assert analysis.latest_value is None
    assert analysis.minimum is None
    assert analysis.maximum is None
    assert analysis.mean == 0.0
    assert analysis.standard_deviation == 0.0


def test_none_values_are_not_converted_to_zero():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), None),
                (date(2026, 1, 2), 0),
                (date(2026, 1, 3), 2),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.observation_count == 2
    assert analysis.first_value == 0
    assert analysis.latest_value == 2
    assert analysis.minimum == 0
    assert analysis.maximum == 2


def test_zero_is_a_valid_value():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 0),
                (date(2026, 1, 2), 2),
                (date(2026, 1, 3), 0),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.observation_count == 3
    assert analysis.first_value == 0
    assert analysis.latest_value == 0
    assert analysis.minimum == 0
    assert analysis.maximum == 2


def test_standard_deviation_uses_population_formula():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
                (date(2026, 1, 3), 3),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.standard_deviation == pytest.approx(
        (2 / 3) ** 0.5
    )


def test_all_positions_can_be_analyzed():
    observations = {
        f"col{i}": (
            (date(2026, 1, 1), i % 10),
            (date(2026, 1, 2), (i + 1) % 10),
        )
        for i in range(1, 9)
    }

    result = build_temporal_position_analysis(observations)

    assert result.position_count == 8
    assert result.positions == (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    )


def test_positions_follow_analysis_column_order():
    result = build_temporal_position_analysis(
        {
            "col4": ((date(2026, 1, 1), 4),),
            "col1": ((date(2026, 1, 1), 1),),
            "col8": ((date(2026, 1, 1), 8),),
        }
    )

    assert result.positions == (
        "col1",
        "col4",
        "col8",
    )


def test_duplicate_dates_are_rejected():
    with pytest.raises(
        ValueError,
        match="duplicate dates",
    ):
        build_temporal_position_analysis(
            {
                "col1": (
                    (date(2026, 1, 1), 1),
                    (date(2026, 1, 1), 2),
                )
            }
        )


def test_unknown_position_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unknown positions",
    ):
        build_temporal_position_analysis(
            {
                "col9": (
                    (date(2026, 1, 1), 1),
                )
            }
        )


def test_invalid_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_analysis([])


def test_invalid_observation_shape_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_analysis(
            {
                "col1": (
                    (date(2026, 1, 1), 1, 2),
                )
            }
        )


def test_invalid_date_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_analysis(
            {
                "col1": (
                    ("2026-01-01", 1),
                )
            }
        )


def test_boolean_value_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_analysis(
            {
                "col1": (
                    (date(2026, 1, 1), True),
                )
            }
        )


def test_out_of_range_value_is_rejected():
    with pytest.raises(ValueError):
        build_temporal_position_analysis(
            {
                "col1": (
                    (date(2026, 1, 1), 10),
                )
            }
        )


def test_negative_value_is_rejected():
    with pytest.raises(ValueError):
        build_temporal_position_analysis(
            {
                "col1": (
                    (date(2026, 1, 1), -1),
                )
            }
        )


def test_result_is_frozen():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            )
        }
    )

    with pytest.raises((AttributeError, TypeError)):
        result.position_count = 99


def test_analysis_is_frozen():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            )
        }
    )

    analysis = result.analyses[0]

    with pytest.raises((AttributeError, TypeError)):
        analysis.mean = 99.0


def test_get_unknown_position_is_rejected():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        get_temporal_position_analysis(
            result,
            "col2",
        )


def test_iterator_returns_tuple():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            ),
            "col2": (
                (date(2026, 1, 1), 2),
            ),
        }
    )

    analyses = iter_temporal_position_analyses(result)

    assert isinstance(analyses, tuple)
    assert len(analyses) == 2


def test_invalid_result_for_getter_is_rejected():
    with pytest.raises(TypeError):
        get_temporal_position_analysis(
            object(),
            "col1",
        )


def test_invalid_result_for_iterator_is_rejected():
    with pytest.raises(TypeError):
        iter_temporal_position_analyses(object())


def test_descriptive_only_no_prediction_fields():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            )
        }
    )

    assert not hasattr(result, "prediction")
    assert not hasattr(result, "score")
    assert not hasattr(result, "rank")
    assert not hasattr(result, "recommended_position")


def test_negative_first_to_latest_change_is_preserved():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 8),
                (date(2026, 1, 2), 3),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert analysis.first_to_latest_change == -5
    assert analysis.absolute_first_to_latest_change == 5


def test_percentage_components_sum_to_100():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
                (date(2026, 1, 3), 2),
                (date(2026, 1, 4), 1),
            )
        }
    )

    analysis = get_temporal_position_analysis(
        result,
        "col1",
    )

    assert (
        analysis.increase_percentage
        + analysis.decrease_percentage
        + analysis.unchanged_percentage
    ) == pytest.approx(100.0)


def test_dataclass_types_are_correct():
    result = build_temporal_position_analysis(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            )
        }
    )

    assert isinstance(result, TemporalPositionAnalysisResult)
    assert isinstance(result.analyses[0], TemporalPositionAnalysis)