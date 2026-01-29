
import logging
from typing import Type
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool

from app.core.db import AsyncSessionLocal
from app.models.skill_log import SkillChangelog
from app.models.settings import SystemSetting
from app.core.skill_loader import SkillLoader

logger = logging.getLogger(__name__)

class LearnSkillRuleSchema(BaseModel):
    skill_name: str = Field(description="Name of the skill to update (e.g. 'homeassistant')")
    rule_content: str = Field(description="The exact text of the rule to learn (e.g. 'Do not use detailed param')")
    reason: str = Field(description="Why this rule is needed (e.g. 'Schema validation failed')")

async def learn_skill_rule_func(skill_name: str, rule_content: str, reason: str) -> str:
    """
    Learns a new rule for a specific skill.
    Depending on system configuration, this will either:
    1. Auto-apply the rule to the skill card.
    2. Log it for human review.
    """
    logger.info(f"Agent proposing rule for {skill_name}: {rule_content}")
    
    # Check if skill exists
    if not SkillLoader.load_by_name(skill_name):
        return f"Error: Skill '{skill_name}' does not exist."

    async with AsyncSessionLocal() as session:
        # Get Mode
        setting = await session.get(SystemSetting, "SKILL_LEARNING_MODE")
        mode = setting.value if setting else "manual"
        
        # Create Log
        log = SkillChangelog(
            skill_name=skill_name,
            rule_content=rule_content,
            reason=reason,
            mode=mode,
            status="pending"
        )
        
        if mode == "auto":
            success = SkillLoader.append_learned_rule(skill_name, rule_content)
            if success:
                log.status = "auto_applied"
                log.reviewed_at = log.created_at # Auto reviewed
                msg = f"Rule auto-applied to {skill_name}.md"
            else:
                log.status = "error"
                msg = "Failed to write rule to file."
        else:
            msg = "Rule logged for review. Will be active after approval."
            
        session.add(log)
        await session.commit()
        
    return msg

learn_skill_rule = StructuredTool.from_function(
    coroutine=learn_skill_rule_func,
    name="learn_skill_rule",
    description="Propose a new rule to fix persistent errors or improve tool usage.",
    args_schema=LearnSkillRuleSchema
)
