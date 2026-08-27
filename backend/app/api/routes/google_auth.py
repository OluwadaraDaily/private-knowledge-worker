from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session
from app.services.credentials import GoogleCredentialError, persist_google_credentials
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
    response = JSONResponse({"status": "authorized"})
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
    session: Annotated[Session, Depends(get_session)],
    google_connection_id: str | None = Cookie(default=None),
) -> GoogleConnectionStatus:
    if not google_connection_id:
        return GoogleConnectionStatus(connected=False)
    try:
        connection_id = UUID(google_connection_id)
    except ValueError:
        return GoogleConnectionStatus(connected=False)
    connection = session.scalar(
        select(GoogleConnection).where(GoogleConnection.id == connection_id)
    )
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


@google_auth_router.delete("", status_code=204, summary="Disconnect Google")
def disconnect_google(
    session: Annotated[Session, Depends(get_session)],
    google_connection_id: str | None = Cookie(default=None),
) -> Response:
    if google_connection_id:
        try:
            connection_id = UUID(google_connection_id)
        except ValueError:
            connection_id = None
        if connection_id is not None:
            session.execute(delete(GoogleConnection).where(GoogleConnection.id == connection_id))
            session.commit()
    response = Response(status_code=204)
    response.delete_cookie(GOOGLE_CONNECTION_COOKIE)
    return response
