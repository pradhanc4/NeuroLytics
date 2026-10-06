import pytest

from analytics.api_validation import (
    API_VALIDATION_BOUNDARY,
    API_VALIDATION_VERSION,
    INVALID,
    VALID,
    ApiValidationPolicy,
    ApiValidationResult,
    validate_api_request,
    validate_api_validation_policy,
    validation_summary,
)

def test_01_version():
    assert API_VALIDATION_VERSION == "74.0.0"

def test_02_boundary():
    assert API_VALIDATION_BOUNDARY == "API_VALIDATION_ERROR_HANDLING_BOUNDARY"

def test_03_default_policy():
    validate_api_validation_policy(ApiValidationPolicy())

def test_04_policy_type():
    with pytest.raises(TypeError):
        validate_api_validation_policy(object())

def test_05_empty_methods():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(allowed_methods=()))

def test_06_bad_method_type():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(allowed_methods=(1,)))

def test_07_bad_content_type():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(required_content_type=""))

def test_08_bad_object_flag():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(require_object_body="x"))

def test_09_bad_size_zero():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(max_json_bytes=0))

def test_10_bad_size_bool():
    with pytest.raises(ValueError):
        validate_api_validation_policy(ApiValidationPolicy(max_json_bytes=True))

def test_11_valid_request():
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=20, payload={"x": 1},
    )
    assert result.is_valid
    assert result.http_status == 200

def test_12_invalid_method():
    result = validate_api_request(
        method="GET", content_type="application/json",
        content_length=20, payload={"x": 1},
    )
    assert result.http_status == 405
    assert result.code == "METHOD_NOT_ALLOWED"

def test_13_large_payload():
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=2_000_000, payload={"x": 1},
    )
    assert result.http_status == 413
    assert result.code == "PAYLOAD_TOO_LARGE"

def test_14_missing_content_type():
    result = validate_api_request(
        method="POST", content_type=None,
        content_length=20, payload={"x": 1},
    )
    assert result.http_status == 415

def test_15_wrong_content_type():
    result = validate_api_request(
        method="POST", content_type="text/plain",
        content_length=20, payload={"x": 1},
    )
    assert result.http_status == 415

def test_16_invalid_json():
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=20, payload=None,
    )
    assert result.http_status == 400
    assert result.code == "INVALID_JSON"

def test_17_non_object():
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=20, payload=[],
    )
    assert result.http_status == 400
    assert result.code == "INVALID_JSON_BODY"

def test_18_null_content_length():
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=None, payload={"x": 1},
    )
    assert result.is_valid

def test_19_json_charset():
    result = validate_api_request(
        method="POST", content_type="application/json; charset=utf-8",
        content_length=20, payload={"x": 1},
    )
    assert result.is_valid

def test_20_custom_limit():
    policy = ApiValidationPolicy(max_json_bytes=100)
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=101, payload={"x": 1}, policy=policy,
    )
    assert result.code == "PAYLOAD_TOO_LARGE"

def test_21_custom_method():
    policy = ApiValidationPolicy(allowed_methods=("PUT",))
    result = validate_api_request(
        method="PUT", content_type="application/json",
        content_length=20, payload={"x": 1}, policy=policy,
    )
    assert result.is_valid

def test_22_optional_object():
    policy = ApiValidationPolicy(require_object_body=False)
    result = validate_api_request(
        method="POST", content_type="application/json",
        content_length=20, payload=[1, 2], policy=policy,
    )
    assert result.is_valid

def test_23_result_valid_property():
    assert ApiValidationResult(VALID, 200, None, "ok").is_valid

def test_24_result_invalid_property():
    assert not ApiValidationResult(INVALID, 400, "X", "bad").is_valid

def test_25_summary_version():
    assert validation_summary()["version"] == API_VALIDATION_VERSION

def test_26_summary_boundary():
    assert validation_summary()["boundary"] == API_VALIDATION_BOUNDARY

def test_27_summary_policy():
    summary = validation_summary()
    assert summary["allowed_methods"] == ("POST",)
    assert summary["require_object_body"] is True

def test_28_deterministic_summary():
    assert validation_summary() == validation_summary()

def test_29_validation_precedence_method():
    result = validate_api_request(
        method="GET", content_type="text/plain",
        content_length=9_999_999, payload=None,
    )
    assert result.code == "METHOD_NOT_ALLOWED"

def test_30_validation_precedence_size():
    result = validate_api_request(
        method="POST", content_type="text/plain",
        content_length=9_999_999, payload=None,
    )
    assert result.code == "PAYLOAD_TOO_LARGE"
