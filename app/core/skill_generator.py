"""
Skill Generator - AI-powered generation of skill cards for MCP tools.
"""

import json
import logging
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

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

    @classmethod
    def get_llm(cls):
        """
        Get the configured LLM for skill generation.

        Returns:
            LangChain LLM instance
        """
        provider = os.getenv("SKILL_GEN_PROVIDER", "local")

        if provider == "openai":
            model = os.getenv("SKILL_GEN_MODEL", "gpt-4o")
            api_key = os.getenv("SKILL_GEN_API_KEY") or os.getenv("OPENAI_API_KEY")
            return ChatOpenAI(model=model, api_key=api_key, temperature=0.3)

        elif provider == "anthropic":
            if not HAS_ANTHROPIC:
                logger.warning("langchain-anthropic not installed, falling back to local LLM")
                from app.core.agent import get_llm

                return get_llm()

            model = os.getenv("SKILL_GEN_MODEL", "claude-3-5-sonnet-20241022")
            api_key = os.getenv("SKILL_GEN_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            return ChatAnthropic(model=model, api_key=api_key, temperature=0.3)

        else:
            # Use local LLM (same as agent)
            from app.core.agent import get_llm

            return get_llm()

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

        response = await llm.ainvoke([HumanMessage(content=prompt)])
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
