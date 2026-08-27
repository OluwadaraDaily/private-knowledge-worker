from datetime import UTC, datetime
from typing import cast
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl
from sqlalchemy.orm import Session

from app.api.routes import google_auth as google_auth_module
from app.core.config import Settings
from app.db.models.oauth_state import OAuthState
from app.db.session import get_session
from app.main import create_app
from app.services.oauth import consume_oauth_state, create_oauth_authorization_url


class FakeSession:
    def __init__(self) -> None:
        self.records: list[OAuthState] = []
        self.commits = 0

    def add(self, record: OAuthState) -> None:
        self.records.append(record)

    def commit(self) -> None:
        self.commits += 1

    def scalar(self, statement: object) -> OAuthState | None:
        del statement
        return self.records[0] if self.records else None

    def execute(self, statement: object) -> object:
        del statement
        self.records.clear()
        return object()


def test_create_oauth_authorization_url_stores_hashed_expiring_state() -> None:
    session = FakeSession()
    settings = Settings(
        backend_url=AnyHttpUrl("http://127.0.0.1:8000"),
        oauth_client_id="client-id",
    )

    authorization = create_oauth_authorization_url(cast(Session, session), settings)

    parsed = urlparse(authorization.url)
    query = parse_qs(parsed.query)
    raw_state = query["state"][0]

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == [
        "http://127.0.0.1:8000/api/v1/auth/google/callback"
    ]
    assert query["response_type"] == ["code"]
    assert set(query["scope"][0].split()) == set(settings.oauth_scopes)
    assert raw_state
    assert session.commits == 1
    assert len(session.records) == 1
    assert session.records[0].state_hash != raw_state
    assert session.records[0].expires_at > datetime.now(UTC)


def test_create_oauth_authorization_url_requires_client_id() -> None:
    settings = Settings(oauth_client_id="")

    with pytest.raises(ValueError, match="OAuth client ID is not configured"):
        create_oauth_authorization_url(cast(Session, FakeSession()), settings)


def test_consume_oauth_state_is_one_time() -> None:
    session = FakeSession()
    settings = Settings(oauth_client_id="client-id")
    authorization = create_oauth_authorization_url(cast(Session, session), settings)

    assert consume_oauth_state(cast(Session, session), authorization.state) is True
    assert consume_oauth_state(cast(Session, session), authorization.state) is False


def test_start_google_oauth_redirects_to_google(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    application = create_app()
    application.dependency_overrides[get_session] = lambda: session
    monkeypatch.setattr(
        google_auth_module,
        "get_settings",
        lambda: Settings(
            backend_url=AnyHttpUrl("http://127.0.0.1:8000"),
            oauth_client_id="client-id",
        ),
    )

    with TestClient(application, follow_redirects=False) as client:
        response = client.get("/api/v1/auth/google/start")
    application.dependency_overrides.clear()

    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    assert session.commits == 1
