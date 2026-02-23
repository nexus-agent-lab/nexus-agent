import datetime
import json
import os
import platform
from typing import Optional

from app.models.user import User

# Default Fallback Soul (if no soul.md found)
DEFAULT_SOUL = """You are Nexus Agent, a secure and intelligent AI assistant.
Your primary mission is to assist the user while adhering to strict security and privacy protocols.
"""


class PromptBuilder:
    """
    Constructs the system prompt dynamically based on:
    1. Static Soul (System Prompt)
    2. User Context (Injected)
    3. Runtime Information
    """

    @staticmethod
    def build_system_prompt(
        user: Optional[User] = None, soul_content: Optional[str] = None, skill_summaries: Optional[str] = None
    ) -> str:
        # 1. Base Persona (Soul)
        base_prompt = soul_content if soul_content else DEFAULT_SOUL

        # 2. User Context Injection
        user_context = ""
        if user:
            # Format policy/preferences safely
            policy_str = "{}"
            if user.policy:
                try:
                    policy_str = json.dumps(user.policy, ensure_ascii=False)
                except Exception:
                    policy_str = str(user.policy)

            user_context = f"""
## User Context
- **User ID**: {user.username}
- **Language Preference**: {user.language}
- **Role**: {user.role}
- **Timezone**: {user.timezone or "Not set (Default CST)"}
- **Custom Notes**: {user.notes or "None"}
- **Policy/Preferences**: {policy_str}
"""

        # 3. Available Skills (L0 Summary)
        skill_info = ""
        if skill_summaries:
            skill_info = f"""
## Available Capabilities (L0)
Your current installation includes these skills:
{skill_summaries}

Note: More details will be injected automatically when you handle relevant tasks.
"""

        # 4. Runtime Information (Conditional, mostly noise for small models)
        runtime_info = ""
        if os.getenv("DEBUG_PROMPT", "false").lower() == "true":
            runtime_info = f"""
## Runtime Environment
- **OS**: {platform.system()} {platform.release()}
- **Time**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        # 5. Protocol Instructions (Slimmed down)
        protocol_instructions = """
## Response Protocols
- **Silent Protocol**: If no reply needed (e.g. "OK", emojis), output `<NO_REPLY>`.
- **Visibility**: Narrate complex steps (e.g. "🔍 Searching files...").
"""

        # 6. Assembly
        full_prompt = f"{base_prompt.strip()}\n{user_context}\n{skill_info}\n{runtime_info}\n{protocol_instructions}"

        return full_prompt
