from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.google_connection import GoogleConnection
from app.db.session import get_session


def get_optional_google_connection(
    session: Annotated[Session, Depends(get_session)],
    google_connection_id: str | None = Cookie(default=None),
) -> GoogleConnection | None:
    """Resolve the connection identified by the request cookie, if present."""
    if not google_connection_id:
        return None
    try:
        connection_id = UUID(google_connection_id)
    except ValueError:
        return None
    return session.scalar(select(GoogleConnection).where(GoogleConnection.id == connection_id))


def require_google_connection(
    connection: Annotated[
        GoogleConnection | None,
        Depends(get_optional_google_connection),
    ],
) -> GoogleConnection:
    """Require a valid Google connection for an authenticated endpoint."""
    if connection is None:
        raise HTTPException(status_code=401, detail="Google account is not connected")
    return connection
