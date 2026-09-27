from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history
from features.unified_dataset import (
    UnifiedFeatureDataset,
    build_unified_feature_dataset,
    get_unified_feature_count,
    get_unified_feature_names,
    get_unified_feature_value,
    get_unified_feature_values,
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


def test_unified_dataset_returns_expected_type():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert isinstance(
        result,
        UnifiedFeatureDataset,
    )


def test_unified_dataset_contains_all_feature_engine_types():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    feature_types = {
        record.feature_type
        for record in result.records
    }

    assert feature_types == {
        "lag",
        "rolling",
        "recency",
        "position",
        "frequency",
        "sequence",
        "cross_position",
    }


def test_unified_dataset_contains_all_feature_sources():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    sources = {
        record.source
        for record in result.records
    }

    assert sources == {
        "lag_features",
        "rolling_features",
        "recency_features",
        "position_features",
        "frequency_features",
        "sequence_features",
        "cross_position_features",
    }


def test_unified_feature_names_are_unique():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    names = get_unified_feature_names(
        result
    )

    assert len(names) == len(set(names))


def test_unified_feature_count_matches_records():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_count(
        result
    ) == len(result.records)


def test_unified_dataset_contains_lag_features():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_lag_1",
    ) == 2


def test_unified_dataset_contains_rolling_features():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            make_observation(
                2,
                date(2026, 1, 2),
                (3, 4, 5, 6, 7, 8, 9, 0),
            ),
        )
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_rolling_3_mean",
    ) == pytest.approx(2.0)


def test_unified_dataset_contains_recency_features():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_digit_2_recency",
    ) == 0


def test_unified_dataset_contains_position_features():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_latest_value",
    ) == 2


def test_unified_dataset_contains_frequency_features():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            make_observation(
                2,
                date(2026, 1, 2),
                (1, 3, 4, 5, 6, 7, 8, 9),
            ),
        )
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_digit_1_frequency_count",
    ) == 2


def test_unified_dataset_contains_sequence_features():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_sequence_transition",
    ) == "1_to_2"


def test_unified_dataset_contains_cross_position_features():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_col2_sum",
    ) == 5


def test_zero_values_are_preserved_in_unified_dataset():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (0, 1, 2, 3, 4, 5, 6, 7),
            ),
            make_observation(
                2,
                date(2026, 1, 2),
                (0, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_latest_value",
    ) == 0

    assert get_unified_feature_value(
        result,
        "col1_col2_sum",
    ) == 2


def test_target_date_is_preserved():
    target_date = date(2026, 1, 5)

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

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert result.target_date == target_date


def test_target_date_row_is_not_used():
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

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_latest_value",
    ) == 1


def test_future_row_is_not_used():
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

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_value(
        result,
        "col1_latest_value",
    ) == 1


def test_feature_version_is_taken_from_config():
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
        feature_version="v-test-001",
    )

    result = build_unified_feature_dataset(
        history,
        config,
    )

    assert result.feature_version == "v-test-001"


def test_configured_positions_are_respected():
    history = make_history(
        (
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
    )

    config = FeatureConfig(
        positions=("col1", "col2"),
    )

    result = build_unified_feature_dataset(
        history,
        config,
    )

    names = get_unified_feature_names(
        result
    )

    assert all(
        name.startswith(
            ("col1_", "col2_")
        )
        for name in names
    )


def test_unified_feature_values_returns_mapping():
    history = make_history(
        (
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
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    values = get_unified_feature_values(
        result
    )

    assert isinstance(values, dict)
    assert values["col1_latest_value"] == 2


def test_empty_history_is_supported():
    history = make_history(())

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert isinstance(
        result,
        UnifiedFeatureDataset,
    )

    assert get_unified_feature_count(
        result
    ) > 0


def test_feature_records_have_metadata():
    history = make_history(
        (
            make_observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    for record in result.records:
        assert record.feature_name
        assert record.feature_type
        assert record.source


def test_feature_names_are_deterministic():
    history = make_history(
        (
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
    )

    result_a = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    result_b = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    assert get_unified_feature_names(
        result_a
    ) == get_unified_feature_names(
        result_b
    )


def test_invalid_history_type_is_rejected():
    with pytest.raises(TypeError):
        build_unified_feature_dataset(
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
        build_unified_feature_dataset(
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

    result = build_unified_feature_dataset(
        history,
        FeatureConfig(),
    )

    with pytest.raises(ValueError):
        get_unified_feature_value(
            result,
            "does_not_exist",
        )


def test_feature_name_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_unified_feature_names(
            "invalid",
        )


def test_feature_value_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_unified_feature_value(
            "invalid",
            "col1_latest_value",
        )


def test_feature_values_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_unified_feature_values(
            "invalid",
        )


def test_feature_count_getter_rejects_invalid_result():
    with pytest.raises(TypeError):
        get_unified_feature_count(
            "invalid",
        )