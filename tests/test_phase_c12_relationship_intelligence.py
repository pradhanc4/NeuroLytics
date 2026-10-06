from datetime import date

from analytics.digit_transition_matrix import build_digit_transition_matrix
from analytics.family_transition_intelligence import build_family_transition_table
from analytics.historical_relationship_intelligence import (
    C12_VERSION,
    build_relationship_intelligence,
    validate_relationship_intelligence,
)
from analytics.temporal_relationship_analysis import day_gap, rolling_frequency
from database.models import HistoricalResult, Market


def _seed(db):
    market = Market(name="C12 Test Market")
    db.add(market)
    db.flush()
    rows = [
        ("2026-01-01", "448", "63", "120"),
        ("2026-01-02", "356", "48", "134"),
        ("2026-01-03", "559", "97", "377"),
    ]
    for d, o, j, c in rows:
        db.add(HistoricalResult(
            market_id=market.id, result_date=date.fromisoformat(d),
            open_result=o, jodi_result=j, close_result=c,
            col1=int(o[0]), col2=int(o[1]), col3=int(o[2]),
            col4=int(j[0]), col5=int(j[1]),
            col6=int(c[0]), col7=int(c[1]), col8=int(c[2]),
        ))
    db.commit()
    return market.id


def test_c12_version_and_digit_transition():
    assert C12_VERSION == "C.12.0"
    matrix = build_digit_transition_matrix([(1, 2), (1, 2), (1, 3), (3, 1)])
    assert matrix[0].source_digit == 1
    assert matrix[0].probability == 0.66666667


def test_c12_family_and_temporal_helpers():
    table = build_family_transition_table([("12", "13"), ("12", "13"), ("12", "14")])
    assert table[0].count == 2
    assert table[0].probability == 0.66666667
    assert day_gap(date(2026, 1, 1), date(2026, 1, 4)) == 3
    assert rolling_frequency([1, 1, 2], 3)[1] == 0.66666667


def test_c12_relationship_report_is_temporal_safe(db):
    market_id = _seed(db)
    report = build_relationship_intelligence(db, market_id)
    status, issues = validate_relationship_intelligence(report)
    assert status == "VALID"
    assert issues == ()
    assert report.record_count == 3
    assert report.temporal_safe is True
    assert len(report.relationship_tables) == 7
    assert len(report.transition_tables) == 8


def test_c12_relationships_include_required_position_relationships(db):
    market_id = _seed(db)
    report = build_relationship_intelligence(db, market_id)
    names = {item.name for item in report.relationship_tables}
    assert "open_digit_to_jodi_digit" in names
    assert "open_digit_to_close_digit" in names
    assert "jodi_digit_to_close_digit" in names
    assert "jodi_first_to_second" in names
    assert "close_first_to_second" in names
    assert "close_second_to_third" in names


def test_c12_transitions_use_previous_to_current_only(db):
    market_id = _seed(db)
    report = build_relationship_intelligence(db, market_id)
    names = {item.name for item in report.transition_tables}
    assert "previous_open_value_to_current_open_value" in names
    assert "previous_jodi_to_current_close" in names
    assert "previous_open_to_current_jodi" in names
