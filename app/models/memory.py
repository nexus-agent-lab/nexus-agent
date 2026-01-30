import os
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, SQLModel, Text

# Support both OpenAI (1536) and local models (512 for bge-small-zh)
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "512"))


class Memory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    content: str = Field(sa_column=Column(Text, nullable=False))

    # Dimension controlled by EMBEDDING_DIMENSION env var (default: 512 for bge-small-zh)
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIMENSION)))

    # profile | reflexion | knowledge
    memory_type: str = Field(index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)


# Note: HNSW Index will be created via Alembic migration manually
# to ensure it's applied correctly with postgres-specific syntax.
