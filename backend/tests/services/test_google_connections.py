from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.interfaces import (
    GoogleDriveFolder,
    GoogleDriveFolderLister,
    GoogleDriveFolderPage,
    GoogleDriveVerifier,
)
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
        self.folder_requests: list[tuple[str, str | None, int]] = []
        self.folder_page = GoogleDriveFolderPage(
            folders=(GoogleDriveFolder(id="folder-1", name="Projects", parents=()),),
            next_page_token="next-page",
        )

    def verify_access(self, access_token: str) -> None:
        self.access_tokens.append(access_token)

    def list_folders(
        self,
        access_token: str,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> GoogleDriveFolderPage:
        self.folder_requests.append((access_token, page_token, page_size))
        return self.folder_page


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
    drive_client: GoogleDriveVerifier = fake_drive_client

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


def test_list_google_drive_folders_uses_injected_drive_gateway(
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
    drive_client: GoogleDriveFolderLister = fake_drive_client
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "access-token",
    )

    page = google_connections_module.list_google_drive_folders(
        session_as_orm,
        settings,
        connection,
        page_token="previous-page",
        page_size=25,
        drive_client=drive_client,
    )

    assert page == fake_drive_client.folder_page
    assert fake_drive_client.folder_requests == [("access-token", "previous-page", 25)]


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
