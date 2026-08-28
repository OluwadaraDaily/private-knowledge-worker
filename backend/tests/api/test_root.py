from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl
from sqlalchemy.orm import Session

from app.api.dependencies.google import get_optional_google_connection, require_google_connection
from app.api.routes import google_auth as google_auth_module
from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session
from app.integrations.google.client import GoogleApiError
from app.main import create_app


class ConnectionSession:
    def __init__(self, connection: GoogleConnection | None) -> None:
        self.connection = connection
        self.commits = 0

    def scalar(self, statement: object) -> GoogleConnection | None:
        del statement
        return self.connection

    def execute(self, statement: object) -> None:
        del statement

    def commit(self) -> None:
        self.commits += 1


def test_get_api_info(client: TestClient) -> None:
    response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Private Knowledge Worker API",
        "version": "0.1.0",
    }


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_localhost_frontend(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_google_status_reports_disconnected_without_cookie(client: TestClient) -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: ConnectionSession(None)
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/auth/google/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "email": None,
        "scopes": [],
        "token_expires_at": None,
    }


def test_google_connection_dependency_ignores_invalid_cookie() -> None:
    session = ConnectionSession(None)

    assert get_optional_google_connection(cast(Session, session), "not-a-uuid") is None


def test_google_connection_dependency_requires_connection() -> None:
    with pytest.raises(HTTPException) as error:
        require_google_connection(None)

    assert error.value.status_code == 401
    assert error.value.detail == "Google account is not connected"


def test_google_status_returns_non_secret_connection_metadata() -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        access_token_encrypted="encrypted-access-token",
        refresh_token_encrypted="encrypted-refresh-token",
        scopes=["openid", "drive.readonly"],
    )
    session = ConnectionSession(connection)
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get("/api/v1/auth/google/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "email": "user@example.com",
        "scopes": ["openid", "drive.readonly"],
        "token_expires_at": None,
    }
    assert "encrypted-access-token" not in response.text
    assert "encrypted-refresh-token" not in response.text


def test_google_drive_verify_makes_authenticated_request_for_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    session = ConnectionSession(connection)
    app.dependency_overrides[get_session] = lambda: session
    verified_connections: list[GoogleConnection] = []
    monkeypatch.setattr(
        google_auth_module,
        "verify_google_drive_connection",
        lambda _session, _settings, given_connection: verified_connections.append(given_connection),
    )

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get("/api/v1/auth/google/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "email": "user@example.com"}
    assert verified_connections == [connection]


def test_google_drive_verify_requires_a_connection() -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: ConnectionSession(None)
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/auth/google/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Google account is not connected"}


def test_google_drive_verify_reports_invalid_google_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    app.dependency_overrides[get_session] = lambda: ConnectionSession(connection)
    monkeypatch.setattr(
        google_auth_module,
        "verify_google_drive_connection",
        lambda *_args: (_ for _ in ()).throw(
            GoogleApiError("provider rejected token", kind="authentication", status_code=401)
        ),
    )

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get("/api/v1/auth/google/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Google authentication is no longer valid; reconnect Google"
    }


def test_google_drive_verify_hides_upstream_failure_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    app.dependency_overrides[get_session] = lambda: ConnectionSession(connection)
    monkeypatch.setattr(
        google_auth_module,
        "verify_google_drive_connection",
        lambda *_args: (_ for _ in ()).throw(GoogleApiError("provider body contains a secret")),
    )

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get("/api/v1/auth/google/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Google Drive verification failed"}
    assert "provider body contains a secret" not in response.text


def test_google_disconnect_clears_cookie_and_commits() -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        scopes=[],
    )
    session = ConnectionSession(connection)
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.delete("/api/v1/auth/google")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert 'google_connection_id="";' in response.headers["set-cookie"]
    assert session.commits == 1


def test_google_callback_redirects_to_frontend_after_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    connection = GoogleConnection(
        id=uuid4(),
        user_id=uuid4(),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["openid"],
    )
    session = ConnectionSession(None)
    app.dependency_overrides[get_session] = lambda: session
    monkeypatch.setattr(google_auth_module, "consume_oauth_state", lambda *_args: True)
    monkeypatch.setattr(
        google_auth_module,
        "get_settings",
        lambda: Settings(
            frontend_url=AnyHttpUrl("http://localhost:5173"),
            environment="development",
        ),
    )
    monkeypatch.setattr(google_auth_module, "exchange_authorization_code", lambda *_args: {})
    monkeypatch.setattr(
        google_auth_module,
        "persist_google_credentials",
        lambda *_args: connection,
    )

    try:
        with TestClient(app, follow_redirects=False) as test_client:
            test_client.cookies.set("oauth_state", "valid-state")
            response = test_client.get(
                "/api/v1/auth/google/callback?code=auth-code&state=valid-state"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:5173"
    assert "google_connection_id=" in response.headers["set-cookie"]
