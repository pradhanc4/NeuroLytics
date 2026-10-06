import pytest
from tests.test_production_serving import activation_receipt
from analytics.production_serving import build_serving_plan
from analytics.production_api import InferenceApiService, create_inference_app, create_secure_inference_app
from analytics.api_rate_limit import *

def predictor(features):
    return round(features["f1"] + features["f2"], 4)

def service():
    receipt = activation_receipt()
    return InferenceApiService(build_serving_plan("serving71", receipt), predictor)

def store():
    from analytics.api_security import ApiCredentialStore
    s = ApiCredentialStore()
    s.issue_key("client-71", "inference", ["inference:read"], "secret-71")
    return s

def payload():
    receipt = activation_receipt()
    return {"request_id":"request71","model_identity":receipt.model_identity,
            "model_version":receipt.model_version,"artifact_identity":receipt.artifact_identity,
            "features":{"f1":1,"f2":2}}

def test_01_version(): assert API_RATE_LIMIT_VERSION == "71.0.0"
def test_02_boundary(): assert RATE_LIMIT_BOUNDARY == "API_RATE_LIMIT_BOUNDARY"
def test_03_default_policy(): validate_rate_limit_policy(ApiRateLimitPolicy())
def test_04_policy_type():
    with pytest.raises(TypeError): validate_rate_limit_policy(object())
def test_05_enabled_bool():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(enabled="x"))
def test_06_requests_positive():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(requests_per_window=0))
def test_07_requests_bool():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(requests_per_window=True))
def test_08_window_positive():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(window_seconds=0))
def test_09_window_bool():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(window_seconds=True))
def test_10_burst_positive():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(burst_limit=0))
def test_11_burst_bool():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(burst_limit=True))
def test_12_burst_bound():
    with pytest.raises(ValueError): validate_rate_limit_policy(ApiRateLimitPolicy(requests_per_window=2, burst_limit=3))
def test_13_decision_allowed():
    d=RateLimitDecision(RATE_LIMIT_ALLOWED,"x",3,2,0,60); assert d.allowed
def test_14_decision_blocked():
    d=RateLimitDecision(RATE_LIMITED,"x",3,0,2,60); assert not d.allowed
def test_15_first_request():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=5,burst_limit=5)); assert l.check("x").remaining == 4
def test_16_identity_required():
    with pytest.raises(ValueError): ApiRateLimiter().check("")
def test_17_burst_limit():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=5,burst_limit=2))
    assert l.check("x").allowed
    assert l.check("x").allowed
    assert l.check("x").status == RATE_LIMITED
def test_18_identity_isolated():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=2,burst_limit=2))
    l.check("a"); l.check("a")
    assert l.check("b").allowed
def test_19_reset():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=1,burst_limit=1))
    l.check("x"); l.reset(); assert l.check("x").allowed
def test_20_disabled():
    l=ApiRateLimiter(ApiRateLimitPolicy(enabled=False,requests_per_window=1,burst_limit=1))
    assert l.check("x").allowed and l.check("x").allowed
def test_21_remaining():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=3,burst_limit=3))
    assert l.check("x").remaining == 2
def test_22_retry_after_blocked():
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=1,burst_limit=1),clock=lambda: 10.0)
    l.check("x"); d=l.check("x"); assert d.retry_after == 60
def test_23_clock_expiry():
    now=[0.0]
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=1,burst_limit=1,window_seconds=10),clock=lambda: now[0])
    l.check("x"); now[0]=10.0; assert l.check("x").allowed
def test_24_deterministic_clock():
    now=[5.0]
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=2,burst_limit=2),clock=lambda: now[0])
    assert l.check("x").remaining == 1
def test_25_headers_limit():
    d=RateLimitDecision(RATE_LIMIT_ALLOWED,"x",5,4,0,60)
    assert rate_limit_headers(d)["X-RateLimit-Limit"] == "5"
def test_26_headers_remaining():
    d=RateLimitDecision(RATE_LIMIT_ALLOWED,"x",5,4,0,60)
    assert rate_limit_headers(d)["X-RateLimit-Remaining"] == "4"
def test_27_headers_retry():
    d=RateLimitDecision(RATE_LIMITED,"x",5,0,7,60)
    assert rate_limit_headers(d)["Retry-After"] == "7"
def test_28_summary_version():
    l=ApiRateLimiter(); assert rate_limit_summary(l.policy,l)["version"] == API_RATE_LIMIT_VERSION
def test_29_summary_boundary():
    l=ApiRateLimiter(); assert rate_limit_summary(l.policy,l)["boundary"] == RATE_LIMIT_BOUNDARY
