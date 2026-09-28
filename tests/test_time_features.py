from datetime import date

import pytest

from features.time_features import (
    TimeFeatureResult,
    build_time_features,
    get_time_feature_names,
    get_time_feature_value,
    get_time_feature_values,
)


def test_build_time_features_returns_expected_result_type():
    result = build_time_features(
        date(2026, 1, 5)
    )

    assert isinstance(
        result,
        TimeFeatureResult,
    )


def test_target_date_is_preserved():
    target_date = date(2026, 1, 5)

    result = build_time_features(
        target_date
    )

    assert result.target_date == target_date


def test_day_of_week_is_correct():
    result = build_time_features(
        date(2026, 1, 5)
    )

    assert get_time_feature_value(
        result,
        "time_day_of_week",
    ) == "Monday"


def test_day_of_week_number_is_correct():
    result = build_time_features(
        date(2026, 1, 5)
    )

    assert get_time_feature_value(
        result,
        "time_day_of_week_number",
    ) == 0


def test_day_of_month_is_correct():
    result = build_time_features(
        date(2026, 1, 15)
    )

    assert get_time_feature_value(
        result,
        "time_day_of_month",
    ) == 15


def test_day_of_year_is_correct():
    result = build_time_features(
        date(2026, 1, 15)
    )

    assert get_time_feature_value(
        result,
        "time_day_of_year",
    ) == 15


def test_week_of_year_is_correct():
    result = build_time_features(
        date(2026, 1, 5)
    )

    assert get_time_feature_value(
        result,
        "time_week_of_year",
    ) == 2


def test_month_is_correct():
    result = build_time_features(
        date(2026, 6, 15)
    )

    assert get_time_feature_value(
        result,
        "time_month",
    ) == 6


def test_month_name_is_correct():
    result = build_time_features(
        date(2026, 6, 15)
    )

    assert get_time_feature_value(
        result,
        "time_month_name",
    ) == "June"


def test_quarter_is_correct():
    result = build_time_features(
        date(2026, 6, 15)
    )

    assert get_time_feature_value(
        result,
        "time_quarter",
    ) == 2


def test_year_is_correct():
    result = build_time_features(
        date(2026, 6, 15)
    )

    assert get_time_feature_value(
        result,
        "time_year",
    ) == 2026


def test_cyclical_feature_names_are_generated():
    result = build_time_features(
        date(2026, 6, 15)
    )

    names = get_time_feature_names(result)

    expected_names = (
        "time_day_of_week_sin",
        "time_day_of_week_cos",
        "time_day_of_month_sin",
        "time_day_of_month_cos",
        "time_day_of_year_sin",
        "time_day_of_year_cos",
        "time_week_of_year_sin",
        "time_week_of_year_cos",
        "time_month_sin",
        "time_month_cos",
        "time_quarter_sin",
        "time_quarter_cos",
    )

    for name in expected_names:
        assert name in names


def test_total_time_feature_count_is_21():
    result = build_time_features(
        date(2026, 6, 15)
    )

    assert len(result.records) == 21


def test_day_of_week_cyclical_values_are_numeric():
    result = build_time_features(
        date(2026, 6, 15)
    )

    sine = get_time_feature_value(
        result,
        "time_day_of_week_sin",
    )

    cosine = get_time_feature_value(
        result,
        "time_day_of_week_cos",
    )

    assert isinstance(sine, float)
    assert isinstance(cosine, float)


def test_month_cyclical_values_are_numeric():
    result = build_time_features(
        date(2026, 6, 15)
    )

    sine = get_time_feature_value(
        result,
        "time_month_sin",
    )

    cosine = get_time_feature_value(
        result,
        "time_month_cos",
    )

    assert isinstance(sine, float)
    assert isinstance(cosine, float)


def test_quarter_cyclical_values_are_numeric():
    result = build_time_features(
        date(2026, 6, 15)
    )

    sine = get_time_feature_value(
        result,
        "time_quarter_sin",
    )

    cosine = get_time_feature_value(
        result,
        "time_quarter_cos",
    )

    assert isinstance(sine, float)
    assert isinstance(cosine, float)


