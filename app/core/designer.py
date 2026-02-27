import logging
import os
from datetime import datetime
from typing import List, Optional

from sqlmodel import select

from app.core.llm_utils import get_llm_client

logger = logging.getLogger("nexus.designer")


class MemSkillDesigner:
    """
    Designer Agent for Memory Skill evolution.

    Workflow:
    1. find_underperforming_skills() — identify skills with high negative rate
    2. evolve_skill()               — generate improved prompt via LLM
    3. test_canary()                — shadow-test with recent inputs
    4. save_changelog()             — record change for admin review
    """

    # Minimum total uses before skill is eligible for evolution
    MIN_TOTAL_USES = int(os.getenv("DESIGNER_MIN_FEEDBACK", "10"))
    # Negative rate threshold to trigger evolution
    NEGATIVE_RATE_THRESHOLD = float(os.getenv("DESIGNER_THRESHOLD", "0.3"))

    @classmethod
    async def find_underperforming_skills(cls) -> list:
        """
        Find skills with negative feedback rate > 30% and sufficient usage.
        Returns list of MemorySkill objects.
        """
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkill

        async with AsyncSessionLocal() as session:
            stmt = select(MemorySkill).where(
                MemorySkill.status == "active",
                (MemorySkill.positive_count + MemorySkill.negative_count) >= cls.MIN_TOTAL_USES,
            )
            result = await session.execute(stmt)
            skills = result.scalars().all()

        # Filter by negative rate in Python (easier than complex SQL with division)
        underperforming = []
        for skill in skills:
            total = skill.positive_count + skill.negative_count
            if total > 0:
                neg_rate = skill.negative_count / total
                if neg_rate > cls.NEGATIVE_RATE_THRESHOLD:
                    logger.info(f"🔴 Underperforming skill: {skill.name} (neg_rate={neg_rate:.1%}, total={total})")
                    underperforming.append(skill)

        return underperforming

    @classmethod
    async def get_recent_samples(cls, skill_id: int, limit: int = 5) -> List[dict]:
        """
        Get recent memories produced by a specific skill for analysis.
        Returns list of dicts with 'content' and 'created_at'.
        """
        from app.core.db import AsyncSessionLocal
        from app.models.memory import Memory

        async with AsyncSessionLocal() as session:
            stmt = select(Memory).where(Memory.skill_id == skill_id).order_by(Memory.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            memories = result.scalars().all()

        return [{"content": m.content, "created_at": str(m.created_at)} for m in memories]

    @classmethod
    async def evolve_skill(cls, skill) -> Optional[dict]:
        """
        Generate an improved prompt for an underperforming skill.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Get recent samples for context
        samples = await cls.get_recent_samples(skill.id)
        if not samples:
            logger.warning(f"No samples for skill {skill.name}, skipping evolution")
            return None

        samples_text = "\n".join([f"- {s['content']}" for s in samples])

        # Use Designer LLM via central utility
        llm = get_llm_client(temperature=0.3)

        total = skill.positive_count + skill.negative_count
        neg_rate = skill.negative_count / total if total > 0 else 0

        prompt = f"""You are a prompt engineering expert. Analyze and improve a memory processing skill.

## Current Skill
- **Name**: {skill.name}
- **Type**: {skill.skill_type}
- **Description**: {skill.description}
- **Performance**: {skill.positive_count} positive / {skill.negative_count} negative ({neg_rate:.0%} failure rate)

## Current Prompt Template
```
{skill.prompt_template}
```

## Recent Output Samples (produced by this prompt)
{samples_text}

## Task
1. Analyze why users might be unsatisfied with these outputs
2. Identify specific weaknesses in the current prompt
3. Generate an IMPROVED version of the prompt template

## Output Format
Return your response in this exact structure:

### Analysis
[Your analysis of the problems]

### Improved Prompt
[The complete new prompt template, keeping {{{{ content }}}} and {{{{ context }}}} placeholders]
"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are an expert at improving AI prompts. Be concise and precise."),
                    HumanMessage(content=prompt),
                ]
            )

            response_text = response.content

            # Parse response
            analysis, new_prompt = cls._parse_evolution_response(response_text)

            if not new_prompt:
                logger.error(f"Failed to parse evolution response for {skill.name}")
                return None

            # Run canary test
            canary_passed = await cls.test_canary(skill, new_prompt)

            # Save changelog
            changelog_id = await cls._save_changelog(
                skill=skill,
                new_prompt=new_prompt,
                reason=analysis,
                canary_passed=canary_passed,
            )

            logger.info(
                f"✅ Evolution complete for {skill.name}: "
                f"changelog_id={changelog_id}, canary={'PASS' if canary_passed else 'FAIL'}"
            )

            return {
                "skill_name": skill.name,
                "new_prompt": new_prompt,
                "reason": analysis,
                "canary_passed": canary_passed,
                "changelog_id": changelog_id,
            }

        except Exception as e:
            logger.error(f"Evolution failed for {skill.name}: {e}")
            return None

    @classmethod
    def _parse_evolution_response(cls, text: str) -> tuple:
        """Parse the Designer LLM's response into (analysis, new_prompt)."""
        analysis = ""
        new_prompt = ""

        # Split by '### Improved Prompt'
        if "### Improved Prompt" in text:
            parts = text.split("### Improved Prompt", 1)
            analysis_part = parts[0]
            prompt_part = parts[1] if len(parts) > 1 else ""

            # Extract analysis
            if "### Analysis" in analysis_part:
                analysis = analysis_part.split("### Analysis", 1)[1].strip()
            else:
                analysis = analysis_part.strip()

            # Extract prompt (remove code fences if present)
            new_prompt = prompt_part.strip()
            if new_prompt.startswith("```"):
                lines = new_prompt.split("\n")
                # Remove first and last lines (``` markers)
                lines = [line for line in lines if not line.strip().startswith("```")]
                new_prompt = "\n".join(lines).strip()

        return analysis, new_prompt

    @classmethod
    async def test_canary(cls, skill, new_prompt: str, test_count: int = 3) -> bool:
        """
        Shadow-test a new prompt against recent inputs.
        Does NOT save results — just validates output quality.

        Returns True if all tests pass.
        """
        from langchain_core.messages import HumanMessage

        samples = await cls.get_recent_samples(skill.id, limit=test_count)
        if not samples:
            logger.warning(f"No samples for canary test of {skill.name}")
            return True  # No data to test against, allow

        # Use runtime LLM via central utility
        llm = get_llm_client()

        passed = 0
        for sample in samples:
            try:
                # Render new prompt with sample content
                test_prompt = new_prompt.replace("{{ content }}", sample["content"])
                test_prompt = test_prompt.replace("{{ context }}", "")

                response = await llm.ainvoke([HumanMessage(content=test_prompt)])
                output = response.content.strip()

                # Basic quality checks
                if len(output) < 5:
                    logger.warning(f"Canary output too short: '{output}'")
                    continue
                if len(output) > len(sample["content"]) * 3:
                    logger.warning(f"Canary output too verbose: {len(output)} chars")
                    continue

                passed += 1
            except Exception as e:
                logger.error(f"Canary test failed: {e}")

        pass_rate = passed / len(samples) if samples else 0
        logger.info(f"Canary test for {skill.name}: {passed}/{len(samples)} passed ({pass_rate:.0%})")

        return pass_rate >= 0.6  # At least 60% must pass

    @classmethod
    async def _save_changelog(cls, skill, new_prompt: str, reason: str, canary_passed: bool) -> int:
        """Save evolution record to MemorySkillChangelog."""
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkillChangelog

        changelog = MemorySkillChangelog(
            skill_id=skill.id,
            skill_name=skill.name,
            old_prompt=skill.prompt_template,
            new_prompt=new_prompt,
            reason=reason,
            status="canary" if canary_passed else "rejected",
        )

        async with AsyncSessionLocal() as session:
            session.add(changelog)
            await session.commit()
            await session.refresh(changelog)
            return changelog.id

    @classmethod
    async def approve_changelog(cls, changelog_id: int) -> str:
        """
        Admin approves a canary changelog: activates new prompt, deprecates old.
        """
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkill, MemorySkillChangelog

        async with AsyncSessionLocal() as session:
            # Get changelog
            cl = await session.get(MemorySkillChangelog, changelog_id)
            if not cl:
                return f"❌ Changelog {changelog_id} not found"
            if cl.status != "canary":
                return f"❌ Changelog {changelog_id} is '{cl.status}', not 'canary'"

            # Get the skill
            skill = await session.get(MemorySkill, cl.skill_id)
            if not skill:
                return f"❌ Skill {cl.skill_id} not found"

            # Apply the new prompt
            skill.prompt_template = cl.new_prompt
            skill.version += 1
            skill.is_base = False  # Now Designer-generated
            skill.updated_at = datetime.utcnow()

            # Mark changelog as approved
            cl.status = "approved"
            cl.reviewed_at = datetime.utcnow()

            await session.commit()

            if skill.source_file:
                from app.core.memory_skill_loader import MemorySkillLoader

                updated = MemorySkillLoader.update_skill_file(
                    filepath=skill.source_file,
                    new_prompt=skill.prompt_template,
                    new_version=skill.version,
                )
                if updated:
                    logger.info(f"Updated skill file: {skill.source_file}")
                else:
                    logger.warning(f"Failed to update skill file: {skill.source_file}")

            logger.info(f"✅ Approved changelog {changelog_id} for skill '{skill.name}' (v{skill.version})")
            return f"✅ Skill '{skill.name}' evolved to v{skill.version}"

    @classmethod
    async def reject_changelog(cls, changelog_id: int) -> str:
        """Admin rejects a canary changelog."""
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkillChangelog

        async with AsyncSessionLocal() as session:
            cl = await session.get(MemorySkillChangelog, changelog_id)
            if not cl:
                return f"❌ Changelog {changelog_id} not found"

            cl.status = "rejected"
            cl.reviewed_at = datetime.utcnow()
            await session.commit()

            logger.info(f"🚫 Rejected changelog {changelog_id}")
            return f"🚫 Changelog {changelog_id} rejected"

    @classmethod
    async def run_evolution_cycle(cls) -> str:
        """
        Main entry point: find underperforming skills and evolve them.
        Can be called by admin tool or scheduled cron.

        Returns summary string.
        """
        logger.info("🧬 Starting MemSkill evolution cycle...")

        underperforming = await cls.find_underperforming_skills()

        if not underperforming:
            msg = "✅ All skills healthy — no evolution needed."
            logger.info(msg)
            return msg

        results = []
        for skill in underperforming:
            result = await cls.evolve_skill(skill)
            if result:
                status = "✅ Canary passed" if result["canary_passed"] else "⚠️ Canary failed"
                results.append(f"- **{skill.name}**: {status} (changelog #{result['changelog_id']})")
            else:
                results.append(f"- **{skill.name}**: ❌ Evolution failed")

        summary = f"🧬 Evolution cycle complete. {len(underperforming)} skills analyzed:\n" + "\n".join(results)
        logger.info(summary)
        return summary

    @classmethod
    async def get_changelog_list(cls, limit: int = 20) -> List[dict]:
        """Get recent changelog entries for admin review."""
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkillChangelog

        async with AsyncSessionLocal() as session:
            stmt = select(MemorySkillChangelog).order_by(MemorySkillChangelog.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "skill_name": e.skill_name,
                "reason": e.reason[:100] + "..." if len(e.reason) > 100 else e.reason,
                "status": e.status,
                "created_at": str(e.created_at),
                "reviewed_at": str(e.reviewed_at) if e.reviewed_at else None,
            }
            for e in entries
        ]

    @classmethod
    async def record_feedback(cls, skill_id: int, is_positive: bool):
        """Record implicit feedback for a skill."""
        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkill

        if not skill_id:
            return

        async with AsyncSessionLocal() as session:
            skill = await session.get(MemorySkill, skill_id)
            if skill:
                if is_positive:
                    skill.positive_count += 1
                else:
                    skill.negative_count += 1
                skill.updated_at = datetime.utcnow()
                await session.commit()
                logger.debug(
                    f"Feedback for '{skill.name}': {'👍' if is_positive else '👎'} "
                    f"(+{skill.positive_count}/-{skill.negative_count})"
                )
