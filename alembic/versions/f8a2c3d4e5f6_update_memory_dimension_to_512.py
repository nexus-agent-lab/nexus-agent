"""update memory dimension to 512

Revision ID: f8a2c3d4e5f6
Revises: d7485beb84b7
Create Date: 2026-01-27 09:42:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f8a2c3d4e5f6"
down_revision = "d7485beb84b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing HNSW index if it exists
    op.execute("DROP INDEX IF EXISTS memory_embedding_hnsw_idx")

    # Alter column to use 512 dimensions (for bge-small-zh-v1.5)
    # Note: This will clear existing data in the embedding column
    op.execute("ALTER TABLE memory ALTER COLUMN embedding TYPE vector(512)")

    # Recreate HNSW index with new dimension
    op.execute("""
        CREATE INDEX memory_embedding_hnsw_idx
        ON memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop 512-dimension index
    op.execute("DROP INDEX IF EXISTS memory_embedding_hnsw_idx")

    # Revert to 1536 dimensions
    op.execute("ALTER TABLE memory ALTER COLUMN embedding TYPE vector(1536)")

    # Recreate index with old dimension
    op.execute("""
        CREATE INDEX memory_embedding_hnsw_idx
        ON memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
