"""add_user_timezone_and_notes

Revision ID: 039acdafdad6
Revises: f8a2c3d4e5f6
Create Date: 2026-02-06 14:00:15.388641

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "039acdafdad6"
down_revision: Union[str, Sequence[str], None] = "f8a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("timezone", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("user", sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "notes")
    op.drop_column("user", "timezone")
