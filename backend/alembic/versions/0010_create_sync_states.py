"""Create synchronization states."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010_create_sync_states"
down_revision = "0009_create_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_page_token", sa.Text),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["google_connection_id"], ["google_connections.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("google_connection_id", name="uq_sync_states_connection"),
    )
    op.create_index("ix_sync_states_user_id", "sync_states", ["user_id"])
    op.create_index("ix_sync_states_google_connection_id", "sync_states", ["google_connection_id"])


def downgrade() -> None:
    op.drop_table("sync_states")
