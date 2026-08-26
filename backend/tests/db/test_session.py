import pytest
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.db.session import get_database_url, get_engine


def test_database_url_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_database_url()


def test_engine_is_created_lazily_from_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    get_settings.cache_clear()
    get_engine.cache_clear()

    engine = get_engine()

    assert isinstance(engine, Engine)
    assert engine.pool is not None
    engine.dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()
