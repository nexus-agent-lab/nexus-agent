from typing import Optional

from sqlmodel import Field, SQLModel


class ToolDefinition(SQLModel, table=True):
    __tablename__ = "tools"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    required_role: str = Field(default="user")
    context_id: Optional[int] = Field(default=None, foreign_key="context.id")
