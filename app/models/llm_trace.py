from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


class LLMTrace(SQLModel, table=True):
    __tablename__ = "llm_trace"

    id: Optional[int] = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True)
    session_id: str = Field(index=True)
    user_id: Optional[int] = Field(default=None, index=True)

    model: str
    phase: str

    prompt_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    response_summary: Optional[str] = Field(default=None, sa_column=Column(Text))

    latency_ms: Optional[float] = None

    tools_bound: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    routing_queries: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    matched_tools: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
