from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.frequency_concentration_features import (
    FrequencyConcentrationFeatureResult,
    build_frequency_concentration_features,
    get_frequency_concentration_feature_names,
    get_frequency_concentration_feature_value,
    get_frequency_concentration_records,
)
from features.historical_data_loader import HistoricalFeatureObservation


def _observation(
    result_id: int,
    result_date: date,
    values: dict[str, int],
) -> HistoricalFeatureObservation:
    positions = (
        values.get("col1", 0),
        values.get("col2", 0),
        values.get("col3", 0),
        values.get("col4", 0),
        values.get("col5", 0),
        values.get("col6", 0),
        values.get("col7", 0),
        values.get("col8", 0),
    )

    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=positions,
    )


def _config(
    positions: tuple[str, ...] = ("col1",),
    frequency_windows: tuple[int, ...] = (3, 5),
) -> FeatureConfig:
    return FeatureConfig(
        positions=positions,
        frequency_windows=frequency_windows,
    )


def _name(
    position: str,
    metric: str,
    window: int,
) -> str:
    return f"{position}_frequency_{metric}_{window}"


def test_build_returns_expected_result_type():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(),
    )

    assert isinstance(
        result,
        FrequencyConcentrationFeatureResult,
    )


def test_dominant_digit_is_detected():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 2}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
        _observation(3, date(2026, 1, 3), {"col1": 5}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 4),
        history=history,
        config=_config(frequency_windows=(3,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 3),
    ) == 2


def test_dominant_percentage_is_detected():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 2}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
        _observation(3, date(2026, 1, 3), {"col1": 5}),
        _observation(4, date(2026, 1, 4), {"col1": 7}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(frequency_windows=(4,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_percentage", 4),
    ) == 50.0


def test_entropy_uses_base_two():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(frequency_windows=(2,)),
    )

    entropy = get_frequency_concentration_feature_value(
        result,
        _name("col1", "entropy", 2),
    )

    assert entropy == pytest.approx(1.0)


def test_normalized_entropy_is_between_zero_and_one():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 0}),
        _observation(2, date(2026, 1, 2), {"col1": 1}),
        _observation(3, date(2026, 1, 3), {"col1": 2}),
        _observation(4, date(2026, 1, 4), {"col1": 3}),
        _observation(5, date(2026, 1, 5), {"col1": 4}),
        _observation(6, date(2026, 1, 6), {"col1": 5}),
        _observation(7, date(2026, 1, 7), {"col1": 6}),
        _observation(8, date(2026, 1, 8), {"col1": 7}),
        _observation(9, date(2026, 1, 9), {"col1": 8}),
        _observation(10, date(2026, 1, 10), {"col1": 9}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 11),
        history=history,
        config=_config(frequency_windows=(10,)),
    )

    normalized = get_frequency_concentration_feature_value(
        result,
        _name("col1", "normalized_entropy", 10),
    )

    assert normalized == pytest.approx(1.0)


def test_concentrated_regime_matches_existing_phase_9_definition():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 4}),
        _observation(2, date(2026, 1, 2), {"col1": 4}),
        _observation(3, date(2026, 1, 3), {"col1": 4}),
        _observation(4, date(2026, 1, 4), {"col1": 4}),
        _observation(5, date(2026, 1, 5), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 6),
        history=history,
        config=_config(frequency_windows=(5,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "concentration_level", 5),
    ) == "CONCENTRATED"


def test_diverse_regime_matches_existing_phase_9_definition():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 0}),
        _observation(2, date(2026, 1, 2), {"col1": 1}),
        _observation(3, date(2026, 1, 3), {"col1": 2}),
        _observation(4, date(2026, 1, 4), {"col1": 3}),
        _observation(5, date(2026, 1, 5), {"col1": 4}),
        _observation(6, date(2026, 1, 6), {"col1": 5}),
        _observation(7, date(2026, 1, 7), {"col1": 6}),
        _observation(8, date(2026, 1, 8), {"col1": 7}),
        _observation(9, date(2026, 1, 9), {"col1": 8}),
        _observation(10, date(2026, 1, 10), {"col1": 9}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 11),
        history=history,
        config=_config(frequency_windows=(10,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "diversity_level", 10),
    ) == "DIVERSE"


def test_same_regime_is_exposed_for_concentration_and_diversity():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 4}),
        _observation(2, date(2026, 1, 2), {"col1": 4}),
        _observation(3, date(2026, 1, 3), {"col1": 4}),
        _observation(4, date(2026, 1, 4), {"col1": 4}),
        _observation(5, date(2026, 1, 5), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 6),
        history=history,
        config=_config(frequency_windows=(5,)),
    )

    concentration = get_frequency_concentration_feature_value(
        result,
        _name("col1", "concentration_level", 5),
    )

    diversity = get_frequency_concentration_feature_value(
        result,
        _name("col1", "diversity_level", 5),
    )

    assert concentration == diversity


