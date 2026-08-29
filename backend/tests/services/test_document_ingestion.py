from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.integrations.google.client import GoogleApiError
from app.integrations.google.interfaces import GoogleDocsDocument, GoogleDriveFile
from app.services import document_ingestion as ingestion
from app.services.document_classification import DocumentClassification


def _drive_file() -> GoogleDriveFile:
    return GoogleDriveFile(
        id="doc-1",
        name="Research notes",
        mime_type="application/vnd.google-apps.document",
        parents=(),
        created_at=None,
        modified_at=None,
        web_url="https://docs.google.com/document/d/doc-1/edit",
    )


def _connection() -> GoogleConnection:
    return GoogleConnection(
        user_id=UUID(int=1), google_account_id="account", email="user@example.com", scopes=[]
    )


def test_ingest_google_document_wires_fetch_normalize_classify_and_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        ingestion,
        "fetch_google_document",
        lambda *_args: GoogleDocsDocument("doc-1", "Research notes", ()),
    )
    monkeypatch.setattr(
        ingestion,
        "persist_document_and_content",
        lambda *args, **kwargs: calls.append(cast(dict[str, object], kwargs)),
    )

    result = ingestion.ingest_google_document(
        cast(Session, object()), Settings(), _connection(), _drive_file(), ("Research",)
    )

    assert result.document_id == "doc-1"
    assert result.status == "succeeded"
    assert result.error_kind is None
    classification = cast(DocumentClassification, calls[0]["classification"])
    assert classification.topics == ("Research",)


def test_ingest_google_document_returns_safe_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ingestion,
        "fetch_google_document",
        lambda *_args: (_ for _ in ()).throw(GoogleApiError("upstream", kind="transient")),
    )

    result = ingestion.ingest_google_document(
        cast(Session, object()), Settings(), _connection(), _drive_file()
    )

    assert result == ingestion.DocumentIngestionResult("doc-1", "failed", "transient")
