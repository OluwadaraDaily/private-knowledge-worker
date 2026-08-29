from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_content import DocumentContent
from app.integrations.google.interfaces import GoogleDriveFile
from app.services.document_persistence import persist_document_and_content


class FakeSession:
    def __init__(self, document: Document | None, content: DocumentContent | None) -> None:
        self.document = document
        self.content = content
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0

    def scalar(self, statement: object) -> Document | DocumentContent | None:
        if "documents" in str(statement):
            return self.document
        return self.content

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, Document):
            value.id = UUID(int=1)
            self.document = value
        if isinstance(value, DocumentContent):
            self.content = value

    def flush(self) -> None:
        self.flushes += 1

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        raise AssertionError("rollback was not expected")


class FailingCommitSession(FakeSession):
    def __init__(self) -> None:
        super().__init__(None, None)
        self.rollbacks = 0

    def commit(self) -> None:
        raise SQLAlchemyError("database unavailable")

    def rollback(self) -> None:
        self.rollbacks += 1


def _drive_file() -> GoogleDriveFile:
    return GoogleDriveFile(
        id="doc-1",
        name="Research notes",
        mime_type="application/vnd.google-apps.document",
        parents=("folder-1",),
        created_at=datetime(2026, 8, 29, 10, tzinfo=UTC),
        modified_at=datetime(2026, 8, 29, 11, tzinfo=UTC),
        web_url="https://docs.google.com/document/d/doc-1/edit",
    )


def test_persist_document_and_content_inserts_metadata_and_canonical_text() -> None:
    session = FakeSession(None, None)
    extracted_at = datetime(2026, 8, 29, 12, tzinfo=UTC)

    document, content = persist_document_and_content(
        cast(Session, session),
        UUID(int=2),
        _drive_file(),
        "# Research notes\nBody",
        extracted_at=extracted_at,
    )

    assert document.title == "Research notes"
    assert document.web_url == "https://docs.google.com/document/d/doc-1/edit"
    assert content.content == "# Research notes\nBody"
    assert content.content_hash == document.content_hash
    assert content.extracted_at == extracted_at
    assert session.commits == 1


def test_persist_document_and_content_updates_existing_rows_idempotently() -> None:
    document = Document(id=UUID(int=1), user_id=UUID(int=2), google_file_id="doc-1")
    content = DocumentContent(id=UUID(int=3), document_id=document.id)
    session = FakeSession(document, content)

    persist_document_and_content(cast(Session, session), UUID(int=2), _drive_file(), "Updated")

    assert session.added == []
    assert document.title == "Research notes"
    assert content.content == "Updated"
    assert session.commits == 1


def test_persist_document_and_content_hashes_the_complete_canonical_text() -> None:
    session = FakeSession(None, None)

    document, content = persist_document_and_content(
        cast(Session, session), UUID(int=2), _drive_file(), "# Title\nOne paragraph"
    )

    assert document.content_hash == (
        "e62652c1251f01b3341aa43d67eed30c730fc1f5bca6a9031a5c59fd24aaa075"
    )
    assert content.content_hash == document.content_hash


def test_persist_document_and_content_rolls_back_when_commit_fails() -> None:
    session = FailingCommitSession()

    try:
        persist_document_and_content(cast(Session, session), UUID(int=2), _drive_file(), "Content")
    except SQLAlchemyError:
        pass
    else:
        raise AssertionError("expected the database error to be raised")

    assert session.rollbacks == 1
