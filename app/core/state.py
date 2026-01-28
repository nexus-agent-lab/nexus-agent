import operator
import uuid
from typing import Annotated, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage

from app.models.user import User


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    user: Optional[User]
    trace_id: uuid.UUID
    memories: Optional[List[str]]  # Retrieved memories for context injection
    session_id: Optional[int]  # Current persistent session ID
    context: str = "home"  # Default context (home/work)
    reflexions: Optional[List[str]] = []  # Stored self-reflections
    retry_count: int = 0  # Track retries for current step
