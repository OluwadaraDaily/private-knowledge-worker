import pytest
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.db.session import get_database_url, get_engine, get_test_database_url, get_test_engine


def test_database_url_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_database_url()


def test_engine_is_created_lazily_from_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    get_settings.cache_clear()

    engine = get_engine()

    assert isinstance(engine, Engine)
    assert engine.pool is not None
    engine.dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_test_database_url_is_required_and_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://dev")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL is not configured"):
        get_test_database_url()

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://dev")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="must differ"):
        get_test_database_url()


def test_test_engine_uses_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///test.db")
    get_settings.cache_clear()
    get_test_engine.cache_clear()

    engine = get_test_engine()

    assert str(engine.url) == "sqlite:///test.db"
    engine.dispose()
    get_test_engine.cache_clear()
    get_settings.cache_clear()
