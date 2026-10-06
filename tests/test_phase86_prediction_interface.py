from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import payload, service as phase76_service


def client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_01_prediction_view_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="view-prediction"' in html


def test_02_prediction_navigation_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'data-view="prediction"' in html


def test_03_prediction_title_exists():
    html = client().get("/").get_data(as_text=True)
    assert "Prediction Interface" in html


def test_04_request_id_control_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-request-id"' in html


def test_05_model_control_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-model-input"' in html


def test_06_version_control_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-version-input"' in html


def test_07_artifact_control_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-artifact-input"' in html


def test_08_features_control_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-features"' in html


def test_09_run_button_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="run-inference"' in html


def test_10_refresh_button_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-refresh"' in html


def test_11_result_panel_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-result"' in html


def test_12_status_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="inference-status"' in html


def test_13_model_kpi_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-model"' in html


def test_14_version_kpi_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-version"' in html


def test_15_artifact_kpi_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-artifact"' in html


def test_16_readiness_kpi_exists():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-readiness"' in html


def test_17_inference_route_is_configured():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["inference"] == "/v1/inference"


def test_18_prediction_js_exists():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "predictionContext" in js


def test_19_prediction_context_reads_health():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'api("/health")' in js


def test_20_prediction_context_reads_readiness():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'api("/ready")' in js


def test_21_prediction_js_posts_inference():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'api("/v1/inference"' in js
    assert 'method:"POST"' in js


def test_22_prediction_js_uses_request_id():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "request_id:requestId" in js


def test_23_prediction_js_uses_model_identity():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "model_identity:model" in js


def test_24_prediction_js_uses_model_version():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "model_version:version" in js


def test_25_prediction_js_uses_artifact_identity():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "artifact_identity:artifact" in js


def test_26_prediction_js_uses_features():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "features" in js


def test_27_prediction_js_validates_json():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "Features must be valid JSON." in js


def test_28_prediction_js_rejects_array_features():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "Array.isArray(features)" in js


def test_29_prediction_js_rejects_non_numeric_features():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "must be a finite number" in js


def test_30_prediction_js_displays_result():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'prediction-result-card' in js
    assert 'JSON.stringify(data,null,2)' in js


def test_31_prediction_route_accepts_existing_contract():
    response = client().post("/v1/inference", json=payload())
    assert response.status_code == 200
    assert response.get_json()["status"] == "API_ACCEPTED"


def test_32_prediction_result_contains_prediction():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["prediction"] == 3.0


def test_33_prediction_result_contains_request_id():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["request_id"] == "phase76-request"


def test_34_prediction_result_contains_model_identity():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["model_identity"]


def test_35_prediction_result_contains_model_version():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["model_version"]


def test_36_prediction_result_contains_artifact_identity():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["artifact_identity"]


def test_37_prediction_result_contains_response_identity():
    response = client().post("/v1/inference", json=payload())
    assert response.get_json()["response_identity"]


def test_38_prediction_result_is_deterministic():
    first = client().post("/v1/inference", json=payload()).get_json()
    second = client().post("/v1/inference", json=payload()).get_json()
    assert first["prediction"] == second["prediction"]
    assert first["request_hash"] == second["request_hash"]
    assert first["response_identity"] == second["response_identity"]


def test_39_missing_request_id_rejected():
    data = payload()
    data.pop("request_id")
    response = client().post("/v1/inference", json=data)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "MISSING_FIELDS"


def test_40_missing_model_identity_rejected():
    data = payload()
    data.pop("model_identity")
    response = client().post("/v1/inference", json=data)
    assert response.status_code == 400


def test_41_missing_model_version_rejected():
    data = payload()
    data.pop("model_version")
    response = client().post("/v1/inference", json=data)
    assert response.status_code == 400


def test_42_missing_artifact_identity_rejected():
    data = payload()
    data.pop("artifact_identity")
    response = client().post("/v1/inference", json=data)
    assert response.status_code == 400


def test_43_missing_features_rejected():
    data = payload()
    data.pop("features")
    response = client().post("/v1/inference", json=data)
    assert response.status_code == 400


def test_44_non_object_json_rejected():
    response = client().post("/v1/inference", json=[1, 2])
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON_BODY"


def test_45_invalid_feature_value_rejected_by_server():
    data = payload()
    data["features"] = {"f1": "bad", "f2": 2}
    response = client().post("/v1/inference", json=data)
    assert response.status_code in (400, 422)


def test_46_wrong_model_identity_rejected():
    data = payload()
    data["model_identity"] = "wrong-model"
    response = client().post("/v1/inference", json=data)
    assert response.status_code in (400, 422)


def test_47_wrong_model_version_rejected():
    data = payload()
    data["model_version"] = "wrong-version"
    response = client().post("/v1/inference", json=data)
    assert response.status_code in (400, 422)


def test_48_wrong_artifact_identity_rejected():
    data = payload()
    data["artifact_identity"] = "wrong-artifact"
    response = client().post("/v1/inference", json=data)
    assert response.status_code in (400, 422)


def test_49_get_inference_not_allowed():
    assert client().get("/v1/inference").status_code == 405


def test_50_prediction_section_mentions_server_side_logic():
    html = client().get("/").get_data(as_text=True)
    assert "production serving boundary" in html


def test_51_prediction_context_preserves_readiness_wording():
    html = client().get("/").get_data(as_text=True)
    assert "Production inference boundary" in html


def test_52_prediction_features_are_editable():
    html = client().get("/").get_data(as_text=True)
    assert 'id="prediction-features"' in html
    assert 'readonly' not in html.split('id="prediction-features"', 1)[1].split(">", 1)[0]


def test_53_serving_metadata_is_read_only_in_ui():
    html = client().get("/").get_data(as_text=True)
    for control in ("prediction-model-input", "prediction-version-input", "prediction-artifact-input"):
        fragment = html.split(f'id="{control}"', 1)[1].split(">", 1)[0]
        assert "readonly" in fragment


def test_54_prediction_view_has_phase_label():
    html = client().get("/").get_data(as_text=True)
    assert "INFERENCE / PHASE 86" in html


def test_55_prediction_refresh_wired():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'prediction-refresh").onclick=predictionContext' in js
