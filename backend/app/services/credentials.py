from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.google_connection import GoogleConnection
from app.db.models.user import User
from app.services.oauth import GoogleOAuthClient, OAuthExchangeError


class CredentialEncryptionError(ValueError):
    """Raised when the credential-encryption key is missing or invalid."""


class GoogleCredentialError(ValueError):
    """Raised when Google credentials cannot be stored or refreshed."""


TOKEN_REFRESH_LEEWAY = timedelta(minutes=1)


def _fernet(settings: Settings) -> Fernet:
    if not settings.token_encryption_key:
        raise CredentialEncryptionError("Token encryption key is not configured")
    try:
        return Fernet(settings.token_encryption_key.encode())
    except (ValueError, TypeError) as error:
        raise CredentialEncryptionError("Token encryption key is invalid") from error


def encrypt_credential(value: str, settings: Settings) -> str:
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt_credential(value: str, settings: Settings) -> str:
    try:
        return _fernet(settings).decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise CredentialEncryptionError("Encrypted credential cannot be decrypted") from error


def _google_user_info(access_token: str, settings: Settings) -> dict[str, Any]:
    try:
        user_info = GoogleOAuthClient(settings).user_info(access_token)
    except OAuthExchangeError as error:
        raise GoogleCredentialError("Google account information could not be retrieved") from error
    if not isinstance(user_info, dict) or not isinstance(user_info.get("sub"), str):
        raise GoogleCredentialError("Google returned invalid account information")
    if not isinstance(user_info.get("email"), str):
        raise GoogleCredentialError("Google account email is unavailable")
    return user_info


def _get_or_create_user(session: Session, user_info: dict[str, Any]) -> User:
    email = user_info["email"]
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=user_info.get("name"))
        session.add(user)
        session.flush()
    return user


def _get_or_create_connection(
    session: Session, user: User, user_info: dict[str, Any]
) -> GoogleConnection:
    account_id = user_info["sub"]
    connection = session.scalar(
        select(GoogleConnection).where(
            GoogleConnection.user_id == user.id,
            GoogleConnection.google_account_id == account_id,
        )
    )
    if connection is None:
        connection = GoogleConnection(
            user_id=user.id,
            google_account_id=account_id,
            email=user_info["email"],
            access_token_encrypted="",
            scopes=[],
        )
        session.add(connection)
    return connection


def _update_connection_tokens(
    connection: GoogleConnection,
    settings: Settings,
    token_data: dict[str, object],
) -> None:
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str):
        raise GoogleCredentialError("Google returned no access token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    if not isinstance(expires_in, int) or expires_in <= 0:
        raise GoogleCredentialError("Google returned an invalid token expiry")
    scope = token_data.get("scope")
    scopes = scope.split() if isinstance(scope, str) else list(settings.oauth_scopes)

    encrypted_access_token = encrypt_credential(access_token, settings)
    encrypted_refresh_token = (
        encrypt_credential(refresh_token, settings) if isinstance(refresh_token, str) else None
    )

    connection.access_token_encrypted = encrypted_access_token
    if encrypted_refresh_token is not None:
        connection.refresh_token_encrypted = encrypted_refresh_token
    connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    connection.scopes = scopes


def persist_google_credentials(
    session: Session, settings: Settings, token_data: dict[str, object]
) -> GoogleConnection:
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str):
        raise GoogleCredentialError("Google returned no access token")
    user_info = _google_user_info(access_token, settings)
    user = _get_or_create_user(session, user_info)
    connection = _get_or_create_connection(session, user, user_info)
    connection.email = user_info["email"]
    _update_connection_tokens(connection, settings, token_data)
    session.commit()
    return connection


def refresh_google_access_token(
    session: Session, settings: Settings, connection: GoogleConnection
) -> str:
    """Force-refresh a Google access token using the stored refresh token."""
    if not connection.refresh_token_encrypted:
        raise GoogleCredentialError("Google refresh token is unavailable")
    try:
        refresh_token = decrypt_credential(connection.refresh_token_encrypted, settings)
    except CredentialEncryptionError as error:
        session.rollback()
        raise GoogleCredentialError("Stored Google refresh token cannot be decrypted") from error
    try:
        token_data = GoogleOAuthClient(settings).refresh_access_token(refresh_token)
    except OAuthExchangeError as error:
        session.rollback()
        raise GoogleCredentialError("Google access-token refresh failed") from error
    try:
        _update_connection_tokens(connection, settings, token_data)
        session.commit()
    except (CredentialEncryptionError, GoogleCredentialError) as error:
        session.rollback()
        if isinstance(error, GoogleCredentialError):
            raise GoogleCredentialError(str(error)) from error
        raise GoogleCredentialError("Refreshed Google credentials could not be stored") from error
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str):
        raise GoogleCredentialError("Google returned no refreshed access token")
    return access_token


def get_valid_google_access_token(
    session: Session,
    settings: Settings,
    connection: GoogleConnection,
    refresh_leeway: timedelta = TOKEN_REFRESH_LEEWAY,
) -> str:
    """Return a usable access token, refreshing it before it expires."""
    if not connection.access_token_encrypted or connection.token_expires_at is None:
        return refresh_google_access_token(session, settings, connection)

    if connection.token_expires_at <= datetime.now(UTC) + refresh_leeway:
        return refresh_google_access_token(session, settings, connection)

    try:
        return decrypt_credential(connection.access_token_encrypted, settings)
    except CredentialEncryptionError as error:
        raise GoogleCredentialError("Stored Google access token cannot be decrypted") from error
