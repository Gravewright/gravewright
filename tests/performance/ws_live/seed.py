"""
Seeds the live-session WebSocket scenario.

Unlike the chunk-stream seed (which exists to exercise the binary viewport
stream), this scenario is about *interactive* realtime traffic:

    * token movement      (token.move)
    * fog of war ops      (fog.paint — fog is enabled here so paint never fails)
    * chat / dice rolls    (HTTP POST /game/chat, incl. "/roll")
    * reconnect / resume   (close + re-subscribe / session.resume)

It provisions a GM account, one campaign, one active scene with a streamable
raster layer, a handful of pre-placed tokens (so movers always have a target),
and writes a small ``fixtures.json`` that the load driver reads to learn the
token ids and chunk-grid bounds.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.persistence.database as database
from app.domain.fog import FogInitialState
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.domain.scenes import SceneStatus
from app.engine.scenes.chunk_codec import encode_uint32_tile_refs
from app.engine.scenes.fog_service import FogService
from app.helpers.password import hash_password
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.database import engine_begin
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_chunk_repository import SceneChunkRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_repository import TokenRepository
from app.persistence.repositories.user_repository import UserRepository


LIVE_EMAIL = "wslive@test.local"
LIVE_PASSWORD = "WsLive1!"
LIVE_NAME = "WS Live GM"

CAMPAIGN_TITLE = "WS Live Campaign"
SCENE_NAME = "WS Live Scene"

# Deliberately small: this scenario is about command throughput, not payload.
SCENE_WIDTH = 2048
SCENE_HEIGHT = 1536
TILE_SIZE = 32
CHUNK_SIZE = 16

TOKEN_COUNT = 20

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures.json"


def _get_or_create_user() -> str:
    users = UserRepository()
    existing = users.get_by_email(LIVE_EMAIL)
    if existing is not None:
        return existing["id"]

    return users.create_with_auto_role(
        name=LIVE_NAME,
        email=LIVE_EMAIL,
        password_hash=hash_password(LIVE_PASSWORD),
    )["id"]


def _get_or_create_campaign(user_id: str) -> str:
    campaigns = CampaignRepository().list_for_user(user_id)
    for campaign in campaigns:
        if campaign["title"] == CAMPAIGN_TITLE:
            return campaign["id"]

    return CampaignRepository().create(
        owner_user_id=user_id,
        title=CAMPAIGN_TITLE,
        description="Interactive realtime load scenario (tokens/fog/chat/reconnect).",
    )["id"]


def _first_stream_layer(scene_id: str):
    with engine_begin() as connection:
        row = connection.exec_driver_sql(
            """
            SELECT *
            FROM scene_layers
            WHERE scene_id = ?
            AND kind = ?
            ORDER BY display_order ASC
            LIMIT 1
            """,
            (scene_id, SceneLayerKind.RASTER_TILE_REFS.value),
        ).fetchone()
        # exec_driver_sql yields positional Rows; expose name-based access.
        return dict(row._mapping) if row is not None else None


def _get_or_create_scene(campaign_id: str, name: str = SCENE_NAME) -> tuple[str, str]:
    scenes = SceneRepository()
    layers = SceneLayerRepository()

    for scene in scenes.list_by_campaign(campaign_id):
        if scene["name"] == name:
            layer = _first_stream_layer(scene["id"])
            if layer is not None:
                scenes.set_active_scene(campaign_id=campaign_id, scene_id=scene["id"])
                return scene["id"], layer["id"]

    scene = scenes.create(
        campaign_id=campaign_id,
        name=name,
        width=SCENE_WIDTH,
        height=SCENE_HEIGHT,
        tile_size=TILE_SIZE,
        chunk_size=CHUNK_SIZE,
        status=SceneStatus.ACTIVE,
        active=True,
        grid_color="#ededed",
    )
    layer = layers.create(
        scene_id=scene["id"],
        name="Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )
    scenes.set_active_scene(campaign_id=campaign_id, scene_id=scene["id"])
    return scene["id"], layer["id"]


def _seed_chunks(*, scene_id: str, layer_id: str, storage_root: Path) -> tuple[int, int, int]:
    storage = LocalChunkStorage(root=storage_root / "scenes")
    chunks = SceneChunkRepository()

    tile_columns = math.ceil(SCENE_WIDTH / TILE_SIZE)
    tile_rows = math.ceil(SCENE_HEIGHT / TILE_SIZE)
    chunk_columns = math.ceil(tile_columns / CHUNK_SIZE)
    chunk_rows = math.ceil(tile_rows / CHUNK_SIZE)

    written = 0
    for cy in range(chunk_rows):
        for cx in range(chunk_columns):
            refs = []
            for local_y in range(CHUNK_SIZE):
                for local_x in range(CHUNK_SIZE):
                    tx = cx * CHUNK_SIZE + local_x
                    ty = cy * CHUNK_SIZE + local_y
                    refs.append((ty * tile_columns + tx + 1) if tx < tile_columns and ty < tile_rows else 0)

            data = encode_uint32_tile_refs(refs)
            chunk_hash = storage.write_chunk(
                scene_id=scene_id,
                layer_id=layer_id,
                cx=cx,
                cy=cy,
                data=data,
            )
            chunks.record_write(
                scene_id=scene_id,
                layer_id=layer_id,
                cx=cx,
                cy=cy,
                hash=chunk_hash,
                byte_size=len(data),
                encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
            )
            written += 1

    return written, chunk_columns, chunk_rows


def _ensure_tokens(scene_id: str, token_count: int) -> list[str]:
    tokens = TokenRepository()
    existing = tokens.list_by_scene(scene_id)
    if len(existing) >= token_count:
        return [t["id"] for t in existing[:token_count]]

    tile_columns = math.ceil(SCENE_WIDTH / TILE_SIZE)
    tile_rows = math.ceil(SCENE_HEIGHT / TILE_SIZE)

    created: list[str] = [t["id"] for t in existing]
    # Lay the tokens out on a coarse grid well inside the map bounds so moves
    # in any direction stay on valid cells.
    index = len(existing)
    while len(created) < token_count:
        gx = 2 + (index * 3) % max(1, tile_columns - 4)
        gy = 2 + (index * 2) % max(1, tile_rows - 4)
        token = tokens.create(
            scene_id=scene_id,
            actor_id=None,
            grid_x=int(gx),
            grid_y=int(gy),
            name=f"Load Token {index + 1}",
        )
        created.append(token["id"])
        index += 1

    return created[:token_count]


def _ensure_fog_enabled(scene_id: str, user_id: str) -> None:
    """Fog paint commands fail unless fog is enabled on the scene first."""
    result = FogService().enable(
        scene_id=scene_id,
        user_id=user_id,
        initial=FogInitialState.HIDE_ALL,
    )
    if not result.success and result.error_key not in (None, "game.fog.errors.already_enabled"):
        # Enable is idempotent enough for our purposes; only surface real failures.
        print(f"[seed] WARNING: fog enable returned {result.error_key}")


def seed(db_path: str, token_count: int = TOKEN_COUNT) -> None:
    database.DATABASE_PATH = Path(db_path)
    database._initialized = False
    database.initialize_database()

    user_id = _get_or_create_user()
    campaign_id = _get_or_create_campaign(user_id)
    scene_id, layer_id = _get_or_create_scene(campaign_id)
    chunk_count, chunk_columns, chunk_rows = _seed_chunks(
        scene_id=scene_id,
        layer_id=layer_id,
        storage_root=Path(db_path).parent,
    )
    token_ids = _ensure_tokens(scene_id, token_count)
    _ensure_fog_enabled(scene_id, user_id)

    fixtures = {
        "email": LIVE_EMAIL,
        "password": LIVE_PASSWORD,
        "campaign_id": campaign_id,
        "scene_id": scene_id,
        "layer_id": layer_id,
        "token_ids": token_ids,
        "tile_columns": math.ceil(SCENE_WIDTH / TILE_SIZE),
        "tile_rows": math.ceil(SCENE_HEIGHT / TILE_SIZE),
        "chunk_columns": chunk_columns,
        "chunk_rows": chunk_rows,
    }
    FIXTURES_PATH.write_text(json.dumps(fixtures, indent=2), encoding="utf-8")

    print("[seed] Done.")
    print(f"  email:      {LIVE_EMAIL}")
    print(f"  password:   {LIVE_PASSWORD}")
    print(f"  campaign:   {campaign_id}")
    print(f"  scene:      {scene_id}")
    print(f"  layer:      {layer_id}")
    print(f"  chunks:     {chunk_count} ({chunk_columns}x{chunk_rows})")
    print(f"  tokens:     {len(token_ids)}")
    print(f"  fog:        enabled (hide_all)")
    print(f"  fixtures:   {FIXTURES_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="storage/gravewright.sqlite3")
    parser.add_argument(
        "--tokens",
        type=int,
        default=TOKEN_COUNT,
        help="number of pre-placed tokens (one per user avoids shared-token contention)",
    )
    args = parser.parse_args()
    seed(args.db, token_count=args.tokens)
