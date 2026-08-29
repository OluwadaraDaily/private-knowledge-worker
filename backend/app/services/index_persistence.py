from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.document_index import DocumentIndex
from app.db.models.index_config import IndexConfig
from app.services.chunking import DocumentChunk


def persist_document_chunks(
    session: Session,
    document: Document,
    index_config: IndexConfig,
    content_hash: str,
    chunks: Sequence[DocumentChunk],
) -> tuple[DocumentIndex, tuple[Chunk, ...]]:
    """Persist chunks for one document/config/content version without duplicates."""
    document_index = session.scalar(
        select(DocumentIndex).where(
            DocumentIndex.document_id == document.id,
            DocumentIndex.index_config_id == index_config.id,
            DocumentIndex.content_hash == content_hash,
        )
    )
    if document_index is not None:
        existing = tuple(
            session.scalars(
                select(Chunk)
                .where(Chunk.document_index_id == document_index.id)
                .order_by(Chunk.chunk_number)
            )
        )
        return document_index, existing

    document_index = DocumentIndex(
        document_id=document.id,
        index_config_id=index_config.id,
        content_hash=content_hash,
        status="pending",
    )
    session.add(document_index)
    try:
        session.flush()
        persisted_chunks: list[Chunk] = []
        for chunk in chunks:
            persisted_chunk = Chunk(
                document_index_id=document_index.id,
                chunk_number=chunk.chunk_number,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_metadata={"heading": chunk.heading} if chunk.heading else None,
            )
            session.add(persisted_chunk)
            persisted_chunks.append(persisted_chunk)
        document_index.status = "ready"
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return document_index, tuple(persisted_chunks)
