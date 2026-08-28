from collections.abc import Callable
from functools import partial

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.client import GoogleApiError
from app.integrations.google.drive import GoogleDriveClient
from app.integrations.google.interfaces import (
    GoogleDriveFile,
    GoogleDriveFileLister,
    GoogleDriveFilePage,
    GoogleDriveFolder,
    GoogleDriveFolderLister,
    GoogleDriveFolderPage,
    GoogleDriveVerifier,
)
from app.services.credentials import get_valid_google_access_token, refresh_google_access_token


def _run_with_google_access_token[ResultT](
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    operation: Callable[[str], ResultT],
) -> ResultT:
    """Run a Drive operation and retry once with a freshly refreshed token."""
    access_token = get_valid_google_access_token(session, settings, connection)
    try:
        return operation(access_token)
    except GoogleApiError as error:
        if error.kind != "authentication":
            raise
        refreshed_token = refresh_google_access_token(session, settings, connection)
        return operation(refreshed_token)


def verify_google_drive_connection(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    drive_client: GoogleDriveVerifier | None = None,
) -> None:
    """Verify a stored Google connection through one authenticated Drive request."""
    client = drive_client if drive_client is not None else GoogleDriveClient()
    _run_with_google_access_token(
        session,
        settings,
        connection,
        client.verify_access,
    )


def list_google_drive_folders(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    *,
    page_token: str | None = None,
    page_size: int = 100,
    drive_client: GoogleDriveFolderLister | None = None,
) -> GoogleDriveFolderPage:
    """List one page of folders through a stored Google connection."""
    client = drive_client if drive_client is not None else GoogleDriveClient()
    return _run_with_google_access_token(
        session,
        settings,
        connection,
        lambda access_token: client.list_folders(
            access_token,
            page_token=page_token,
            page_size=page_size,
        ),
    )


def list_all_google_drive_folders(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    *,
    page_size: int = 100,
    drive_client: GoogleDriveFolderLister | None = None,
) -> tuple[GoogleDriveFolder, ...]:
    """Fetch every folder page while keeping pagination out of the API route."""
    client = drive_client if drive_client is not None else GoogleDriveClient()
    folders: list[GoogleDriveFolder] = []
    page_token: str | None = None
    seen_page_tokens: set[str] = set()

    while True:
        folder_page = _run_with_google_access_token(
            session,
            settings,
            connection,
            partial(
                client.list_folders,
                page_token=page_token,
                page_size=page_size,
            ),
        )
        folders.extend(folder_page.folders)
        next_page_token = folder_page.next_page_token
        if next_page_token is None:
            return tuple(folders)
        if next_page_token in seen_page_tokens:
            raise GoogleApiError(
                "Google Drive returned a non-advancing page token",
                kind="malformed",
            )
        seen_page_tokens.add(next_page_token)
        page_token = next_page_token


def list_all_google_drive_documents(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    *,
    page_size: int = 100,
    drive_client: GoogleDriveFileLister | None = None,
) -> tuple[GoogleDriveFile, ...]:
    """Fetch every page of owned Google Docs metadata."""
    client = drive_client if drive_client is not None else GoogleDriveClient()
    files: list[GoogleDriveFile] = []
    page_token: str | None = None
    seen_page_tokens: set[str] = set()
    while True:
        page: GoogleDriveFilePage = _run_with_google_access_token(
            session,
            settings,
            connection,
            partial(client.list_documents, page_token=page_token, page_size=page_size),
        )
        files.extend(page.files)
        if page.next_page_token is None:
            return tuple(files)
        if page.next_page_token in seen_page_tokens:
            raise GoogleApiError(
                "Google Drive returned a non-advancing document page token",
                kind="malformed",
            )
        seen_page_tokens.add(page.next_page_token)
        page_token = page.next_page_token


def disconnect_google_connection(session: Session, connection: GoogleConnection) -> None:
    """Delete a Google connection and commit its local removal."""
    session.execute(delete(GoogleConnection).where(GoogleConnection.id == connection.id))
    session.commit()
