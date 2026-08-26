"""Create document chunks."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_create_chunks"
down_revision = "0008_create_document_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_index_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_number", sa.Integer, nullable=False),
        sa.Column("heading", sa.Text),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("embedding", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("chunk_number >= 0", name="ck_chunks_number_nonnegative"),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count > 0", name="ck_chunks_token_count_positive"
        ),
        sa.ForeignKeyConstraint(["document_index_id"], ["document_indexes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_index_id", "chunk_number", name="uq_chunks_index_number"),
    )
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector USING embedding::vector")
    op.create_index("ix_chunks_document_index_id", "chunks", ["document_index_id"])


def downgrade() -> None:
    op.drop_table("chunks")
