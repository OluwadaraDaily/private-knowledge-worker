from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.indexed_folder import IndexedFolder
from app.integrations.google.interfaces import GoogleDriveFolder


class FolderSelectionValidationError(ValueError):
    """Raised when a requested folder set is not a valid owned-folder selection."""


def list_selected_folders(session: Session, user_id: UUID) -> list[IndexedFolder]:
    """Return the user's enabled folder sources in a stable order."""
    return list(
        session.scalars(
            select(IndexedFolder)
            .where(IndexedFolder.user_id == user_id, IndexedFolder.enabled.is_(True))
            .order_by(IndexedFolder.created_at, IndexedFolder.id)
        ).all()
    )


def replace_selected_folders(
    session: Session,
    user_id: UUID,
    folders: list[tuple[str, str]],
) -> list[IndexedFolder]:
    """Replace the user's enabled folder sources and return the saved rows."""
    existing = list(
        session.scalars(select(IndexedFolder).where(IndexedFolder.user_id == user_id)).all()
    )
    requested = dict(folders)

    for folder in existing:
        requested_name = requested.pop(folder.google_folder_id, None)
        if requested_name is None:
            session.delete(folder)
            continue
        folder.name = requested_name
        folder.enabled = True

    for google_folder_id, name in requested.items():
        session.add(
            IndexedFolder(
                user_id=user_id,
                google_folder_id=google_folder_id,
                name=name,
                enabled=True,
            )
        )

    session.commit()
    return list_selected_folders(session, user_id)


def validate_selected_folders(
    available_folders: tuple[GoogleDriveFolder, ...],
    selected_ids: list[str],
) -> list[tuple[str, str]]:
    """Validate ownership and ancestor conflicts, returning canonical folder names."""
    folders_by_id = {folder.id: folder for folder in available_folders}
    if len(selected_ids) != len(set(selected_ids)):
        raise FolderSelectionValidationError("Selected folders must be unique")

    unknown_ids = [folder_id for folder_id in selected_ids if folder_id not in folders_by_id]
    if unknown_ids:
        raise FolderSelectionValidationError(
            "Selected folders must belong to the connected Google Drive account"
        )

    selected_id_set = set(selected_ids)
    for folder_id in selected_ids:
        ancestors = set(folders_by_id[folder_id].parents)
        pending_ancestors = list(ancestors)
        while pending_ancestors:
            ancestor_id = pending_ancestors.pop()
            if ancestor_id in selected_id_set:
                raise FolderSelectionValidationError(
                    "Select either a folder or one of its descendants, not both"
                )
            ancestor = folders_by_id.get(ancestor_id)
            if ancestor is not None:
                pending_ancestors.extend(ancestor.parents)

    return [(folder_id, folders_by_id[folder_id].name) for folder_id in selected_ids]
