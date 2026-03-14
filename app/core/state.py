import operator
import uuid
from typing import Annotated, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage

from app.core.result_classifier import ResultClassification
from app.core.tool_executor import ToolExecutionOutcome
from app.models.user import User


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    user: Optional[User]
    trace_id: uuid.UUID
    memories: Optional[List[str]]  # Retrieved memories for context injection
    session_id: Optional[int]  # Current persistent session ID
    context: str = "home"  # Default context (home/work)
    intent_class: Optional[str] = None  # Fast intent gate classification
    route_confidence: Optional[float] = None  # Fast routing confidence score
    selected_worker: Optional[str] = None  # Current preferred worker
    candidate_workers: Optional[List[str]] = None  # Worker candidates from fast routing
    execution_mode: Optional[str] = None  # Dispatcher-selected execution mode
    next_execution_hint: Optional[str] = None  # Worker-suggested next phase such as verify/discover/ask_user
    verify_context: Optional[dict[str, str]] = None  # Normalized verification context for follow-up passes
    selected_skill: Optional[str] = None  # Preferred skill selected for this turn
    candidate_skills: Optional[List[str]] = None  # Skill candidates from fast routing
    reflexions: Optional[List[str]] = []  # Stored self-reflections
    retry_count: int = 0  # Track retries for current step
    search_count: int = 0  # Track tool search retries (Tier 2)
    attempts_by_worker: Optional[dict[str, int]] = None  # Count retry-relevant failures by worker
    attempts_by_tool: Optional[dict[str, int]] = None  # Count attempts by normalized tool fingerprint
    blocked_fingerprints: Optional[List[str]] = None  # Fingerprints blocked after repeated failures
    active_tool_names: Optional[List[str]] = None  # Explicitly selected tools for current turn
    intent_queries: Optional[List[str]] = None  # Cached fast-brain decomposition for the current user turn
    execution_history: Optional[List[dict]] = None  # Normalized per-tool execution records for later analysis
    last_outcome: Optional[ToolExecutionOutcome] = None  # Last normalized tool execution outcome
    last_classification: Optional[ResultClassification] = None  # Last normalized result classification
    verification_status: Optional[str] = None  # Reviewer-facing status: passed/required/pending/failed
    llm_call_count: int = 0  # Count main LLM calls in the current graph run
    tool_call_count: int = 0  # Count tool invocations in the current graph run
