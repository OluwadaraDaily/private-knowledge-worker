from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


def get_database_url() -> str:
    """Return the configured database URL or fail with an actionable message."""
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def get_test_database_url() -> str:
    """Return an explicitly configured isolated test database URL."""
    settings = get_settings()
    test_database_url = settings.test_database_url
    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")
    if test_database_url == settings.database_url:
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")
    return test_database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one lazily initialized SQLAlchemy engine for the process."""
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_test_engine() -> Engine:
    """Create a lazily initialized engine for the isolated test database."""
    return create_engine(get_test_database_url(), pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    with Session(get_engine()) as session:
        yield session
