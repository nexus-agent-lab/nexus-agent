import logging
import os
import random
import string
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy.future import select

from app.core.db import AsyncSessionLocal
from app.models.user import User, UserIdentity

logger = logging.getLogger("nexus.auth")

# Redis for temporary tokens
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class AuthService:
    @staticmethod
    def _get_redis():
        return redis.from_url(REDIS_URL, decode_responses=True)

    @staticmethod
    async def create_bind_token(user_id: int) -> str:
        """
        Generate a 6-digit numeric token for account binding.
        TTL: 5 minutes.
        """
        token = "".join(random.choices(string.digits, k=6))
        r = AuthService._get_redis()

        # Key: bind:123456 -> user_id
        await r.setex(f"bind:{token}", 300, str(user_id))
        await r.close()
        return token

    @staticmethod
    async def verify_bind_token(token: str) -> int:
        """Return user_id if token is valid, else None."""
        r = AuthService._get_redis()
        user_id = await r.get(f"bind:{token}")
        await r.delete(f"bind:{token}")  # One-time use
        await r.close()

        if user_id:
            return int(user_id)
        return None

    @staticmethod
    async def bind_identity(user_id: int, provider: str, provider_user_id: str, username: str = None) -> bool:
        """Link a provider ID to a User."""
        async with AsyncSessionLocal() as session:
            # Check if this provider ID is already taken
            stmt = select(UserIdentity).where(
                UserIdentity.provider == provider, UserIdentity.provider_user_id == provider_user_id
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                if existing.user_id == user_id:
                    return True  # Already linked
                else:
                    logger.warning(f"ID {provider_user_id} already linked to another user.")
                    return False  # Conflict

            # Create new identity
            new_id = UserIdentity(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_username=username,
                last_seen=datetime.utcnow(),
            )
            session.add(new_id)
            await session.commit()
            logger.info(f"Bound {provider}:{provider_user_id} to User {user_id}")
            return True

    @staticmethod
    async def get_user_by_identity(provider: str, provider_user_id: str) -> User:
        """Resolve a User from an incoming message ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(UserIdentity).where(
                UserIdentity.provider == provider, UserIdentity.provider_user_id == provider_user_id
            )
            result = await session.execute(stmt)
            identity = result.scalar_one_or_none()

            if identity:
                # Update last see
                identity.last_seen = datetime.utcnow()
                await session.commit()

                # Fetch User (eagerly loaded? No, need explicit join or separate fetch)
                # Since we need the full User object (and its policy), let's fetch it.
                # Identity.user relationship should work if loaded, but session context matters.
                # Let's just fetch the user directly.
                stmt_user = select(User).where(User.id == identity.user_id)
                res_user = await session.execute(stmt_user)
                return res_user.scalar_one_or_none()

            return None

    @staticmethod
    def check_tool_permission(user: User, tool_name: str, domain: str = "standard") -> bool:
        """
        Check if user is allowed to use this tool/domain.
        """
        if user.role == "admin":
            return True

        policy = user.policy or {}

        # 1. Deny List
        if tool_name in policy.get("deny_tools", []):
            return False

        # 2. Allow Domains
        # Default allowed domains for standard users
        defaults = ["standard", "time", "weather"]
        allowed = policy.get("allow_domains", defaults)

        if domain in allowed:
            return True

        return False
