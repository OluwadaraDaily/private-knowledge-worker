from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_index import DocumentIndex
from app.db.models.index_config import IndexConfig
from app.services.chunking import DocumentChunk
from app.services.index_persistence import persist_document_chunks


class FakeSession:
    def __init__(self) -> None:
        self.index: DocumentIndex | None = None
        self.added: list[object] = []
        self.commits = 0

    def scalar(self, _statement: object) -> DocumentIndex | None:
        return self.index

    def scalars(self, _statement: object) -> tuple[object, ...]:
        return ()

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, DocumentIndex):
            self.index = value

    def flush(self) -> None:
        assert self.index is not None
        self.index.id = UUID(int=3)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        raise AssertionError("rollback was not expected")


def test_persist_document_chunks_stores_order_heading_and_metadata() -> None:
    session = FakeSession()
    document = Document(id=UUID(int=1), user_id=UUID(int=2), google_file_id="doc-1")
    config = IndexConfig(
        id=UUID(int=4),
        name="fixed",
        chunking_strategy="fixed_tokens",
        embedding_model="model",
        embedding_dimensions=3,
    )

    document_index, chunks = persist_document_chunks(
        cast(Session, session),
        document,
        config,
        "hash",
        (DocumentChunk(0, "one two", 2, "Intro"),),
    )

    assert document_index.status == "ready"
    assert chunks[0].heading == "Intro"
    assert chunks[0].chunk_metadata == {"heading": "Intro"}
    assert session.commits == 1
