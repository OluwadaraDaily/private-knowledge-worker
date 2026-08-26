import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

DATABASE_URL_ENV = "DATABASE_URL"


def get_database_url() -> str:
    """Return the configured database URL or fail with an actionable message."""
    database_url = os.getenv(DATABASE_URL_ENV)
    if not database_url:
        raise RuntimeError(f"{DATABASE_URL_ENV} is not configured")
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one lazily initialized SQLAlchemy engine for the process."""
    return create_engine(get_database_url(), pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    with Session(get_engine()) as session:
        yield session
