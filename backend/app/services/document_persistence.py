import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_content import DocumentContent
from app.integrations.google.interfaces import GoogleDriveFile


def persist_document_and_content(
    session: Session,
    user_id: UUID,
    drive_file: GoogleDriveFile,
    canonical_text: str,
    *,
    extracted_at: datetime | None = None,
) -> tuple[Document, DocumentContent]:
    """Upsert Drive metadata and its canonical content in one transaction."""
    content_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    document = session.scalar(
        select(Document).where(
            Document.user_id == user_id,
            Document.google_file_id == drive_file.id,
        )
    )
    if document is None:
        document = Document(user_id=user_id, google_file_id=drive_file.id)
        session.add(document)

    document.title = drive_file.name
    document.mime_type = drive_file.mime_type
    document.web_url = drive_file.web_url
    document.google_created_at = drive_file.created_at
    document.google_modified_at = drive_file.modified_at
    document.owned_by_me = True
    document.content_hash = content_hash

    try:
        session.flush()
        content = session.scalar(
            select(DocumentContent).where(DocumentContent.document_id == document.id)
        )
        if content is None:
            content = DocumentContent(document_id=document.id)
            session.add(content)
        content.content = canonical_text
        content.content_hash = content_hash
        content.extracted_at = extracted_at or datetime.now(UTC)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise

    return document, content
