from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.drive import GoogleDriveClient
from app.integrations.google.interfaces import (
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


def disconnect_google_connection(session: Session, connection: GoogleConnection) -> None:
    """Delete a Google connection and commit its local removal."""
    session.execute(delete(GoogleConnection).where(GoogleConnection.id == connection.id))
    session.commit()
