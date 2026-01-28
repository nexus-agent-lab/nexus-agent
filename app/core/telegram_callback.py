from typing import Any, Dict, List

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.interfaces.telegram import broadcast_message


class TelegramProgressCallback(BaseCallbackHandler):
    """Callback handler that syncs agent progress to Telegram."""

    def __init__(self):
        super().__init__()

    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Run when LLM starts running."""
        # await broadcast_message("🤖 Thinking...")
        pass

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Run when tool starts running."""
        tool_name = serialized.get("name") or "Tool"
        await broadcast_message(f"🔧 **Executing Tool**: `{tool_name}`\nArgs: `{input_str}`")

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        # Truncate output if too long
        display_output = output[:200] + "..." if len(output) > 200 else output
        await broadcast_message(f"✅ **Tool Result**:\n`{display_output}`")

    async def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Run when tool errors."""
        await broadcast_message(f"❌ **Tool Error**:\n{str(error)}")

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        # Typically the final response is handled by the route, but if we want chunks...
        # Here we just acknowledge completion of a thought step.
        pass
