from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.client import GoogleApiError
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
        self.folder_pages: dict[str | None, GoogleDriveFolderPage] = {None: self.folder_page}
        self.verify_errors: list[BaseException] = []

    def verify_access(self, access_token: str) -> None:
        self.access_tokens.append(access_token)
        if self.verify_errors:
            raise self.verify_errors.pop(0)

    def list_folders(
        self,
        access_token: str,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> GoogleDriveFolderPage:
        self.folder_requests.append((access_token, page_token, page_size))
        return self.folder_pages.get(page_token, self.folder_page)


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


def test_google_drive_request_refreshes_after_token_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    fake_drive_client = FakeDriveClient()
    fake_drive_client.verify_errors = [
        GoogleApiError("expired token", kind="authentication", status_code=401)
    ]
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "expired-token",
    )
    monkeypatch.setattr(
        google_connections_module,
        "refresh_google_access_token",
        lambda *_args: "fresh-token",
    )

    google_connections_module.verify_google_drive_connection(
        cast(Session, FakeSession()),
        settings,
        connection,
        fake_drive_client,
    )

    assert fake_drive_client.access_tokens == ["expired-token", "fresh-token"]


def test_google_drive_request_surfaces_refresh_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    fake_drive_client = FakeDriveClient()
    fake_drive_client.verify_errors = [
        GoogleApiError("revoked token", kind="authentication", status_code=401)
    ]
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "expired-token",
    )
    monkeypatch.setattr(
        google_connections_module,
        "refresh_google_access_token",
        lambda *_args: (_ for _ in ()).throw(
            GoogleCredentialError("Google access-token refresh failed")
        ),
    )

    with pytest.raises(GoogleCredentialError, match="refresh failed"):
        google_connections_module.verify_google_drive_connection(
            cast(Session, FakeSession()),
            settings,
            connection,
            fake_drive_client,
        )


def test_google_drive_request_refreshes_at_most_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=["drive.readonly"],
    )
    fake_drive_client = FakeDriveClient()
    fake_drive_client.verify_errors = [
        GoogleApiError("expired token", kind="authentication", status_code=401),
        GoogleApiError("refreshed token rejected", kind="authentication", status_code=401),
    ]
    refresh_calls = 0
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "expired-token",
    )

    def fake_refresh(*_args: object) -> str:
        nonlocal refresh_calls
        refresh_calls += 1
        return "fresh-token"

    monkeypatch.setattr(google_connections_module, "refresh_google_access_token", fake_refresh)

    with pytest.raises(GoogleApiError, match="rejected"):
        google_connections_module.verify_google_drive_connection(
            cast(Session, FakeSession()),
            settings,
            connection,
            fake_drive_client,
        )

    assert refresh_calls == 1
    assert fake_drive_client.access_tokens == ["expired-token", "fresh-token"]


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


def test_list_all_google_drive_folders_follows_page_tokens(
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
    fake_drive_client = FakeDriveClient()
    first_page = GoogleDriveFolderPage(
        folders=(GoogleDriveFolder(id="folder-1", name="One", parents=()),),
        next_page_token="next-page",
    )
    second_page = GoogleDriveFolderPage(
        folders=(GoogleDriveFolder(id="folder-2", name="Two", parents=()),),
        next_page_token=None,
    )
    fake_drive_client.folder_pages = {None: first_page, "next-page": second_page}
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "access-token",
    )

    folders = google_connections_module.list_all_google_drive_folders(
        cast(Session, session),
        settings,
        connection,
        page_size=25,
        drive_client=fake_drive_client,
    )

    assert [folder.id for folder in folders] == ["folder-1", "folder-2"]
    assert fake_drive_client.folder_requests == [
        ("access-token", None, 25),
        ("access-token", "next-page", 25),
    ]


def test_list_all_google_drive_folders_rejects_repeated_page_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=[],
    )
    fake_drive_client = FakeDriveClient()
    repeated_page = GoogleDriveFolderPage(folders=(), next_page_token="same-page")
    fake_drive_client.folder_pages = {None: repeated_page, "same-page": repeated_page}
    monkeypatch.setattr(
        google_connections_module,
        "get_valid_google_access_token",
        lambda *_args: "access-token",
    )

    with pytest.raises(GoogleApiError, match="non-advancing"):
        google_connections_module.list_all_google_drive_folders(
            cast(Session, FakeSession()),
            settings,
            connection,
            drive_client=fake_drive_client,
        )


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
