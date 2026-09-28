from datetime import date

import pytest

from features.feature_schema import FeatureSchema
from features.feature_validator import (
    INVALID,
    VALID,
    FeatureValidationIssue,
    FeatureValidationResult,
    get_validation_issue_count,
    get_validation_issues,
    get_validation_status,
    is_feature_dataset_valid,
    validate_feature_dataset,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)


def make_record(
    feature_name="col1_lag_1",
    value=5,
    feature_type="lag",
    source="lag_features",
):
    return UnifiedFeatureRecord(
        feature_name=feature_name,
        value=value,
        feature_type=feature_type,
        source=source,
    )


def make_dataset(
    records=None,
    feature_version="v1",
):
    if records is None:
        records = (
            make_record(),
        )

    return UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version=feature_version,
        records=tuple(records),
    )


def test_valid_dataset_returns_valid_status():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.status == VALID


def test_valid_dataset_has_no_issues():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.issues == ()


def test_valid_dataset_is_valid():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.is_valid is True


def test_valid_dataset_issue_count_is_zero():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.issue_count == 0


def test_feature_count_matches_schema_count():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.feature_count == 1
    assert result.schema_count == 1


def test_multiple_valid_features_are_accepted():
    records = (
        make_record(
            feature_name="col1_lag_1",
            value=1,
        ),
        make_record(
            feature_name="col2_lag_2",
            value=2,
        ),
        make_record(
            feature_name="col3_lag_3",
            value=3,
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert result.status == VALID
    assert result.feature_count == 3
    assert result.schema_count == 3
    assert result.issues == ()


def test_none_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    value=None,
                ),
            )
        )
    )

    assert result.status == VALID


def test_zero_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    value=0,
                ),
            )
        )
    )

    assert result.status == VALID
    assert result.issues == ()


def test_zero_and_none_are_distinct_valid_values():
    records = (
        make_record(
            feature_name="col1_lag_1",
            value=0,
        ),
        make_record(
            feature_name="col2_lag_1",
            value=None,
        ),
    )

    result = validate_feature_dataset(
        make_dataset(
            records=records,
        )
    )

    assert result.status == VALID
    assert result.feature_count == 2
    assert result.schema_count == 2


def test_integer_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    value=5,
                ),
            )
        )
    )

    assert result.status == VALID


def test_float_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    feature_name="col1_rolling_3_mean",
                    value=5.5,
                    feature_type="rolling",
                    source="rolling_features",
                ),
            )
        )
    )

    assert result.status == VALID


def test_string_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    feature_name="col1_sequence_transition",
                    value="1_to_2",
                    feature_type="sequence",
                    source="sequence_features",
                ),
            )
        )
    )

    assert result.status == VALID


def test_boolean_value_is_allowed():
    result = validate_feature_dataset(
        make_dataset(
            records=(
                make_record(
                    feature_name="col1_flag",
                    value=True,
                    feature_type="position",
                    source="position_features",
                ),
            )
        )
    )

    assert result.status == VALID


