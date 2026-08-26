from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, timestamp_column, updated_at_column, uuid_primary_key


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("documents_discovered >= 0", name="ck_sync_runs_discovered_nonnegative"),
        CheckConstraint("documents_ingested >= 0", name="ck_sync_runs_ingested_nonnegative"),
        CheckConstraint("documents_failed >= 0", name="ck_sync_runs_failed_nonnegative"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    sync_type: Mapped[str] = mapped_column(String(30), nullable=False)
    documents_discovered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    documents_ingested: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    documents_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    started_at: Mapped[datetime | None] = timestamp_column()
    completed_at: Mapped[datetime | None] = timestamp_column()
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
