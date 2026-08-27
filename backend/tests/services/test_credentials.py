import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings
from app.services.credentials import (
    CredentialEncryptionError,
    decrypt_credential,
    encrypt_credential,
)


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
