from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.drive import GoogleDriveError
from app.integrations.google.interfaces import (
    GoogleDriveFolder,
    GoogleDriveFolderLister,
)
from app.services.google_connections import list_all_google_drive_folders


@dataclass(frozen=True, slots=True)
class GoogleFolderNode:
    """A folder with its owned descendants."""

    id: str
    name: str
    children: tuple["GoogleFolderNode", ...]


def build_google_folder_hierarchy(
    folders: Sequence[GoogleDriveFolder],
) -> tuple[GoogleFolderNode, ...]:
    """Build a deterministic tree from flat folder metadata."""
    folders_by_id: dict[str, GoogleDriveFolder] = {}
    for folder in folders:
        if folder.id in folders_by_id:
            raise GoogleDriveError("Google Drive returned duplicate folder metadata")
        folders_by_id[folder.id] = folder

    children_by_parent: dict[str, list[str]] = {}
    root_ids: list[str] = []
    ordered_folders = sorted(
        folders_by_id.values(), key=lambda folder: (folder.name.casefold(), folder.id)
    )
    for folder in ordered_folders:
        parent_id = next((parent for parent in folder.parents if parent in folders_by_id), None)
        if parent_id is None:
            root_ids.append(folder.id)
        else:
            children_by_parent.setdefault(parent_id, []).append(folder.id)

    visited: set[str] = set()

    def build_node(folder_id: str, ancestors: frozenset[str]) -> GoogleFolderNode:
        if folder_id in ancestors:
            raise GoogleDriveError("Google Drive returned a cyclic folder hierarchy")
        folder = folders_by_id[folder_id]
        visited.add(folder_id)
        child_nodes = tuple(
            build_node(child_id, ancestors | {folder_id})
            for child_id in sorted(
                children_by_parent.get(folder_id, []),
                key=lambda child: (folders_by_id[child].name.casefold(), child),
            )
        )
        return GoogleFolderNode(id=folder.id, name=folder.name, children=child_nodes)

    tree = tuple(build_node(folder_id, frozenset()) for folder_id in root_ids)
    if len(visited) != len(folders_by_id):
        raise GoogleDriveError("Google Drive returned a cyclic folder hierarchy")
    return tree


def list_google_folder_hierarchy(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    *,
    page_size: int = 100,
    drive_client: GoogleDriveFolderLister | None = None,
) -> tuple[GoogleFolderNode, ...]:
    """Fetch all owned folders and return their parent/child hierarchy."""
    folders = list_all_google_drive_folders(
        session,
        settings,
        connection,
        page_size=page_size,
        drive_client=drive_client,
    )
    return build_google_folder_hierarchy(folders)
