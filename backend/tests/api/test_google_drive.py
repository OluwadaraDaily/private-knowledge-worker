from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import google_drive as google_drive_module
from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session
from app.integrations.google.drive import GoogleDriveAuthenticationError, GoogleDriveError
from app.integrations.google.interfaces import GoogleDriveFolder, GoogleDriveFolderPage
from app.main import create_app


class ConnectionSession:
    def __init__(self, connection: GoogleConnection | None) -> None:
        self.connection = connection

    def scalar(self, statement: object) -> GoogleConnection | None:
        del statement
        return self.connection


def test_list_google_drive_folders_returns_a_page_and_forwards_pagination(
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
    calls: list[tuple[str | None, int]] = []
    expected_page = GoogleDriveFolderPage(
        folders=(GoogleDriveFolder(id="folder-1", name="Projects", parents=("root",)),),
        next_page_token="next-page",
    )

    def fake_list_folders(
        _session: Session,
        _settings: Settings,
        given_connection: GoogleConnection,
        *,
        page_token: str | None,
        page_size: int,
    ) -> GoogleDriveFolderPage:
        assert given_connection is connection
        calls.append((page_token, page_size))
        return expected_page

    monkeypatch.setattr(google_drive_module, "list_google_drive_folders", fake_list_folders)

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get(
                "/api/v1/drive/folders?page_token=previous-page&page_size=25"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "folders": [{"id": "folder-1", "name": "Projects", "parents": ["root"]}],
        "next_page_token": "next-page",
    }
    assert calls == [("previous-page", 25)]


def test_list_google_drive_folders_requires_a_connection() -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: ConnectionSession(None)
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/drive/folders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Google account is not connected"}


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            GoogleDriveAuthenticationError("provider rejected token"),
            401,
            "Google authentication is no longer valid; reconnect Google",
        ),
        (
            GoogleDriveError("provider response contains a secret"),
            502,
            "Google Drive folder listing failed",
        ),
    ],
)
def test_list_google_drive_folders_hides_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: GoogleDriveError,
    status_code: int,
    detail: str,
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
        google_drive_module,
        "list_google_drive_folders",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("google_connection_id", str(connection.id))
            response = test_client.get("/api/v1/drive/folders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "provider response contains a secret" not in response.text
