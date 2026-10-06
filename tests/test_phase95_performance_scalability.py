from analytics.performance_scalability_audit import (
    DEFAULT_THRESHOLDS,
    PERFORMANCE_SCALABILITY_VERSION,
    VALID,
    WARNING,
    run_performance_scalability_audit,
    performance_scalability_summary,
    write_performance_scalability_report,
)


def test_phase95_version():
    assert PERFORMANCE_SCALABILITY_VERSION == "95.0.0"


def test_phase95_thresholds_are_defined():
    assert DEFAULT_THRESHOLDS["database_count_ms"] > 0
    assert DEFAULT_THRESHOLDS["prediction_1000_ms"] > 0
    assert DEFAULT_THRESHOLDS["panel_ranking_1000_ms"] > 0


def test_phase95_audit_runs(db):
    report = run_performance_scalability_audit(db)
    assert report.version == PERFORMANCE_SCALABILITY_VERSION
    assert report.status in (VALID, WARNING)
    assert len(report.measurements) >= 6
    assert len(report.scalability) >= 7


def test_phase95_database_measurements_exist(db):
    summary = performance_scalability_summary(run_performance_scalability_audit(db))
    names = {item["name"] for item in summary["measurements"]}
    assert "database_count" in names
    assert "database_fetch_1000" in names


def test_phase95_prediction_measurement_exists(db):
    summary = performance_scalability_summary(run_performance_scalability_audit(db))
    item = next(x for x in summary["measurements"] if x["name"] == "prediction_1000")
    assert item["iterations"] == 1000
    assert item["throughput_per_second"] > 0


def test_phase95_ranking_measurements_exist(db):
    summary = performance_scalability_summary(run_performance_scalability_audit(db))
    names = {item["name"] for item in summary["measurements"]}
    assert "panel_ranking_1000" in names
    assert "jodi_ranking_100" in names


def test_phase95_scalability_sizes_are_recorded(db):
    summary = performance_scalability_summary(run_performance_scalability_audit(db))
    sizes = [item["input_size"] for item in summary["scalability"] if item["name"] == "feature_vector_scaling"]
    assert sizes == [100, 1000, 5000, 10000]


def test_phase95_report_identity_is_present(db):
    report = run_performance_scalability_audit(db)
    assert report.report_identity.startswith("performance-scalability-")


def test_phase95_report_can_be_written(db, tmp_path):
    report = run_performance_scalability_audit(db)
    path = write_performance_scalability_report(report, tmp_path / "performance.json")
    assert path.exists()


def test_phase95_environment_is_recorded(db):
    report = run_performance_scalability_audit(db)
    assert report.environment["python"]
    assert report.environment["platform"]


def test_phase95_bottlenecks_match_warnings(db):
    report = run_performance_scalability_audit(db)
    warnings = tuple(item.name for item in report.measurements if item.status == WARNING)
    assert report.bottlenecks == warnings
