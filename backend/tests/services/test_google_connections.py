from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.interfaces import GoogleDriveGateway
from app.services import google_connections as google_connections_module
from app.services.credentials import GoogleCredentialError


class FakeSession:
    def __init__(self) -> None:
        self.executed_statements: list[object] = []
        self.commits = 0

    def execute(self, statement: object) -> None:
        self.executed_statements.append(statement)

    def commit(self) -> None:
        self.commits += 1


class FakeDriveClient:
    def __init__(self) -> None:
        self.access_tokens: list[str] = []

    def verify_access(self, access_token: str) -> None:
        self.access_tokens.append(access_token)


def test_verify_google_drive_connection_uses_injected_drive_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    session = FakeSession()
    session_as_orm = cast(Session, session)
    fake_drive_client = FakeDriveClient()
    drive_client: GoogleDriveGateway = fake_drive_client

    def fake_get_valid_google_access_token(
        given_session: Session,
        given_settings: Settings,
        given_connection: GoogleConnection,
    ) -> str:
        assert given_session is session_as_orm
        assert given_settings is settings
        assert given_connection is connection
        return "access-token"

    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        fake_get_valid_google_access_token,
    )

    google_connections_module.verify_google_drive_connection(
        session_as_orm, settings, connection, drive_client
    )

    assert fake_drive_client.access_tokens == ["access-token"]


def test_verify_google_drive_connection_propagates_credential_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=[],
    )
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: (_ for _ in ()).throw(GoogleCredentialError("refresh failed")),
    )
    with pytest.raises(GoogleCredentialError, match="refresh failed"):
        google_connections_module.verify_google_drive_connection(
            cast(Session, FakeSession()), settings, connection
        )


def test_disconnect_google_connection_deletes_and_commits() -> None:
    session = FakeSession()
    connection = GoogleConnection(
        id=UUID(int=1),
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=[],
    )

    google_connections_module.disconnect_google_connection(cast(Session, session), connection)

    assert len(session.executed_statements) == 1
    assert session.commits == 1