def test_zero_is_counted_as_valid_digit():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 0}),
        _observation(2, date(2026, 1, 2), {"col1": 0}),
        _observation(3, date(2026, 1, 3), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 4),
        history=history,
        config=_config(frequency_windows=(3,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 3),
    ) == 0

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_percentage", 3),
    ) == pytest.approx(66.6666666667)


def test_target_date_is_never_used():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 2), {"col1": 9}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(frequency_windows=(1,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 1),
    ) == 1


def test_future_observation_is_never_used():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 3), {"col1": 9}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(frequency_windows=(1,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 1),
    ) == 1


def test_window_is_limited_to_requested_observations():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 7}),
        _observation(2, date(2026, 1, 2), {"col1": 7}),
        _observation(3, date(2026, 1, 3), {"col1": 2}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 4),
        history=history,
        config=_config(frequency_windows=(1,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 1),
    ) == 2


def test_multiple_windows_are_supported():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
        _observation(3, date(2026, 1, 3), {"col1": 2}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 4),
        history=history,
        config=_config(frequency_windows=(1, 3)),
    )

    names = get_frequency_concentration_feature_names(result)

    assert _name("col1", "dominant_digit", 1) in names
    assert _name("col1", "dominant_digit", 3) in names


def test_multiple_positions_are_supported():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {
                "col1": 1,
                "col2": 2,
            },
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {
                "col1": 1,
                "col2": 3,
            },
        ),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(
            positions=("col1", "col2"),
            frequency_windows=(2,),
        ),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 2),
    ) == 1

    assert get_frequency_concentration_feature_value(
        result,
        _name("col2", "dominant_digit", 2),
    ) == 2


def test_empty_history_returns_insufficient_data():
    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(frequency_windows=(3,)),
    )

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 3),
    ) is None

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_percentage", 3),
    ) is None

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "entropy", 3),
    ) is None

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "normalized_entropy", 3),
    ) is None

    assert get_frequency_concentration_feature_value(
        result,
        _name("col1", "concentration_level", 3),
    ) == "INSUFFICIENT_DATA"


def test_feature_values_have_expected_types():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(frequency_windows=(2,)),
    )

    dominant = get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_digit", 2),
    )

    percentage = get_frequency_concentration_feature_value(
        result,
        _name("col1", "dominant_percentage", 2),
    )

    entropy = get_frequency_concentration_feature_value(
        result,
        _name("col1", "entropy", 2),
    )

    normalized = get_frequency_concentration_feature_value(
        result,
        _name("col1", "normalized_entropy", 2),
    )

    assert isinstance(dominant, int)
    assert isinstance(percentage, float)
    assert isinstance(entropy, float)
    assert isinstance(normalized, float)


def test_feature_names_are_deterministic():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
        _observation(2, date(2026, 1, 2), {"col1": 2}),
    ]

    result1 = build_frequency_concentration_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(frequency_windows=(2,)),
    )

    result2 = build_frequency_concentration_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(frequency_windows=(2,)),
    )

    assert get_frequency_concentration_feature_names(
        result1
    ) == get_frequency_concentration_feature_names(result2)


def test_expected_feature_count():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(
            positions=("col1",),
            frequency_windows=(3, 5),
        ),
    )

    assert len(result.records) == 12


def test_expected_feature_count_for_all_positions():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(
            positions=(
                "col1",
                "col2",
                "col3",
                "col4",
                "col5",
                "col6",
                "col7",
                "col8",
            ),
            frequency_windows=(3,),
        ),
    )

    assert len(result.records) == 48


def test_records_are_immutable():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(frequency_windows=(3,)),
    )

    with pytest.raises(AttributeError):
        result.records = ()


def test_get_records_returns_result_records():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(frequency_windows=(3,)),
    )

    assert get_frequency_concentration_records(result) == result.records


def test_missing_feature_raises_value_error():
    history = [
        _observation(1, date(2026, 1, 1), {"col1": 1}),
    ]

    result = build_frequency_concentration_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(frequency_windows=(3,)),
    )

    with pytest.raises(ValueError):
        get_frequency_concentration_feature_value(
            result,
            "does_not_exist",
        )


def test_invalid_target_date_is_rejected():
    with pytest.raises(TypeError):
        build_frequency_concentration_features(
            target_date="2026-01-01",
            history=[],
            config=_config(),
        )


def test_invalid_history_is_rejected():
    with pytest.raises(TypeError):
        build_frequency_concentration_features(
            target_date=date(2026, 1, 1),
            history=None,
            config=_config(),
        )


def test_invalid_config_is_rejected():
    with pytest.raises(TypeError):
        build_frequency_concentration_features(
            target_date=date(2026, 1, 1),
            history=[],
            config=None,
        )


def test_result_target_date_is_preserved():
    target_date = date(2026, 2, 15)

    result = build_frequency_concentration_features(
        target_date=target_date,
        history=[],
        config=_config(frequency_windows=(3,)),
    )

    assert result.target_date == target_date