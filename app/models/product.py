from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ProductSuggestion(SQLModel, table=True):
    __tablename__ = "product_suggestions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    content: str
    category: str = Field(default="feature")  # feature, bug, improvement
    status: str = Field(default="pending")  # pending, approved, rejected, implemented
    priority: str = Field(default="medium")  # low, medium, high
    votes: int = Field(default=0)
    tags: str = Field(default="")  # Comma-separated tags

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
