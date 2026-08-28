from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.interfaces import GoogleDriveFile
from app.services.google_connections import (
    GoogleDriveDocumentsResult,
    list_all_google_drive_folders,
    list_google_drive_documents_with_status,
)


def discover_selected_google_docs(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    selected_folder_ids: set[str],
) -> GoogleDriveDocumentsResult:
    """Discover owned Google Docs inside selected folder trees without fetching content."""
    if not selected_folder_ids:
        return GoogleDriveDocumentsResult((), complete=True)

    folders = list_all_google_drive_folders(session, settings, connection)
    folder_parents = {folder.id: folder.parents for folder in folders}
    discovery_result = list_google_drive_documents_with_status(session, settings, connection)
    documents = discovery_result.files

    def is_in_scope(document: GoogleDriveFile) -> bool:
        pending = list(document.parents)
        visited: set[str] = set()
        while pending:
            folder_id = pending.pop()
            if folder_id in selected_folder_ids:
                return True
            if folder_id in visited:
                continue
            visited.add(folder_id)
            pending.extend(folder_parents.get(folder_id, ()))
        return False

    return GoogleDriveDocumentsResult(
        tuple(
            sorted(
                (document for document in documents if is_in_scope(document)),
                key=lambda document: (document.name.casefold(), document.id),
            )
        ),
        complete=discovery_result.complete,
        warning=discovery_result.warning,
    )
