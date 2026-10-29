"""Create workflow review records linked to documents."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_create_workflow_reviews"
down_revision: Union[str, None] = "0001_create_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column("structured_result", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("reviewer_decision", sa.String(length=32), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected', 'failed')",
            name="ck_workflow_reviews_status",
        ),
        sa.CheckConstraint("workflow_type IN ('summary')", name="ck_workflow_reviews_type"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_reviews_document_id", "workflow_reviews", ["document_id"])
    op.create_index("ix_workflow_reviews_status", "workflow_reviews", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_reviews_status", table_name="workflow_reviews")
    op.drop_index("ix_workflow_reviews_document_id", table_name="workflow_reviews")
    op.drop_table("workflow_reviews")
