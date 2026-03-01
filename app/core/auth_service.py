import logging
import os
import random
import string
from datetime import datetime
from enum import Enum
from typing import List

import redis.asyncio as redis
from sqlalchemy.future import select

from app.core.db import AsyncSessionLocal
from app.models.user import User, UserIdentity

logger = logging.getLogger("nexus.auth")

# Redis for temporary tokens
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# RBAC Role Levels
ROLE_LEVELS = {"admin": 100, "user": 50, "guest": 10}


class BindResult(str, Enum):
    SUCCESS = "success"
    PROVIDER_CONFLICT = "provider_conflict"  # Social ID already linked to another user
    USER_CONFLICT = "user_conflict"  # User already linked to another Social ID of this type


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
            stmt_user = select(UserIdentity).where(UserIdentity.user_id == user_id, UserIdentity.provider == provider)
            result_user = await session.execute(stmt_user)
            existing_user = result_user.scalar_one_or_none()
            if existing_user:
                logger.warning(
                    f"User {user_id} already has a {provider} identity linked ({existing_user.provider_user_id})."
                )
                return BindResult.USER_CONFLICT  # Conflict: One Nexus User -> One Social ID per provider

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

                # Fetch User
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
    def check_tool_permission(
        user: User,
        tool_name: str,
        domain: str = "standard",
        required_role: str = None,
        allowed_groups: List[str] = None,
    ) -> bool:
        """
        Check if user is allowed to use this tool/domain.
        """
        # Admin bypass
        if user.role == "admin":
            return True

        policy = user.policy or {}

        # 1. Deny List (User-specific override) - Takes precedence
        if tool_name in policy.get("deny_tools", []):
            return False

        # 2. Vertical Gate (Role-based)
        if required_role:
            user_level = ROLE_LEVELS.get(user.role, 0)
            target_level = ROLE_LEVELS.get(required_role, 50)
            if user_level < target_level:
                return False
            # Role requirement met. If no group restriction, grant access.
            if not allowed_groups:
                return True
            # Otherwise, fall through to group check below
        # 3. Horizontal Gate (Group-based)
        if allowed_groups:
            user_groups = set(getattr(user, "groups", []) or [])
            if not user_groups.intersection(set(allowed_groups)):
                return False
            # If we match a group, we are allowed (unless denied by role above)
            return True

        # 4. Fallback: Allow Domains (User-specific whitelist)
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
            # Extract metadata from tool (MCP tools should have domain/category in metadata)
            metadata = getattr(tool, "metadata", {}) or {}
            domain = metadata.get("domain") or metadata.get("category") or "standard"
            required_role = metadata.get("required_role")
            allowed_groups = metadata.get("allowed_groups")

            if AuthService.check_tool_permission(
                user,
                tool_name,
                domain=domain,
                required_role=required_role,
                allowed_groups=allowed_groups,
            ):
                allowed.append(tool)
        return allowed
