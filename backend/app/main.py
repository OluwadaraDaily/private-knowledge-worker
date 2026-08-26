from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings


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
        allow_methods=["GET", "POST", "PUT", "DELETE", "QUERY",  "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
