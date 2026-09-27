from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.leakage_detector import (
    CLEAN,
    DUPLICATE_DATE,
    FUTURE_ROW,
    LEAKAGE,
    TARGET_DATE_INCLUDED,
    TEMPORAL_ORDER,
    LeakageDetectionResult,
    detect_history_leakage,
    detect_point_in_time_history_leakage,
    get_leakage_issue_count,
    get_leakage_issues,
    get_leakage_status,
    is_leakage_free,
)
from features.point_in_time import (
    build_point_in_time_history,
)


def make_observation(
    result_id: int,
    result_date: date,
    values: tuple[int, ...] = (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ),
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=values,
    )


def test_clean_history_returns_clean_status():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == CLEAN


def test_clean_history_has_no_issues():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 3),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.issues == ()


def test_clean_history_is_leakage_free():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert is_leakage_free(result) is True


def test_future_row_is_detected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 6),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == FUTURE_ROW
        for issue in result.issues
    )


def test_future_row_reports_correct_date():
    future_date = date(2026, 1, 6)

    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            future_date,
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    issue = next(
        issue
        for issue in result.issues
        if issue.code == FUTURE_ROW
    )

    assert issue.result_date == future_date


def test_target_date_inclusion_is_detected():
    target_date = date(2026, 1, 5)

    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            target_date,
        ),
    )

    result = detect_history_leakage(
        observations,
        target_date,
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == TARGET_DATE_INCLUDED
        for issue in result.issues
    )


def test_target_date_inclusion_reports_correct_date():
    target_date = date(2026, 1, 5)

    observations = (
        make_observation(
            1,
            target_date,
        ),
    )

    result = detect_history_leakage(
        observations,
        target_date,
    )

    issue = next(
        issue
        for issue in result.issues
        if issue.code == TARGET_DATE_INCLUDED
    )

    assert issue.result_date == target_date


def test_duplicate_date_is_detected():
    duplicate_date = date(2026, 1, 2)

    observations = (
        make_observation(
            1,
            duplicate_date,
        ),
        make_observation(
            2,
            duplicate_date,
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == DUPLICATE_DATE
        for issue in result.issues
    )


def test_duplicate_date_reports_duplicate_date():
    duplicate_date = date(2026, 1, 2)

    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            duplicate_date,
        ),
        make_observation(
            3,
            duplicate_date,
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    issue = next(
        issue
        for issue in result.issues
        if issue.code == DUPLICATE_DATE
    )

    assert issue.result_date == duplicate_date


def test_temporal_order_violation_is_detected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 3),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == TEMPORAL_ORDER
        for issue in result.issues
    )


