from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.plugin import Plugin


class SecretScope(str, Enum):
    global_scope = "global"
    user_scope = "user"


class Secret(SQLModel, table=True):
    """
    Secret model for storing encrypted sensitive data such as API keys.
    """

    __tablename__ = "secret"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, description="The key or name of the secret")
    encrypted_value: str = Field(description="The encrypted value of the secret")
    scope: SecretScope = Field(default=SecretScope.user_scope, description="Scope of the secret")

    owner_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE")),
        description="ID of the user who owns this secret (if scope is user)",
    )
    plugin_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("plugin.id", ondelete="CASCADE")),
        description="ID of the plugin this secret belongs to",
    )

    plugin: Optional["Plugin"] = Relationship(back_populates="secrets")
