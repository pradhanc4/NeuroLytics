from database.engine import Base, engine
from database import models  # noqa: F401


def init_database():
    """Create all registered database tables."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_database()
    print("NeuroLytics database initialized successfully.")