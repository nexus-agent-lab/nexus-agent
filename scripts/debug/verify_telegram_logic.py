import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sqlalchemy.future import select

from app.core.auth_service import AuthService
from app.core.db import AsyncSessionLocal
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage
from app.core.worker import AgentWorker
from app.models.user import User

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_telegram")


# Mock Tools
class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description


async def verify_logic():
    print("--- 🚀 Starting Telegram Logic Verification ---")

    # 1. Setup Mock Tools
    tools = [
        MockTool("get_weather", "Get current weather"),
        MockTool("search_web", "Search the internet"),
        MockTool("internal_admin", "Admin only tool"),
    ]
    AgentWorker.set_tools(tools)
    AgentWorker.set_agent_graph(MagicMock())  # Mock graph

    # 2. Verify Onboarding
    print("\n[Test 1] Verifying Guest Onboarding...")

    # Mock a message from a new Telegram user
    msg_guest = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id="999999",  # Unknown ID
        content="Hello Agent",
        msg_type=MessageType.TEXT,
        meta={"username": "guest_user"},
    )

    # We need to monkeypatch MQService.push_outbox to capture result
    captured_messages = []
    original_push = MQService.push_outbox

    async def mock_push(msg):
        captured_messages.append(msg)
        print(f"   -> Outbox: {msg.content[:100]}... Meta: {msg.meta}")

    MQService.push_outbox = mock_push

    # Run process
    # Note: This relies on DB to resolve user.
    # If "999999" doesn't exist, it creates a guest.
    await AgentWorker._process_message(msg_guest)

    if any("Welcome to Nexus" in m.content for m in captured_messages):
        print("   ✅ Onboarding message sent.")
    else:
        print("   ❌ Onboarding message missing!")

    # 3. Verify Dynamic Menus (Binding)
    print("\n[Test 2] Verifying Dynamic Menus on /bind...")
    captured_messages.clear()

    # Create a real user to bind to
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        stmt = select(User).where(User.username == "verify_tg_user")
        user = (await session.execute(stmt)).scalars().first()
        if not user:
            user = User(
                username="verify_tg_user",
                api_key="verify_key_123",
                role="user",
                policy={"allow_domains": ["weather", "standard"]},
            )
            session.add(user)
            await session.commit()
            print(f"   created test user {user.id}")

        user_id = user.id

    # Generate Token
    token = await AuthService.create_bind_token(user_id)
    print(f"   Generated Token: {token}")

    # Send /bind command
    msg_bind = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id="888888",
        content=f"/bind {token}",
        msg_type=MessageType.TEXT,
        meta={"username": "bind_tester"},
    )

    await AgentWorker._process_message(msg_bind)

    # Check for success and commands
    success_msg = next((m for m in captured_messages if "Success" in m.content), None)
    if success_msg:
        print("   ✅ Bind Success message received.")
        commands = success_msg.meta.get("telegram_commands")
        if commands:
            print(f"   ✅ Commands found: {commands}")
            # Check correctness
            cmd_names = [c["command"] for c in commands]
            if "getweather" in cmd_names and "searchweb" in cmd_names:
                print("   ✅ Tools correctly mapped.")
            else:
                print(f"   ⚠️ Unexpected commands: {cmd_names}")
        else:
            print("   ❌ No 'telegram_commands' metadata found!")
    else:
        print("   ❌ Bind failed or no response.")

    # restore
    MQService.push_outbox = original_push


if __name__ == "__main__":
    try:
        if sys.platform != "win32":
            import uvloop

            uvloop.install()
    except ImportError:
        pass

    asyncio.run(verify_logic())
