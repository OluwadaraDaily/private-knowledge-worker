from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.services.credentials import GoogleCredentialError, persist_google_credentials
from app.services.oauth import (
    OAuthExchangeError,
    consume_oauth_state,
    create_oauth_authorization_url,
    exchange_authorization_code,
)


class ApiInfo(BaseModel):
    name: str
    version: str


class HealthStatus(BaseModel):
    status: str


api_router = APIRouter()


@api_router.get("/health", response_model=HealthStatus, summary="Check application health")
async def get_health() -> HealthStatus:
    return HealthStatus(status="ok")


@api_router.get("/", response_model=ApiInfo, summary="Get API information")
async def get_api_info() -> ApiInfo:
    return ApiInfo(
        name="Private Knowledge Worker API",
        version="0.1.0",
    )


@api_router.get("/auth/google/start", summary="Start Google OAuth authorization")
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


@api_router.get("/auth/google/callback", summary="Complete Google OAuth authorization")
def complete_google_oauth(
    session: Annotated[Session, Depends(get_session)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None),
) -> dict[str, str]:
    if error:
        raise HTTPException(status_code=400, detail="Google authorization was denied")
    if not code or not state or state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        if not consume_oauth_state(session, state):
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        settings = get_settings()
        token_data = exchange_authorization_code(settings, code)
        persist_google_credentials(session, settings, token_data)
    except (GoogleCredentialError, OAuthExchangeError) as exchange_error:
        raise HTTPException(
            status_code=502, detail="Google authorization failed"
        ) from exchange_error
    return {"status": "authorized"}
