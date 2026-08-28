from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.drive import GoogleDriveClient, GoogleDriveError
from app.integrations.google.interfaces import (
    GoogleDriveFolder,
    GoogleDriveFolderLister,
    GoogleDriveFolderPage,
    GoogleDriveVerifier,
)
from app.services.credentials import get_valid_google_access_token


def verify_google_drive_connection(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    drive_client: GoogleDriveVerifier | None = None,
) -> None:
    """Verify a stored Google connection through one authenticated Drive request."""
    access_token = get_valid_google_access_token(session, settings, connection)
    client = drive_client if drive_client is not None else GoogleDriveClient()
    client.verify_access(access_token)


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
    access_token = get_valid_google_access_token(session, settings, connection)
    client = drive_client if drive_client is not None else GoogleDriveClient()
    return client.list_folders(access_token, page_token=page_token, page_size=page_size)


def list_all_google_drive_folders(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    *,
    page_size: int = 100,
    drive_client: GoogleDriveFolderLister | None = None,
) -> tuple[GoogleDriveFolder, ...]:
    """Fetch every folder page while keeping pagination out of the API route."""
    access_token = get_valid_google_access_token(session, settings, connection)
    client = drive_client if drive_client is not None else GoogleDriveClient()
    folders: list[GoogleDriveFolder] = []
    page_token: str | None = None
    seen_page_tokens: set[str] = set()

    while True:
        folder_page = client.list_folders(
            access_token,
            page_token=page_token,
            page_size=page_size,
        )
        folders.extend(folder_page.folders)
        next_page_token = folder_page.next_page_token
        if next_page_token is None:
            return tuple(folders)
        if next_page_token in seen_page_tokens:
            raise GoogleDriveError("Google Drive returned a non-advancing page token")
        seen_page_tokens.add(next_page_token)
        page_token = next_page_token


def disconnect_google_connection(session: Session, connection: GoogleConnection) -> None:
    """Delete a Google connection and commit its local removal."""
    session.execute(delete(GoogleConnection).where(GoogleConnection.id == connection.id))
    session.commit()
