from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, uuid_primary_key
from .types import Vector


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_index_id", "chunk_number", name="uq_chunks_index_number"),
        CheckConstraint("chunk_number >= 0", name="ck_chunks_number_nonnegative"),
        CheckConstraint(
            "token_count IS NULL OR token_count > 0", name="ck_chunks_token_count_positive"
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    document_index_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_indexes.id", ondelete="CASCADE"), index=True
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
    created_at: Mapped[datetime] = created_at_column()
