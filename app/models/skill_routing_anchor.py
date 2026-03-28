import os
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))


class SkillRoutingAnchor(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("skill_name", "anchor_type", "text", name="uq_skill_anchor_identity"),)

    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    skill_name: str = Field(index=True)
    anchor_type: str = Field(index=True)
    language: str = Field(default="auto", index=True)
    text: str = Field(sa_column=Column(Text, nullable=False))
    weight: float = Field(default=1.0, sa_column=Column(Float, nullable=False, default=1.0))
    source: str = Field(default="skill_frontmatter", index=True)
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True, index=True))
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIMENSION)))
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, default=datetime.utcnow))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
