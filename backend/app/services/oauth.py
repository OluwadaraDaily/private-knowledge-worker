import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.oauth_state import OAuthState

OAUTH_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class OAuthAuthorization:
    url: str
    state: str


def create_oauth_authorization_url(
    session: Session, settings: Settings
) -> OAuthAuthorization:
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
    return OAuthAuthorization(url=f"{OAUTH_AUTHORIZATION_URL}?{query}", state=raw_state)


def consume_oauth_state(session: Session, raw_state: str) -> bool:
    state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
    state = session.scalar(
        select(OAuthState).where(
            OAuthState.state_hash == state_hash,
            OAuthState.expires_at > datetime.now(UTC),
        )
    )
    if state is None:
        return False
    session.execute(delete(OAuthState).where(OAuthState.id == state.id))
    session.commit()
    return True


class OAuthExchangeError(Exception):
    """Raised when Google rejects an authorization-code exchange."""


def exchange_authorization_code(settings: Settings, code: str) -> dict[str, object]:
    if not settings.oauth_client_id or not settings.oauth_client_secret:
        raise OAuthExchangeError("OAuth client credentials are not configured")

    redirect_uri = f"{str(settings.backend_url).rstrip('/')}/api/v1/auth/google/callback"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.oauth_client_id,
                    "client_secret": settings.oauth_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            response.raise_for_status()
            token_data = response.json()
    except (httpx.HTTPError, ValueError) as exchange_error:
        raise OAuthExchangeError("Google authorization-code exchange failed") from exchange_error

    if not isinstance(token_data, dict) or not isinstance(token_data.get("access_token"), str):
        raise OAuthExchangeError("Google returned an invalid token response")
    return token_data
