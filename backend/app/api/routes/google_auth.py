from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.google import (
    get_optional_google_connection,
    require_google_connection,
)
from app.api.errors.google import google_drive_http_exception
from app.core.config import get_settings
from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session
from app.integrations.google.client import GoogleApiError
from app.services.credentials import (
    GoogleCredentialError,
    persist_google_credentials,
)
from app.services.google_connections import (
    disconnect_google_connection,
    verify_google_drive_connection,
)
from app.services.oauth import (
    OAuthExchangeError,
    consume_oauth_state,
    create_oauth_authorization_url,
    exchange_authorization_code,
)


class GoogleConnectionStatus(BaseModel):
    connected: bool
    email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    token_expires_at: str | None = None


class GoogleDriveVerification(BaseModel):
    authenticated: bool
    email: str


GOOGLE_CONNECTION_COOKIE = "google_connection_id"


google_auth_router = APIRouter(prefix="/auth/google")


@google_auth_router.get("/start", summary="Start Google OAuth authorization")
def start_google_oauth(
    session: Annotated[Session, Depends(get_session)],
) -> RedirectResponse:
    try:
        authorization = create_oauth_authorization_url(session, get_settings())
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured") from error
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="OAuth authorization is unavailable") from error
    response = RedirectResponse(url=authorization.url, status_code=307)
    response.set_cookie(
        "oauth_state",
        authorization.state,
        max_age=600,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
    )
    return response


@google_auth_router.get("/callback", summary="Complete Google OAuth authorization")
def complete_google_oauth(
    session: Annotated[Session, Depends(get_session)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None),
) -> Response:
    if error:
        raise HTTPException(status_code=400, detail="Google authorization was denied")
    if not code or not state or state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        if not consume_oauth_state(session, state):
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        settings = get_settings()
        token_data = exchange_authorization_code(settings, code)
        persisted_connection = persist_google_credentials(session, settings, token_data)
    except (GoogleCredentialError, OAuthExchangeError) as exchange_error:
        raise HTTPException(
            status_code=502, detail="Google authorization failed"
        ) from exchange_error
    response = RedirectResponse(
        url=str(settings.frontend_url).rstrip("/"),
        status_code=303,
    )
    response.set_cookie(
        GOOGLE_CONNECTION_COOKIE,
        str(persisted_connection.id),
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )
    return response


@google_auth_router.get(
    "/status",
    response_model=GoogleConnectionStatus,
    summary="Get Google connection status",
)
def get_google_connection_status(
    connection: Annotated[
        GoogleConnection | None,
        Depends(get_optional_google_connection),
    ],
) -> GoogleConnectionStatus:
    if connection is None:
        return GoogleConnectionStatus(connected=False)
    return GoogleConnectionStatus(
        connected=True,
        email=connection.email,
        scopes=connection.scopes,
        token_expires_at=(
            connection.token_expires_at.isoformat() if connection.token_expires_at else None
        ),
    )


@google_auth_router.get(
    "/verify",
    response_model=GoogleDriveVerification,
    summary="Verify authenticated Google Drive access",
)
def verify_google_drive(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
) -> GoogleDriveVerification:
    settings = get_settings()
    try:
        verify_google_drive_connection(session, settings, connection)
    except (GoogleApiError, GoogleCredentialError) as error:
        raise google_drive_http_exception(error) from error

    return GoogleDriveVerification(authenticated=True, email=connection.email)


@google_auth_router.delete("", status_code=204, summary="Disconnect Google")
def disconnect_google(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[
        GoogleConnection | None,
        Depends(get_optional_google_connection),
    ],
) -> Response:
    if connection is not None:
        disconnect_google_connection(session, connection)
    response = Response(status_code=204)
    response.delete_cookie(GOOGLE_CONNECTION_COOKIE)
    return response
