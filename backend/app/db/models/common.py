from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column


def uuid_primary_key() -> Mapped[UUID]:
    return mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


def timestamp_column() -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True))


def required_timestamp_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False)
