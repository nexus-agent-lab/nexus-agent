from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class WatchRule(SQLModel, table=True):
    __tablename__ = "watch_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    entity_pattern: str = Field(index=True)  # e.g. "sensor.phone_battery" or "binary_sensor.front_door"
    condition: str  # e.g. "< 2" or "== 'on'"

    action: str = Field(default="notify")  # "notify" | "agent_prompt"
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    cooldown_minutes: int = Field(default=60)
    last_triggered_at: Optional[datetime] = Field(default=None)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
