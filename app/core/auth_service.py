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

from enum import Enum

class BindResult(str, Enum):
    SUCCESS = "success"
    PROVIDER_CONFLICT = "provider_conflict" # Social ID already linked to another user
    USER_CONFLICT = "user_conflict"     # User already linked to another Social ID of this type
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
    async def bind_identity(user_id: int, provider: str, provider_user_id: str, username: str = None) -> BindResult:
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
                    return BindResult.SUCCESS  # Already linked correctly
                else:
                    logger.warning(f"Social ID {provider_user_id} already linked to another user ({existing.user_id}).")
                    return BindResult.PROVIDER_CONFLICT  # Conflict: One social ID -> One Nexus User

            # Check if this User already has an identity for this provider
            stmt_user = select(UserIdentity).where(
                UserIdentity.user_id == user_id, UserIdentity.provider == provider
            )
            result_user = await session.execute(stmt_user)
            existing_user = result_user.scalar_one_or_none()
            if existing_user:
                logger.warning(f"User {user_id} already has a {provider} identity linked ({existing_user.provider_user_id}).")
                return BindResult.USER_CONFLICT # Conflict: One Nexus User -> One Social ID per provider

            # Create new identity
            new_id = UserIdentity(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_username=username,
                last_seen=datetime.utcnow(),
            )
            session.add(new_id)

            # Role Promotion: If target user is a 'guest', promote to 'user'
            from app.models.user import User
            user = await session.get(User, user_id)
            if user and user.role == "guest":
                logger.info(f"Promoting User {user_id} from guest to user upon binding.")
                user.role = "user"
                session.add(user)

            await session.commit()
            logger.info(f"Bound {provider}:{provider_user_id} to User {user_id}")
            return BindResult.SUCCESS

    @staticmethod
    async def unbind_identity(provider: str, provider_user_id: str) -> bool:
        """Remove a binding by provider and ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(UserIdentity).where(
                UserIdentity.provider == provider, UserIdentity.provider_user_id == provider_user_id
            )
            result = await session.execute(stmt)
            identity = result.scalar_one_or_none()
            if identity:
                await session.delete(identity)
                await session.commit()
                logger.info(f"Unbound {provider}:{provider_user_id}")
                return True
            return False

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
    async def notify_admins(content: str, meta: dict = None):
        """Send a message to all users with role 'admin'."""
        async with AsyncSessionLocal() as session:
            # 1. Find all admin users
            stmt = select(User).where(User.role == "admin")
            res = await session.execute(stmt)
            admins = res.scalars().all()

            from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage

            for admin in admins:
                # 2. Get their identities
                stmt_id = select(UserIdentity).where(UserIdentity.user_id == admin.id)
                res_id = await session.execute(stmt_id)
                identities = res_id.scalars().all()

                for identity in identities:
                    # 3. Push to outbox
                    try:
                        channel = ChannelType(identity.provider)
                        msg = UnifiedMessage(
                            channel=channel,
                            channel_id=identity.provider_user_id,
                            content=content,
                            msg_type=MessageType.TEXT,
                            meta=meta or {},
                        )
                        await MQService.push_outbox(msg)
                        logger.info(f"Notification sent to admin {admin.username} via {channel.value}")
                    except ValueError:
                        logger.warning(f"Unknown channel provider: {identity.provider}")

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

    @staticmethod
    def get_allowed_tools(user: User, all_tools: list) -> list:
        """
        Return list of tools that the user is allowed to use.
        """
        allowed = []
        for tool in all_tools:
            # We assume tool has .name attribute
            tool_name = getattr(tool, "name", str(tool))
            # domain inference (simplified as per check_tool_permission)
            domain = "standard"
            if AuthService.check_tool_permission(user, tool_name, domain):
                allowed.append(tool)
        return allowed
