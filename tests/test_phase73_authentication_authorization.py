from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy
from analytics.performance_monitoring_api import PerformanceMonitoringApiService, create_monitoring_app


def make_service():
    return PerformanceMonitoringApiService()


def make_store():
    store = ApiCredentialStore()
    store.issue_key("monitor-read", "monitor", ("monitoring:read",), "phase73-secret")
    store.issue_key("wrong-scope", "other", ("inference:read",), "phase73-other")
    store.issue_key("revoked", "monitor", ("monitoring:read",), "phase73-revoked")
    store.revoke("revoked")
    return store


def make_app():
    return create_monitoring_app(
        make_service(),
        security_store=make_store(),
        security_policy=ApiSecurityPolicy(enabled=True),
        required_scope="monitoring:read",
    )


def test_public_health_remains_public():
    response = make_app().test_client().get("/health")
    assert response.status_code == 200


def test_missing_credential_is_401():
    response = make_app().test_client().get("/v1/monitoring/summary")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "MISSING_CREDENTIAL"


def test_invalid_credential_is_401():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "bad"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_CREDENTIAL"


def test_valid_monitoring_scope_is_accepted():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    assert response.status_code == 200


def test_wrong_scope_is_403():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-other"})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "INSUFFICIENT_SCOPE"


def test_revoked_credential_is_403():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-revoked"})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "REVOKED"


def test_all_monitoring_requires_authentication():
    response = make_app().test_client().get("/v1/monitoring")
    assert response.status_code == 401


def test_named_report_requires_authentication():
    response = make_app().test_client().get("/v1/monitoring/model_health")
    assert response.status_code == 401


def test_named_report_accepts_authorized_credential():
    response = make_app().test_client().get("/v1/monitoring/model_health", headers={"X-API-Key": "phase73-secret"})
    assert response.status_code in (200, 404)


def test_health_does_not_expose_credential_data():
    response = make_app().test_client().get("/health")
    body = response.get_data(as_text=True)
    assert "phase73-secret" not in body


def test_error_does_not_echo_raw_key():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "secret-not-echoed"})
    assert "secret-not-echoed" not in response.get_data(as_text=True)


def test_security_can_be_disabled_for_compatibility():
    app = create_monitoring_app(make_service(), security_policy=ApiSecurityPolicy(enabled=False))
    assert app.test_client().get("/v1/monitoring/summary").status_code == 200


def test_enabled_security_without_store_returns_503():
    app = create_monitoring_app(make_service(), security_policy=ApiSecurityPolicy(enabled=True))
    response = app.test_client().get("/v1/monitoring/summary")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "SECURITY_STORE_REQUIRED"


def test_custom_monitoring_scope_is_supported():
    store = ApiCredentialStore()
    store.issue_key("custom", "monitor", ("observability:read",), "custom-secret")
    app = create_monitoring_app(make_service(), security_store=store, security_policy=ApiSecurityPolicy(enabled=True), required_scope="observability:read")
    assert app.test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "custom-secret"}).status_code == 200


def test_custom_header_is_supported():
    store = ApiCredentialStore()
    store.issue_key("custom", "monitor", ("monitoring:read",), "custom-header-secret")
    policy = ApiSecurityPolicy(enabled=True, credential_header="X-Monitor-Key")
    app = create_monitoring_app(make_service(), security_store=store, security_policy=policy)
    assert app.test_client().get("/v1/monitoring/summary", headers={"X-Monitor-Key": "custom-header-secret"}).status_code == 200


def test_wrong_header_is_rejected():
    store = ApiCredentialStore()
    store.issue_key("custom", "monitor", ("monitoring:read",), "custom-header-secret")
    policy = ApiSecurityPolicy(enabled=True, credential_header="X-Monitor-Key")
    app = create_monitoring_app(make_service(), security_store=store, security_policy=policy)
    assert app.test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "custom-header-secret"}).status_code == 401


def test_non_monitoring_route_is_not_caught_by_monitoring_auth_boundary():
    response = make_app().test_client().get("/unknown")
    assert response.status_code == 404


def test_post_monitoring_route_is_authenticated_before_method_check():
    response = make_app().test_client().post("/v1/monitoring/summary")
    assert response.status_code == 401


def test_authenticated_post_is_method_rejected():
    response = make_app().test_client().post("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    assert response.status_code == 405


def test_security_boundary_is_present_on_auth_error():
    response = make_app().test_client().get("/v1/monitoring/summary")
    assert response.get_json()["boundary"] == "PERFORMANCE_MONITORING_API_BOUNDARY"


def test_authorized_request_does_not_modify_store():
    store = make_store()
    before = store.credentials()
    app = create_monitoring_app(make_service(), security_store=store, security_policy=ApiSecurityPolicy(enabled=True))
    app.test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    assert store.credentials() == before


def test_multiple_authorized_requests_remain_deterministic():
    app = make_app()
    client = app.test_client()
    a = client.get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    b = client.get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    assert a.status_code == b.status_code == 200
    assert a.get_json() == b.get_json()


def test_security_policy_requires_nonempty_scope():
    store = make_store()
    try:
        create_monitoring_app(make_service(), security_store=store, security_policy=ApiSecurityPolicy(enabled=True), required_scope="")
    except ValueError:
        return
    raise AssertionError("empty required scope was accepted")


def test_security_store_type_is_validated():
    try:
        create_monitoring_app(make_service(), security_store=object(), security_policy=ApiSecurityPolicy(enabled=True))
    except TypeError:
        return
    raise AssertionError("invalid security store type was accepted")


def test_security_policy_type_is_validated():
    try:
        create_monitoring_app(make_service(), security_policy=object())
    except TypeError:
        return
    raise AssertionError("invalid security policy type was accepted")


def test_authorized_summary_remains_monitoring_api_versioned():
    response = make_app().test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "phase73-secret"})
    assert response.get_json()["api_version"] == "72.0.0"


def test_authorization_is_applied_to_named_security_like_route():
    response = make_app().test_client().get("/v1/monitoring/security")
    assert response.status_code == 401


def test_health_can_be_protected_when_disabled_public_health():
    policy = ApiSecurityPolicy(enabled=True)
    app = create_monitoring_app(make_service(), security_store=make_store(), security_policy=policy)
    assert app.test_client().get("/health").status_code == 200
