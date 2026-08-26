from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, timestamp_column, updated_at_column, uuid_primary_key


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_modified_at", "user_id", "google_modified_at"),
        Index("ix_documents_user_document_type", "user_id", "document_type"),
        UniqueConstraint("user_id", "google_file_id", name="uq_documents_user_file"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    web_url: Mapped[str | None] = mapped_column(String(2048))
    google_created_at: Mapped[datetime | None] = timestamp_column()
    google_modified_at: Mapped[datetime | None] = timestamp_column()
    owned_by_me: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    document_type: Mapped[str | None] = mapped_column(String(100))
    indexed_at: Mapped[datetime | None] = timestamp_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
