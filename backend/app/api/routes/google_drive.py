from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies.google import require_google_connection
from app.core.config import get_settings
from app.db.models.google_connection import GoogleConnection
from app.db.models.indexed_folder import IndexedFolder
from app.db.session import get_session
from app.services.document_discovery import discover_selected_google_docs
from app.services.folder_hierarchy import GoogleFolderNode, list_google_folder_hierarchy
from app.services.folder_selection import (
    FolderSelectionValidationError,
    list_selected_folders,
    replace_selected_folders,
    validate_selected_folders,
)
from app.services.google_connections import (
    list_all_google_drive_folders,
    list_google_drive_folders,
)


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


class SelectedFolderRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=1024)


class SelectedFoldersRequest(BaseModel):
    folders: list[SelectedFolderRequest] = Field(default_factory=list, max_length=1000)


class SelectedFolderResponse(BaseModel):
    id: str
    name: str


class GoogleDocumentResponse(BaseModel):
    id: str
    title: str
    mime_type: str
    parents: list[str]
    created_at: datetime | None
    modified_at: datetime | None
    version: str | None
    web_url: str | None


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
    folder_page = list_google_drive_folders(
        session,
        get_settings(),
        connection,
        page_token=page_token,
        page_size=page_size,
    )

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
    folder_tree = list_google_folder_hierarchy(
        session,
        get_settings(),
        connection,
        page_size=page_size,
    )

    return [_folder_node_response(node) for node in folder_tree]


def _selected_folder_response(folder: IndexedFolder) -> SelectedFolderResponse:
    return SelectedFolderResponse(
        id=folder.google_folder_id,
        name=folder.name,
    )


@google_drive_router.get(
    "/folders/selected",
    response_model=list[SelectedFolderResponse],
    summary="List selected Google Drive folders",
)
def get_selected_google_drive_folders(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
) -> list[SelectedFolderResponse]:
    return [
        _selected_folder_response(folder)
        for folder in list_selected_folders(session, connection.user_id)
    ]


@google_drive_router.put(
    "/folders/selected",
    response_model=list[SelectedFolderResponse],
    summary="Replace selected Google Drive folders",
)
def put_selected_google_drive_folders(
    selection: SelectedFoldersRequest,
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
) -> list[SelectedFolderResponse]:
    folder_pairs = [(folder.id, folder.name) for folder in selection.folders]
    if len(folder_pairs) != len({folder_id for folder_id, _name in folder_pairs}):
        raise HTTPException(status_code=422, detail="Selected folders must be unique")
    try:
        available_folders = list_all_google_drive_folders(
            session,
            get_settings(),
            connection,
        )
        validated_folders = validate_selected_folders(
            available_folders,
            [folder_id for folder_id, _name in folder_pairs],
        )
    except FolderSelectionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    selected_folders = replace_selected_folders(
        session,
        connection.user_id,
        validated_folders,
    )
    return [_selected_folder_response(folder) for folder in selected_folders]


@google_drive_router.get(
    "/documents/discover",
    response_model=list[GoogleDocumentResponse],
    summary="Discover eligible Google Docs in selected folders",
)
def discover_google_drive_documents(
    session: Annotated[Session, Depends(get_session)],
    connection: Annotated[GoogleConnection, Depends(require_google_connection)],
    response: Response,
) -> list[GoogleDocumentResponse]:
    selected_folder_ids = {
        folder.google_folder_id for folder in list_selected_folders(session, connection.user_id)
    }
    discovery_result = discover_selected_google_docs(
        session,
        get_settings(),
        connection,
        selected_folder_ids,
    )
    if not discovery_result.complete:
        response.status_code = 206
        response.headers["X-Discovery-Partial"] = "true"
        if discovery_result.warning:
            response.headers["X-Discovery-Warning"] = discovery_result.warning
    return [
        GoogleDocumentResponse(
            id=document.id,
            title=document.name,
            mime_type=document.mime_type,
            parents=list(document.parents),
            created_at=document.created_at,
            modified_at=document.modified_at,
            version=document.version,
            web_url=document.web_url,
        )
        for document in discovery_result.files
    ]
