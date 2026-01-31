"""add tools to drafts

Revision ID: 42d9e05e0639
Revises: 31c9a05e0528
Create Date: 2026-01-31 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "42d9e05e0639"
down_revision: Union[str, None] = "31c9a05e0528"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drafts", sa.Column("tools", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("drafts", "tools")
