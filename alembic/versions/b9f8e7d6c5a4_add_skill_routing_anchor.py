"""add skill_routing_anchor

Revision ID: b9f8e7d6c5a4
Revises: a42cd2621fdf
Create Date: 2026-03-28 10:05:00.000000

"""

import os
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9f8e7d6c5a4"
down_revision: Union[str, Sequence[str], None] = "a42cd2621fdf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(bind, constraint_name: str) -> bool:
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = :name LIMIT 1"
        ),
        {"name": constraint_name},
    ).scalar()
    return bool(result)


def _index_exists(bind, index_name: str) -> bool:
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_class WHERE relkind = 'i' AND relname = :name LIMIT 1"
        ),
        {"name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if "skill_routing_anchor" not in inspector.get_table_names():
        op.create_table(
            "skill_routing_anchor",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("skill_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("anchor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="skill_frontmatter"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("embedding", Vector(embedding_dimension), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # Deduplicate pre-existing rows created before the unique constraint existed.
    op.execute(
        """
        DELETE FROM skill_routing_anchor a
        USING skill_routing_anchor b
        WHERE a.id > b.id
          AND a.skill_name = b.skill_name
          AND a.anchor_type = b.anchor_type
          AND a.text = b.text
        """
    )

    if not _constraint_exists(bind, "uq_skill_anchor_identity"):
        op.create_unique_constraint(
            "uq_skill_anchor_identity",
            "skill_routing_anchor",
            ["skill_name", "anchor_type", "text"],
        )

    indexes = {item["name"] for item in inspector.get_indexes("skill_routing_anchor")}
    expected_indexes = {
        "ix_skill_routing_anchor_skill_name": ["skill_name"],
        "ix_skill_routing_anchor_anchor_type": ["anchor_type"],
        "ix_skill_routing_anchor_language": ["language"],
        "ix_skill_routing_anchor_source": ["source"],
        "ix_skill_routing_anchor_enabled": ["enabled"],
    }
    for index_name, columns in expected_indexes.items():
        if index_name not in indexes and not _index_exists(bind, index_name):
            op.create_index(index_name, "skill_routing_anchor", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "skill_routing_anchor" not in inspector.get_table_names():
        return

    for index_name in [
        "ix_skill_routing_anchor_enabled",
        "ix_skill_routing_anchor_source",
        "ix_skill_routing_anchor_language",
        "ix_skill_routing_anchor_anchor_type",
        "ix_skill_routing_anchor_skill_name",
    ]:
        existing_indexes = {item["name"] for item in inspector.get_indexes("skill_routing_anchor")}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="skill_routing_anchor")

    unique_constraints = {item["name"] for item in inspector.get_unique_constraints("skill_routing_anchor")}
    if "uq_skill_anchor_identity" in unique_constraints:
        op.drop_constraint("uq_skill_anchor_identity", "skill_routing_anchor", type_="unique")

    op.drop_table("skill_routing_anchor")
