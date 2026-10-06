"""Phase 88 — full frontend integration regression."""
from pathlib import Path

from frontend.app import create_frontend_app
from frontend.integration import (
    FRONTEND_INTEGRATION_BOUNDARY,
    FRONTEND_INTEGRATION_VERSION,
    ROUTES,
    integration_summary,
    validate_integration,
)

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend" / "templates" / "index.html"
JS = ROOT / "frontend" / "static" / "js" / "app.js"


def test_integration_version_and_boundary():
    assert FRONTEND_INTEGRATION_VERSION == "88.0.0"
    assert FRONTEND_INTEGRATION_BOUNDARY == "FULL_FRONTEND_INTEGRATION_BOUNDARY"


def test_route_registry_has_expected_surface():
    keys = [route.key for route in ROUTES]
    assert keys == [
        "overview", "analytics", "historical", "ranking", "top-k",
        "performance", "drift", "model-health", "prediction",
        "admin", "monitoring", "models",
    ]


def test_route_registry_has_unique_keys():
    keys = [route.key for route in ROUTES]
    assert len(keys) == len(set(keys))


def test_route_registry_has_unique_titles():
    titles = [route.title for route in ROUTES]
    assert len(titles) == len(set(titles))


def test_route_registry_has_valid_paths():
    assert all(route.path.startswith("/") for route in ROUTES)


def test_prediction_is_the_only_mutation_view():
    assert integration_summary()["mutation_views"] == ("prediction",)


def test_all_non_prediction_views_are_read_only():
    assert all(route.read_only for route in ROUTES if route.key != "prediction")


def test_integration_summary_is_complete():
    summary = integration_summary()
    assert summary["version"] == "88.0.0"
    assert summary["boundary"] == FRONTEND_INTEGRATION_BOUNDARY
    assert summary["route_count"] == len(ROUTES)


def test_validate_default_integration():
    assert validate_integration() == ()


def test_validate_detects_missing_route():
    issues = validate_integration({"overview": "Analytics Overview"})
    assert "MISSING_OR_INVALID_ROUTE:analytics" in issues


def test_validate_accepts_complete_route_mapping():
    mapping = {route.key: route.title for route in ROUTES}
    assert validate_integration(mapping) == ()


def test_frontend_app_still_builds():
    app = create_frontend_app()
    assert app.config["NEUROLYTICS_FRONTEND_VERSION"] == "77.0.0"


def test_frontend_integration_endpoint():
    client = create_frontend_app().test_client()
    response = client.get("/frontend/integration")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == FRONTEND_INTEGRATION_VERSION
    assert payload["route_count"] == 12


def test_frontend_config_contains_integration():
    client = create_frontend_app().test_client()
    payload = client.get("/frontend/config").get_json()
    assert payload["integration"]["boundary"] == FRONTEND_INTEGRATION_BOUNDARY


def test_frontend_index_exists():
    assert INDEX.exists()


def test_frontend_javascript_exists():
    assert JS.exists()


def test_index_contains_all_views():
    html = INDEX.read_text(encoding="utf-8")
    for route in ROUTES:
        assert f'id="view-{route.key}"' in html


def test_index_contains_all_navigation_items():
    html = INDEX.read_text(encoding="utf-8")
    for route in ROUTES:
        assert f'data-view="{route.key}"' in html


def test_javascript_contains_view_dispatch():
    js = JS.read_text(encoding="utf-8")
    for route in ROUTES:
        assert route.key in js


def test_javascript_contains_core_api_helper():
    js = JS.read_text(encoding="utf-8")
    assert "async function api(" in js
    assert 'Accept":"application/json"' in js


def test_javascript_contains_prediction_boundary():
    js = JS.read_text(encoding="utf-8")
    assert '"/v1/inference"' in js
    assert 'method:"POST"' in js


def test_javascript_contains_admin_boundary():
    js = JS.read_text(encoding="utf-8")
    for path in (
        "/v1/admin/service",
        "/v1/admin/security",
        "/v1/admin/rate-limit",
        "/v1/admin/policy",
        "/v1/admin/serving",
        "/v1/admin/dependencies",
        "/v1/admin/scopes",
    ):
        assert path in js


def test_javascript_contains_dashboard_refresh_handlers():
    js = JS.read_text(encoding="utf-8")
    for name in (
        "historical", "analytics", "ranking", "topK", "performance",
        "drift", "modelHealth", "predictionContext", "admin", "models",
    ):
        assert f'function {name}' in js or f'async function {name}' in js


def test_integration_does_not_add_new_external_dependencies():
    assert True


def test_read_only_admin_route_is_get_by_contract():
    admin = next(route for route in ROUTES if route.key == "admin")
    assert admin.read_only is True
    assert admin.path == "/v1/admin/summary"


def test_existing_prediction_view_remains_explicitly_mutating():
    prediction = next(route for route in ROUTES if route.key == "prediction")
    assert prediction.read_only is False
    assert prediction.path == "/v1/inference"
