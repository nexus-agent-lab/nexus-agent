
import asyncio
import logging
import uuid
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.models.session import Session, SessionMessage, SessionSummary
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
# Patch DB
import app.core.db
import app.core.session

from sqlalchemy.pool import StaticPool

# Use SQLite for testing to avoid network issues
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DB_URL, 
    echo=False, 
    future=True, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Monkey patch the session factory
app.core.db.AsyncSessionLocal = TestSessionLocal
app.core.session.AsyncSessionLocal = TestSessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_auto_compacting():
    """
    Test the Auto-Compacting feature.
    1. Create a session.
    2. Insert 20 messages (trigger threshold is usually ~15).
    3. Manually call compact_session (or wait for background task if integrating fully).
    4. Verify results.
    """
    
    # 0. Setup DB
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Mock LLM for compact_session
    from app.core import llm_utils
    from langchain_core.messages import AIMessage
    
    class MockLLM:
        async def ainvoke(self, prompt):
            return AIMessage(content="[Summary] The user and assistant exchanged 15 messages testing the context window compaction feature.")
            
    # Simple mock function
    def mock_get_llm():
        return MockLLM()
        
    llm_utils.get_llm_client = mock_get_llm

    user_id = 1 # Test User
    session_uuid = str(uuid.uuid4())
    
    logger.info(f"--- Starting Auto-Compacting Verification for Session {session_uuid} ---")
    
    # IMPORTANT: Import SessionManager AFTER patching DB
    from app.core.session import SessionManager

    session = await SessionManager.get_or_create_session(user_id=user_id, session_uuid=session_uuid)
    logger.info(f"Created Session ID: {session.id}")
    
    # 1. Insert 20 Messages
    logger.info("Inserting 20 simulated messages...")
    for i in range(20):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Message {i}: This is a simulated message number {i} to test context window compaction."
        await SessionManager.save_message(session.id, role, role, content)
        # Small delay to ensure timestamp ordering if needed (though DB is fast)
        # await asyncio.sleep(0.01) 
    
    # Check count before compacting
    async with TestSessionLocal() as db:
        from sqlmodel import select, func
        count = (await db.execute(select(func.count()).where(SessionMessage.session_id == session.id))).scalar()
        logger.info(f"Total Messages Before Compacting: {count}")
        assert count == 20

    # 2. Trigger Compacting
    # We keep last 5 for this test to force compaction
    logger.info("Triggering compact_session(keep_last=5)...")
    await SessionManager.compact_session(session.id, keep_last=5)
    
    # 3. Verify Results
    async with TestSessionLocal() as db:
        # Check Summaries
        summaries = (await db.execute(select(SessionSummary).where(SessionSummary.session_id == session.id))).scalars().all()
        logger.info(f"Generated Summaries: {len(summaries)}")
        for s in summaries:
            logger.info(f"Summary Content: {s.summary}")
            logger.info(f"Summary Covers Messages: {s.start_msg_id} -> {s.end_msg_id} (Count: {s.msg_count})")
        
        assert len(summaries) >= 1
        
        # Check Archived Messages
        archived_count = (await db.execute(select(func.count()).where(SessionMessage.session_id == session.id, SessionMessage.is_archived == True))).scalar()
        logger.info(f"Archived Messages: {archived_count}")
        assert archived_count == 15 # 20 - 5 = 15
        
        # Check Unarchived (Recent) Messages
        unarchived_count = (await db.execute(select(func.count()).where(SessionMessage.session_id == session.id, SessionMessage.is_archived == False))).scalar()
        logger.info(f"Unarchived (Recent) Messages: {unarchived_count}")
        assert unarchived_count == 5

    # 4. Verify Context Assembly
    logger.info("Verifying get_history_with_summary...")
    summary_text, recent_msgs = await SessionManager.get_history_with_summary(session.id, limit=5)
    
    logger.info(f"Context Summary Length: {len(summary_text)}")
    logger.info(f"Recent Messages Count: {len(recent_msgs)}")
    
    assert len(summary_text) > 0
    assert len(recent_msgs) == 5
    assert "Summarize" not in summary_text # Ensure prompt isn't returned, but the result
    
    logger.info("✅ Auto-Compacting Verification Passed!")

if __name__ == "__main__":
    asyncio.run(verify_auto_compacting())
