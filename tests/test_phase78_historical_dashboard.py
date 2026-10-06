from analytics.historical_dashboard import HISTORICAL_DASHBOARD_VERSION

def test_phase78_version():
    assert HISTORICAL_DASHBOARD_VERSION == '78.0.0'
from analytics.historical_dashboard import HistoricalDashboardService, HISTORICAL_DASHBOARD_BOUNDARY
from database.engine import SessionLocal
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service

def test_phase78_summary_empty():
    db=SessionLocal()
    try:
        result=HistoricalDashboardService(db).summary()
        assert result['status']=='VALID'
        assert result['record_count']>=0
    finally:
        db.close()

def test_phase78_boundary():
    db=SessionLocal()
    try: assert HistoricalDashboardService(db).summary()['boundary']==HISTORICAL_DASHBOARD_BOUNDARY
    finally: db.close()

def test_phase78_markets():
    db=SessionLocal()
    try: assert isinstance(HistoricalDashboardService(db).markets(),list)
    finally: db.close()

from database.engine import SessionLocal
from analytics.historical_dashboard import HistoricalDashboardService, HISTORICAL_DASHBOARD_BOUNDARY

def test_phase78_summary_empty():
    db=SessionLocal()
    try:
        result=HistoricalDashboardService(db).summary()
        assert result['status']=='VALID'
        assert result['record_count']>=0
    finally:
        db.close()

def test_phase78_boundary():
    db=SessionLocal()
    try:
        assert HistoricalDashboardService(db).summary()['boundary']==HISTORICAL_DASHBOARD_BOUNDARY
    finally:
        db.close()
def test_phase78_markets():
    db=SessionLocal()
    try:
        assert isinstance(HistoricalDashboardService(db).markets(),list)
    finally:
        db.close()

def test_phase78_records():
    db=SessionLocal()
    try:
        assert isinstance(HistoricalDashboardService(db).records()['records'],list)
    finally:
        db.close()

def test_phase78_frequency():
    db=SessionLocal()
    try:
        result=HistoricalDashboardService(db).frequency()
        assert len(result['digits'])==10
    finally:
        db.close()
def test_phase78_daily():
    db=SessionLocal()
    try:
        assert isinstance(HistoricalDashboardService(db).daily_series()['points'],list)
    finally:
        db.close()

def test_phase78_limit_guard():
    db=SessionLocal()
    try:
        try:
            HistoricalDashboardService(db).records(limit=0)
        except ValueError:
            return
        raise AssertionError('expected ValueError')
    finally:
        db.close()

def test_phase78_large_limit_guard():
    db=SessionLocal()
    try:
        try:
            HistoricalDashboardService(db).records(limit=5001)
        except ValueError:
            return
        raise AssertionError('expected ValueError')
    finally:
        db.close()
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service

def test_phase78_production_summary_route():
    client=create_production_app(service(security_enabled=False)).test_client()
    assert client.get('/v1/historical/summary').status_code==200

def test_phase78_production_records_route():
    client=create_production_app(service(security_enabled=False)).test_client()
    assert client.get('/v1/historical/records').status_code==200

def test_phase78_production_frequency_route():
    client=create_production_app(service(security_enabled=False)).test_client()
    assert client.get('/v1/historical/frequency').status_code==200

def test_phase78_production_daily_route():
    client=create_production_app(service(security_enabled=False)).test_client()
    assert client.get('/v1/historical/daily').status_code==200
def test_phase78_frontend_contains_dashboard():
    client=create_production_app(service(security_enabled=False)).test_client()
    data=client.get('/').data
    assert b'ONE-PAGE SMART DASHBOARD' in data and b'DATABASE' in data and b'prediction-families' in data
    assert b'database-fullscreen' in data and b'Expand Database' in data and b'Collapse Database' not in data

def test_phase78_frontend_static_js():
    client=create_production_app(service(security_enabled=False)).test_client()
    data=client.get('/frontend/static/js/app.js').data
    assert b'/v1/historical/summary' in data

def test_phase78_frontend_static_css():
    client=create_production_app(service(security_enabled=False)).test_client()
    data=client.get('/frontend/static/css/app.css').data
    assert b'dashboard-grid' in data

def test_phase78_route_is_read_only():
    client=create_production_app(service(security_enabled=False)).test_client()
    assert client.post('/v1/historical/summary').status_code==405
