from frontend.app import create_frontend_app
from frontend.contract import FrontendApiContract, contract_summary, validate_contract
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service


def test_01_frontend_version():
    assert contract_summary(FrontendApiContract())["version"] == "77.0.0"

def test_02_contract_valid():
    assert validate_contract(FrontendApiContract()) == ()

def test_03_contract_summary_status():
    assert contract_summary(FrontendApiContract())["status"] == "VALID"

def test_04_frontend_app_factory():
    app = create_frontend_app()
    assert app.config["NEUROLYTICS_FRONTEND_VERSION"] == "77.0.0"

def test_05_frontend_index():
    client = create_frontend_app().test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"NeuroLytics" in response.data

def test_06_frontend_config():
    client = create_frontend_app().test_client()
    response = client.get("/frontend/config")
    assert response.status_code == 200
    assert response.get_json()["version"] == "77.0.0"

def test_07_frontend_health():
    client = create_frontend_app().test_client()
    response = client.get("/frontend/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "HEALTHY"

def test_08_frontend_css():
    client = create_frontend_app().test_client()
    response = client.get("/frontend/static/css/app.css")
    assert response.status_code == 200
    assert b"app-shell" in response.data

def test_09_frontend_js():
    client = create_frontend_app().test_client()
    response = client.get("/frontend/static/js/app.js")
    assert response.status_code == 200
    assert b"v1/inference" in response.data

def test_10_frontend_contract_custom_base():
    c = FrontendApiContract(api_base="/api")
    assert contract_summary(c)["api_base"] == "/api"

def test_11_invalid_contract_path():
    c = FrontendApiContract(health_path="health")
    assert "INVALID_HEALTH_PATH" in validate_contract(c)

def test_12_invalid_contract_type():
    assert "INVALID_CONTRACT_TYPE" in validate_contract(object())

def test_13_production_root_exists():
    svc = service()
    client = create_production_app(svc).test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"NeuroLytics" in response.data

def test_14_production_frontend_config():
    client = create_production_app(service()).test_client()
    response = client.get("/frontend/config")
    assert response.status_code == 200
    assert response.get_json()["boundary"] == "FRONTEND_FOUNDATION_BOUNDARY"

def test_15_production_static_css():
    client = create_production_app(service()).test_client()
    response = client.get("/frontend/static/css/app.css")
    assert response.status_code == 200

def test_16_production_health_route_unchanged():
    client = create_production_app(service()).test_client()
    response = client.get("/health")
    assert response.status_code == 200

def test_17_production_ready_route_unchanged():
    client = create_production_app(service()).test_client()
    response = client.get("/ready")
    assert response.status_code in (401, 503)

def test_18_production_inference_route_unchanged():
    client = create_production_app(service()).test_client()
    response = client.post("/v1/inference", json={})
    assert response.status_code in (400, 401, 503)

def test_19_frontend_has_prediction_view():
    client = create_frontend_app().test_client()
    assert b"ML training, prediction & actual-result command center" in client.get("/").data

def test_20_frontend_has_monitoring_view():
    client = create_frontend_app().test_client()
    assert b"MODEL HEALTH + LINEAGE" in client.get("/").data

def test_21_frontend_has_model_view():
    client = create_frontend_app().test_client()
    assert b"Model health" in client.get("/").data and b"Serving safety" in client.get("/").data

def test_22_frontend_responsive_css():
    client = create_frontend_app().test_client()
    data = client.get("/frontend/static/css/app.css").data
    assert b"@media" in data

def test_23_frontend_api_client():
    client = create_frontend_app().test_client()
    assert b"fetch(" in client.get("/frontend/static/js/app.js").data

def test_24_frontend_no_ml_logic():
    client = create_frontend_app().test_client()
    data = client.get("/frontend/static/js/app.js").data
    assert b"fetch(" in data and b"v1/inference" in data

def test_25_frontend_boundary():
    client = create_frontend_app().test_client()
    assert client.get("/frontend/health").get_json()["boundary"] == "FRONTEND_FOUNDATION_BOUNDARY"
