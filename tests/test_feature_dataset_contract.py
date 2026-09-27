from datetime import date

import pytest

from database.services import HistoricalResultService

from features.feature_config import FeatureConfig
from features.feature_dataset_contract import (
    VALID,
    INVALID,
    ContractValidationIssue,
    ContractValidationResult,
    FeatureDatasetContract,
    build_feature_dataset_contract,
    get_contract_feature_count,
    get_contract_feature_names,
    get_contract_schema_count,
    get_contract_validation_issues,
    get_contract_validation_status,
    get_contract_version_identity,
    is_feature_dataset_contract_valid,
    validate_feature_dataset_contract,
)
from features.feature_pipeline import (
    build_feature_pipeline,
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
):
    service = HistoricalResultService(db)

    market = service.create_market(
        "TEST_CONTRACT_MARKET"
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

    return service, market


def build_valid_contract(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    return build_feature_dataset_contract(
        pipeline
    )


def test_build_contract_returns_expected_type(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert isinstance(
        contract,
        FeatureDatasetContract,
    )


def test_contract_target_date_is_preserved(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert contract.target_date == date(
        2026,
        1,
        5,
    )


def test_contract_feature_version_is_preserved(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(
            feature_version="v7"
        ),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    assert contract.feature_version == "v7"


def test_contract_feature_count_matches_pipeline(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    assert (
        contract.feature_count
        == pipeline.feature_count
    )


def test_contract_schema_count_matches_pipeline(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    assert (
        contract.schema_count
        == len(pipeline.schemas)
    )


def test_contract_feature_names_are_preserved(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    assert (
        contract.feature_names
        == pipeline.dataset.feature_names
    )


def test_contract_schemas_are_preserved(
    db,
):
    service, market = seed_market(
        db
    )

    pipeline = build_feature_pipeline(
        service=service,
        market=market,
        target_date=date(2026, 1, 5),
        config=make_config(),
    )

    contract = build_feature_dataset_contract(
        pipeline
    )

    assert contract.schemas == pipeline.schemas


def test_contract_version_identity_is_preserved(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        contract.version_identity.identity
    )


def test_contract_validation_status_is_preserved(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        contract.validation_status
        == VALID
    )


def test_contract_leakage_status_is_preserved(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert contract.leakage_status == "CLEAN"


def test_valid_contract_returns_valid_status(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert result.status == VALID
    assert result.issues == ()
    assert result.is_valid is True


def test_valid_contract_has_zero_issues(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert result.issue_count == 0


def test_valid_result_has_expected_type(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert isinstance(
        result,
        ContractValidationResult,
    )


def test_contract_validation_issue_type(
):
    issue = ContractValidationIssue(
        code="TEST",
        message="Test issue.",
    )

    assert issue.code == "TEST"
    assert issue.message == "Test issue."


def test_invalid_target_date_is_detected():
    contract = FeatureDatasetContract(
        target_date="2026-01-05",
        feature_version="v1",
        feature_count=0,
        schema_count=0,
        feature_names=(),
        schemas=(),
        version_identity=object(),
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    with pytest.raises(AttributeError):
        validate_feature_dataset_contract(
            contract
        )


def test_empty_feature_names_with_zero_count_is_valid(
    db,
):
    contract = build_valid_contract(
        db
    )

    empty_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=0,
        schema_count=0,
        feature_names=(),
        schemas=(),
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        empty_contract
    )

    assert result.status == VALID


def test_duplicate_feature_names_are_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    duplicate_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=2,
        schema_count=2,
        feature_names=(
            "col1_lag_1",
            "col1_lag_1",
        ),
        schemas=(
            contract.schemas[0],
            contract.schemas[0],
        ),
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        duplicate_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "DUPLICATE_FEATURE_NAMES"
        for issue in result.issues
    )


def test_feature_schema_count_mismatch_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count + 1,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "FEATURE_SCHEMA_COUNT_MISMATCH"
        for issue in result.issues
    )


def test_feature_name_count_mismatch_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count + 1,
        schema_count=contract.schema_count + 1,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "FEATURE_NAME_COUNT_MISMATCH"
        for issue in result.issues
    )


def test_schema_order_mismatch_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    if len(contract.schemas) < 2:
        pytest.skip(
            "At least two schemas are required."
        )

    reversed_schemas = tuple(
        reversed(contract.schemas)
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=reversed_schemas,
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "SCHEMA_FEATURE_ORDER_MISMATCH"
        for issue in result.issues
    )


def test_schema_version_mismatch_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    if not contract.schemas:
        pytest.skip(
            "At least one schema is required."
        )

    original = contract.schemas[0]

    from features.feature_schema import FeatureSchema

    modified_schema = FeatureSchema(
        feature_name=original.feature_name,
        feature_version="different-version",
        feature_type=original.feature_type,
        source=original.source,
        position=original.position,
        window=original.window,
        lag=original.lag,
        description=original.description,
        availability_rule=original.availability_rule,
        data_type=original.data_type,
    )

    modified_schemas = (
        modified_schema,
        *contract.schemas[1:],
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=modified_schemas,
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "SCHEMA_VERSION_MISMATCH"
        for issue in result.issues
    )


def test_dataset_validation_failure_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=INVALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "DATASET_VALIDATION_FAILED"
        for issue in result.issues
    )


def test_leakage_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=VALID,
        leakage_status="LEAKAGE",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "LEAKAGE_DETECTED"
        for issue in result.issues
    )


def test_version_identity_mismatch_is_detected(
    db,
):
    contract = build_valid_contract(
        db
    )

    from features.feature_versioning import (
        FeatureVersionIdentity,
    )

    mismatched_identity = FeatureVersionIdentity(
        feature_version="different-version",
        identity=contract.version_identity.identity,
        algorithm=contract.version_identity.algorithm,
        canonical_definition=(
            contract.version_identity.canonical_definition
        ),
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=mismatched_identity,
        validation_status=VALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert result.status == INVALID

    assert any(
        issue.code
        == "VERSION_IDENTITY_MISMATCH"
        for issue in result.issues
    )


def test_contract_get_feature_count(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        get_contract_feature_count(contract)
        == contract.feature_count
    )


def test_contract_get_schema_count(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        get_contract_schema_count(contract)
        == contract.schema_count
    )


def test_contract_get_feature_names(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        get_contract_feature_names(contract)
        == contract.feature_names
    )


def test_contract_get_version_identity(
    db,
):
    contract = build_valid_contract(
        db
    )

    assert (
        get_contract_version_identity(contract)
        == contract.version_identity
    )


def test_get_validation_status(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert (
        get_contract_validation_status(result)
        == VALID
    )


def test_get_validation_issues(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert (
        get_contract_validation_issues(result)
        == ()
    )


def test_is_contract_valid(
    db,
):
    contract = build_valid_contract(
        db
    )

    result = validate_feature_dataset_contract(
        contract
    )

    assert (
        is_feature_dataset_contract_valid(result)
        is True
    )


def test_invalid_contract_returns_false(
    db,
):
    contract = build_valid_contract(
        db
    )

    invalid_contract = FeatureDatasetContract(
        target_date=contract.target_date,
        feature_version=contract.feature_version,
        feature_count=contract.feature_count,
        schema_count=contract.schema_count,
        feature_names=contract.feature_names,
        schemas=contract.schemas,
        version_identity=contract.version_identity,
        validation_status=INVALID,
        leakage_status="CLEAN",
    )

    result = validate_feature_dataset_contract(
        invalid_contract
    )

    assert (
        is_feature_dataset_contract_valid(result)
        is False
    )


def test_invalid_contract_type_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_dataset_contract(
            "invalid"
        )


def test_getters_reject_invalid_contract_type():
    with pytest.raises(TypeError):
        get_contract_feature_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_contract_schema_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_contract_feature_names(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_contract_version_identity(
            "invalid"
        )


def test_result_getters_reject_invalid_result_type():
    with pytest.raises(TypeError):
        get_contract_validation_status(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_contract_validation_issues(
            "invalid"
        )

    with pytest.raises(TypeError):
        is_feature_dataset_contract_valid(
            "invalid"
        )


def test_contract_validation_is_deterministic(
    db,
):
    contract = build_valid_contract(
        db
    )

    result_a = validate_feature_dataset_contract(
        contract
    )

    result_b = validate_feature_dataset_contract(
        contract
    )

    assert result_a == result_b


def test_contract_is_immutable(
    db,
):
    contract = build_valid_contract(
        db
    )

    with pytest.raises(
        AttributeError
    ):
        contract.feature_version = "changed"


def test_contract_preserves_feature_order(
    db,
):
    contract = build_valid_contract(
        db
    )

    schema_names = tuple(
        schema.feature_name
        for schema in contract.schemas
    )

    assert (
        contract.feature_names
        == schema_names
    )