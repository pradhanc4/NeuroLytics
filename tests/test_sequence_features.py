from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history
from features.sequence_features import (
    SequenceFeatureResult,
    build_sequence_features,
    get_sequence_feature_names,
    get_sequence_feature_value,
)


def make_observation(
    result_id: int,
    result_date: date,
    values: tuple[int, ...],
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=values,
    )


def make_history(
    observations: tuple[HistoricalFeatureObservation, ...],
    target_date: date = date(2026, 1, 5),
):
    return build_point_in_time_history(
        observations,
        target_date,
    )


def test_sequence_features_return_expected_result_type():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)
    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert isinstance(
        result,
        SequenceFeatureResult,
    )


def test_latest_value_comes_from_latest_historical_row():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_latest_value",
    ) == 9

    assert get_sequence_feature_value(
        result,
        "col8_sequence_latest_value",
    ) == 2


def test_previous_value_comes_from_previous_historical_row():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_previous_value",
    ) == 1

    assert get_sequence_feature_value(
        result,
        "col8_sequence_previous_value",
    ) == 8


def test_transition_is_generated_from_previous_and_latest():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition",
    ) == "1_to_9"

    assert get_sequence_feature_value(
        result,
        "col8_sequence_transition",
    ) == "8_to_2"


def test_transition_distance_is_absolute_digit_difference():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 8, 1, 2, 4, 1, 3, 0),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition_distance",
    ) == 8

    assert get_sequence_feature_value(
        result,
        "col8_sequence_transition_distance",
    ) == 8


def test_changed_flag_is_one_when_digit_changes():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 2, 3, 8, 5, 6, 0, 8),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_changed",
    ) == 1

    assert get_sequence_feature_value(
        result,
        "col2_sequence_changed",
    ) == 0


def test_changed_flag_is_zero_when_digit_repeats():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    for position in (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ):
        assert get_sequence_feature_value(
            result,
            f"{position}_sequence_changed",
        ) == 0


def test_zero_is_treated_as_a_valid_sequence_value():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (0, 1, 2, 3, 4, 5, 6, 7),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (5, 0, 8, 9, 0, 1, 2, 3),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_previous_value",
    ) == 0

    assert get_sequence_feature_value(
        result,
        "col2_sequence_latest_value",
    ) == 0

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition",
    ) == "0_to_5"


def test_insufficient_history_returns_none_for_previous_value():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_previous_value",
    ) is None

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition",
    ) is None

    assert get_sequence_feature_value(
        result,
        "col1_sequence_changed",
    ) is None


def test_transition_counts_are_calculated_inside_configured_window():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        make_observation(
            3,
            date(2026, 1, 3),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    config = FeatureConfig(
        rolling_windows=(3,),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        config,
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_latest_transition_count",
    ) == 1


def test_latest_transition_percentage_is_calculated():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        make_observation(
            3,
            date(2026, 1, 3),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    config = FeatureConfig(
        rolling_windows=(3,),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        config,
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_latest_transition_percentage",
    ) == pytest.approx(50.0)


def test_target_date_row_is_excluded():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        make_observation(
            3,
            date(2026, 1, 5),
            (9, 9, 9, 9, 9, 9, 9, 9),
        ),
    )

    history = make_history(
        observations,
        target_date=date(2026, 1, 5),
    )

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_latest_value",
    ) == 2

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition",
    ) == "1_to_2"


def test_future_row_is_excluded():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        make_observation(
            3,
            date(2026, 1, 6),
            (9, 9, 9, 9, 9, 9, 9, 9),
        ),
    )

    history = make_history(
        observations,
        target_date=date(2026, 1, 5),
    )

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_latest_value",
    ) == 2


def test_missing_calendar_dates_do_not_break_sequence_features():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 3),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = make_history(
        observations,
        target_date=date(2026, 1, 5),
    )

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_value(
        result,
        "col1_sequence_transition",
    ) == "1_to_2"


def test_configured_positions_are_respected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    config = FeatureConfig(
        positions=("col1", "col3"),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        config,
    )

    names = get_sequence_feature_names(
        result
    )

    assert "col1_sequence_latest_value" in names
    assert "col3_sequence_latest_value" in names
    assert "col2_sequence_latest_value" not in names


def test_feature_names_are_deterministic():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = make_history(observations)

    result_a = build_sequence_features(
        history,
        FeatureConfig(),
    )

    result_b = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert get_sequence_feature_names(
        result_a
    ) == get_sequence_feature_names(
        result_b
    )


def test_feature_names_are_unique():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    names = get_sequence_feature_names(
        result
    )

    assert len(names) == len(set(names))


def test_result_target_date_matches_history():
    target_date = date(2026, 2, 1)

    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(
        observations,
        target_date=target_date,
    )

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    assert result.target_date == target_date


def test_invalid_history_type_is_rejected():
    with pytest.raises(TypeError):
        build_sequence_features(
            "invalid",
            FeatureConfig(),
        )


def test_invalid_config_type_is_rejected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)

    with pytest.raises(TypeError):
        build_sequence_features(
            history,
            "invalid",
        )


def test_unknown_feature_name_is_rejected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    with pytest.raises(ValueError):
        get_sequence_feature_value(
            result,
            "does_not_exist",
        )


def test_feature_name_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_sequence_feature_names(
            "invalid",
        )


def test_value_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_sequence_feature_value(
            "invalid",
            "col1_sequence_latest_value",
        )


def test_value_getter_rejects_invalid_feature_name():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = make_history(observations)

    result = build_sequence_features(
        history,
        FeatureConfig(),
    )

    with pytest.raises(TypeError):
        get_sequence_feature_value(
            result,
            123,
        )