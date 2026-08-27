from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.services.oauth import create_oauth_authorization_url


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
        authorization_url = create_oauth_authorization_url(session, get_settings())
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured") from error
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="OAuth authorization is unavailable") from error
    return RedirectResponse(url=authorization_url, status_code=307)