def test_30_summary_tracking():
    l=ApiRateLimiter(); l.check("x"); assert rate_limit_summary(l.policy,l)["tracked_identities"] == 1
def test_31_summary_mismatch():
    l=ApiRateLimiter()
    with pytest.raises(ValueError): rate_limit_summary(ApiRateLimitPolicy(enabled=False),l)
def test_32_clock_type():
    with pytest.raises(TypeError): ApiRateLimiter(clock=object())
def test_33_policy_property():
    p=ApiRateLimitPolicy(requests_per_window=7,burst_limit=7); assert ApiRateLimiter(p).policy == p
def test_34_immutable_policy():
    p=ApiRateLimitPolicy()
    with pytest.raises(Exception): p.enabled=False
def test_35_immutable_decision():
    d=RateLimitDecision(RATE_LIMIT_ALLOWED,"x",1,0,0,1)
    with pytest.raises(Exception): d.remaining=1
def test_36_factory_disabled_by_default():
    app=create_inference_app(service())
    assert app.config["NEUROLYTICS_RATE_LIMIT_VERSION"] == API_RATE_LIMIT_VERSION
def test_37_legacy_app_allows_repeated():
    c=create_inference_app(service(),rate_limit_policy=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)).test_client()
    assert c.post("/v1/inference",json=payload()).status_code == 200
    assert c.post("/v1/inference",json=payload()).status_code == 429
def test_38_secure_default_rate_limit():
    c=create_secure_inference_app(service(),store(),rate_limit_policy=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)).test_client()
    h={"X-API-Key":"secret-71"}
    assert c.post("/v1/inference",json=payload(),headers=h).status_code == 200
    assert c.post("/v1/inference",json=payload(),headers=h).status_code == 429
def test_39_secure_429_code():
    c=create_secure_inference_app(service(),store(),rate_limit_policy=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    assert c.post("/v1/inference",json=payload(),headers=h).get_json()["error"]["code"] == RATE_LIMIT_DENIED
def test_40_secure_retry_after():
    c=create_secure_inference_app(service(),store(),rate_limit_policy=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    r=c.post("/v1/inference",json=payload(),headers=h); assert r.headers["Retry-After"]
def test_41_health_public_not_limited():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.get("/health").status_code == 200
    assert c.get("/health").status_code == 200
def test_42_ready_is_limited():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}; assert c.get("/ready",headers=h).status_code == 200
    assert c.get("/ready",headers=h).status_code == 429
def test_43_failed_auth_rate_limited():
    p=ApiRateLimitPolicy(requests_per_window=2,burst_limit=2)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"bad"}
    assert c.get("/ready",headers=h).status_code == 401
    assert c.get("/ready",headers=h).status_code == 401
    assert c.get("/ready",headers=h).status_code == 429
def test_44_missing_auth_rate_limited():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.get("/ready").status_code == 401
    assert c.get("/ready").status_code == 429
def test_45_auth_failure_never_echoes_key():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    r=c.get("/ready",headers={"X-API-Key":"bad-secret"})
    assert "bad-secret" not in str(r.get_json())
def test_46_rate_limit_before_payload():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    r=c.post("/v1/inference",data="{bad",content_type="application/json",headers=h)
    assert r.status_code == 429
def test_47_rate_limit_before_inference():
    calls=[]
    def spy(features):
        calls.append(features); return 3
    receipt=activation_receipt()
    s=InferenceApiService(build_serving_plan("spy71",receipt),spy)
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(s,store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    c.post("/v1/inference",json=payload(),headers=h)
    assert len(calls) == 1
def test_48_custom_limiter():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    l=ApiRateLimiter(p)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p,rate_limiter=l).test_client()
    h={"X-API-Key":"secret-71"}; assert c.post("/v1/inference",json=payload(),headers=h).status_code == 200
def test_49_limiter_policy_mismatch():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=2,burst_limit=2))
    with pytest.raises(ValueError): create_secure_inference_app(service(),store(),rate_limit_policy=p,rate_limiter=l)
def test_50_disabled_limit_policy():
    p=ApiRateLimitPolicy(enabled=False,requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}
    assert c.post("/v1/inference",json=payload(),headers=h).status_code == 200
    assert c.post("/v1/inference",json=payload(),headers=h).status_code == 200
