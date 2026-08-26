from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, updated_at_column, uuid_primary_key


class DocumentIndex(Base):
    __tablename__ = "document_indexes"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "index_config_id",
            "content_hash",
            name="uq_document_indexes_content_version",
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    index_config_id: Mapped[UUID] = mapped_column(
        ForeignKey("index_configs.id", ondelete="CASCADE"), index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
