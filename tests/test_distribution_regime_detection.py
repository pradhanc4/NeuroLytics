from datetime import date

import pytest

from analytics.distribution_regime_detection import (
    DEFAULT_WINDOW_SIZE,
    DistributionRegimeDetection,
    DistributionRegimeDetectionResult,
    DistributionRegimeWindow,
    build_distribution_regime_detection,
    build_distribution_regime_detection_result,
    get_distribution_regime_detection,
    get_distribution_regime_window,
    iter_distribution_regime_detections,
    iter_distribution_regime_windows,
)


def make_observations():
    return (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), 1),
        (date(2026, 1, 3), 1),
        (date(2026, 1, 4), 1),
        (date(2026, 1, 5), 2),
        (date(2026, 1, 6), 2),
        (date(2026, 1, 7), 3),
        (date(2026, 1, 8), 4),
        (date(2026, 1, 9), 5),
        (date(2026, 1, 10), 6),
    )


def test_default_window_size_is_five():
    assert DEFAULT_WINDOW_SIZE == 5


def test_build_returns_expected_type():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
    )

    assert isinstance(
        result,
        DistributionRegimeDetection,
    )


def test_position_is_preserved():
    result = build_distribution_regime_detection(
        "col3",
        make_observations(),
    )

    assert result.position == "col3"


def test_window_size_is_preserved():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    assert result.window_size == 3


def test_window_count_uses_sequential_windows():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    assert result.window_count == 4


def test_final_partial_window_is_preserved():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    assert result.windows[-1].observation_count == 1


def test_windows_are_numbered_from_one():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    assert tuple(
        window.window_index
        for window in result.windows
    ) == (1, 2, 3, 4)


def test_observations_are_processed_chronologically():
    observations = (
        (date(2026, 1, 3), 3),
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), 2),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=2,
    )

    assert result.windows[0].start_date == date(
        2026,
        1,
        1,
    )
    assert result.windows[0].end_date == date(
        2026,
        1,
        2,
    )


def test_window_dates_are_preserved():
    result = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=5,
    )

    first = result.windows[0]

    assert first.start_date == date(
        2026,
        1,
        1,
    )
    assert first.end_date == date(
        2026,
        1,
        5,
    )


def test_zero_is_counted_as_valid_digit():
    observations = (
        (date(2026, 1, 1), 0),
        (date(2026, 1, 2), 0),
        (date(2026, 1, 3), 1),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=3,
    )

    window = result.windows[0]

    assert window.observation_count == 3
    assert window.frequency_total == 3
    assert window.dominant_digit == 0


def test_none_is_not_converted_to_zero():
    observations = (
        (date(2026, 1, 1), None),
        (date(2026, 1, 2), 1),
        (date(2026, 1, 3), 1),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=3,
    )

    window = result.windows[0]

    assert window.observation_count == 2
    assert window.frequency_total == 2
    assert window.dominant_digit == 1


def test_all_missing_values_produce_insufficient_data():
    observations = (
        (date(2026, 1, 1), None),
        (date(2026, 1, 2), None),
        (date(2026, 1, 3), None),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=3,
    )

    window = result.windows[0]

    assert window.observation_count == 0
    assert window.frequency_total == 0
    assert window.dominant_digit is None
    assert window.dominant_digit_percentage is None
    assert window.distribution_mean is None
    assert window.distribution_std is None
    assert window.entropy is None
    assert window.regime == "INSUFFICIENT_DATA"


def test_dominant_digit_percentage_is_calculated():
    observations = (
        (date(2026, 1, 1), 7),
        (date(2026, 1, 2), 7),
        (date(2026, 1, 3), 7),
        (date(2026, 1, 4), 7),
        (date(2026, 1, 5), 1),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=5,
    )

    assert result.windows[0].dominant_digit_percentage == pytest.approx(
        80.0
    )


def test_distribution_mean_is_calculated():
    observations = (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), 2),
        (date(2026, 1, 3), 3),
        (date(2026, 1, 4), 4),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=4,
    )

    assert result.windows[0].distribution_mean == pytest.approx(
        2.5
    )


def test_distribution_std_is_population_standard_deviation():
    observations = (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), 2),
        (date(2026, 1, 3), 3),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=3,
    )

    assert result.windows[0].distribution_std == pytest.approx(
        0.816496580927726
    )


