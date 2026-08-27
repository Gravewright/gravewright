from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass


MIN_MODERN_TILE_SIZE = 256


@dataclass(frozen=True)
class LegacyScene:
    scene_id: str
    campaign_id: str
    owner_user_id: str
    name: str
    tile_size: int
    has_original: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retile legacy raster scenes to reduce browser decode pressure."
    )
    parser.add_argument("--campaign-id", help="Limit migration to one campaign.")
    parser.add_argument("--target-size", type=int, default=MIN_MODERN_TILE_SIZE)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the migration. Without this flag the command is read-only.",
    )
    return parser.parse_args()


def find_legacy_scenes(*, campaign_id: str | None, target_size: int) -> list[LegacyScene]:
    from sqlalchemy import and_, select

    from app.persistence.database import engine_connect
    from app.persistence.tables import campaigns, scene_assets, scenes

    original = scene_assets.alias("original")
    conditions = [scenes.c.tile_size < target_size]
    if campaign_id:
        conditions.append(scenes.c.campaign_id == campaign_id)
    statement = (
        select(
            scenes.c.id,
            scenes.c.campaign_id,
            campaigns.c.owner_user_id,
            scenes.c.name,
            scenes.c.tile_size,
            original.c.id.label("original_id"),
        )
        .select_from(
            scenes.join(campaigns, campaigns.c.id == scenes.c.campaign_id).outerjoin(
                original,
                and_(original.c.scene_id == scenes.c.id, original.c.kind == "original_image"),
            )
        )
        .where(*conditions)
        .order_by(scenes.c.created_at.asc())
    )
    with engine_connect() as connection:
        rows = connection.execute(statement).mappings().all()
    return [
        LegacyScene(
            scene_id=str(row["id"]),
            campaign_id=str(row["campaign_id"]),
            owner_user_id=str(row["owner_user_id"]),
            name=str(row["name"]),
            tile_size=int(row["tile_size"]),
            has_original=row["original_id"] is not None,
        )
        for row in rows
    ]


async def run() -> int:
    args = parse_args()
    if not MIN_MODERN_TILE_SIZE <= args.target_size <= 1024:
        raise SystemExit("--target-size must be between 256 and 1024")

    candidates = find_legacy_scenes(
        campaign_id=args.campaign_id,
        target_size=args.target_size,
    )
    if not candidates:
        print("No legacy raster scenes found.")
        return 0

    for scene in candidates:
        status = "ready" if scene.has_original else "skip: original image missing"
        print(f"{scene.scene_id} | {scene.name} | {scene.tile_size} -> {args.target_size} | {status}")

    if not args.apply:
        print("Dry run only. Pass --apply to retile scenes marked ready.")
        return 0

    from app.engine.scenes.map_upload_service import MapUploadService

    service = MapUploadService()
    failed = 0
    for scene in candidates:
        if not scene.has_original:
            continue
        result = await service.retile_scene(
            scene_id=scene.scene_id,
            user_id=scene.owner_user_id,
            new_tile_size=args.target_size,
        )
        if result.success:
            print(
                f"migrated: {scene.name} "
                f"({result.tile_count} tiles, {result.chunk_count} chunks)"
            )
        else:
            failed += 1
            print(f"failed: {scene.name} ({result.error_key or 'unknown error'})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
