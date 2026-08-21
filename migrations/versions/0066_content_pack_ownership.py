"""Per-pack compendium access, so a table can read some packs and not others.

Compendiums were all-or-nothing and GM-only, which made "let the players look up
spells but not monsters" impossible. Access becomes a property of each pack, per
role, in the shape the rest of the project already uses for actors, items and
journals: none / read / owner.

An absent row means ``none``. That is what keeps the migration silent: today no
player reaches a compendium, and after it none does either, until the GM opens
one deliberately.

Revision ID: 0066_content_pack_ownership
Revises: 0065_scene_lighting_mode
"""
from alembic import op
import sqlalchemy as sa

revision = "0066_content_pack_ownership"
down_revision = "0065_scene_lighting_mode"
branch_labels = None
depends_on = None

TABLE = "content_pack_ownership"


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table(TABLE):
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.String(64),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # A identidade de um pack é o PAR: um pack_id só é único dentro do seu
        # pacote, e é esse par que import_entry recebe.
        sa.Column("package_id", sa.String(191), nullable=False),
        sa.Column("pack_id", sa.String(191), nullable=False),
        sa.Column("role", sa.String(191), nullable=False),
        sa.Column("level", sa.String(191), nullable=False, server_default="none"),
        sa.Column("created_at", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.Integer, nullable=False),
        sa.UniqueConstraint(
            "campaign_id", "package_id", "pack_id", "role", name="uq_content_pack_ownership"
        ),
    )
    op.create_index(
        "idx_content_pack_ownership_campaign", TABLE, ["campaign_id", "package_id", "pack_id"]
    )


def downgrade() -> None:
    if _has_table(TABLE):
        op.drop_index("idx_content_pack_ownership_campaign", table_name=TABLE)
        op.drop_table(TABLE)
