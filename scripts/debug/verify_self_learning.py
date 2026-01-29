
import asyncio
import logging
import sys
import os

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.db import init_db, AsyncSessionLocal
from app.models.settings import SystemSetting
from app.models.skill_log import SkillChangelog
from app.tools.learning_tools import learn_skill_rule_func
from app.core.skill_loader import SkillLoader
from sqlmodel import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_learning")

async def main():
    logger.info("Initializing DB...")
    await init_db()
    
    skill_name = "test_learning"
    rule_text = "Never use magic numbers."
    reason = "Test Verification"

    async with AsyncSessionLocal() as session:
        # 1. Set Mode to Manual
        logger.info("Setting mode to MANUAL...")
        setting = await session.get(SystemSetting, "SKILL_LEARNING_MODE")
        if not setting:
            setting = SystemSetting(key="SKILL_LEARNING_MODE", value="manual")
            session.add(setting)
        else:
            setting.value = "manual"
            session.add(setting)
        await session.commit()
    
    # 2. Simulate Tool Call
    logger.info("Simulating Agent tool call...")
    msg = await learn_skill_rule_func(skill_name, rule_text, reason)
    logger.info(f"Tool returned: {msg}")
    
    assert "logged for review" in msg
    
    # 3. Verify Log
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SkillChangelog).where(SkillChangelog.skill_name == skill_name).order_by(SkillChangelog.created_at.desc()))
        log = result.scalars().first()
        
        assert log is not None
        assert log.status == "pending"
        assert log.rule_content == rule_text
        logger.info(f"Log created with ID {log.id}, Status: {log.status}")
        
        # 4. Approve Log (Simulate API)
        logger.info("Approving log...")
        success = SkillLoader.append_learned_rule(log.skill_name, log.rule_content)
        assert success
        
        log.status = "approved"
        session.add(log)
        await session.commit()
        
    # 5. Verify Content
    content = SkillLoader.load_by_name(skill_name)
    logger.info("Checking skill content...")
    if "Never use magic numbers" in content and "## 🧠 Learned Rules" in content:
        logger.info("✅ SUCCESS: Rule appended to skill card.")
    else:
        logger.error("❌ FAILURE: Rule not found in content.")
        print(content)

if __name__ == "__main__":
    asyncio.run(main())
