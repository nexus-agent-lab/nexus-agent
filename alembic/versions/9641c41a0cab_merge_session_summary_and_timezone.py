"""merge_session_summary_and_timezone

Revision ID: 9641c41a0cab
Revises: 039acdafdad6, f9c2d3e4a5b6
Create Date: 2026-02-16 02:03:21.732299

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "9641c41a0cab"
down_revision: Union[str, Sequence[str], None] = ("039acdafdad6", "f9c2d3e4a5b6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
