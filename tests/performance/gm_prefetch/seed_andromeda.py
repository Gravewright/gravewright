from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.roles import PlayerRole
from app.engine.scenes.map_upload_service import MapUploadService
from app.helpers.password import hash_password
from app.persistence.database import engine_begin
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.user_repository import UserRepository

PASSWORD = "Andromeda1!"
GM_EMAIL = "andromeda-gm@test.local"
PLAYER_EMAILS = [f"andromeda-player-{index}@test.local" for index in range(1, 6)]
CAMPAIGN = "Andromeda GM Prefetch Benchmark"
SCENE = "Andromeda M31 Full Resolution"


def user(email: str, name: str) -> str:
    repo = UserRepository()
    found = repo.get_by_email(email)
    if found:
        return found["id"]
    return repo.create_with_auto_role(
        name=name, email=email, password_hash=hash_password(PASSWORD)
    )["id"]


def add_member(campaign_id: str, user_id: str) -> None:
    if CampaignRepository().get_member(campaign_id=campaign_id, user_id=user_id):
        return
    now = int(time.time())
    with engine_begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO campaign_members (id,campaign_id,user_id,role,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex, campaign_id, user_id, PlayerRole.PLAYER.value, now, now),
        )


async def seed(image: Path, output: Path, *, scene_name: str = SCENE, tile_size: int | None = 512, chunk_size: int = 16) -> None:
    gm_id = user(GM_EMAIL, "Andromeda GM")
    campaigns = CampaignRepository()
    campaign = next((row for row in campaigns.list_for_user(gm_id) if row["title"] == CAMPAIGN), None)
    campaign_id = campaign["id"] if campaign else campaigns.create(
        owner_user_id=gm_id, title=CAMPAIGN, description="1 GM + 5 player predictive prefetch benchmark"
    )["id"]
    player_ids = []
    for index, email in enumerate(PLAYER_EMAILS, 1):
        player_id = user(email, f"Andromeda Player {index}")
        add_member(campaign_id, player_id)
        player_ids.append(player_id)

    scenes = SceneRepository()
    scene = next((row for row in scenes.list_by_campaign(campaign_id) if row["name"] == scene_name), None)
    ingest_seconds = 0.0
    if scene is None:
        started = time.perf_counter()
        result = await MapUploadService().upload_raster_map(
            campaign_id=campaign_id, user_id=gm_id, name=scene_name,
            filename=image.name, content_type="image/jpeg", data=image.read_bytes(),
            tile_size=tile_size, chunk_size=chunk_size, grid_size=tile_size,
        )
        if not result.success or not result.scene:
            raise RuntimeError(f"Andromeda ingestion failed: {result.error_key}")
        scene = result.scene
        ingest_seconds = time.perf_counter() - started
    selected_tile_size = int(scene["tile_size"])
    scenes.set_active_scene(campaign_id=campaign_id, scene_id=scene["id"])
    scenes.update_start_point(
        scene_id=scene["id"], start_world_x=1.5 * chunk_size * selected_tile_size,
        start_world_y=0.5 * chunk_size * selected_tile_size, start_zoom=1.0,
    )
    payload = {
        "password": PASSWORD, "gm": {"email": GM_EMAIL, "user_id": gm_id},
        "players": [{"email": email, "user_id": uid} for email, uid in zip(PLAYER_EMAILS, player_ids)],
        "campaign_id": campaign_id, "scene_id": scene["id"],
        "image": {"path": str(image.resolve()), "bytes": image.stat().st_size},
        "raster": {"tile_size": selected_tile_size, "chunk_span": int(scene["chunk_size"]),
                   "selection_mode": scene.get("raster_selection_mode", "legacy"),
                   "policy_version": int(scene.get("raster_policy_version", 0))},
        "ingest_seconds": round(ingest_seconds, 3),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default="tests/performance/gm_prefetch/fixtures.json")
    parser.add_argument("--scene-name", default=SCENE)
    parser.add_argument("--tile-size", type=int, default=512)
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument("--adaptive", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(Path(args.image), Path(args.output), scene_name=args.scene_name, tile_size=None if args.adaptive else args.tile_size, chunk_size=args.chunk_size))
