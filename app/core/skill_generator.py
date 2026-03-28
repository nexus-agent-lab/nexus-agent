"""
Skill Generator - AI-powered generation of skill cards for MCP tools.
"""

import json
import logging
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.llm_utils import ainvoke_with_backoff, get_llm_client

try:
    from langchain_anthropic import ChatAnthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)


class SkillGenerator:
    """Generate skill cards using configurable LLM."""

    GENERATION_PROMPT_TEMPLATE = """You are an expert at creating skill cards for AI agents.

Given the following MCP server tools, generate a comprehensive Skill Card in Markdown format.

**MCP Server**: {mcp_name}
**Tools**:
{tools_json}

**Requirements**:
1. Use the template format with YAML frontmatter
2. Include:
   - Core Capabilities (3-5 bullet points)
   - Critical Rules (MUST FOLLOW) - especially data handling patterns
   - 2-3 Few-Shot Examples with step-by-step reasoning
   - Tool Usage Patterns for each tool
   - Best Practices
   - Common Mistakes

3. Focus on:
   - When to use each tool
   - How to chain tools together
   - Data handling (especially large responses)
   - Error cases and safety checks

4. Write in Chinese for user-facing content, English for code examples

5. Be specific and actionable - this will guide a local LLM (GLM-4.7-Flash)

Output ONLY the Markdown content, no additional commentary.
"""

    ROUTING_EXAMPLES_PROMPT_TEMPLATE = """You are generating semantic routing examples for an AI agent skill.

Your job is to output realistic user requests that should route to this skill.

Skill name: {skill_name}
Skill description: {skill_description}
Skill domain: {domain}
Tool summaries:
{tool_summaries}
Constraints:
{constraints}

Requirements:
1. Output ONLY a JSON array of strings.
2. Generate exactly {count} user utterances.
3. Each utterance must sound like a real user request, not documentation.
4. Do NOT mention tool names, API names, function names, parameters, MCP, or implementation details.
5. Do NOT invent permissions or capabilities that are not supported.
6. Prefer short, natural phrasing.
7. Cover direct asks, result-oriented asks, and colloquial variants.
8. If the skill is read-only or public-only, do not generate login, upload, payment, submit, or account-changing requests.
9. Use the same language as the skill context when possible, and prefer Chinese if the description is Chinese.
"""

    @classmethod
    def get_llm(cls):
        """
        Get the configured LLM for skill generation.

        Returns:
            LangChain LLM instance
        """
        dedicated_base_url = os.getenv("SKILL_GEN_BASE_URL")
        dedicated_model = os.getenv("SKILL_GEN_MODEL")
        dedicated_api_key = os.getenv("SKILL_GEN_API_KEY")

        # Preferred path: dedicated OpenAI-compatible endpoint for skill generation.
        # Any missing value falls back to the main LLM configuration.
        if dedicated_base_url or dedicated_model or dedicated_api_key:
            return get_llm_client(
                temperature=0.3,
                base_url=dedicated_base_url or os.getenv("LLM_BASE_URL"),
                model_name=dedicated_model or os.getenv("LLM_MODEL", "gpt-4o"),
                api_key=dedicated_api_key or os.getenv("LLM_API_KEY"),
            )

        provider = os.getenv("SKILL_GEN_PROVIDER", "local")

        if provider == "openai":
            model = os.getenv("SKILL_GEN_MODEL", "gpt-4o")
            api_key = os.getenv("SKILL_GEN_API_KEY") or os.getenv("OPENAI_API_KEY")
            return ChatOpenAI(model=model, api_key=api_key, temperature=0.3)

        elif provider == "anthropic":
            if not HAS_ANTHROPIC:
                logger.warning("langchain-anthropic not installed, falling back to local LLM")
                return get_llm_client(temperature=0.3)

            model = os.getenv("SKILL_GEN_MODEL", "claude-3-5-sonnet-20241022")
            api_key = os.getenv("SKILL_GEN_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            return ChatAnthropic(model=model, api_key=api_key, temperature=0.3)

        else:
            # Use local LLM (same as agent)
            return get_llm_client(temperature=0.3)

    @classmethod
    async def generate_skill_card(cls, mcp_name: str, tools: List[Dict[str, Any]], domain: str = "unknown") -> str:
        """
        Generate a skill card for an MCP server using AI.

        Args:
            mcp_name: Name of the MCP server
            tools: List of tool definitions (from MCP)
            domain: Domain category (smart_home, communication, etc.)

        Returns:
            Generated skill card content in Markdown
        """
        # Format tools for prompt
        tools_json = json.dumps(tools, indent=2, ensure_ascii=False)

        # Build prompt
        prompt = cls.GENERATION_PROMPT_TEMPLATE.format(mcp_name=mcp_name, tools_json=tools_json)

        # Call LLM
        llm = cls.get_llm()
        logger.info(f"Generating skill card for {mcp_name} using {llm.__class__.__name__}")

        response = await ainvoke_with_backoff(
            llm,
            [HumanMessage(content=prompt)],
            operation_name=f"skill_generator.card:{mcp_name}",
        )
        skill_content = response.content

        # Ensure frontmatter exists
        if not skill_content.startswith("---"):
            # Add basic frontmatter
            frontmatter = f"""---
name: {mcp_name.title()}
domain: {domain}
priority: medium
mcp_server: {mcp_name}
---

"""
            skill_content = frontmatter + skill_content

        logger.info(f"Successfully generated skill card for {mcp_name}")
        return skill_content

    @classmethod
    async def generate_routing_examples(
        cls,
        skill_name: str,
        skill_description: str,
        tools: List[Dict[str, Any]],
        domain: str = "unknown",
        constraints: List[str] | None = None,
        count: int = 12,
    ) -> List[str]:
        """Generate natural-language routing examples for a skill."""
        tool_summaries = (
            "\n".join(f"- {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}" for tool in tools)
            or "- (no tools provided)"
        )
        constraint_text = "\n".join(f"- {item}" for item in (constraints or [])) or "- none"
        prompt = cls.ROUTING_EXAMPLES_PROMPT_TEMPLATE.format(
            skill_name=skill_name,
            skill_description=skill_description,
            domain=domain,
            tool_summaries=tool_summaries,
            constraints=constraint_text,
            count=count,
        )

        llm = cls.get_llm()
        logger.info("Generating routing examples for %s using %s", skill_name, llm.__class__.__name__)

        response = await ainvoke_with_backoff(
            llm,
            [HumanMessage(content=prompt)],
            operation_name=f"skill_generator.routing_examples:{skill_name}",
        )
        content = response.content if isinstance(response.content, str) else str(response.content)

        try:
            parsed = json.loads(content)
            if not isinstance(parsed, list):
                raise ValueError("Routing example response is not a JSON array")
            cleaned = [str(item).strip() for item in parsed if str(item).strip()]
            return cleaned[:count]
        except Exception as e:
            logger.error("Failed to parse routing examples for %s: %s", skill_name, e)
            raise ValueError(f"Failed to parse routing examples: {e}") from e

    @classmethod
    def _get_fallback_template(cls, mcp_name: str, tools: List[Dict[str, Any]], domain: str) -> str:
        """
        Generate a basic skill card template when AI generation fails.

        Args:
            mcp_name: Name of the MCP server
            tools: List of tool definitions
            domain: Domain category

        Returns:
            Basic skill card template
        """
        tool_list = "\n".join(
            [f"- {t.get('name', 'unknown')}: {t.get('description', 'No description')}" for t in tools]
        )

        return f"""---
name: {mcp_name.title()}
domain: {domain}
priority: medium
mcp_server: {mcp_name}
---

# {mcp_name.title()} Skill

## 🎯 Core Capabilities
{tool_list}

## ⚠️ Critical Rules (MUST FOLLOW)

1. **Rule 1**: Add specific rules for this MCP
2. **Data Handling**: How to handle large responses

## 📝 Examples (Few-Shot Learning)

### Example 1: Basic Usage
**User**: "Example request"

**Correct Flow**:
1. Step 1: Tool call
2. Step 2: Process result
3. Step 3: Respond

## 🔧 Tool Usage Patterns

(Add tool-specific patterns here)

## 💡 Best Practices

- Practice 1: Add specific recommendations
- Practice 2: Performance tips

## 🚫 Common Mistakes

1. **Mistake**: Description
   - **Fix**: Solution
"""
