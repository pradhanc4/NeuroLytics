from datetime import date

import pytest

from features.cross_position_features import (
    CrossPositionFeatureResult,
    build_cross_position_features,
    get_cross_position_feature_names,
    get_cross_position_feature_value,
)
from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history


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


def test_cross_position_features_return_expected_result_type():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert isinstance(
        result,
        CrossPositionFeatureResult,
    )


def test_equal_feature_is_one_for_equal_digits():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (5, 5, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_equal",
    ) == 1


def test_equal_feature_is_zero_for_different_digits():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 5, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_equal",
    ) == 0


def test_absolute_difference_is_calculated():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (2, 8, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_absolute_difference",
    ) == 6


def test_sum_is_calculated():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (2, 8, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_sum",
    ) == 10


def test_order_returns_one_when_first_position_is_greater():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (8, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_order",
    ) == 1


def test_order_returns_minus_one_when_first_position_is_smaller():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (2, 8, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_order",
    ) == -1


def test_order_returns_zero_when_values_are_equal():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (5, 5, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_order",
    ) == 0


def test_same_parity_is_detected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (2, 8, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_same_parity",
    ) == 1


def test_different_parity_is_detected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (2, 7, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_same_parity",
    ) == 0


def test_same_zero_state_is_detected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (0, 0, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_same_zero_state",
    ) == 1


def test_zero_and_nonzero_have_different_zero_state():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (0, 5, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_same_zero_state",
    ) == 0


def test_zero_is_treated_as_a_valid_value():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (0, 5, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_absolute_difference",
    ) == 5

    assert get_cross_position_feature_value(
        result,
        "col1_col2_sum",
    ) == 5


def test_target_date_row_is_excluded():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            make_observation(
                2,
                date(2026, 1, 5),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        target_date=date(2026, 1, 5),
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_equal",
    ) == 0

    assert get_cross_position_feature_value(
        result,
        "col1_col2_sum",
    ) == 3


def test_future_row_is_excluded():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            make_observation(
                2,
                date(2026, 1, 6),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        target_date=date(2026, 1, 5),
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_sum",
    ) == 3


def test_no_history_returns_none_values():
    history = make_history(())

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_value(
        result,
        "col1_col2_equal",
    ) is None

    assert get_cross_position_feature_value(
        result,
        "col1_col2_sum",
    ) is None


def test_configured_positions_are_respected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    config = FeatureConfig(
        positions=("col1", "col3"),
    )

    result = build_cross_position_features(
        history,
        config,
    )

    names = get_cross_position_feature_names(
        result
    )

    assert "col1_col3_equal" in names
    assert "col1_col2_equal" not in names
    assert "col2_col3_equal" not in names


def test_all_unique_position_pairs_are_generated():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    names = get_cross_position_feature_names(
        result
    )

    pair_names = {
        "_".join(name.split("_")[:2])
        for name in names
    }

    assert len(pair_names) == 28


def test_feature_names_are_unique():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    names = get_cross_position_feature_names(
        result
    )

    assert len(names) == len(set(names))


def test_feature_names_are_deterministic():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result_a = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    result_b = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert get_cross_position_feature_names(
        result_a
    ) == get_cross_position_feature_names(
        result_b
    )


def test_result_target_date_matches_history():
    target_date = date(2026, 2, 1)

    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=target_date,
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    assert result.target_date == target_date


def test_invalid_history_type_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_features(
            "invalid",
            FeatureConfig(),
        )


def test_invalid_config_type_is_rejected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    with pytest.raises(TypeError):
        build_cross_position_features(
            history,
            "invalid",
        )


def test_unknown_feature_name_is_rejected():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    with pytest.raises(ValueError):
        get_cross_position_feature_value(
            result,
            "does_not_exist",
        )


def test_names_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_cross_position_feature_names(
            "invalid",
        )


def test_value_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_cross_position_feature_value(
            "invalid",
            "col1_col2_equal",
        )


def test_value_getter_rejects_invalid_feature_name():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_cross_position_features(
        history,
        FeatureConfig(),
    )

    with pytest.raises(TypeError):
        get_cross_position_feature_value(
            result,
            123,
        )