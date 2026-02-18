from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    api_key: str = Field(unique=True, index=True)
    role: str = Field(default="user")  # 'admin', 'user', 'guest'
    language: str = Field(default="en")  # 'en', 'zh'
    timezone: Optional[str] = Field(default=None)  # e.g. 'Asia/Shanghai'
    notes: Optional[str] = Field(default=None)  # Personal notes/context

    # Granular Permission Policy
    # Example: {"allow_domains": ["clock"], "deny_tools": ["system_shell"]}
    policy: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    identities: list["UserIdentity"] = Relationship(back_populates="user")


class UserIdentity(SQLModel, table=True):
    __tablename__ = "user_identities"

    id: Optional[int] = Field(default=None, primary_key=True)
    # user_id: int = Field(foreign_key="user.id")
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE")))

    provider: str = Field(index=True)  # 'telegram', 'feishu', 'dingtalk'
    provider_user_id: str = Field(index=True)  # '12345678', 'ou_xxxx'
    provider_username: Optional[str] = Field(default=None)  # '@mike'

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = Field(default=None)

    user: User = Relationship(back_populates="identities")


class Context(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)  # e.g. "home", "work"
    description: Optional[str] = None
