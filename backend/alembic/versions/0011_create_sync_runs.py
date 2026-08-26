"""Create synchronization runs."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011_create_sync_runs"
down_revision = "0010_create_sync_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("sync_type", sa.String(30), nullable=False),
        sa.Column("documents_discovered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("documents_ingested", sa.Integer, nullable=False, server_default="0"),
        sa.Column("documents_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("documents_discovered >= 0", name="ck_sync_runs_discovered_nonnegative"),
        sa.CheckConstraint("documents_ingested >= 0", name="ck_sync_runs_ingested_nonnegative"),
        sa.CheckConstraint("documents_failed >= 0", name="ck_sync_runs_failed_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sync_runs_user_id", "sync_runs", ["user_id"])


def downgrade() -> None:
    op.drop_table("sync_runs")
