"""Add campaign PDF annotations.

Revision ID: 0046_pdf_annotations
Revises: 0045_adaptive_raster_policy
"""

from alembic import op
import sqlalchemy as sa

revision = "0046_pdf_annotations"
down_revision = "0045_adaptive_raster_policy"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("pdf_annotations"):
        return
    op.create_table(
        "pdf_annotations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("campaign_id", sa.String(64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("library_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("region_json", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_pdf_annotations_document_page",
        "pdf_annotations",
        ["campaign_id", "document_id", "page", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_pdf_annotations_document_page", table_name="pdf_annotations")
    op.drop_table("pdf_annotations")
