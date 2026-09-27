from datetime import date

import pytest

from database.models import Market
from database.services import HistoricalResultService

from features.feature_config import FeatureConfig
from features.feature_pipeline import (
    FeaturePipelineResult,
    build_feature_pipeline,
    get_pipeline_dataset,
    get_pipeline_feature_count,
    get_pipeline_leakage,
    get_pipeline_schemas,
    get_pipeline_validation,
    get_pipeline_version_identity,
    is_pipeline_valid,
)


def make_config(
    **overrides,
):
    values = {
        "feature_version": "v1",
        "positions": (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
        "lag_windows": (1, 2, 3),
        "rolling_windows": (3, 5, 7),
        "frequency_enabled": True,
        "frequency_window": 5,
        "recency_enabled": True,
        "recency_lookback": 10,
        "position_features_enabled": True,
    }

    values.update(overrides)

    return FeatureConfig(
        **values
    )


def seed_market(
    db,
    service,
):
    market = service.create_market(
        "TEST_PIPELINE_MARKET"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 2),
        open_result="234",
        jodi_result="56",
        close_result="789",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 3),
        open_result="345",
        jodi_result="67",
        close_result="890",
    )

    return market


def test_feature_pipeline_returns_expected_result_type(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert isinstance(
        result,
        FeaturePipelineResult,
    )


def test_pipeline_uses_all_historical_observations_before_target(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        result.historical_observation_count
        == 3
    )

    assert (
        result.point_in_time_observation_count
        == 3
    )


def test_pipeline_excludes_target_date(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 5),
        open_result="999",
        jodi_result="99",
        close_result="999",
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        result.historical_observation_count
        == 4
    )

    assert (
        result.point_in_time_observation_count
        == 3
    )


def test_pipeline_excludes_future_rows(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 6),
        open_result="999",
        jodi_result="99",
        close_result="999",
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        result.historical_observation_count
        == 4
    )

    assert (
        result.point_in_time_observation_count
        == 3
    )


def test_pipeline_builds_features(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.feature_count > 0
    assert result.dataset.feature_count > 0
    assert len(result.schemas) == result.feature_count


def test_pipeline_feature_count_matches_schema_count(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        result.dataset.feature_count
        == len(result.schemas)
    )


def test_pipeline_validation_is_valid(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.validation.is_valid is True
    assert result.validation.issues == ()


def test_pipeline_leakage_check_is_clean(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.leakage.is_clean is True
    assert result.leakage.issues == ()


def test_pipeline_is_valid(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.is_valid is True
    assert is_pipeline_valid(result) is True


def test_pipeline_feature_version_is_preserved(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version="v9",
        ),
    )

    assert (
        result.feature_version
        == "v9"
    )

    assert (
        result.dataset.feature_version
        == "v9"
    )


def test_pipeline_target_date_is_preserved(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    target_date = date(
        2026,
        2,
        10,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=target_date,
        config=make_config(),
    )

    assert result.target_date == target_date
    assert result.dataset.target_date == target_date


def test_pipeline_market_id_is_preserved(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.market_id == market.id


def test_pipeline_version_identity_is_created(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        result.version_identity.identity
    )

    assert (
        result.version_identity.feature_version
        == result.feature_version
    )


def test_pipeline_version_identity_is_reproducible(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    config = make_config()

    result_a = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=config,
    )

    result_b = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=config,
    )

    assert (
        result_a.version_identity.identity
        == result_b.version_identity.identity
    )


def test_pipeline_feature_names_are_unique(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    names = result.dataset.feature_names

    assert len(names) == len(
        set(names)
    )


def test_pipeline_schema_names_match_feature_names(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    schema_names = tuple(
        schema.feature_name
        for schema in result.schemas
    )

    assert (
        schema_names
        == result.dataset.feature_names
    )


def test_get_pipeline_dataset(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_dataset(result)
        is result.dataset
    )


def test_get_pipeline_schemas(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_schemas(result)
        == result.schemas
    )


def test_get_pipeline_validation(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_validation(result)
        == result.validation
    )


def test_get_pipeline_leakage(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_leakage(result)
        == result.leakage
    )


def test_get_pipeline_version_identity(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_version_identity(result)
        == result.version_identity
    )


def test_get_pipeline_feature_count(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert (
        get_pipeline_feature_count(result)
        == result.feature_count
    )


def test_invalid_service_type_is_rejected(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    with pytest.raises(TypeError):
        build_feature_pipeline(
            service="invalid",
            market=market,
            target_date=date(2026, 1, 5),
            config=make_config(),
        )


def test_invalid_market_type_is_rejected(
    db,
):
    service = HistoricalResultService(db)

    with pytest.raises(TypeError):
        build_feature_pipeline(
            service=service,
            market="invalid",
            target_date=date(2026, 1, 5),
            config=make_config(),
        )


def test_invalid_target_date_type_is_rejected(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    with pytest.raises(TypeError):
        build_feature_pipeline(
            service=service,
            market=market,
            target_date="2026-01-05",
            config=make_config(),
        )


def test_invalid_config_type_is_rejected(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    with pytest.raises(TypeError):
        build_feature_pipeline(
            service=service,
            market=market,
            target_date=date(2026, 1, 5),
            config="invalid",
        )


def test_invalid_result_getters_are_rejected():
    with pytest.raises(TypeError):
        get_pipeline_dataset("invalid")

    with pytest.raises(TypeError):
        get_pipeline_schemas("invalid")

    with pytest.raises(TypeError):
        get_pipeline_validation("invalid")

    with pytest.raises(TypeError):
        get_pipeline_leakage("invalid")

    with pytest.raises(TypeError):
        get_pipeline_version_identity("invalid")

    with pytest.raises(TypeError):
        get_pipeline_feature_count("invalid")

    with pytest.raises(TypeError):
        is_pipeline_valid("invalid")


def test_pipeline_handles_zero_values(
    db,
):
    service = HistoricalResultService(db)

    market = service.create_market(
        "TEST_ZERO_PIPELINE_MARKET"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 1),
        open_result="000",
        jodi_result="00",
        close_result="000",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 2),
        open_result="100",
        jodi_result="01",
        close_result="010",
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.is_valid is True
    assert result.leakage.is_clean is True
    assert result.feature_count > 0


def test_pipeline_handles_missing_calendar_dates(
    db,
):
    service = HistoricalResultService(db)

    market = service.create_market(
        "TEST_MISSING_DATE_PIPELINE_MARKET"
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    service.create_historical_result(
        market=market,
        result_date=date(2026, 1, 3),
        open_result="234",
        jodi_result="56",
        close_result="789",
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    assert result.is_valid is True
    assert result.point_in_time_observation_count == 2


def test_pipeline_returns_immutable_result(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    result = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    with pytest.raises(
        AttributeError
    ):
        result.target_date = date(
            2026,
            2,
            1,
        )


def test_pipeline_is_deterministic_for_same_inputs(
    db,
):
    service = HistoricalResultService(db)

    market = seed_market(
        db,
        service,
    )

    config = make_config()

    result_a = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=config,
    )

    result_b = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=config,
    )

    assert (
        result_a.dataset.feature_names
        == result_b.dataset.feature_names
    )

    assert (
        result_a.dataset.values
        == result_b.dataset.values
    )

    assert (
        result_a.version_identity.identity
        == result_b.version_identity.identity
    )