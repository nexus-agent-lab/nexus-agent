import asyncio
import json
import logging
import os
import sys

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.db import init_db, AsyncSessionLocal
from app.core.session import SessionManager
from app.models.user import User
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_session")

async def main():
    logger.info("Initializing DB...")
    await init_db()

    user_id = None
    async with AsyncSessionLocal() as session:
        # Create test user if not exists
        result = await session.execute(select(User).where(User.username == "session_tester"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(username="session_tester", role="admin", api_key="sk-test-session-key")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created user: {user.username} (ID: {user.id})")
        else:
            logger.info(f"Using existing user: {user.username} (ID: {user.id})")
        user_id = user.id

    # 1. Test Session Creation
    logger.info("--- Testing Session Creation ---")
    active_session = await SessionManager.get_or_create_session(user_id)
    logger.info(f"Session ID: {active_session.id}, UUID: {active_session.session_uuid}")
    
    # 2. Test Message Saving (Normal)
    logger.info("--- Testing Normal Message Saving ---")
    msg1 = await SessionManager.save_message(
        session_id=active_session.id,
        role="user",
        type="human",
        content="Hello Nexus"
    )
    logger.info(f"Saved Msg 1: {msg1.content}")

    # 3. Test Tool Output Pruning
    logger.info("--- Testing Tool Pruning ---")
    # Simulate a large cleanup
    large_json = json.dumps([{"id": f"light.{i}", "state": "on"} for i in range(100)])
    logger.info(f"Original JSON size: {len(large_json)}")
    
    pruned_content, is_pruned, original = await SessionManager.prune_tool_output(large_json, "list_entities")
    logger.info(f"Pruned Content: \n{pruned_content}")
    logger.info(f"Is Pruned: {is_pruned}")
    
    msg2 = await SessionManager.save_message(
        session_id=active_session.id,
        role="tool",
        type="tool",
        content=pruned_content,
        tool_name="list_entities",
        is_pruned=is_pruned,
        original_content=original
    )
    
    # 4. Test History Retrieval
    logger.info("--- Testing History Retrieval ---")
    history = await SessionManager.get_history(active_session.id)
    for m in history:
        logger.info(f"[{m.type}] {m.content[:50]}...")
        
    assert len(history) >= 2
    logger.info("✅ Session Verification Passed!")

if __name__ == "__main__":
    asyncio.run(main())
