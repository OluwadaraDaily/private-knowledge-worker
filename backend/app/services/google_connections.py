from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.drive import GoogleDriveClient
from app.integrations.google.interfaces import GoogleDriveGateway
from app.services.credentials import get_valid_google_access_token


def verify_google_drive_connection(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    drive_client: GoogleDriveGateway | None = None,
) -> None:
    """Verify a stored Google connection through one authenticated Drive request."""
    access_token = get_valid_google_access_token(session, settings, connection)
    client = drive_client if drive_client is not None else GoogleDriveClient()
    client.verify_access(access_token)


def disconnect_google_connection(session: Session, connection: GoogleConnection) -> None:
    """Delete a Google connection and commit its local removal."""
    session.execute(delete(GoogleConnection).where(GoogleConnection.id == connection.id))
    session.commit()
