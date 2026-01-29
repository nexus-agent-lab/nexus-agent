import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Redis for temporary tokens
if os.getenv("DOCKER_ENV"):
    REDIS_URL = "redis://redis:6379/0"
else:
    REDIS_URL = "redis://localhost:6379/0"

# Monkeypatch AuthService to use our test Redis URL if needed
import app.core.auth_service

app.core.auth_service.REDIS_URL = REDIS_URL

from sqlmodel import select

from app.core.auth_service import AuthService
from app.core.db import get_session
from app.core.mq import ChannelType, MessageType, UnifiedMessage
from app.models.user import User, UserIdentity


async def cleanup_test_data(user_id):
    async for session in get_session():
        # Delete test identities
        stmt = select(UserIdentity).where(UserIdentity.user_id == user_id)
        result = await session.execute(stmt)
        identities = result.scalars().all()
        for identity in identities:
            await session.delete(identity)

        # Reset user role/policy
        user = await session.get(User, user_id)
        if user:
            user.role = "admin"  # Set back to admin for this script's user
            user.policy = {}
            session.add(user)
        await session.commit()


async def test_identity_system():
    print("🚀 Starting Identity System Test...")

    # 1. Setup Test User
    async for session in get_session():
        result = await session.execute(select(User).limit(1))
        test_user = result.scalar_one_or_none()

        if not test_user:
            print("📝 No users found. Creating a temporary test user...")
            test_user = User(username="test_admin", api_key="test_api_key_123", role="admin")
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)

        test_user_id = test_user.id
        print(f"Using Test User: {test_user.username} (ID: {test_user_id})")
        break

    await cleanup_test_data(test_user_id)

    # 2. Test Bind Token Generation
    token = await AuthService.create_bind_token(test_user_id)
    print(f"✅ Generated Bind Token: {token}")

    # 3. Simulate Bind Message (/bind <token>)
    msg = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id="999888777",  # Fake TG chat ID
        content=f"/bind {token}",
        msg_type=MessageType.TEXT,
        meta={"username": "test_tg_user"},
    )

    print(f"📥 Simulating message: {msg.content} from {msg.channel_id}")

    # We'll use the AuthService directly to simulate what AgentWorker does
    verified_user_id = await AuthService.verify_bind_token(token)
    if verified_user_id == test_user_id:
        print("✅ Token verified successfully.")
        success = await AuthService.bind_identity(
            user_id=test_user_id,
            provider=msg.channel.value,
            provider_user_id=str(msg.channel_id),
            username=msg.meta.get("username"),
        )
        if success:
            print("✅ Identity bound successfully.")
        else:
            print("❌ Identity binding failed.")
    else:
        print(f"❌ Token verification failed. Got: {verified_user_id}")

    # 4. Test User Resolution by Identity
    resolved_user = await AuthService.get_user_by_identity(msg.channel.value, str(msg.channel_id))
    if resolved_user and resolved_user.id == test_user_id:
        print(f"✅ User resolved by identity: {resolved_user.username}")
    else:
        print("❌ User resolution failed.")

    # 5. Test Permission Check
    # Case A: Admin (Should allow everything)
    resolved_user.role = "admin"
    can_use = AuthService.check_tool_permission(resolved_user, "run_command", "system")
    print(f"🛡️ Permission (Admin - run_command): {'✅ ALLOWED' if can_use else '❌ DENIED'}")

    # Case B: Standard User (Should deny system, allow standard)
    resolved_user.role = "user"
    resolved_user.policy = {}
    can_use_standard = AuthService.check_tool_permission(resolved_user, "get_weather", "weather")
    can_use_system = AuthService.check_tool_permission(resolved_user, "run_command", "system")
    print(f"🛡️ Permission (User - get_weather): {'✅ ALLOWED' if can_use_standard else '❌ DENIED'}")
    print(f"🛡️ Permission (User - run_command): {'✅ ALLOWED' if can_use_system else '❌ DENIED'}")

    # Case C: Custom Policy (Deny specific tool)
    resolved_user.policy = {"deny_tools": ["get_weather"]}
    can_use_denied = AuthService.check_tool_permission(resolved_user, "get_weather", "weather")
    print(f"🛡️ Permission (User Policy - Deny get_weather): {'✅ ALLOWED' if can_use_denied else '❌ DENIED'}")

    print("\n🏁 Test Completed.")


if __name__ == "__main__":
    asyncio.run(test_identity_system())
