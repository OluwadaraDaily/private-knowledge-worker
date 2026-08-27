from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.db.models.user import User
from app.services.credentials import (
    CredentialEncryptionError,
    GoogleCredentialError,
    decrypt_credential,
    encrypt_credential,
    get_valid_google_access_token,
    persist_google_credentials,
    refresh_google_access_token,
)
from app.services.oauth import OAuthExchangeError


class FakeSession:
    def __init__(self, scalar_values: list[object | None]) -> None:
        self.scalar_values = scalar_values
        self.added: list[object] = []
        self.commits = 0

    def scalar(self, statement: object) -> object | None:
        del statement
        return self.scalar_values.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        user = next(item for item in self.added if isinstance(item, User))
        user.id = uuid4()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass


def test_credentials_round_trip_without_exposing_plaintext() -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())

    encrypted = encrypt_credential("access-token", settings)

    assert encrypted != "access-token"
    assert decrypt_credential(encrypted, settings) == "access-token"


def test_credentials_fail_with_missing_key() -> None:
    with pytest.raises(CredentialEncryptionError, match="not configured"):
        encrypt_credential("access-token", Settings(token_encryption_key=""))


def test_credentials_fail_with_wrong_key() -> None:
    first_settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    second_settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    encrypted = encrypt_credential("access-token", first_settings)

    with pytest.raises(CredentialEncryptionError, match="cannot be decrypted"):
        decrypt_credential(encrypted, second_settings)


def test_persist_google_credentials_encrypts_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    session = FakeSession([None, None])
    monkeypatch.setattr(
        "app.services.credentials._google_user_info",
        lambda access_token, settings: {
            "sub": "google-id",
            "email": "user@example.com",
            "name": "User",
        },
    )

    connection = persist_google_credentials(
        cast(Session, session),
        settings,
        {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "scope": "openid email",
        },
    )

    assert isinstance(connection, GoogleConnection)
    assert connection.access_token_encrypted != "access-token"
    assert connection.refresh_token_encrypted is not None
    assert decrypt_credential(connection.access_token_encrypted or "", settings) == "access-token"
    assert decrypt_credential(connection.refresh_token_encrypted, settings) == "refresh-token"
    assert connection.scopes == ["openid", "email"]
    assert session.commits == 1


def test_refresh_requires_a_refresh_token() -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        scopes=[],
    )

    with pytest.raises(GoogleCredentialError, match="refresh token is unavailable"):
        refresh_google_access_token(cast(Session, FakeSession([])), settings, connection)


def test_refresh_updates_access_token_and_preserves_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    session = FakeSession([])
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        access_token_encrypted=encrypt_credential("old-access", settings),
        refresh_token_encrypted=encrypt_credential("refresh-token", settings),
        token_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        scopes=["openid"],
    )
    monkeypatch.setattr(
        "app.services.credentials.GoogleOAuthClient.refresh_access_token",
        lambda _client, refresh_token: {
            "access_token": "new-access",
            "expires_in": 3600,
        },
    )

    assert (
        get_valid_google_access_token(cast(Session, session), settings, connection) == "new-access"
    )
    assert decrypt_credential(connection.refresh_token_encrypted or "", settings) == "refresh-token"
    assert session.commits == 1


def test_valid_access_token_is_not_refreshed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        access_token_encrypted=encrypt_credential("access-token", settings),
        refresh_token_encrypted=encrypt_credential("refresh-token", settings),
        token_expires_at=datetime.now(UTC) + timedelta(minutes=10),
        scopes=[],
    )
    monkeypatch.setattr(
        "app.services.credentials.refresh_google_access_token",
        lambda *_args: pytest.fail("refresh should not be called"),
    )

    assert get_valid_google_access_token(cast(Session, FakeSession([])), settings, connection) == (
        "access-token"
    )


def test_refresh_failure_is_wrapped_without_committing(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(token_encryption_key=Fernet.generate_key().decode())
    session = FakeSession([])
    connection = GoogleConnection(
        user_id=UUID(int=0),
        google_account_id="google-id",
        email="user@example.com",
        refresh_token_encrypted=encrypt_credential("refresh-token", settings),
        scopes=[],
    )
    monkeypatch.setattr(
        "app.services.credentials.GoogleOAuthClient.refresh_access_token",
        lambda *_args: (_ for _ in ()).throw(OAuthExchangeError("revoked")),
    )

    with pytest.raises(GoogleCredentialError, match="refresh failed"):
        refresh_google_access_token(cast(Session, session), settings, connection)
    assert session.commits == 0
