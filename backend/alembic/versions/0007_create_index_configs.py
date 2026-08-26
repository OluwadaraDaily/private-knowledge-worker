"""Create index configurations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_create_index_configs"
down_revision = "0006_create_document_contents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("chunking_strategy", sa.String(50), nullable=False),
        sa.Column("chunk_size", sa.Integer),
        sa.Column("chunk_overlap", sa.Integer),
        sa.Column("embedding_model", sa.String(255), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer, nullable=False),
        sa.Column("retrieval_config", postgresql.JSONB),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "chunk_size IS NULL OR chunk_size > 0", name="ck_index_configs_chunk_size_positive"
        ),
        sa.CheckConstraint(
            "chunk_overlap IS NULL OR chunk_overlap >= 0",
            name="ck_index_configs_chunk_overlap_nonnegative",
        ),
        sa.CheckConstraint(
            "chunk_size IS NULL OR chunk_overlap IS NULL OR chunk_overlap < chunk_size",
            name="ck_index_configs_overlap_smaller_than_size",
        ),
        sa.UniqueConstraint("name", name="uq_index_configs_name"),
    )


def downgrade() -> None:
    op.drop_table("index_configs")
