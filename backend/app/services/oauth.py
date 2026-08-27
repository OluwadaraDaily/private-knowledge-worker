import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode

from app.core.config import Settings
from app.db.models.oauth_state import OAuthState

OAUTH_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_STATE_TTL = timedelta(minutes=10)


class OAuthStateSession(Protocol):
    def add(self, instance: OAuthState) -> None: ...

    def commit(self) -> None: ...


def create_oauth_authorization_url(session: OAuthStateSession, settings: Settings) -> str:
    if not settings.oauth_client_id:
        raise ValueError("OAuth client ID is not configured")

    raw_state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.add(
        OAuthState(
            state_hash=hashlib.sha256(raw_state.encode()).hexdigest(),
            expires_at=now + OAUTH_STATE_TTL,
        )
    )
    session.commit()

    redirect_uri = f"{str(settings.backend_url).rstrip('/')}/api/v1/auth/google/callback"
    query = urlencode(
        {
            "client_id": settings.oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(settings.oauth_scopes),
            "state": raw_state,
            "access_type": "offline",
            "include_granted_scopes": "true",
        }
    )
    return f"{OAUTH_AUTHORIZATION_URL}?{query}"
