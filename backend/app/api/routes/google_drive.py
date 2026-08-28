from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies.google import require_google_connection
from app.api.errors.google import google_drive_http_exception
from app.core.config import get_settings
from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session
from app.integrations.google.client import GoogleApiError
from app.services.credentials import GoogleCredentialError
from app.services.folder_hierarchy import GoogleFolderNode, list_google_folder_hierarchy
from app.services.google_connections import list_google_drive_folders


class GoogleFolderResponse(BaseModel):
    id: str
    name: str
    parents: list[str] = Field(default_factory=list)


class GoogleFolderPageResponse(BaseModel):
    folders: list[GoogleFolderResponse]
    next_page_token: str | None = None


class GoogleFolderTreeResponse(BaseModel):
    id: str
    name: str
    children: list["GoogleFolderTreeResponse"] = Field(default_factory=list)


google_drive_router = APIRouter(prefix="/drive")


@google_drive_router.get(
    "/folders",
    response_model=GoogleFolderPageResponse,
    summary="List owned Google Drive folders",
)
def get_google_drive_folders(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
    page_token: str | None = Query(default=None),
    page_size: int = Query(default=100, ge=1, le=1000),
) -> GoogleFolderPageResponse:
    try:
        folder_page = list_google_drive_folders(
            session,
            get_settings(),
            connection,
            page_token=page_token,
            page_size=page_size,
        )
    except (GoogleCredentialError, GoogleApiError) as error:
        raise google_drive_http_exception(error, operation="folder listing") from error

    return GoogleFolderPageResponse(
        folders=[
            GoogleFolderResponse(
                id=folder.id,
                name=folder.name,
                parents=list(folder.parents),
            )
            for folder in folder_page.folders
        ],
        next_page_token=folder_page.next_page_token,
    )


def _folder_node_response(node: GoogleFolderNode) -> GoogleFolderTreeResponse:
    return GoogleFolderTreeResponse(
        id=node.id,
        name=node.name,
        children=[_folder_node_response(child) for child in node.children],
    )


@google_drive_router.get(
    "/folders/tree",
    response_model=list[GoogleFolderTreeResponse],
    summary="Build the owned Google Drive folder hierarchy",
)
def get_google_drive_folder_tree(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
    page_size: int = Query(default=100, ge=1, le=1000),
) -> list[GoogleFolderTreeResponse]:
    try:
        folder_tree = list_google_folder_hierarchy(
            session,
            get_settings(),
            connection,
            page_size=page_size,
        )
    except (GoogleCredentialError, GoogleApiError) as error:
        raise google_drive_http_exception(error, operation="folder hierarchy") from error

    return [_folder_node_response(node) for node in folder_tree]
