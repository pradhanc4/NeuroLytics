import sys
from pathlib import Path

import pytest
from sqlalchemy import delete


# Ensure the NeuroLytics project root is available
# when pytest loads the test configuration.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.engine import Base, SessionLocal, engine
from database.models import (
    HistoricalClassification,
    HistoricalDataQuality,
    HistoricalResult,
    JodiFamily,
    JodiFamilyMember,
    Market,
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)


@pytest.fixture
def db():
    """Create an isolated database session for each test."""

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        yield session

    finally:
        session.rollback()

        # Delete dependent tables first to respect
        # foreign-key relationships.

        session.execute(
            delete(HistoricalDataQuality)
        )

        session.execute(
            delete(HistoricalClassification)
        )

        session.execute(
            delete(PanelFamilyMember)
        )

        session.execute(
            delete(PanelFamily)
        )

        session.execute(
            delete(JodiFamilyMember)
        )

        session.execute(
            delete(JodiFamily)
        )

        session.execute(
            delete(PannaReference)
        )

        session.execute(
            delete(HistoricalResult)
        )

        session.execute(
            delete(Market)
        )

        session.commit()
        session.close()

