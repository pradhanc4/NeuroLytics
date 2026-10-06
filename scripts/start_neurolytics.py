from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "neurolytics_startup.log"
HOST = os.getenv("NEUROLYTICS_HOST", "127.0.0.1")
PORT = int(os.getenv("NEUROLYTICS_PORT", "5000"))
OPEN_BROWSER = os.getenv("NEUROLYTICS_OPEN_BROWSER", "1") != "0"


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def create_launcher_app():
    """Start the real production API boundary without activating prediction."""
    from analytics.api_rate_limit import ApiRateLimitPolicy, ApiRateLimiter
    from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy
    from analytics.performance_monitoring_api import PerformanceMonitoringApiService
    from analytics.production_api import InferenceApiService
    from analytics.production_service_weight import (
        NeuroLyticsProductionService,
        ProductionServicePolicy,
        create_production_app,
    )
    from analytics.production_serving import BLOCKED, ServingCheck, ServingPlan, ServingPolicy

    blocked_plan = ServingPlan(
        serving_id="neurolytics-local-data-entry",
        activation_id="NOT_ACTIVATED",
        model_identity="NEUROLYTICS_PENDING_MODEL",
        model_version="PENDING",
        artifact_identity="PERSISTED_ARTIFACT_REQUIRED",
        policy=ServingPolicy(),
        checks=(
            ServingCheck(
                "ACTIVATION_STATUS",
                "FAIL",
                "Operational model activation is intentionally blocked until a validated persisted artifact exists.",
            ),
        ),
        status=BLOCKED,
        serving_state=BLOCKED,
        plan_identity="production-serving-local-data-entry-blocked",
    )

    inference_service = InferenceApiService(
        blocked_plan,
        lambda _features: (_ for _ in ()).throw(
            RuntimeError("Operational inference is not activated.")
        ),
    )

    disabled_limits = ApiRateLimitPolicy(enabled=False)
    service = NeuroLyticsProductionService(
        inference_service,
        PerformanceMonitoringApiService(),
        security_store=ApiCredentialStore(),
        security_policy=ApiSecurityPolicy(enabled=False),
        rate_limit_policy=disabled_limits,
        rate_limiter=ApiRateLimiter(disabled_limits),
        policy=ProductionServicePolicy(
            require_inference_ready=False,
            require_monitoring_healthy=True,
            require_shared_security=True,
            require_shared_rate_limiter=True,
        ),
    )

    return create_production_app(service)


def main() -> None:
    os.chdir(PROJECT_ROOT)
    log("NeuroLytics launcher starting.")
    log(f"Project root: {PROJECT_ROOT}")
    log(f"UI/API address: http://{HOST}:{PORT}/")
    log("Production inference gate: CONDITIONAL / NOT ACTIVATED.")
    log("Historical data entry API: ENABLED.")
    log("No synthetic model activation or operational predictor is used.")

    app = create_launcher_app()

    if OPEN_BROWSER:
        webbrowser.open(f"http://{HOST}:{PORT}/", new=2)

    log("NeuroLytics UI + production API routes are running.")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("NeuroLytics launcher stopped by user.")
    except Exception as exc:
        log(f"NeuroLytics launcher failed: {type(exc).__name__}: {exc}")
        raise