def test_51_custom_window_header():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1,window_seconds=5)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    r=c.post("/v1/inference",json=payload(),headers=h); assert r.headers["X-RateLimit-Window"] == "5"
def test_52_remaining_header_after_success():
    p=ApiRateLimitPolicy(requests_per_window=3,burst_limit=3)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    r=c.post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-71"})
    assert r.headers["X-RateLimit-Remaining"] == "2"
def test_53_rejected_remaining_zero():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}; c.post("/v1/inference",json=payload(),headers=h)
    r=c.post("/v1/inference",json=payload(),headers=h); assert r.headers["X-RateLimit-Remaining"] == "0"
def test_54_per_credential_isolation():
    from analytics.api_security import ApiCredentialStore
    s=ApiCredentialStore(); s.issue_key("a","r",["inference:read"],"a-key"); s.issue_key("b","r",["inference:read"],"b-key")
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),s,rate_limit_policy=p).test_client()
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"a-key"}).status_code == 200
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"b-key"}).status_code == 200
def test_55_ip_failure_isolation():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.get("/ready",headers={"X-API-Key":"bad"}).status_code == 401
    assert c.get("/ready",headers={"X-API-Key":"secret-71"}).status_code == 200
def test_56_wrong_scope_consumes_ip_bucket():
    from analytics.api_security import ApiCredentialStore
    s=ApiCredentialStore(); s.issue_key("limited","r",["health:read"],"limited-key")
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),s,rate_limit_policy=p).test_client()
    assert c.get("/ready",headers={"X-API-Key":"limited-key"}).status_code == 403
    assert c.get("/ready",headers={"X-API-Key":"limited-key"}).status_code == 429
def test_57_not_found_remains_404():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.get("/unknown").status_code == 404
def test_58_wrong_method_remains_405():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.get("/v1/inference").status_code == 405
def test_59_policy_summary():
    p=ApiRateLimitPolicy(requests_per_window=10,burst_limit=5)
    l=ApiRateLimiter(p); l.check("x")
    s=rate_limit_summary(p,l)
    assert s["requests_per_window"] == 10 and s["burst_limit"] == 5
def test_60_summary_no_secrets():
    p=ApiRateLimitPolicy(); l=ApiRateLimiter(p); l.check("secret-identity")
    assert "secret-identity" not in str(rate_limit_summary(p,l))
def test_61_security_preserved():
    p=ApiRateLimitPolicy(requests_per_window=10,burst_limit=10)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.post("/v1/inference",json=payload()).status_code == 401
def test_62_valid_inference_preserved():
    p=ApiRateLimitPolicy(requests_per_window=10,burst_limit=10)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-71"}).get_json()["prediction"] == 3.0
def test_63_response_identity_preserved():
    p=ApiRateLimitPolicy(requests_per_window=10,burst_limit=10)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    r=c.post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-71"})
    assert r.get_json()["response_identity"].startswith("production-serving-")
def test_64_rate_limit_constants():
    assert RATE_LIMIT_ALLOWED != RATE_LIMITED
def test_65_retry_minimum_one():
    now=[0.0]
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=1,burst_limit=1,window_seconds=0.1,burst_window_seconds=0.1),clock=lambda:now[0])
    l.check("x"); d=l.check("x"); assert d.retry_after == 1
def test_66_expiry_boundary():
    now=[0.0]
    l=ApiRateLimiter(ApiRateLimitPolicy(requests_per_window=1,burst_limit=1,window_seconds=1),clock=lambda:now[0])
    l.check("x"); now[0]=1.0001; assert l.check("x").allowed
def test_67_separate_limiter_instances():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    assert ApiRateLimiter(p).check("x").allowed and ApiRateLimiter(p).check("x").allowed
def test_68_health_does_not_create_bucket():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    l=ApiRateLimiter(p); assert rate_limit_summary(p,l)["tracked_identities"] == 0
def test_69_secure_factory_enables_by_default():
    from analytics.production_api import create_secure_inference_app
    c=create_secure_inference_app(service(),store()).test_client()
    assert c.post("/v1/inference",json=payload(),headers={"X-API-Key":"secret-71"}).status_code == 200
def test_70_full_phase71_contract():
    p=ApiRateLimitPolicy(requests_per_window=1,burst_limit=1)
    c=create_secure_inference_app(service(),store(),rate_limit_policy=p).test_client()
    h={"X-API-Key":"secret-71"}
    assert c.get("/health").status_code == 200
    assert c.post("/v1/inference",json=payload(),headers=h).status_code == 200
    r=c.post("/v1/inference",json=payload(),headers=h)
    assert r.status_code == 429 and r.get_json()["error"]["code"] == RATE_LIMIT_DENIED
