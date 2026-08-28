from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors.google import google_api_error_handler, google_credential_error_handler
from app.api.router import api_router
from app.core.config import get_settings
from app.integrations.google.client import GoogleApiError
from app.services.credentials import GoogleCredentialError


def create_app() -> FastAPI:
    application = FastAPI(
        title="Private Knowledge Worker API",
        version="0.1.0",
    )
    settings = get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_exception_handler(GoogleApiError, google_api_error_handler)
    application.add_exception_handler(GoogleCredentialError, google_credential_error_handler)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