def test_temporal_order_equal_dates_are_detected():
    observations = (
        make_observation(
            1,
            date(2026, 1, 2),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert any(
        issue.code == TEMPORAL_ORDER
        for issue in result.issues
    )


def test_multiple_leakage_types_can_be_detected():
    target_date = date(2026, 1, 5)

    observations = (
        make_observation(
            1,
            date(2026, 1, 6),
        ),
        make_observation(
            2,
            target_date,
        ),
        make_observation(
            3,
            date(2026, 1, 6),
        ),
    )

    result = detect_history_leakage(
        observations,
        target_date,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert FUTURE_ROW in codes
    assert TARGET_DATE_INCLUDED in codes
    assert DUPLICATE_DATE in codes


def test_empty_history_is_clean():
    result = detect_history_leakage(
        (),
        date(2026, 1, 5),
    )

    assert result.status == CLEAN
    assert result.observation_count == 0
    assert result.issues == ()


def test_observation_count_is_reported():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
        ),
        make_observation(
            3,
            date(2026, 1, 3),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.observation_count == 3


def test_target_date_is_preserved():
    target_date = date(2026, 2, 10)

    result = detect_history_leakage(
        (),
        target_date,
    )

    assert result.target_date == target_date


def test_result_is_expected_dataclass():
    result = detect_history_leakage(
        (),
        date(2026, 1, 5),
    )

    assert isinstance(
        result,
        LeakageDetectionResult,
    )


def test_result_issue_count_is_correct():
    observations = (
        make_observation(
            1,
            date(2026, 1, 6),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.issue_count == 1
    assert get_leakage_issue_count(result) == 1


def test_get_leakage_status():
    result = detect_history_leakage(
        (),
        date(2026, 1, 5),
    )

    assert get_leakage_status(result) == CLEAN


def test_get_leakage_issues():
    result = detect_history_leakage(
        (),
        date(2026, 1, 5),
    )

    assert get_leakage_issues(result) == ()


def test_invalid_observation_type_is_rejected():
    with pytest.raises(TypeError):
        detect_history_leakage(
            ("invalid",),
            date(2026, 1, 5),
        )


def test_invalid_target_date_type_is_rejected():
    with pytest.raises(TypeError):
        detect_history_leakage(
            (),
            "2026-01-05",
        )


def test_string_observations_are_rejected():
    with pytest.raises(TypeError):
        detect_history_leakage(
            "invalid",
            date(2026, 1, 5),
        )


def test_bytes_observations_are_rejected():
    with pytest.raises(TypeError):
        detect_history_leakage(
            b"invalid",
            date(2026, 1, 5),
        )


def test_non_iterable_observations_are_rejected():
    with pytest.raises(TypeError):
        detect_history_leakage(
            123,
            date(2026, 1, 5),
        )


def test_point_in_time_history_is_clean():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 2),
        ),
    )

    history = build_point_in_time_history(
        observations,
        date(2026, 1, 5),
    )

    result = detect_point_in_time_history_leakage(
        history
    )

    assert result.status == CLEAN
    assert result.observation_count == 2
    assert result.issues == ()


def test_point_in_time_history_excludes_target_date():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 5),
        ),
    )

    history = build_point_in_time_history(
        observations,
        date(2026, 1, 5),
    )

    result = detect_point_in_time_history_leakage(
        history
    )

    assert result.status == CLEAN
    assert result.observation_count == 1


def test_point_in_time_history_excludes_future_rows():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 6),
        ),
    )

    history = build_point_in_time_history(
        observations,
        date(2026, 1, 5),
    )

    result = detect_point_in_time_history_leakage(
        history
    )

    assert result.status == CLEAN
    assert result.observation_count == 1


def test_invalid_point_in_time_history_type_is_rejected():
    with pytest.raises(TypeError):
        detect_point_in_time_history_leakage(
            "invalid"
        )


def test_is_leakage_free_returns_false_for_leakage():
    observations = (
        make_observation(
            1,
            date(2026, 1, 6),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert is_leakage_free(result) is False


def test_leakage_result_has_issues():
    observations = (
        make_observation(
            1,
            date(2026, 1, 6),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert len(
        get_leakage_issues(result)
    ) == 1


def test_invalid_result_getter_types_are_rejected():
    with pytest.raises(TypeError):
        get_leakage_status("invalid")

    with pytest.raises(TypeError):
        get_leakage_issues("invalid")

    with pytest.raises(TypeError):
        get_leakage_issue_count("invalid")

    with pytest.raises(TypeError):
        is_leakage_free("invalid")


def test_zero_values_do_not_create_leakage():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
            (
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == CLEAN
    assert result.issues == ()


def test_missing_calendar_dates_do_not_create_leakage():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 4),
        ),
    )

    result = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result.status == CLEAN
    assert result.issues == ()


def test_detection_is_deterministic():
    observations = (
        make_observation(
            1,
            date(2026, 1, 1),
        ),
        make_observation(
            2,
            date(2026, 1, 6),
        ),
    )

    result_a = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    result_b = detect_history_leakage(
        observations,
        date(2026, 1, 5),
    )

    assert result_a == result_b