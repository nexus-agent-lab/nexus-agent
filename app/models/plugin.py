from typing import TYPE_CHECKING, List, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.secret import Secret


class Plugin(SQLModel, table=True):
    """
    Plugin model representing an extensible module or integration.
    """

    __tablename__ = "plugin"

    id: Optional[int] = Field(default=None, primary_key=True)
    manifest_id: Optional[str] = Field(default=None)
    name: str = Field(index=True, description="Name of the plugin")
    type: str = Field(description="Type or category of the plugin")
    source_url: str = Field(description="Source URL or repository for the plugin")
    status: str = Field(default="active", index=True, description="Current status of the plugin")
    required_role: str = Field(default="user")
    config: dict = Field(default={}, sa_column=Column(JSON), description="Configuration for the plugin")

    # Relationships
    secrets: List["Secret"] = Relationship(back_populates="plugin")
