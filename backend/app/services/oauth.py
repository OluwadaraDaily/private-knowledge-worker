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
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
OAUTH_STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class OAuthAuthorization:
    url: str
    state: str


class OAuthExchangeError(Exception):
    """Raised when Google rejects an OAuth request or response."""


class GoogleOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def exchange_code(self, code: str) -> dict[str, object]:
        return self._post_token(
            {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri(),
            },
            "Google authorization-code exchange failed",
        )

    def refresh_access_token(self, refresh_token: str) -> dict[str, object]:
        return self._post_token(
            {
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            "Google access-token refresh failed",
        )

    def user_info(self, access_token: str) -> dict[str, object]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                user_info = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OAuthExchangeError("Google account information could not be retrieved") from error
        if not isinstance(user_info, dict):
            raise OAuthExchangeError("Google returned invalid account information")
        return user_info

    def _post_token(self, data: dict[str, str], failure_message: str) -> dict[str, object]:
        if not self.settings.oauth_client_id or not self.settings.oauth_client_secret:
            raise OAuthExchangeError("OAuth client credentials are not configured")
        request_data = {
            "client_id": self.settings.oauth_client_id,
            "client_secret": self.settings.oauth_client_secret,
            **data,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(GOOGLE_TOKEN_URL, data=request_data)
                response.raise_for_status()
                token_data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OAuthExchangeError(failure_message) from error
        if not isinstance(token_data, dict) or not isinstance(token_data.get("access_token"), str):
            raise OAuthExchangeError("Google returned an invalid token response")
        return token_data

    def _redirect_uri(self) -> str:
        return f"{str(self.settings.backend_url).rstrip('/')}/api/v1/auth/google/callback"


def create_oauth_authorization_url(session: Session, settings: Settings) -> OAuthAuthorization:
    if not settings.oauth_client_id:
        raise ValueError("OAuth client ID is not configured")

    raw_state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.execute(delete(OAuthState).where(OAuthState.expires_at <= now))
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


def exchange_authorization_code(settings: Settings, code: str) -> dict[str, object]:
    return GoogleOAuthClient(settings).exchange_code(code)
