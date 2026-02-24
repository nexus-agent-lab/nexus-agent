import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Cache the Fernet instance to avoid recreating it
_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Optional[Fernet]:
    """Retrieves or initializes a Fernet instance using the NEXUS_MASTER_KEY."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    master_key = os.getenv("NEXUS_MASTER_KEY")
    if not master_key:
        logger.warning("NEXUS_MASTER_KEY is not set. Encryption/decryption will be bypassed.")
        return None

    try:
        # Validate that it's a valid 32-byte urlsafe base64 string
        # Pad if necessary for validation
        padding_needed = len(master_key) % 4
        padded_key = master_key + "=" * padding_needed
        decoded = base64.urlsafe_b64decode(padded_key.encode("utf-8"))

        if len(decoded) != 32:
            logger.error("Master key must be exactly 32 bytes when base64 decoded. Bypassing encryption.")
            return None

        _fernet_instance = Fernet(master_key.encode("utf-8"))
        return _fernet_instance
    except Exception as e:
        logger.error(f"Failed to initialize Fernet with provided master key: {e}")
        return None


def encrypt_secret(val: str) -> str:
    """
    Encrypts a string value using Fernet (AES-256).
    Returns the original string if encryption fails or if NEXUS_MASTER_KEY is missing.
    """
    if not val:
        return val

    fernet = _get_fernet()
    if not fernet:
        return val

    try:
        encrypted_bytes = fernet.encrypt(val.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return val


def decrypt_secret(val: str) -> str:
    """
    Decrypts a Fernet (AES-256) encrypted string.
    Returns the original string if decryption fails or if it wasn't encrypted.
    """
    if not val:
        return val

    fernet = _get_fernet()
    if not fernet:
        return val

    try:
        decrypted_bytes = fernet.decrypt(val.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        logger.debug("Decryption failed: Invalid token (maybe not encrypted). Returning original value.")
        return val
    except Exception as e:
        logger.error(f"Decryption failed: {e}. Returning original value.")
        return val
