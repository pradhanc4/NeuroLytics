import pytest
from tests.test_production_serving import activation_receipt
from analytics.production_serving import build_serving_plan
from analytics.production_api import InferenceApiService, create_secure_inference_app, authorize_http_request
from analytics.api_security import *

def predictor(features):
    return round(features["f1"] + features["f2"], 4)

def service():
    receipt = activation_receipt()
    return InferenceApiService(build_serving_plan("serving70", receipt), predictor)

def store():
    s = ApiCredentialStore()
    s.issue_key("client-70", "inference", ["inference:read"], "secret-70")
    return s

def admin_store():
    s = ApiCredentialStore()
    s.issue_key("admin-70", "admin", ["inference:read", "admin"], "admin-70")
    return s

def payload():
    receipt = activation_receipt()
    return {
        "request_id": "request70",
        "model_identity": receipt.model_identity,
        "model_version": receipt.model_version,
        "artifact_identity": receipt.artifact_identity,
        "features": {"f1": 1, "f2": 2},
    }

def client():
    return create_secure_inference_app(service(), store()).test_client()

def test_01_version(): assert API_SECURITY_VERSION == "70.0.0"
def test_02_boundary(): assert SECURITY_BOUNDARY == "API_SECURITY_BOUNDARY"
def test_03_policy_default(): validate_security_policy(ApiSecurityPolicy())
def test_04_policy_type():
    with pytest.raises(TypeError): validate_security_policy(object())
def test_05_policy_bool():
    with pytest.raises(ValueError): validate_security_policy(ApiSecurityPolicy(enabled="x"))
def test_06_header_validation():
    with pytest.raises(ValueError): validate_security_policy(ApiSecurityPolicy(credential_header=""))
def test_07_scope_validation():
    with pytest.raises(ValueError): validate_security_policy(ApiSecurityPolicy(required_inference_scope=""))
def test_08_credential_type():
    with pytest.raises(TypeError): ApiCredentialStore().add_credential(object())
def test_09_credential_id_validation():
    with pytest.raises(ValueError): ApiCredentialStore().issue_key("", "role", ["s"], "key")
def test_10_role_validation():
    with pytest.raises(ValueError): ApiCredentialStore().issue_key("id", "", ["s"], "key")
def test_11_scope_validation():
    with pytest.raises(ValueError): ApiCredentialStore().issue_key("id", "role", [""], "key")
def test_12_duplicate_scopes():
    c=ApiCredentialStore().issue_key("id","role",["s","s"],"key"); assert c.scopes == ("s",)
def test_13_key_hash_deterministic(): assert ApiCredentialStore.hash_key("abc") == ApiCredentialStore.hash_key("abc")
def test_14_key_hash_distinct(): assert ApiCredentialStore.hash_key("abc") != ApiCredentialStore.hash_key("abd")
def test_15_key_hash_empty():
    with pytest.raises(ValueError): ApiCredentialStore.hash_key("")
def test_16_issue_key_hash_only(): assert len(store().get("client-70").key_hash) == 64
def test_17_raw_key_not_stored(): assert not hasattr(store().get("client-70"), "raw_key")
def test_18_credentials_sorted(): assert store().credentials()[0].credential_id == "client-70"
def test_19_verify_valid(): assert store().verify("secret-70").status == AUTHENTICATED
def test_20_verify_invalid(): assert store().verify("wrong").code == INVALID_CREDENTIAL
def test_21_verify_missing(): assert store().verify("").code == MISSING_CREDENTIAL
def test_22_verify_context(): assert store().verify("secret-70").context.credential_id == "client-70"
def test_23_verify_role(): assert store().verify("secret-70").context.role == "inference"
def test_24_verify_scope(): assert "inference:read" in store().verify("secret-70").context.scopes
def test_25_revoke(): assert store().revoke("client-70").revoked
def test_26_revoked_status():
    s=store(); s.revoke("client-70")
    assert s.verify("secret-70").code == REVOKED
def test_27_unknown_revoke():
    with pytest.raises(KeyError): store().revoke("missing")
def test_28_authorize_valid(): assert authorize(store().verify("secret-70"), "inference:read").status == AUTHORIZED
def test_29_authorize_missing(): assert authorize(store().verify("wrong"), "inference:read").status == UNAUTHENTICATED
def test_30_authorize_scope(): assert authorize(store().verify("secret-70"), "admin").code == INSUFFICIENT_SCOPE
def test_31_authorize_revoked():
    s=store(); s.revoke("client-70")
    assert authorize(s.verify("secret-70"), "inference:read").status == FORBIDDEN
