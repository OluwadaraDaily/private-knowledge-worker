"""Create indexed folders."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_create_indexed_folders"
down_revision = "0003_create_google_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indexed_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_folder_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(1024), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "google_folder_id", name="uq_indexed_folders_user_folder"),
    )
    op.create_index("ix_indexed_folders_user_id", "indexed_folders", ["user_id"])


def downgrade() -> None:
    op.drop_table("indexed_folders")
