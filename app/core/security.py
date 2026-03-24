import base64
import logging
import os
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Cache the Fernet instance to avoid recreating it
_fernet_instance: Optional[Fernet] = None
_process_jwt_secret: Optional[str] = None


def reset_security_caches() -> None:
    global _fernet_instance, _process_jwt_secret
    _fernet_instance = None
    _process_jwt_secret = None


def _is_valid_fernet_key(master_key: str | None) -> bool:
    if not master_key:
        return False
    try:
        decoded = base64.urlsafe_b64decode(master_key.encode("utf-8"))
    except Exception:
        return False
    return len(decoded) == 32


def _is_strong_jwt_secret(secret: str | None) -> bool:
    return bool(secret and len(secret.encode("utf-8")) >= 32)


def get_jwt_secret() -> str:
    global _process_jwt_secret

    env_secret = os.getenv("JWT_SECRET")
    if _is_strong_jwt_secret(env_secret):
        return env_secret

    if _process_jwt_secret is None:
        _process_jwt_secret = secrets.token_urlsafe(32)
        logger.warning("JWT_SECRET is missing or too short. Using a generated process-local fallback secret.")

    return _process_jwt_secret


async def ensure_runtime_security_settings() -> None:
    from sqlmodel import select

    from app.core.db import AsyncSessionLocal
    from app.models.settings import SystemSetting

    generated_values: dict[str, str] = {}
    resolved_values: dict[str, str] = {}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(["JWT_SECRET", "NEXUS_MASTER_KEY"]))
        )
        settings = {item.key: item for item in result.scalars().all()}

        env_jwt = os.getenv("JWT_SECRET")
        if _is_strong_jwt_secret(env_jwt):
            resolved_values["JWT_SECRET"] = env_jwt
        elif settings.get("JWT_SECRET") and _is_strong_jwt_secret(settings["JWT_SECRET"].value):
            resolved_values["JWT_SECRET"] = settings["JWT_SECRET"].value
        else:
            generated_values["JWT_SECRET"] = secrets.token_urlsafe(32)
            resolved_values["JWT_SECRET"] = generated_values["JWT_SECRET"]

        env_master = os.getenv("NEXUS_MASTER_KEY")
        if _is_valid_fernet_key(env_master):
            resolved_values["NEXUS_MASTER_KEY"] = env_master
        elif settings.get("NEXUS_MASTER_KEY") and _is_valid_fernet_key(settings["NEXUS_MASTER_KEY"].value):
            resolved_values["NEXUS_MASTER_KEY"] = settings["NEXUS_MASTER_KEY"].value
        else:
            generated_values["NEXUS_MASTER_KEY"] = Fernet.generate_key().decode("utf-8")
            resolved_values["NEXUS_MASTER_KEY"] = generated_values["NEXUS_MASTER_KEY"]

        for key, value in generated_values.items():
            if settings.get(key):
                settings[key].value = value
                session.add(settings[key])
            else:
                session.add(
                    SystemSetting(
                        key=key,
                        value=value,
                        description="Auto-generated runtime security secret",
                    )
                )

        if generated_values:
            await session.commit()

    for key, value in resolved_values.items():
        os.environ[key] = value

    reset_security_caches()

    if generated_values:
        logger.warning("Generated secure runtime settings for: %s", ", ".join(sorted(generated_values.keys())))


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
        if not _is_valid_fernet_key(master_key):
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
