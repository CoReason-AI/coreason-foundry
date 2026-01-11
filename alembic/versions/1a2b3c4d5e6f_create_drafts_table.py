"""create drafts table

Revision ID: 1a2b3c4d5e6f
Revises: 759679af095f
Create Date: 2025-05-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "759679af095f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.String(), nullable=False),
        sa.Column("model_configuration", sa.JSON(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "version_number", name="uq_draft_project_version"),
    )
    op.create_index(op.f("ix_drafts_project_id"), "drafts", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_drafts_project_id"), table_name="drafts")
    op.drop_table("drafts")
