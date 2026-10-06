import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.engine import Base
from database.models import (
    HistoricalClassification,
    HistoricalDataQuality,
    HistoricalResult,
    PredictionFeedback,
    SequentialPredictionStage,
    JodiFamily,
    JodiFamilyMember,
    Market,
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)


# Tests that request the db fixture must never operate on the live
# production database.  Use a dedicated SQLite file for test isolation.
TEST_DB_PATH = PROJECT_ROOT / "tests" / ".pytest_neurolytics.db"
TEST_ENGINE = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture
def db():
    """Create an isolated database session for each test."""

    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.rollback()

        session.execute(delete(HistoricalDataQuality))
        session.execute(delete(HistoricalClassification))
        session.execute(delete(PanelFamilyMember))
        session.execute(delete(PanelFamily))
        session.execute(delete(JodiFamilyMember))
        session.execute(delete(JodiFamily))
        session.execute(delete(PannaReference))
        session.execute(delete(PredictionFeedback))
        session.execute(delete(SequentialPredictionStage))
        session.execute(delete(HistoricalResult))
        session.execute(delete(Market))

        session.commit()
        session.close()
