from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ScheduledTask(SQLModel, table=True):
    __tablename__ = "scheduled_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")

    # Target for the notification
    channel: str = Field(index=True)  # 'telegram', 'feishu', 'web'
    channel_id: str = Field(index=True) # Chat ID or User ID

    # Schedule
    cron_expr: str = Field() # e.g. "0 9 * * *"
    description: str = Field() # User-friendly description

    # Task Details
    # type can be 'prompt' (triggers agent) or 'notification' (just sends text)
    task_type: str = Field(default="prompt")
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # State
    enabled: bool = Field(default=True)
    last_run: Optional[datetime] = Field(default=None)
    next_run: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata for tracking
    meta: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
