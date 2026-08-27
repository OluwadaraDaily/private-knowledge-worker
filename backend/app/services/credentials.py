from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class CredentialEncryptionError(ValueError):
    """Raised when the credential-encryption key is missing or invalid."""


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
