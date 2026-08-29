from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.client import GoogleApiError
from app.integrations.google.interfaces import GoogleDocsDocumentFetcher, GoogleDriveFile
from app.services.document_classification import (
    DeterministicDocumentClassifier,
    DocumentClassifier,
)
from app.services.document_normalization import normalize_google_document
from app.services.document_persistence import persist_document_and_content
from app.services.google_connections import fetch_google_document

IngestionStatus = Literal["succeeded", "failed"]


@dataclass(frozen=True, slots=True)
class DocumentIngestionResult:
    """Safe per-document ingestion status without document content or secrets."""

    document_id: str
    status: IngestionStatus
    error_kind: str | None = None


def ingest_google_document(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    drive_file: GoogleDriveFile,
    folder_names: tuple[str, ...] = (),
    *,
    docs_client: GoogleDocsDocumentFetcher | None = None,
    classifier: DocumentClassifier | None = None,
) -> DocumentIngestionResult:
    """Fetch, normalize, classify, and persist one Google Doc with safe status reporting."""
    try:
        raw_document = fetch_google_document(
            session,
            settings,
            connection,
            drive_file.id,
            docs_client,
        )
        canonical_text = normalize_google_document(raw_document)
        classification = (classifier or DeterministicDocumentClassifier()).classify(
            drive_file.name,
            folder_names,
        )
        persist_document_and_content(
            session,
            connection.user_id,
            drive_file,
            canonical_text,
            classification=classification,
        )
    except GoogleApiError as error:
        return DocumentIngestionResult(drive_file.id, "failed", error.kind)
    except (OSError, ValueError):
        return DocumentIngestionResult(drive_file.id, "failed", "processing")
    return DocumentIngestionResult(drive_file.id, "succeeded")
