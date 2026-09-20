from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///database/neurolytics.db",
)


def get_database_url() -> str:
    """Return the configured database URL."""
    return DATABASE_URL