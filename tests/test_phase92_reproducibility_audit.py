from datetime import date

from analytics.reproducibility_audit import (
    DEFAULT_SEED,
    REPRODUCIBILITY_AUDIT_VERSION,
    VALID,
    configuration_identity,
    dataset_fingerprint,
    deterministic_configuration,
    environment_identity,
    environment_snapshot,
    reproducibility_summary,
    run_reproducibility_audit,
    seed_everything,
    stable_identity,
    validate_reproducibility_audit,
    write_reproducibility_report,
)
from database.models import HistoricalResult, Market
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as production_test_service


def add_result(db, day=1):
    market = db.query(Market).filter(Market.name == "Audit Market").first()
    if market is None:
        market = Market(name="Audit Market")
        db.add(market)
        db.flush()
    db.add(
        HistoricalResult(
            market_id=market.id,
            result_date=date(2026, 1, day),
            open_result="123",
            jodi_result="45",
            close_result="678",
            col1=1,
            col2=2,
            col3=3,
            col4=4,
            col5=5,
            col6=6,
            col7=7,
            col8=8,
        )
    )
    db.commit()
    return market


def test_phase92_version():
    assert REPRODUCIBILITY_AUDIT_VERSION == "92.0.0"


def test_phase92_stable_identity_is_deterministic():
    first = stable_identity("test-", {"b": 2, "a": [1, 2]})
    second = stable_identity("test-", {"a": [1, 2], "b": 2})
    assert first == second


def test_phase92_seed_configuration_is_stable():
    assert deterministic_configuration(DEFAULT_SEED) == deterministic_configuration(DEFAULT_SEED)
    assert configuration_identity(DEFAULT_SEED) == configuration_identity(DEFAULT_SEED)


def test_phase92_environment_identity_is_stable():
    assert environment_snapshot() == environment_snapshot()
    assert environment_identity() == environment_identity()


def test_phase92_dataset_fingerprint_is_order_stable(db):
    add_result(db, 1)
    add_result(db, 2)
    first = dataset_fingerprint(db)
    second = dataset_fingerprint(db)
    assert first == second
    assert first[1] == 2


def test_phase92_full_audit_is_valid(db):
    add_result(db, 1)
    report = run_reproducibility_audit(db)
    status, issues = validate_reproducibility_audit(report)
    assert status == VALID
    assert issues == ()
    assert report.is_reproducible
    assert len(report.replay_checks) == 3
    assert all(item.reproducible for item in report.replay_checks)


def test_phase92_summary_contains_fingerprints(db):
    add_result(db)
    summary = reproducibility_summary(run_reproducibility_audit(db))
    assert summary["status"] == VALID
    assert summary["dataset_identity"].startswith("dataset-")
    assert summary["schema_identity"].startswith("schema-")
    assert summary["source_identity"].startswith("source-")
    assert summary["environment_identity"].startswith("environment-")
    assert summary["configuration_identity"].startswith("configuration-")
    assert summary["artifact_count"] >= 0


def test_phase92_report_identity_is_reproducible(db):
    add_result(db)
    first = run_reproducibility_audit(db)
    second = run_reproducibility_audit(db)
    assert first.report_identity == second.report_identity
    assert first.dataset_identity == second.dataset_identity
    assert first.source_identity == second.source_identity


def test_phase92_seed_function_accepts_integer():
    assert seed_everything(12345) == 12345


def test_phase92_report_can_be_written(db, tmp_path):
    add_result(db)
    report = run_reproducibility_audit(db)
    path = write_reproducibility_report(
        report,
        tmp_path / "reproducibility.json",
    )
    assert path.exists()
    assert "reproducibility-audit-" in path.read_text(encoding="utf-8")


def test_phase92_admin_endpoint_exposes_audit(db):
    add_result(db)
    app = create_production_app(
        production_test_service(security_enabled=False, rate_enabled=False)
    )
    response = app.test_client().get("/v1/admin/reproducibility")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == VALID
    assert payload["version"] == REPRODUCIBILITY_AUDIT_VERSION
    assert payload["report_identity"].startswith("reproducibility-audit-")


def test_phase92_admin_endpoint_requires_admin_scope():
    app = create_production_app(
        production_test_service(security_enabled=True, rate_enabled=False)
    )
    response = app.test_client().get("/v1/admin/reproducibility")
    assert response.status_code in {401, 403}
