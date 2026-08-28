from fastapi import HTTPException

from app.integrations.google.client import GoogleApiError
from app.services.credentials import GoogleCredentialError


def google_drive_http_exception(
    error: GoogleCredentialError | GoogleApiError,
    *,
    operation: str = "verification",
) -> HTTPException:
    """Translate Google Drive and credential failures into safe API errors."""
    if isinstance(error, GoogleCredentialError):
        return HTTPException(
            status_code=401,
            detail="Google authentication is unavailable; reconnect Google",
        )
    if error.kind == "authentication":
        return HTTPException(
            status_code=401,
            detail="Google authentication is no longer valid; reconnect Google",
        )
    if error.kind == "rate_limit":
        headers = (
            {"Retry-After": str(error.retry_after_seconds)}
            if error.retry_after_seconds is not None
            else None
        )
        return HTTPException(
            status_code=429,
            detail="Google Drive rate limit exceeded; please try again later",
            headers=headers,
        )
    return HTTPException(status_code=502, detail=f"Google Drive {operation} failed")
