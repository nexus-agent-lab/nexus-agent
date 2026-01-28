from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    api_key: str = Field(unique=True, index=True)
    role: str = Field(default="user")  # 'admin' or 'user'


class Context(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)  # e.g. "home", "work"
    description: Optional[str] = None