def test_cyclical_values_are_within_unit_circle():
    result = build_time_features(
        date(2026, 6, 15)
    )

    pairs = (
        (
            "time_day_of_week_sin",
            "time_day_of_week_cos",
        ),
        (
            "time_day_of_month_sin",
            "time_day_of_month_cos",
        ),
        (
            "time_day_of_year_sin",
            "time_day_of_year_cos",
        ),
        (
            "time_week_of_year_sin",
            "time_week_of_year_cos",
        ),
        (
            "time_month_sin",
            "time_month_cos",
        ),
        (
            "time_quarter_sin",
            "time_quarter_cos",
        ),
    )

    for sine_name, cosine_name in pairs:
        sine = get_time_feature_value(
            result,
            sine_name,
        )

        cosine = get_time_feature_value(
            result,
            cosine_name,
        )

        magnitude = (
            sine ** 2
            + cosine ** 2
        ) ** 0.5

        assert magnitude == pytest.approx(1.0)


def test_month_cycle_is_deterministic():
    january = build_time_features(
        date(2026, 1, 15)
    )

    january_again = build_time_features(
        date(2026, 1, 15)
    )

    assert get_time_feature_values(
        january
    ) == get_time_feature_values(
        january_again
    )


def test_different_months_have_different_cyclical_values():
    january = build_time_features(
        date(2026, 1, 15)
    )

    july = build_time_features(
        date(2026, 7, 15)
    )

    january_sin = get_time_feature_value(
        january,
        "time_month_sin",
    )

    july_sin = get_time_feature_value(
        july,
        "time_month_sin",
    )

    assert january_sin != july_sin


def test_monday_and_sunday_are_part_of_same_weekly_cycle():
    monday = build_time_features(
        date(2026, 1, 5)
    )

    sunday = build_time_features(
        date(2026, 1, 11)
    )

    monday_sin = get_time_feature_value(
        monday,
        "time_day_of_week_sin",
    )

    monday_cos = get_time_feature_value(
        monday,
        "time_day_of_week_cos",
    )

    sunday_sin = get_time_feature_value(
        sunday,
        "time_day_of_week_sin",
    )

    sunday_cos = get_time_feature_value(
        sunday,
        "time_day_of_week_cos",
    )

    distance = (
        (monday_sin - sunday_sin) ** 2
        + (monday_cos - sunday_cos) ** 2
    ) ** 0.5

    assert distance < 1.0


def test_leap_year_day_of_year_cycle_is_supported():
    result = build_time_features(
        date(2024, 12, 31)
    )

    sine = get_time_feature_value(
        result,
        "time_day_of_year_sin",
    )

    cosine = get_time_feature_value(
        result,
        "time_day_of_year_cos",
    )

    magnitude = (
        sine ** 2
        + cosine ** 2
    ) ** 0.5

    assert magnitude == pytest.approx(1.0)


def test_invalid_target_date_is_rejected():
    with pytest.raises(TypeError):
        build_time_features(
            "2026-01-01"
        )


def test_feature_names_are_deterministic():
    result1 = build_time_features(
        date(2026, 6, 15)
    )

    result2 = build_time_features(
        date(2026, 6, 15)
    )

    assert get_time_feature_names(
        result1
    ) == get_time_feature_names(
        result2
    )


def test_missing_feature_raises_value_error():
    result = build_time_features(
        date(2026, 6, 15)
    )

    with pytest.raises(ValueError):
        get_time_feature_value(
            result,
            "does_not_exist",
        )


def test_invalid_result_is_rejected_by_getter():
    with pytest.raises(TypeError):
        get_time_feature_value(
            None,
            "time_month",
        )


def test_feature_values_returns_mapping():
    result = build_time_features(
        date(2026, 6, 15)
    )

    values = get_time_feature_values(
        result
    )

    assert isinstance(values, dict)
    assert len(values) == 21
    assert values["time_month"] == 6