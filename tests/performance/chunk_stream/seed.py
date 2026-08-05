"""
Seeds a WebSocket chunk-stream test scene.

The scenario is intentionally smaller than max_stress: it exists to validate the
binary viewport stream, reconnect, and session.resume path under Docker.
"""
                  
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.persistence.database as database
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.domain.scenes import SceneStatus
from app.engine.scenes.chunk_codec import encode_uint32_tile_refs
from app.helpers.password import hash_password
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.database import engine_begin
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_chunk_repository import SceneChunkRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.user_repository import UserRepository


STREAM_EMAIL = "chunkstream@test.local"
STREAM_PASSWORD = "ChunkStream1!"
STREAM_NAME = "Chunk Stream GM"

SCENE_WIDTH = 4096
SCENE_HEIGHT = 3072
TILE_SIZE = 32
CHUNK_SIZE = 16


def _get_or_create_user() -> str:
    users = UserRepository()
    existing = users.get_by_email(STREAM_EMAIL)
    if existing is not None:
        return existing["id"]

    return users.create_with_auto_role(
        name=STREAM_NAME,
        email=STREAM_EMAIL,
        password_hash=hash_password(STREAM_PASSWORD),
    )["id"]


def _get_or_create_campaign(user_id: str) -> str:
    campaigns = CampaignRepository().list_for_user(user_id)
    for campaign in campaigns:
        if campaign["title"] == "Chunk Stream Campaign":
            return campaign["id"]

    return CampaignRepository().create(
        owner_user_id=user_id,
        title="Chunk Stream Campaign",
        description="Docker chunk stream reconnect scenario.",
    )["id"]


def _get_or_create_scene(campaign_id: str) -> tuple[str, str]:
    scenes = SceneRepository()
    layers = SceneLayerRepository()

    for scene in scenes.list_by_campaign(campaign_id):
        if scene["name"] == "Chunk Stream Scene":
            layer = _first_stream_layer(scene["id"])
            if layer is not None:
                scenes.set_active_scene(campaign_id=campaign_id, scene_id=scene["id"])
                return scene["id"], layer["id"]

    scene = scenes.create(
        campaign_id=campaign_id,
        name="Chunk Stream Scene",
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


def _first_stream_layer(scene_id: str):
    with engine_begin() as connection:
        return connection.exec_driver_sql(
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


def _seed_chunks(*, scene_id: str, layer_id: str, storage_root: Path) -> int:
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

    return written


def seed(db_path: str) -> None:
    database.DATABASE_PATH = Path(db_path)
    database._initialized = False
    database.initialize_database()

    user_id = _get_or_create_user()
    campaign_id = _get_or_create_campaign(user_id)
    scene_id, layer_id = _get_or_create_scene(campaign_id)
    chunk_count = _seed_chunks(
        scene_id=scene_id,
        layer_id=layer_id,
        storage_root=Path(db_path).parent,
    )

    print("[seed] Done.")
    print(f"  email:      {STREAM_EMAIL}")
    print(f"  password:   {STREAM_PASSWORD}")
    print(f"  campaign:   {campaign_id}")
    print(f"  scene:      {scene_id}")
    print(f"  layer:      {layer_id}")
    print(f"  chunks:     {chunk_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="storage/gravewright.sqlite3")
    args = parser.parse_args()
    seed(args.db)
