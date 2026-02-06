import datetime
import json
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
    def build_system_prompt(user: Optional[User] = None, soul_content: Optional[str] = None) -> str:
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

        # 3. Runtime Information
        runtime_info = f"""
## Runtime Environment
- **OS**: {platform.system()} {platform.release()}
- **Time**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        # 4. Protocol Instructions
        protocol_instructions = """
## Response Protocols

### Silent Protocol (NO_REPLY)
If the user's message does NOT require a response (e.g., simple acknowledgements like "OK", "Got it", "Thanks", single emojis, or messages clearly not directed at you in a group chat), you MUST respond with ONLY the token:
`<NO_REPLY>`
Do NOT add any other text. This token will be intercepted and no message will be sent.

### Thinking Visibility
When performing complex tasks, briefly narrate your current step to keep the user informed:
- "🔍 Searching files..."
- "🧠 Analyzing code..."
- "🛠️ Running tool: {tool_name}..."
This helps users understand your progress.
"""

        # 5. Assembly
        full_prompt = f"{base_prompt.strip()}\n{user_context}\n{runtime_info}\n{protocol_instructions}"

        return full_prompt
