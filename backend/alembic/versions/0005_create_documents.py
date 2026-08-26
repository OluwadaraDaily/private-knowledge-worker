"""Create documents."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_create_documents"
down_revision = "0004_create_indexed_folders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_file_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("web_url", sa.String(2048)),
        sa.Column("google_created_at", sa.DateTime(timezone=True)),
        sa.Column("google_modified_at", sa.DateTime(timezone=True)),
        sa.Column("owned_by_me", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("document_type", sa.String(100)),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "google_file_id", name="uq_documents_user_file"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_user_modified_at", "documents", ["user_id", "google_modified_at"])
    op.create_index("ix_documents_user_document_type", "documents", ["user_id", "document_type"])


def downgrade() -> None:
    op.drop_table("documents")
