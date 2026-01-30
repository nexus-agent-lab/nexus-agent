import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Field, SQLModel


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trace_id: uuid.UUID = Field(index=True)  # Correlates multiple steps in one request
    user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", nullable=True
    )  # Nullable for unauthorized attempts

    action: str = Field(index=True)  # e.g., 'tool_execution', 'unauthorized_access'
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    status: str = Field(default="PENDING")  # PENDING, SUCCESS, FAILURE
    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