def test_uniform_four_digit_distribution_has_entropy_two():
    observations = (
        (date(2026, 1, 1), 0),
        (date(2026, 1, 2), 1),
        (date(2026, 1, 3), 2),
        (date(2026, 1, 4), 3),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=4,
    )

    assert result.windows[0].entropy == pytest.approx(
        2.0
    )


def test_concentrated_regime_is_detected():
    observations = (
        (date(2026, 1, 1), 5),
        (date(2026, 1, 2), 5),
        (date(2026, 1, 3), 5),
        (date(2026, 1, 4), 5),
        (date(2026, 1, 5), 1),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=5,
    )

    assert result.windows[0].regime == "CONCENTRATED"


def test_balanced_regime_is_detected():
    observations = (
        (date(2026, 1, 1), 0),
        (date(2026, 1, 2), 0),
        (date(2026, 1, 3), 1),
        (date(2026, 1, 4), 1),
        (date(2026, 1, 5), 2),
        (date(2026, 1, 6), 2),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=6,
    )

    assert result.windows[0].regime == "BALANCED"


def test_diverse_regime_is_detected():
    observations = tuple(
        (date(2026, 1, day + 1), digit)
        for day, digit in enumerate(
            (
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
            )
        )
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=10,
    )

    assert result.windows[0].regime == "DIVERSE"


def test_valid_window_count_excludes_insufficient_windows():
    observations = (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), 1),
        (date(2026, 1, 3), 1),
        (date(2026, 1, 4), 1),
        (date(2026, 1, 5), 1),
        (date(2026, 1, 6), None),
        (date(2026, 1, 7), None),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=5,
    )

    assert result.window_count == 2
    assert result.valid_window_count == 1


def test_result_builder_returns_expected_type():
    observations = {
        "col1": make_observations(),
        "col2": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
        window_size=5,
    )

    assert isinstance(
        result,
        DistributionRegimeDetectionResult,
    )


def test_result_builder_preserves_positions():
    observations = {
        "col3": make_observations(),
        "col1": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
        window_size=5,
    )

    assert result.positions == (
        "col3",
        "col1",
    )


def test_result_builder_preserves_position_count():
    observations = {
        "col1": make_observations(),
        "col2": make_observations(),
        "col3": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
        window_size=5,
    )

    assert result.position_count == 3


def test_get_detection_returns_requested_position():
    observations = {
        "col1": make_observations(),
        "col2": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
        window_size=5,
    )

    detection = get_distribution_regime_detection(
        result,
        "col2",
    )

    assert detection.position == "col2"


def test_iter_detections_returns_all_detections():
    observations = {
        "col1": make_observations(),
        "col2": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
        window_size=5,
    )

    detections = iter_distribution_regime_detections(
        result
    )

    assert detections == result.detections
    assert len(detections) == 2


def test_get_window_returns_requested_window():
    detection = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    window = get_distribution_regime_window(
        detection,
        2,
    )

    assert window.window_index == 2


def test_iter_windows_returns_all_windows():
    detection = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    windows = iter_distribution_regime_windows(
        detection
    )

    assert windows == detection.windows
    assert len(windows) == 4


def test_invalid_position_type_raises():
    with pytest.raises(
        TypeError,
        match="position must be a string",
    ):
        build_distribution_regime_detection(
            123,
            make_observations(),
        )


def test_invalid_position_raises():
    with pytest.raises(
        ValueError,
        match="unsupported position",
    ):
        build_distribution_regime_detection(
            "invalid",
            make_observations(),
        )


def test_boolean_window_size_is_rejected():
    with pytest.raises(
        TypeError,
        match="window_size must be an integer",
    ):
        build_distribution_regime_detection(
            "col1",
            make_observations(),
            window_size=True,
        )


def test_zero_window_size_is_rejected():
    with pytest.raises(
        ValueError,
        match="window_size must be greater than zero",
    ):
        build_distribution_regime_detection(
            "col1",
            make_observations(),
            window_size=0,
        )


def test_negative_window_size_is_rejected():
    with pytest.raises(
        ValueError,
        match="window_size must be greater than zero",
    ):
        build_distribution_regime_detection(
            "col1",
            make_observations(),
            window_size=-1,
        )


