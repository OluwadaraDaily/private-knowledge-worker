from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.indexed_folder import IndexedFolder


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
