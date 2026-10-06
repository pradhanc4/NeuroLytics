from analytics.admin_dashboard import (
    ADMIN_DASHBOARD_BOUNDARY,
    ADMIN_DASHBOARD_VERSION,
    AdminDashboardService,
    admin_dashboard_contract,
    admin_dashboard_summary,
)
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import payload, service as phase76_service


def client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_01_version():
    assert ADMIN_DASHBOARD_VERSION == "87.0.0"


def test_02_boundary():
    assert ADMIN_DASHBOARD_BOUNDARY == "ADMIN_CONFIGURATION_DASHBOARD_BOUNDARY"


def test_03_summary_contract():
    x = admin_dashboard_summary()
    assert x["version"] == ADMIN_DASHBOARD_VERSION
    assert x["read_only"] is True


def test_04_contract_is_read_only():
    x = admin_dashboard_contract()
    assert x["read_only"] is True
    assert x["mutation_routes"] == []
    assert x["secrets_exposed"] is False


def test_05_service_rejects_invalid_object():
    try:
        AdminDashboardService(object())
    except TypeError:
        return
    assert False


def test_06_service_state():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    x = AdminDashboardService(svc).service_state()
    assert x["status"] == "VALID"
    assert x["service_state"] == "RUNNING"


def test_07_security_summary():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).security()
    assert x["status"] == "VALID"
    assert x["summary"]["raw_keys_exposed"] is False


def test_08_security_no_key_hash():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).security()
    for item in x["credential_metadata"]:
        assert "key_hash" not in item


def test_09_rate_limit_summary():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).rate_limit()
    assert x["status"] == "VALID"
    assert "requests_per_window" in x["summary"]


def test_10_policy_summary():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).production_policy()
    assert x["status"] == "VALID"
    assert "policy" in x


def test_11_serving_summary():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).serving()
    assert x["status"] == "VALID"
    assert "serving_state" in x


def test_12_dependencies_summary():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).dependencies()
    assert x["status"] == "VALID"
    assert len(x["dependencies"]) >= 1


def test_13_scopes():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).scopes({"inference": "inference:read", "admin": "admin:read"})
    assert x["count"] == 2


def test_14_scopes_are_sorted():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).scopes({"z": "z:read", "a": "a:read"})
    assert [v["name"] for v in x["scopes"]] == ["a", "z"]


def test_15_empty_scopes():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    assert AdminDashboardService(svc).scopes({})["count"] == 0


def test_16_dashboard_composes_sections():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    x = AdminDashboardService(svc).dashboard({"admin": "admin:read"})
    for key in ("service_state", "security", "rate_limit", "production_policy", "serving", "dependencies", "scopes"):
        assert key in x


def test_17_dashboard_is_read_only():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    assert AdminDashboardService(svc).dashboard({})["read_only"] is True


def test_18_dashboard_version():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    assert AdminDashboardService(svc).dashboard({})["version"] == "87.0.0"


def test_19_summary_route():
    response = client().get("/v1/admin/summary")
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True


def test_20_service_route():
    response = client().get("/v1/admin/service")
    assert response.status_code == 200
    assert response.get_json()["status"] == "VALID"


def test_21_security_route():
    assert client().get("/v1/admin/security").status_code == 200


def test_22_rate_route():
    assert client().get("/v1/admin/rate-limit").status_code == 200


def test_23_policy_route():
    assert client().get("/v1/admin/policy").status_code == 200


def test_24_serving_route():
    assert client().get("/v1/admin/serving").status_code == 200


def test_25_dependencies_route():
    assert client().get("/v1/admin/dependencies").status_code == 200


def test_26_scopes_route():
    response = client().get("/v1/admin/scopes")
    assert response.status_code == 200
    assert response.get_json()["count"] >= 1


def test_27_get_only_summary():
    assert client().post("/v1/admin/summary", json={}).status_code == 405


def test_28_get_only_security():
    assert client().post("/v1/admin/security", json={}).status_code == 405


def test_29_get_only_rate():
    assert client().post("/v1/admin/rate-limit", json={}).status_code == 405


def test_30_get_only_policy():
    assert client().post("/v1/admin/policy", json={}).status_code == 405


def test_31_get_only_serving():
    assert client().post("/v1/admin/serving", json={}).status_code == 405


def test_32_get_only_dependencies():
    assert client().post("/v1/admin/dependencies", json={}).status_code == 405


def test_33_get_only_scopes():
    assert client().post("/v1/admin/scopes", json={}).status_code == 405


def test_34_frontend_config_summary():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_summary"] == "/v1/admin/summary"


def test_35_frontend_config_service():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_service"] == "/v1/admin/service"


def test_36_frontend_config_security():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_security"] == "/v1/admin/security"


def test_37_frontend_config_rate():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_rate_limit"] == "/v1/admin/rate-limit"


def test_38_frontend_config_policy():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_policy"] == "/v1/admin/policy"


def test_39_frontend_config_serving():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_serving"] == "/v1/admin/serving"


def test_40_frontend_config_dependencies():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_dependencies"] == "/v1/admin/dependencies"


def test_41_frontend_config_scopes():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["admin_scopes"] == "/v1/admin/scopes"


def test_42_frontend_admin_view():
    html = client().get("/").get_data(as_text=True)
    assert 'id="view-admin"' in html


def test_43_frontend_admin_navigation():
    html = client().get("/").get_data(as_text=True)
    assert 'data-view="admin"' in html


def test_44_frontend_admin_refresh():
    html = client().get("/").get_data(as_text=True)
    assert 'id="admin-refresh"' in html


def test_45_frontend_security_panel():
    html = client().get("/").get_data(as_text=True)
    assert 'id="admin-security"' in html


def test_46_frontend_rate_panel():
    html = client().get("/").get_data(as_text=True)
    assert 'id="admin-rate"' in html


def test_47_frontend_scope_table():
    html = client().get("/").get_data(as_text=True)
    assert 'id="admin-scope-rows"' in html


def test_48_frontend_admin_js():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "async function admin()" in js


def test_49_frontend_admin_api_usage():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'api("/v1/admin/service")' in js
    assert 'api("/v1/admin/security")' in js
    assert 'api("/v1/admin/rate-limit")' in js


def test_50_frontend_admin_scope_usage():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'api("/v1/admin/scopes")' in js


def test_51_frontend_admin_navigation_title():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'admin:"Admin / Configuration Dashboard"' in js


def test_52_frontend_admin_switch():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'v==="admin"' in js


def test_53_frontend_admin_refresh_wiring():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'admin-refresh").onclick=admin' in js


def test_54_no_mutation_route_contract():
    app = client().application
    routes = [rule for rule in app.url_map.iter_rules() if "/v1/admin/" in rule.rule]
    assert all(rule.methods <= {"GET", "HEAD", "OPTIONS"} for rule in routes)


def test_55_prediction_route_remains_available():
    response = client().post("/v1/inference", json=payload())
    assert response.status_code == 200