def test_duplicate_feature_names_are_rejected():
    records = (
        make_record(
            feature_name="col1_lag_1",
            value=1,
        ),
        make_record(
            feature_name="col1_lag_1",
            value=2,
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert result.status == INVALID

    assert any(
        issue.code == "DUPLICATE_FEATURE_NAMES"
        for issue in result.issues
    )


def test_feature_schema_count_is_reported():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col2_lag_2",
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert result.feature_count == 2
    assert result.schema_count == 2


def test_schema_versions_match_dataset_version():
    dataset = make_dataset(
        feature_version="v9",
    )

    result = validate_feature_dataset(
        dataset
    )

    assert result.status == VALID


def test_result_has_expected_dataclass_type():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert isinstance(
        result,
        FeatureValidationResult,
    )


def test_validation_issue_dataclass_can_be_created():
    issue = FeatureValidationIssue(
        code="TEST",
        message="Test issue.",
        feature_name="col1_lag_1",
        severity=INVALID,
    )

    assert issue.code == "TEST"
    assert issue.message == "Test issue."
    assert issue.feature_name == "col1_lag_1"
    assert issue.severity == INVALID


def test_validation_result_properties():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert result.is_valid is True
    assert result.issue_count == 0


def test_get_validation_status():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert (
        get_validation_status(result)
        == VALID
    )


def test_get_validation_issues():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert (
        get_validation_issues(result)
        == ()
    )


def test_get_validation_issue_count():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert (
        get_validation_issue_count(result)
        == 0
    )


def test_is_feature_dataset_valid():
    result = validate_feature_dataset(
        make_dataset()
    )

    assert is_feature_dataset_valid(
        result
    ) is True


def test_invalid_result_reports_false_validity():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col1_lag_1",
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert result.status == INVALID
    assert result.is_valid is False
    assert is_feature_dataset_valid(
        result
    ) is False


def test_invalid_result_contains_issue():
    records = (
        make_record(
            feature_name="col1_lag_1",
        ),
        make_record(
            feature_name="col1_lag_1",
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert len(result.issues) >= 1
    assert all(
        isinstance(
            issue,
            FeatureValidationIssue,
        )
        for issue in result.issues
    )


def test_validation_is_deterministic():
    dataset = make_dataset()

    result_a = validate_feature_dataset(
        dataset
    )

    result_b = validate_feature_dataset(
        dataset
    )

    assert result_a == result_b


def test_validation_does_not_modify_dataset():
    dataset = make_dataset()

    original_records = dataset.records
    original_version = dataset.feature_version
    original_date = dataset.target_date

    validate_feature_dataset(
        dataset
    )

    assert dataset.records == original_records
    assert dataset.feature_version == original_version
    assert dataset.target_date == original_date


def test_invalid_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        validate_feature_dataset(
            "invalid"
        )


def test_status_getter_rejects_invalid_result_type():
    with pytest.raises(TypeError):
        get_validation_status(
            "invalid"
        )


def test_issues_getter_rejects_invalid_result_type():
    with pytest.raises(TypeError):
        get_validation_issues(
            "invalid"
        )


def test_issue_count_getter_rejects_invalid_result_type():
    with pytest.raises(TypeError):
        get_validation_issue_count(
            "invalid"
        )


def test_validity_getter_rejects_invalid_result_type():
    with pytest.raises(TypeError):
        is_feature_dataset_valid(
            "invalid"
        )


def test_validation_supports_all_feature_types():
    records = (
        # Phase 13
        make_record(
            feature_name="col1_lag_1",
            value=1,
            feature_type="lag",
            source="lag_features",
        ),
        make_record(
            feature_name="col1_rolling_3_mean",
            value=2.5,
            feature_type="rolling",
            source="rolling_features",
        ),
        make_record(
            feature_name="col1_digit_1_recency",
            value=2,
            feature_type="recency",
            source="recency_features",
        ),
        make_record(
            feature_name="col1_latest_value",
            value=4,
            feature_type="position",
            source="position_features",
        ),
        make_record(
            feature_name="col1_digit_1_frequency_count",
            value=3,
            feature_type="frequency",
            source="frequency_features",
        ),
        make_record(
            feature_name="col1_sequence_transition",
            value="1_to_2",
            feature_type="sequence",
            source="sequence_features",
        ),
        make_record(
            feature_name="col1_col2_same",
            value=True,
            feature_type="cross_position",
            source="cross_position_features",
        ),

        # Phase 15
        make_record(
            feature_name=(
                "panna_family_frequency_count_5_FamilyA"
            ),
            value=3,
            feature_type="historical_family_frequency",
            source="features.historical_family_frequency",
        ),
        make_record(
            feature_name=(
                "jodi_family_frequency_percentage_7_FamilyB"
            ),
            value=42.5,
            feature_type="historical_family_frequency",
            source="features.historical_family_frequency",
        ),
        make_record(
            feature_name="panna_family_recency_FamilyA",
            value=2,
            feature_type="family_recency",
            source="features.family_recency",
        ),
        make_record(
            feature_name=(
                "panna_family_seen_within_lookback_5_FamilyA"
            ),
            value=True,
            feature_type="family_recency",
            source="features.family_recency",
        ),
    )

    result = validate_feature_dataset(
        make_dataset(records=records)
    )

    assert result.status == VALID
    assert result.feature_count == 11
    assert result.schema_count == 11


def test_historical_family_frequency_feature_is_valid():
    record = make_record(
        feature_name=(
            "panna_family_frequency_count_5_FamilyA"
        ),
        value=4,
        feature_type="historical_family_frequency",
        source="features.historical_family_frequency",
    )

    result = validate_feature_dataset(
        make_dataset(
            records=(record,),
        )
    )

    assert result.status == VALID
    assert result.issues == ()
    assert result.feature_count == 1
    assert result.schema_count == 1


def test_historical_family_frequency_percentage_is_valid():
    record = make_record(
        feature_name=(
            "panel_family_frequency_percentage_10_FamilyB"
        ),
        value=37.5,
        feature_type="historical_family_frequency",
        source="features.historical_family_frequency",
    )

    result = validate_feature_dataset(
        make_dataset(
            records=(record,),
        )
    )

    assert result.status == VALID
    assert result.issues == ()


def test_family_recency_feature_is_valid():
    record = make_record(
        feature_name="jodi_family_recency_FamilyA",
        value=3,
        feature_type="family_recency",
        source="features.family_recency",
    )

    result = validate_feature_dataset(
        make_dataset(
            records=(record,),
        )
    )

    assert result.status == VALID
    assert result.issues == ()


def test_family_seen_within_lookback_feature_is_valid():
    record = make_record(
        feature_name=(
            "panel_family_seen_within_lookback_7_FamilyA"
        ),
        value=True,
        feature_type="family_recency",
        source="features.family_recency",
    )

    result = validate_feature_dataset(
        make_dataset(
            records=(record,),
        )
    )

    assert result.status == VALID
    assert result.issues == ()


def test_feature_version_is_preserved():
    dataset = make_dataset(
        feature_version="feature-v42",
    )

    result = validate_feature_dataset(
        dataset
    )

    assert result.status == VALID
    assert dataset.feature_version == "feature-v42"


def test_target_date_is_preserved():
    dataset = make_dataset()

    result = validate_feature_dataset(
        dataset
    )

    assert result.status == VALID
    assert dataset.target_date == date(
        2026,
        1,
        5,
    )


def test_empty_feature_dataset_is_valid():
    dataset = make_dataset(
        records=(),
    )

    result = validate_feature_dataset(
        dataset
    )

    assert result.status == VALID
    assert result.feature_count == 0
    assert result.schema_count == 0
    assert result.issues == ()