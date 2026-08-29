"""Add document enrichment fields."""

import sqlalchemy as sa
from alembic import op

revision = "0013_add_document_enrichment"
down_revision = "0012_create_oauth_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("topics", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("documents", sa.Column("summary", sa.Text()))
    op.add_column("documents", sa.Column("classification_method", sa.String(100)))
    op.add_column("documents", sa.Column("classified_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("documents", "classified_at")
    op.drop_column("documents", "classification_method")
    op.drop_column("documents", "summary")
    op.drop_column("documents", "topics")
