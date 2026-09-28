from datetime import date

import pytest

from features.cyclical_time_features import (
    CyclicalTimeFeatureResult,
    build_cyclical_time_features,
    get_cyclical_time_feature_names,
    get_cyclical_time_feature_value,
    get_cyclical_time_feature_values,
)


def test_build_returns_result():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    assert isinstance(
        result,
        CyclicalTimeFeatureResult,
    )


def test_result_preserves_target_date():
    target_date = date(2026, 9, 27)

    result = build_cyclical_time_features(
        target_date
    )

    assert result.target_date == target_date


def test_feature_count():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    assert len(result.records) == 12


def test_all_feature_names_are_unique():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    names = get_cyclical_time_feature_names(result)

    assert len(names) == len(set(names))


def test_all_feature_names_use_cyclical_prefix():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    names = get_cyclical_time_feature_names(result)

    assert all(
        name.startswith("cyclical_")
        for name in names
    )


def test_day_of_week_features_are_bounded():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    values = get_cyclical_time_feature_values(result)

    assert -1.0 <= values["cyclical_day_of_week_sin"] <= 1.0
    assert -1.0 <= values["cyclical_day_of_week_cos"] <= 1.0


def test_month_features_are_bounded():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    values = get_cyclical_time_feature_values(result)

    assert -1.0 <= values["cyclical_month_sin"] <= 1.0
    assert -1.0 <= values["cyclical_month_cos"] <= 1.0


def test_quarter_features_are_bounded():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    values = get_cyclical_time_feature_values(result)

    assert -1.0 <= values["cyclical_quarter_sin"] <= 1.0
    assert -1.0 <= values["cyclical_quarter_cos"] <= 1.0


def test_day_of_week_monday():
    result = build_cyclical_time_features(
        date(2026, 9, 21)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_day_of_week_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_day_of_week_cos",
    )

    assert sin_value == pytest.approx(0.0)
    assert cos_value == pytest.approx(1.0)


def test_day_of_week_sunday():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_day_of_week_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_day_of_week_cos",
    )

    assert sin_value == pytest.approx(
        -0.7818314825
    )
    assert cos_value == pytest.approx(
        0.6234898019
    )


def test_month_january():
    result = build_cyclical_time_features(
        date(2026, 1, 15)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_month_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_month_cos",
    )

    assert sin_value == pytest.approx(0.0)
    assert cos_value == pytest.approx(1.0)


def test_month_july():
    result = build_cyclical_time_features(
        date(2026, 7, 15)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_month_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_month_cos",
    )

    assert sin_value == pytest.approx(0.0)
    assert cos_value == pytest.approx(-1.0)


def test_quarter_first():
    result = build_cyclical_time_features(
        date(2026, 2, 15)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_quarter_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_quarter_cos",
    )

    assert sin_value == pytest.approx(0.0)
    assert cos_value == pytest.approx(1.0)


def test_quarter_third():
    result = build_cyclical_time_features(
        date(2026, 8, 15)
    )

    sin_value = get_cyclical_time_feature_value(
        result,
        "cyclical_quarter_sin",
    )
    cos_value = get_cyclical_time_feature_value(
        result,
        "cyclical_quarter_cos",
    )

    assert sin_value == pytest.approx(0.0)
    assert cos_value == pytest.approx(-1.0)


def test_leap_year_day_of_year_is_supported():
    result = build_cyclical_time_features(
        date(2024, 12, 31)
    )

    values = get_cyclical_time_feature_values(result)

    assert -1.0 <= values["cyclical_day_of_year_sin"] <= 1.0
    assert -1.0 <= values["cyclical_day_of_year_cos"] <= 1.0


def test_non_leap_year_day_of_year_is_supported():
    result = build_cyclical_time_features(
        date(2025, 12, 31)
    )

    values = get_cyclical_time_feature_values(result)

    assert -1.0 <= values["cyclical_day_of_year_sin"] <= 1.0
    assert -1.0 <= values["cyclical_day_of_year_cos"] <= 1.0


def test_feature_values_returns_mapping():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    values = get_cyclical_time_feature_values(result)

    assert isinstance(values, dict)
    assert len(values) == 12


def test_invalid_target_date_rejected():
    with pytest.raises(TypeError):
        build_cyclical_time_features("2026-09-27")


def test_invalid_result_type_rejected_by_names():
    with pytest.raises(TypeError):
        get_cyclical_time_feature_names("invalid")


def test_invalid_result_type_rejected_by_value():
    with pytest.raises(TypeError):
        get_cyclical_time_feature_value(
            "invalid",
            "cyclical_month_sin",
        )


def test_invalid_result_type_rejected_by_values():
    with pytest.raises(TypeError):
        get_cyclical_time_feature_values("invalid")


def test_missing_feature_raises_value_error():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    with pytest.raises(
        ValueError,
        match="Cyclical time feature not found",
    ):
        get_cyclical_time_feature_value(
            result,
            "cyclical_missing",
        )


def test_feature_records_have_expected_metadata():
    result = build_cyclical_time_features(
        date(2026, 9, 27)
    )

    for record in result.records:
        assert record.feature_type == "cyclical_time"
        assert record.source == "target_date"