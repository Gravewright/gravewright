"""cards system tables

Revision ID: 0009_cards_system
Revises: 0008_package_manifest_integrity
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_cards_system"
down_revision = "0008_package_manifest_integrity"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("card_deck_definitions"):
        op.create_table(
            "card_deck_definitions",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
            sa.Column("package_id", ID, nullable=True),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("scope", STR, nullable=False),
            sa.Column("name", STR, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("default_back_asset_id", ID, nullable=True),
            sa.Column("editable", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
            sa.UniqueConstraint("card_instance_id"),
        )
        op.create_index("idx_card_deck_definitions_campaign", "card_deck_definitions", ["campaign_id"])
        op.create_index("idx_card_deck_definitions_package", "card_deck_definitions", ["package_id"])
        op.create_index("idx_card_deck_definitions_owner", "card_deck_definitions", ["owner_user_id"])
        op.create_index("idx_card_deck_definitions_scope", "card_deck_definitions", ["scope"])

    if not _has_table("card_definitions"):
        op.create_table(
            "card_definitions",
            sa.Column("id", ID, primary_key=True),
            sa.Column("deck_definition_id", ID, sa.ForeignKey("card_deck_definitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", STR, nullable=False),
            sa.Column("subtitle", STR, nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("front_asset_id", ID, nullable=False),
            sa.Column("back_asset_id", ID, nullable=True),
            sa.Column("tags_json", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("sort_key", STR, nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_card_definitions_deck", "card_definitions", ["deck_definition_id"])

    if not _has_table("card_deck_instances"):
        op.create_table(
            "card_deck_instances",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("room_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
            sa.Column("deck_definition_id", ID, sa.ForeignKey("card_deck_definitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", STR, nullable=False),
            sa.Column("active", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_card_deck_instances_campaign", "card_deck_instances", ["campaign_id"])
        op.create_index("idx_card_deck_instances_definition", "card_deck_instances", ["deck_definition_id"])

    if not _has_table("card_piles"):
        op.create_table(
            "card_piles",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("deck_instance_id", ID, sa.ForeignKey("card_deck_instances.id", ondelete="CASCADE"), nullable=True),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("kind", STR, nullable=False),
            sa.Column("name", STR, nullable=False),
            sa.Column("visibility", STR, nullable=False),
            sa.Column("ordered", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_card_piles_campaign", "card_piles", ["campaign_id"])
        op.create_index("idx_card_piles_deck", "card_piles", ["deck_instance_id", "kind"])
        op.create_index("idx_card_piles_owner", "card_piles", ["owner_user_id"])

    if not _has_table("card_instances"):
        op.create_table(
            "card_instances",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("deck_instance_id", ID, sa.ForeignKey("card_deck_instances.id", ondelete="CASCADE"), nullable=False),
            sa.Column("card_definition_id", ID, sa.ForeignKey("card_definitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("current_pile_id", ID, sa.ForeignKey("card_piles.id", ondelete="SET NULL"), nullable=True),
            sa.Column("current_scene_id", ID, sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("face_state", STR, nullable=False),
            sa.Column("visibility", STR, nullable=False),
            sa.Column("locked", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_card_instances_campaign", "card_instances", ["campaign_id"])
        op.create_index("idx_card_instances_deck", "card_instances", ["deck_instance_id"])
        op.create_index("idx_card_instances_pile", "card_instances", ["current_pile_id"])

    if not _has_table("card_pile_entries"):
        op.create_table(
            "card_pile_entries",
            sa.Column("pile_id", ID, sa.ForeignKey("card_piles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("card_instance_id", ID, sa.ForeignKey("card_instances.id", ondelete="CASCADE"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("inserted_at", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("pile_id", "card_instance_id"),
            sa.UniqueConstraint("pile_id", "position"),
            sa.UniqueConstraint("card_instance_id"),
        )
        op.create_index("idx_card_pile_entries_pile_order", "card_pile_entries", ["pile_id", "position"])

    if not _has_table("scene_card_placements"):
        op.create_table(
            "scene_card_placements",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scene_id", ID, sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("card_instance_id", ID, sa.ForeignKey("card_instances.id", ondelete="CASCADE"), nullable=False),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("x", sa.Float(), nullable=False),
            sa.Column("y", sa.Float(), nullable=False),
            sa.Column("rotation", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("scale", sa.Float(), nullable=False, server_default=sa.text("1")),
            sa.Column("z_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("face_state", STR, nullable=False),
            sa.Column("visibility", STR, nullable=False),
            sa.Column("locked", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_scene_card_placements_scene", "scene_card_placements", ["scene_id", "z_index"])
        op.create_index("idx_scene_card_placements_card", "scene_card_placements", ["card_instance_id"])

    if not _has_table("card_events"):
        op.create_table(
            "card_events",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("room_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
            sa.Column("actor_user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", STR, nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("visibility", STR, nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_card_events_campaign", "card_events", ["campaign_id", "created_at"])
        op.create_index("idx_card_events_type", "card_events", ["event_type"])


def downgrade() -> None:
    for table_name in [
        "card_events",
        "scene_card_placements",
        "card_pile_entries",
        "card_instances",
        "card_piles",
        "card_deck_instances",
        "card_definitions",
        "card_deck_definitions",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)
