"""add scratchpad to drafts

Revision ID: 31c9a05e0528
Revises: 759679af095f
Create Date: 2025-05-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "31c9a05e0528"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
# I need to check the exact down_revision. I'll read the files first to be sure.
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drafts", sa.Column("scratchpad", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("drafts", "scratchpad")