def test_duplicate_dates_are_rejected():
    observations = (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 1), 2),
    )

    with pytest.raises(
        ValueError,
        match="duplicate observation dates",
    ):
        build_distribution_regime_detection(
            "col1",
            observations,
            window_size=2,
        )


def test_invalid_digit_is_rejected():
    observations = (
        (date(2026, 1, 1), 10),
    )

    with pytest.raises(
        ValueError,
        match="between 0 and 9",
    ):
        build_distribution_regime_detection(
            "col1",
            observations,
        )


def test_boolean_digit_is_rejected():
    observations = (
        (date(2026, 1, 1), True),
    )

    with pytest.raises(
        TypeError,
        match="integer or None",
    ):
        build_distribution_regime_detection(
            "col1",
            observations,
        )


def test_non_integer_digit_is_rejected():
    observations = (
        (date(2026, 1, 1), 1.5),
    )

    with pytest.raises(
        TypeError,
        match="integer or None",
    ):
        build_distribution_regime_detection(
            "col1",
            observations,
        )


def test_invalid_date_is_rejected():
    observations = (
        ("2026-01-01", 1),
    )

    with pytest.raises(
        TypeError,
        match="observation date must be a date",
    ):
        build_distribution_regime_detection(
            "col1",
            observations,
        )


def test_string_observations_are_rejected():
    with pytest.raises(
        TypeError,
        match="observations must be an iterable",
    ):
        build_distribution_regime_detection(
            "col1",
            "invalid",
        )


def test_invalid_mapping_type_is_rejected():
    with pytest.raises(
        TypeError,
        match="observations_by_position must be a mapping",
    ):
        build_distribution_regime_detection_result(
            [],
        )


def test_missing_detection_raises():
    observations = {
        "col1": make_observations(),
    }

    result = build_distribution_regime_detection_result(
        observations,
    )

    with pytest.raises(
        ValueError,
        match="Distribution regime detection not found",
    ):
        get_distribution_regime_detection(
            result,
            "col2",
        )


def test_missing_window_raises():
    detection = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    with pytest.raises(
        ValueError,
        match="Distribution regime window not found",
    ):
        get_distribution_regime_window(
            detection,
            99,
        )


def test_window_index_boolean_is_rejected():
    detection = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    with pytest.raises(
        TypeError,
        match="window_index must be an integer",
    ):
        get_distribution_regime_window(
            detection,
            True,
        )


def test_window_index_non_integer_is_rejected():
    detection = build_distribution_regime_detection(
        "col1",
        make_observations(),
        window_size=3,
    )

    with pytest.raises(
        TypeError,
        match="window_index must be an integer",
    ):
        get_distribution_regime_window(
            detection,
            1.5,
        )


def test_detection_type_validation():
    with pytest.raises(
        TypeError,
        match="result must be a DistributionRegimeDetectionResult",
    ):
        get_distribution_regime_detection(
            None,
            "col1",
        )


def test_detection_iterator_type_validation():
    with pytest.raises(
        TypeError,
        match="result must be a DistributionRegimeDetectionResult",
    ):
        iter_distribution_regime_detections(None)


def test_window_type_validation():
    with pytest.raises(
        TypeError,
        match="detection must be a DistributionRegimeDetection",
    ):
        get_distribution_regime_window(
            None,
            1,
        )


def test_window_iterator_type_validation():
    with pytest.raises(
        TypeError,
        match="detection must be a DistributionRegimeDetection",
    ):
        iter_distribution_regime_windows(None)


def test_empty_observations_produce_no_windows():
    result = build_distribution_regime_detection(
        "col1",
        (),
        window_size=5,
    )

    assert result.window_count == 0
    assert result.valid_window_count == 0
    assert result.windows == ()


def test_window_observation_count_excludes_missing_values():
    observations = (
        (date(2026, 1, 1), 1),
        (date(2026, 1, 2), None),
        (date(2026, 1, 3), 2),
        (date(2026, 1, 4), None),
    )

    result = build_distribution_regime_detection(
        "col1",
        observations,
        window_size=4,
    )

    assert result.windows[0].observation_count == 2
    assert result.windows[0].frequency_total == 2