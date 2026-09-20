from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from database.config import get_database_url


DATABASE_URL = get_database_url()


class Base(DeclarativeBase):
    """Base class for all NeuroLytics SQLAlchemy models."""

    pass


connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    """Provide a database session."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()