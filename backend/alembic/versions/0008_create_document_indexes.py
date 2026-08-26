"""Create document index versions."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_create_document_indexes"
down_revision = "0007_create_index_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_indexes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["index_config_id"], ["index_configs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "document_id",
            "index_config_id",
            "content_hash",
            name="uq_document_indexes_content_version",
        ),
    )
    op.create_index("ix_document_indexes_document_id", "document_indexes", ["document_id"])
    op.create_index("ix_document_indexes_index_config_id", "document_indexes", ["index_config_id"])


def downgrade() -> None:
    op.drop_table("document_indexes")
