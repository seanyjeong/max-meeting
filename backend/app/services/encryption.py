"""
PII Encryption Service using Fernet (symmetric encryption).

Provides encryption and decryption for Personally Identifiable Information (PII)
such as phone numbers and email addresses.
"""

from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting PII data using Fernet.

    Fernet guarantees that a message encrypted using it cannot be manipulated
    or read without the key. Fernet is an implementation of symmetric (also known
    as "secret key") authenticated cryptography.
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption service.

        Args:
            key: Base64-encoded Fernet key. If not provided, uses PII_ENCRYPTION_KEY
                 from settings.
        """
        if key is None:
            settings = get_settings()
            key = settings.PII_ENCRYPTION_KEY

        if not key:
            raise EncryptionError(
                "PII_ENCRYPTION_KEY is not configured. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        # Ensure the key is properly formatted
        try:
            # If the key is not bytes, encode it
            if isinstance(key, str):
                key = key.encode()

            # Validate key by creating Fernet instance
            self._fernet = Fernet(key)
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key: {e}")

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt plaintext string to bytes.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Encrypted bytes that can be stored in database.
        """
        if not plaintext:
            return b""

        try:
            return self._fernet.encrypt(plaintext.encode("utf-8"))
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt bytes back to plaintext string.

        Args:
            ciphertext: The encrypted bytes to decrypt.

        Returns:
            Decrypted plaintext string.
        """
        if not ciphertext:
            return ""

        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken:
            raise EncryptionError("Decryption failed: Invalid token or corrupted data")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")


@lru_cache()
def _get_encryption_service() -> EncryptionService:
    """Get cached encryption service instance."""
    return EncryptionService()


def encrypt_pii(data: str) -> bytes:
    """
    Encrypt PII data.

    This is a convenience function that uses the default encryption service.

    Args:
        data: The PII string to encrypt (e.g., phone number, email).

    Returns:
        Encrypted bytes suitable for database storage.

    Example:
        >>> encrypted_phone = encrypt_pii("010-1234-5678")
        >>> # Store encrypted_phone in database
    """
    if not data:
        return b""
    service = _get_encryption_service()
    return service.encrypt(data)


def decrypt_pii(data: bytes) -> str:
    """
    Decrypt PII data.

    This is a convenience function that uses the default encryption service.

    Args:
        data: The encrypted bytes from database.

    Returns:
        Decrypted plaintext string.

    Example:
        >>> phone = decrypt_pii(contact.phone_encrypted)
        >>> print(phone)  # "010-1234-5678"
    """
    if not data:
        return ""
    service = _get_encryption_service()
    return service.decrypt(data)


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded key string suitable for PII_ENCRYPTION_KEY.

    Example:
        >>> key = generate_key()
        >>> print(key)  # Use this in your .env file
    """
    return Fernet.generate_key().decode()
