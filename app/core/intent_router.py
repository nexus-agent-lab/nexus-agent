import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm_utils import get_llm_client

logger = logging.getLogger(__name__)


class IntentRouter:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(IntentRouter, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # glm4.7-flash works better with slight temperature (0.1)
        self.llm = get_llm_client(temperature=0.1)
        self.system_prompt = (
            "You are an intent decomposition engine. "
            "Decompose the user's query into a JSON list of search strings or sub-intents. "
            "Return ONLY JSON array. Do not include markdown formatting, explanations, or any other text."
        )
        self._initialized = True

    async def decompose(self, user_message: str) -> List[str]:
        """
        Decomposes a user query into a JSON list of search strings using a lightweight LLM call.
        No tools, no history.
        Falls back to [user_message] on any error.
        """
        try:
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=user_message)]
            response = await self.llm.ainvoke(messages)

            content = response.content.strip()

            # Robust JSON parsing: strip markdown fences
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]

            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()

            result = json.loads(content)

            if isinstance(result, list) and all(isinstance(i, str) for i in result):
                return result
            else:
                logger.warning(f"IntentRouter received invalid JSON structure: {result}")
                return [user_message]

        except json.JSONDecodeError as e:
            content_str = response.content if "response" in locals() else "Unknown"
            logger.error(f"IntentRouter JSON parsing error: {e}. Content: {content_str}")
            return [user_message]
        except Exception as e:
            logger.error(f"IntentRouter error during decomposition: {e}")
            return [user_message]
