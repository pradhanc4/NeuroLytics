from pathlib import Path
import subprocess
from tests.test_phase76_production_service_integration import service
from analytics.production_service import create_production_app

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/"frontend/static/js/app.js"

def app_client():
    svc=service(security_enabled=False,rate_enabled=False)
    return create_production_app(svc).test_client()

def test_89_01_javascript_syntax():
    result=subprocess.run(["node","--check",str(JS)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr

def test_89_02_frontend_is_served_by_production_boundary():
    c=app_client()
    r=c.get("/")
    assert r.status_code==200
    assert b"Overview" in r.data
    assert b"Prediction" in r.data

def test_89_03_frontend_static_javascript_is_served():
    r=app_client().get("/frontend/static/js/app.js")
    assert r.status_code==200
    assert b"switchView" in r.data
    assert b"/v1/inference" in r.data

def test_89_04_health_and_readiness_are_reachable():
    c=app_client()
    assert c.get("/health").status_code==200
    assert c.get("/ready").status_code in (200,503)

def test_89_05_core_dashboard_endpoints_are_reachable():
    c=app_client()
    paths=["/v1/analytics/summary","/v1/historical/summary","/v1/ranking/summary",
           "/v1/top-k/summary","/v1/performance/summary","/v1/drift/summary",
           "/v1/model-health/summary","/v1/model/summary","/v1/admin/summary",
           "/v1/monitoring/summary"]
    statuses=[c.get(p).status_code for p in paths]
    assert all(s in (200,404,503) for s in statuses)
    assert 404 not in statuses

def test_89_06_inference_boundary_is_post_only():
    r=app_client().get("/v1/inference")
    assert r.status_code in (405,415)

def test_89_07_frontend_has_all_phase_89_navigation_views():
    html=app_client().get("/").get_data(as_text=True)
    for label in ["Analytics","Historical Data","Ranking","Top-K","Performance",
                  "Drift / Monitoring","Model Health","Prediction",
                  "Admin / Configuration","Monitoring","Model Status"]:
        assert label in html

def test_89_08_live_client_loads_all_api_families():
    js=JS.read_text(encoding="utf-8")
    for path in ["/v1/analytics/summary","/v1/historical/summary",
                 "/v1/ranking/summary","/v1/top-k/summary",
                 "/v1/performance/summary","/v1/drift/summary",
                 "/v1/model-health/summary","/v1/model/summary",
                 "/v1/admin/summary","/v1/monitoring/summary"]:
        assert path in js

def test_89_09_prediction_client_preserves_mutation_boundary():
    js=JS.read_text(encoding="utf-8")
    assert 'api("/v1/inference"' in js
    assert 'method:"POST"' in js

def test_89_10_phase_89_is_local_first():
    js=JS.read_text(encoding="utf-8")
    assert "http://" not in js and "https://" not in js
