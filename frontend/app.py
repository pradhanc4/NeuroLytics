from __future__ import annotations

from flask import Flask, jsonify, render_template

from frontend.contract import FrontendApiContract, contract_summary, validate_contract
from frontend.integration import integration_summary

FRONTEND_BOUNDARY = "FRONTEND_FOUNDATION_BOUNDARY"

def create_frontend_app(
    *,
    contract: FrontendApiContract = FrontendApiContract(),
) -> Flask:
    issues = validate_contract(contract)
    if issues:
        raise ValueError("invalid frontend contract: " + ", ".join(issues))
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/frontend/static",
    )
    app.config["NEUROLYTICS_FRONTEND_VERSION"] = "77.0.0"
    app.config["NEUROLYTICS_FRONTEND_BOUNDARY"] = FRONTEND_BOUNDARY
    app.config["NEUROLYTICS_FRONTEND_INTEGRATION"] = integration_summary()
    app.config["NEUROLYTICS_FRONTEND_CONTRACT"] = contract

    @app.get("/")
    def index():
        return render_template("index_weight.html")

    @app.get("/frontend/config")
    def config():
        return jsonify({
            "version": "77.0.0",
            "boundary": FRONTEND_BOUNDARY,
            "contract": dict(contract_summary(contract)),
            "integration": integration_summary(),
        })

    @app.get("/frontend/integration")
    def integration():
        return jsonify(integration_summary())

    @app.get("/frontend/health")
    def health():
        return jsonify({
            "status": "HEALTHY",
            "version": "77.0.0",
            "boundary": FRONTEND_BOUNDARY,
            "integration_version": integration_summary()["version"],
        })

    return app

__all__ = ["FRONTEND_BOUNDARY", "create_frontend_app"]