def test_32_summary_enabled(): assert security_summary(ApiSecurityPolicy(), store())["enabled"] is True
def test_33_summary_count(): assert security_summary(ApiSecurityPolicy(), store())["credential_count"] == 1
def test_34_summary_ids(): assert security_summary(ApiSecurityPolicy(), store())["credential_ids"] == ("client-70",)
def test_35_summary_no_raw(): assert security_summary(ApiSecurityPolicy(), store())["raw_keys_exposed"] is False
def test_36_secure_health_public(): assert client().get("/health").status_code == 200
def test_37_ready_missing(): assert client().get("/ready").status_code == 401
def test_38_ready_invalid(): assert client().get("/ready",headers={"X-API-Key":"wrong"}).status_code == 401
def test_39_ready_valid(): assert client().get("/ready",headers={"X-API-Key":"secret-70"}).status_code == 200
def test_40_inference_missing(): assert client().post("/v1/inference",json=payload()).status_code == 401
def test_41_inference_invalid(): assert client().post("/v1/inference",json=payload(),headers={"X-API-Key":"wrong"}).status_code == 401
def test_42_inference_valid(): assert client().post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-70"}).status_code == 200
def test_43_inference_prediction(): assert client().post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-70"}).get_json()["prediction"] == 3.0
def test_44_auth_error_code(): assert client().get("/ready").get_json()["error"]["details"]["code"] == MISSING_CREDENTIAL
def test_45_invalid_error_code(): assert client().get("/ready",headers={"X-API-Key":"wrong"}).get_json()["error"]["details"]["code"] == INVALID_CREDENTIAL
def test_46_health_no_key(): assert client().get("/health").get_json()["status"] == "HEALTHY"
def test_47_wrong_scope_store():
    s=ApiCredentialStore(); s.issue_key("limited","limited",["health:read"],"limited-key")
    assert create_secure_inference_app(service(),s).test_client().get("/ready",headers={"X-API-Key":"limited-key"}).status_code == 403
def test_48_wrong_scope_code():
    s=ApiCredentialStore(); s.issue_key("limited","limited",["health:read"],"limited-key")
    assert create_secure_inference_app(service(),s).test_client().get("/ready",headers={"X-API-Key":"limited-key"}).get_json()["error"]["details"]["code"] == INSUFFICIENT_SCOPE
def test_49_revoked_http():
    s=store(); s.revoke("client-70")
    assert create_secure_inference_app(service(),s).test_client().get("/ready",headers={"X-API-Key":"secret-70"}).status_code == 403
def test_50_revoked_code():
    s=store(); s.revoke("client-70")
    assert create_secure_inference_app(service(),s).test_client().get("/ready",headers={"X-API-Key":"secret-70"}).get_json()["error"]["details"]["code"] == REVOKED
def test_51_custom_header():
    s=store(); p=ApiSecurityPolicy(credential_header="Authorization")
    c=create_secure_inference_app(service(),s,security_policy=p).test_client()
    assert c.get("/ready",headers={"Authorization":"secret-70"}).status_code == 200
def test_52_custom_scope():
    s=ApiCredentialStore(); s.issue_key("custom","role",["custom:read"],"custom-key")
    p=ApiSecurityPolicy(required_inference_scope="custom:read",required_ready_scope="custom:read")
    c=create_secure_inference_app(service(),s,security_policy=p).test_client()
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"custom-key"}).status_code == 200
def test_53_disabled_policy_allows():
    c=create_secure_inference_app(service(),store(),security_policy=ApiSecurityPolicy(enabled=True)).test_client()
    assert c.get("/health").status_code == 200
def test_54_secure_factory_disabled_rejected():
    with pytest.raises(ValueError): create_secure_inference_app(service(),store(),security_policy=ApiSecurityPolicy(enabled=False))
def test_55_http_authorize_disabled():
    p=ApiSecurityPolicy(enabled=False)
    from analytics.production_api import authorize_http_request
    assert authorize_http_request(ApiCredentialStore(),p,"x").status == AUTHORIZED
def test_56_http_authorize_valid():
    from analytics.production_api import authorize_http_request
    with client().application.test_request_context(headers={"X-API-Key":"secret-70"}):
        assert authorize_http_request(store(),ApiSecurityPolicy(),"inference:read").status == AUTHORIZED
def test_57_http_authorize_invalid():
    from analytics.production_api import authorize_http_request
    with client().application.test_request_context(headers={"X-API-Key":"bad"}):
        assert authorize_http_request(store(),ApiSecurityPolicy(),"inference:read").status == UNAUTHENTICATED
def test_58_health_is_public_even_with_security(): assert client().get("/health").status_code == 200
def test_59_not_found_secure(): assert client().get("/missing").status_code == 404
def test_60_wrong_method_secure(): assert client().get("/v1/inference").status_code == 405
def test_61_content_type_after_auth(): assert client().post("/v1/inference",data="{}",headers={"X-API-Key":"secret-70"}).status_code == 415
def test_62_invalid_json_after_auth(): assert client().post("/v1/inference",data="{bad",content_type="application/json",headers={"X-API-Key":"secret-70"}).status_code == 400
def test_63_missing_fields_after_auth(): assert client().post("/v1/inference",json={},headers={"X-API-Key":"secret-70"}).status_code == 400
def test_64_model_mismatch_after_auth():
    p=payload(); p["model_identity"]="bad"
    assert client().post("/v1/inference",json=p,headers={"X-API-Key":"secret-70"}).status_code == 422
def test_65_security_header_not_echoed(): assert "X-API-Key" not in str(client().get("/ready").get_json())
def test_66_hash_uses_utf8(): assert len(ApiCredentialStore.hash_key("✓")) == 64
def test_67_credential_immutable():
    c=store().get("client-70")
    with pytest.raises(Exception): c.revoked=True
def test_68_context_immutable():
    c=store().verify("secret-70").context
    with pytest.raises(Exception): c.role="admin"
def test_69_admin_scope_authorized():
    s=admin_store(); c=create_secure_inference_app(service(),s).test_client()
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"admin-70"}).status_code == 200
def test_70_full_security_contract():
    s=store(); c=create_secure_inference_app(service(),s).test_client()
    assert c.get("/health").status_code == 200
    assert c.get("/ready").status_code == 401
    assert c.get("/ready",headers={"X-API-Key":"secret-70"}).status_code == 200
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-70"}).status_code == 200
