from fastapi import Request
from fastapi.responses import JSONResponse

from app.integrations.google.client import GoogleApiError
from app.services.credentials import GoogleCredentialError


def google_api_error_response(error: GoogleApiError) -> JSONResponse:
    """Translate one shared Google API error into a safe API response."""
    if error.kind == "authentication":
        return JSONResponse(
            status_code=401,
            content={"detail": "Google authentication is no longer valid; reconnect Google"},
        )
    if error.kind == "rate_limit":
        headers = (
            {"Retry-After": str(error.retry_after_seconds)}
            if error.retry_after_seconds is not None
            else None
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Google API rate limit exceeded; please try again later"},
            headers=headers,
        )
    return JSONResponse(
        status_code=502,
        content={"detail": "Google API request failed"},
    )


def google_credential_error_response(error: GoogleCredentialError) -> JSONResponse:
    """Translate a credential failure into a safe API response."""
    del error
    return JSONResponse(
        status_code=401,
        content={"detail": "Google authentication is unavailable; reconnect Google"},
    )


async def google_api_error_handler(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, GoogleApiError):
        return google_api_error_response(error)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def google_credential_error_handler(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    if isinstance(error, GoogleCredentialError):
        return google_credential_error_response(error)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
