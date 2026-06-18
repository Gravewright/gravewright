"""
Seeds the *sharded* live-session stress scenario.

Instead of one giant room, this provisions many small tables — the realistic
shape of a 500-player load. Each room gets its own GM-staffed campaign, active
scene (chunks + fog), and one token per player, so the realtime fan-out of any
command only reaches that room's handful of sockets (not all 500).

    rooms × users_per_room = total players (default 100 × 5 = 500)

Every player is a distinct account that is a *GM of exactly one campaign*, which
keeps both permissions simple (GMs can move tokens / paint fog) and the
broadcast fan-out correctly scoped per room.

Writes ``fixtures_multiroom.json`` (per-player credentials + token) for the
driver to consume in per-user-login mode.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
for path in (str(PROJECT_ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.persistence.database as database
from app.persistence.database import engine_begin
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.user_repository import UserRepository
from app.persistence.tables import campaign_members
from app.domain.roles import PlayerRole
from app.helpers.password import hash_password
from sqlalchemy import insert, select

import seed as single  # reuse chunk/scene/token/fog helpers + dimensions


LIVE_PASSWORD = single.LIVE_PASSWORD
FIXTURES_PATH = HERE / "fixtures_multiroom.json"


def _get_or_create_user(email: str, name: str) -> str:
    users = UserRepository()
    existing = users.get_by_email(email)
    if existing is not None:
        return existing["id"]
    return users.create_with_auto_role(
        name=name,
        email=email,
        password_hash=hash_password(LIVE_PASSWORD),
    )["id"]


def _get_or_create_campaign(owner_user_id: str, title: str) -> str:
    for campaign in CampaignRepository().list_for_user(owner_user_id):
        if campaign["title"] == title:
            return campaign["id"]
    return CampaignRepository().create(
        owner_user_id=owner_user_id,
        title=title,
        description="Sharded WS stress room.",
    )["id"]


def _ensure_gm_member(campaign_id: str, user_id: str) -> None:
    now = int(time.time())
    with engine_begin() as conn:
        exists = conn.execute(
            select(campaign_members.c.id)
            .where(campaign_members.c.campaign_id == campaign_id)
            .where(campaign_members.c.user_id == user_id)
            .limit(1)
        ).first()
        if exists is not None:
            return
        conn.execute(
            insert(campaign_members).values(
                id=uuid.uuid4().hex,
                campaign_id=campaign_id,
                user_id=user_id,
                role=PlayerRole.GM.value,
                created_at=now,
                updated_at=now,
            )
        )


def seed(db_path: str, *, rooms: int, users_per_room: int) -> None:
    database.DATABASE_PATH = Path(db_path)
    database._initialized = False
    database.initialize_database()

    storage_root = Path(db_path).parent
    slots: list[dict] = []

    for r in range(rooms):
        user_ids: list[str] = []
        emails: list[str] = []
        for k in range(users_per_room):
            email = f"wsroom{r:03d}u{k}@test.local"
            uid = _get_or_create_user(email, name=f"Room {r:03d} Player {k}")
            user_ids.append(uid)
            emails.append(email)

        campaign_id = _get_or_create_campaign(user_ids[0], title=f"WS Stress Room {r:03d}")
        for uid in user_ids[1:]:
            _ensure_gm_member(campaign_id, uid)

        scene_id, layer_id = single._get_or_create_scene(
            campaign_id, name=f"WS Stress Scene {r:03d}"
        )
        single._seed_chunks(scene_id=scene_id, layer_id=layer_id, storage_root=storage_root)
        single._ensure_fog_enabled(scene_id, user_ids[0])
        token_ids = single._ensure_tokens(scene_id, users_per_room)

        for k in range(users_per_room):
            slots.append({"email": emails[k], "token_id": token_ids[k]})

        if (r + 1) % 10 == 0 or r == rooms - 1:
            print(f"[seed] provisioned {r + 1}/{rooms} rooms ({len(slots)} players)")

    fixtures = {
        "mode": "multiroom",
        "password": LIVE_PASSWORD,
        "tile_columns": math.ceil(single.SCENE_WIDTH / single.TILE_SIZE),
        "tile_rows": math.ceil(single.SCENE_HEIGHT / single.TILE_SIZE),
        "chunk_columns": math.ceil(
            math.ceil(single.SCENE_WIDTH / single.TILE_SIZE) / single.CHUNK_SIZE
        ),
        "chunk_rows": math.ceil(
            math.ceil(single.SCENE_HEIGHT / single.TILE_SIZE) / single.CHUNK_SIZE
        ),
        "slots": slots,
    }
    FIXTURES_PATH.write_text(json.dumps(fixtures), encoding="utf-8")

    print("[seed] Done.")
    print(f"  rooms:          {rooms}")
    print(f"  users_per_room: {users_per_room}")
    print(f"  total players:  {len(slots)}")
    print(f"  password:       {LIVE_PASSWORD}")
    print(f"  fixtures:       {FIXTURES_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="storage/gravewright.sqlite3")
    parser.add_argument("--rooms", type=int, default=100)
    parser.add_argument("--users-per-room", type=int, default=5)
    args = parser.parse_args()
    seed(args.db, rooms=args.rooms, users_per_room=args.users_per_room)
