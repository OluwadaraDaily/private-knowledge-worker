from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, timestamp_column, updated_at_column, uuid_primary_key


class SyncState(Base):
    __tablename__ = "sync_states"
    __table_args__ = (UniqueConstraint("google_connection_id", name="uq_sync_states_connection"),)

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_connection_id: Mapped[UUID] = mapped_column(
        ForeignKey("google_connections.id", ondelete="CASCADE"), index=True
    )
    change_page_token: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = timestamp_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
