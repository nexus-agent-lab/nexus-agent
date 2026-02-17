"""add skill_id to memory table

Revision ID: a1b2c3d4e5f7
Revises: 9641c41a0cab
Create Date: 2026-02-16 10:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "9641c41a0cab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory", sa.Column("skill_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_memory_skill_id", "memory", "memoryskill", ["skill_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_memory_skill_id", "memory", type_="foreignkey")
    op.drop_column("memory", "skill_id")
