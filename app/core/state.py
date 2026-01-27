from typing import Annotated, Sequence, TypedDict, Union, Optional
from typing import Annotated, Sequence, TypedDict, Union, Optional, List
from langchain_core.messages import BaseMessage
import operator
import uuid
from app.models.user import User

class AgentState(TypedDict):
    """The state of the agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user: Optional[User] 
    trace_id: uuid.UUID
    memories: Optional[List[str]] # Retrieved memories for context injection
