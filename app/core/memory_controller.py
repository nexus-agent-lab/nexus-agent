import logging
import os
from typing import Dict, List, Optional

from app.core.llm_utils import get_llm_client

logger = logging.getLogger("nexus.memory_controller")


class MemoryController:
    """
    Controller for selecting Memory Skills based on context.
    Uses keyword matching first, falls back to LLM for ambiguous cases.
    """

    @classmethod
    async def select_skill(
        cls, context: str, skill_type: str = "encoding", available_skills: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Select the most appropriate Memory Skill for the given context.
        """
        from app.core.memory_skill_loader import MemorySkillLoader

        if available_skills is None:
            available_skills = MemorySkillLoader.get_skills_by_type(skill_type)

        if not available_skills:
            logger.warning(f"No {skill_type} skills available")
            return None

        # Stage 1: Keyword matching (fast, no LLM call)
        matched_skill = cls._keyword_match(context, available_skills)
        if matched_skill:
            logger.debug(f"Keyword matched skill: {matched_skill['name']}")
            return matched_skill

        # Stage 2: LLM selection (slower, more accurate)
        if os.getenv("MEMSKILL_USE_LLM_SELECTION", "false").lower() == "true":
            llm_skill = await cls._llm_select(context, available_skills)
            if llm_skill:
                return llm_skill

        # Default: return first skill of the type
        default_skill = available_skills[0]
        logger.debug(f"Using default skill: {default_skill['name']}")
        return default_skill

    @classmethod
    def _keyword_match(cls, context: str, skills: List[Dict]) -> Optional[Dict]:
        """
        Match context against skill intent_keywords.
        Returns the skill with the most keyword matches.
        """
        context_lower = context.lower()
        best_match = None
        best_score = 0

        for skill in skills:
            keywords = skill.get("intent_keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in context_lower)
            if score > best_score:
                best_score = score
                best_match = skill

        return best_match if best_score > 0 else None

    @classmethod
    async def _llm_select(cls, context: str, skills: List[Dict]) -> Optional[Dict]:
        """
        Use LLM to select the best skill when keyword matching is inconclusive.
        """
        try:
            # Use LLM via central utility
            llm = get_llm_client()

            skills_desc = "\n".join([f"- {s['name']}: {s['description']}" for s in skills])

            prompt = f"""Select the most appropriate memory skill for this context.

Context: {context[:500]}

Available skills:
{skills_desc}

Return ONLY the skill name, nothing else."""

            response = await llm.ainvoke(prompt)
            skill_name = response.content.strip()

            # Find matching skill
            for skill in skills:
                if skill["name"].lower() == skill_name.lower():
                    logger.info(f"LLM selected skill: {skill_name}")
                    return skill

        except Exception as e:
            logger.warning(f"LLM skill selection failed: {e}")

        return None

    @classmethod
    def prepare_context(cls, raw_input: str, max_len: int = 1000) -> str:
        """
        Smart context preparation with Head + Tail strategy.
        Avoids losing important information from mechanical truncation.
        """
        if len(raw_input) <= max_len:
            return raw_input

        # Head + Tail strategy
        head_len = max_len // 2
        tail_len = max_len // 2

        head = raw_input[:head_len]
        tail = raw_input[-tail_len:]

        return f"{head}\n...[truncated {len(raw_input) - max_len} chars]...\n{tail}"
