import pytest

from database.engine import Base, SessionLocal, engine
from database.models import (
    HistoricalResult,
    Market,
    PannaReference,
)
from sqlalchemy import delete


@pytest.fixture
def db():
    """Create an isolated database session for each test."""

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()

        session.execute(delete(PannaReference))
        session.execute(delete(HistoricalResult))
        session.execute(delete(Market))

        session.commit()
        session.close()