from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .common import created_at_column, uuid_primary_key


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id: Mapped[UUID] = uuid_primary_key()
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = created_at_column()
