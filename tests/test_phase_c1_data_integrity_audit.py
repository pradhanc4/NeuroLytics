from database.engine import SessionLocal
from analytics.data_integrity_audit import run_data_integrity_audit, data_integrity_summary, write_data_integrity_report

def test_audit_allows_supported_jodi_feedback_stages_and_warning_only():
    db = SessionLocal()
    try:
        report = run_data_integrity_audit(db)
        summary = data_integrity_summary(report)
        assert summary["status"] == "VALID"
        assert summary["row_counts"]["historical_results"] == 1990
        assert summary["invalid_issue_count"] == 0
        assert summary["warning_count"] >= 0
        assert all(
            item["code"] != "INVALID_FEEDBACK_STAGE"
            for item in summary["issues"]
        )
        write_data_integrity_report(report)
    finally:
        db.close()
