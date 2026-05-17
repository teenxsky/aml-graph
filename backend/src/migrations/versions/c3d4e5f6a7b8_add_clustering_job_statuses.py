"""Add CLUSTERING and HIERARCHICAL_LAYOUT to job_status enum

Revision ID: c3d4e5f6a7b8
Revises: b1de7453b950
Create Date: 2026-05-18 00:19:00.020429

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b1de7453b950'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'CLUSTERING' AFTER 'LAYOUT'")
        op.execute(
            "ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'HIERARCHICAL_LAYOUT' AFTER 'CLUSTERING'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
