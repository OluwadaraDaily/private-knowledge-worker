from fastapi import HTTPException

from app.integrations.google.drive import GoogleDriveAuthenticationError, GoogleDriveError
from app.services.credentials import GoogleCredentialError


def google_drive_http_exception(
    error: GoogleCredentialError | GoogleDriveError,
    *,
    operation: str = "verification",
) -> HTTPException:
    """Translate Google Drive and credential failures into safe API errors."""
    if isinstance(error, GoogleDriveAuthenticationError):
        return HTTPException(
            status_code=401,
            detail="Google authentication is no longer valid; reconnect Google",
        )
    if isinstance(error, GoogleCredentialError):
        return HTTPException(
            status_code=401,
            detail="Google authentication is unavailable; reconnect Google",
        )
    return HTTPException(status_code=502, detail=f"Google Drive {operation} failed")
