from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, updated_at_column, uuid_primary_key


class IndexConfig(Base):
    __tablename__ = "index_configs"
    __table_args__ = (
        CheckConstraint(
            "chunk_size IS NULL OR chunk_size > 0", name="ck_index_configs_chunk_size_positive"
        ),
        CheckConstraint(
            "chunk_overlap IS NULL OR chunk_overlap >= 0",
            name="ck_index_configs_chunk_overlap_nonnegative",
        ),
        CheckConstraint(
            "chunk_size IS NULL OR chunk_overlap IS NULL OR chunk_overlap < chunk_size",
            name="ck_index_configs_overlap_smaller_than_size",
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    chunking_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    chunk_size: Mapped[int | None] = mapped_column(Integer)
    chunk_overlap: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_config: Mapped[dict[str, object] | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
