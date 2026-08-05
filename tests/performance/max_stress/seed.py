"""
Seeds an absurd stress-test scene:
  - 8000 x 6000 px map
  - 32 px tile size → 250 x 188 = 47 000 tiles
  - 1 GM user: stress@test.local / StressMax1!

This is a scenario that will practically never happen in a real session.

Run once before the stress test:
    python tests/performance/max_stress/seed.py [--db storage/gravewright.sqlite3]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import math
import secrets
from sqlalchemy import create_engine
import time
import uuid
from pathlib import Path


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

STRESS_EMAIL = "stress@test.local"
STRESS_PASSWORD = "StressMax1!"
STRESS_NAME = "Stress GM"

SCENE_WIDTH = 8000
SCENE_HEIGHT = 6000
TILE_SIZE = 32


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(key)}"


def _generate_tiles(scene_id: str, layer_id: str, storage_root: Path) -> list[dict]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[seed] Pillow not installed — aborting")
        raise

    tx_count = math.ceil(SCENE_WIDTH / TILE_SIZE)
    ty_count = math.ceil(SCENE_HEIGHT / TILE_SIZE)
    total = tx_count * ty_count
    print(f"[seed] Generating {tx_count}×{ty_count} = {total} tiles for {SCENE_WIDTH}x{SCENE_HEIGHT} map...")

    tile_dir = storage_root / "scenes" / scene_id / "assets" / "tiles" / layer_id
    orig_dir = storage_root / "scenes" / scene_id / "assets" / "original"
    tile_dir.mkdir(parents=True, exist_ok=True)
    orig_dir.mkdir(parents=True, exist_ok=True)

                                                                                        
    orig_path = orig_dir / "original.png"

                                                                
    if not orig_path.exists():
        print("[seed] Rendering source image in bands...")
                                                     
        full = Image.new("RGBA", (SCENE_WIDTH, SCENE_HEIGHT), (20, 24, 30, 255))
        draw = ImageDraw.Draw(full)
        for x in range(0, SCENE_WIDTH, TILE_SIZE):
            draw.line([(x, 0), (x, SCENE_HEIGHT)], fill=(45, 45, 60, 160), width=1)
        for y in range(0, SCENE_HEIGHT, TILE_SIZE):
            draw.line([(0, y), (SCENE_WIDTH, y)], fill=(45, 45, 60, 160), width=1)
        for x in range(0, SCENE_WIDTH, TILE_SIZE * 5):
            draw.line([(x, 0), (x, SCENE_HEIGHT)], fill=(90, 80, 55, 200), width=1)
        for y in range(0, SCENE_HEIGHT, TILE_SIZE * 5):
            draw.line([(0, y), (SCENE_WIDTH, y)], fill=(90, 80, 55, 200), width=1)
        full.save(str(orig_path), "PNG")
        del full
        print("[seed] Source image saved.")
    else:
        print("[seed] Source image already exists, reusing.")
        from PIL import Image as _img
        full = _img.open(str(orig_path))
                                          

                      
    print("[seed] Slicing tiles...")
    from PIL import Image as PILImage
    source = PILImage.open(str(orig_path))

    tile_records = []
    tile_ref = 1
    done = 0

    for ty in range(ty_count):
        for tx in range(tx_count):
            tile_path = tile_dir / f"{tx}_{ty}.png"
            x0, y0 = tx * TILE_SIZE, ty * TILE_SIZE
            x1 = min(x0 + TILE_SIZE, SCENE_WIDTH)
            y1 = min(y0 + TILE_SIZE, SCENE_HEIGHT)

            if not tile_path.exists():
                tile_img = source.crop((x0, y0, x1, y1))
                tile_img.save(str(tile_path), "PNG")

            data = tile_path.read_bytes()
            tile_hash = hashlib.sha256(data).hexdigest()
            tile_records.append({
                "asset_id": uuid.uuid4().hex,
                "tile_ref": tile_ref,
                "tx": tx, "ty": ty,
                "width": x1 - x0, "height": y1 - y0,
                "hash": tile_hash,
                "byte_size": len(data),
                "storage_path": str(tile_path.relative_to(storage_root)),
            })
            tile_ref += 1
            done += 1

        if (ty + 1) % 20 == 0 or ty + 1 == ty_count:
            print(f"  {done}/{total} tiles ({100*done//total}%)")

    source.close()
    return tile_records



class _Result:
    def __init__(self, result):
        self._result = result

    def fetchone(self):
        return self._result.mappings().first()

    def fetchall(self):
        return self._result.mappings().all()


class _Connection:
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path.as_posix()}", future=True)
        self._ctx = self._engine.begin()
        self._conn = self._ctx.__enter__()

    def execute(self, statement: str, parameters=()):
        return _Result(self._conn.exec_driver_sql(statement, parameters))

    def commit(self) -> None:
                                                                          
        return None

    def close(self) -> None:
        self._ctx.__exit__(None, None, None)
        self._engine.dispose()

def seed(db_path: str) -> None:
    path = Path(db_path)
    storage_root = path.parent
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _Connection(str(path))
    conn.execute("PRAGMA foreign_keys = ON")

          
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (STRESS_EMAIL,)).fetchone()
    if existing:
        user_id = existing["id"]
        print(f"[seed] User already exists: {user_id}")
    else:
        user_id = uuid.uuid4().hex
        now = int(time.time())
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, system_role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, STRESS_NAME, STRESS_EMAIL, hash_password(STRESS_PASSWORD), "user", now, now),
        )
        print(f"[seed] Created user: {user_id}")

              
    existing_campaign = conn.execute(
        "SELECT id FROM campaigns WHERE id IN "
        "(SELECT campaign_id FROM campaign_members WHERE user_id = ?)",
        (user_id,),
    ).fetchone()

    if existing_campaign:
        campaign_id = existing_campaign["id"]
        print(f"[seed] Campaign already exists: {campaign_id}")
    else:
        campaign_id = uuid.uuid4().hex
        now = int(time.time())
        conn.execute(
            "INSERT INTO campaigns "
            "(id, owner_user_id, title, description, active_system_id, "
            "initial_state_json, persistent_state_json, state_version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (campaign_id, user_id, "Max Stress Campaign", "", None, "{}", "{}", 1, now, now),
        )
        conn.execute(
            "INSERT INTO campaign_members "
            "(id, campaign_id, user_id, role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, campaign_id, user_id, "gm", now, now),
        )
        print(f"[seed] Created campaign: {campaign_id}")

           
    existing_scene = conn.execute(
        "SELECT id FROM scenes WHERE campaign_id = ? AND active = 1", (campaign_id,)
    ).fetchone()

    if existing_scene:
        scene_id = existing_scene["id"]
        print(f"[seed] Active scene already exists: {scene_id}")
        layer = conn.execute(
            "SELECT id FROM scene_layers WHERE scene_id = ? AND kind = 'raster_tile_refs'",
            (scene_id,),
        ).fetchone()
        layer_id = layer["id"] if layer else None
    else:
        scene_id = uuid.uuid4().hex
        layer_id = uuid.uuid4().hex
        now = int(time.time())
        conn.execute(
            "INSERT INTO scenes "
            "(id, campaign_id, name, status, visibility, width, height, tile_size, chunk_size, "
            "image_scale, grid_visible, grid_color, active, group_id, tile_table_version, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (scene_id, campaign_id, "Max Stress Scene", "active", "players",
             SCENE_WIDTH, SCENE_HEIGHT, TILE_SIZE, 16,
             1.0, 1, "#ededed", 1, None, 1, now, now),
        )
        conn.execute(
            "INSERT INTO scene_layers "
            "(id, scene_id, kind, name, visibility, display_order, encoding, "
            "tile_table_version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (layer_id, scene_id, "raster_tile_refs", "Ground", "visible", 0,
             "uint32_tile_refs_v1", 1, now, now),
        )
        print(f"[seed] Created scene: {scene_id}, layer: {layer_id}")

                   
    tile_dir = storage_root / "scenes" / scene_id / "assets" / "tiles" / (layer_id or "")
    existing_db_tiles = conn.execute(
        "SELECT COUNT(*) as n FROM scene_tiles WHERE layer_id = ?", (layer_id,)
    ).fetchone()["n"]
    existing_disk_tiles = sum(1 for _ in tile_dir.glob("*.png")) if tile_dir.exists() else 0

    tx_count = math.ceil(SCENE_WIDTH / TILE_SIZE)
    ty_count = math.ceil(SCENE_HEIGHT / TILE_SIZE)
    expected = tx_count * ty_count

    if existing_db_tiles >= expected and existing_disk_tiles >= expected:
        print(f"[seed] {existing_disk_tiles} tiles already on disk + DB — skipping generation")
    else:
        print(f"[seed] Found {existing_disk_tiles}/{expected} tiles on disk, {existing_db_tiles}/{expected} in DB")
        tile_records = _generate_tiles(scene_id, layer_id, storage_root)
        now = int(time.time())
        for rec in tile_records:
            asset_id = rec["asset_id"]
            conn.execute(
                "INSERT INTO scene_assets "
                "(id, scene_id, kind, storage_path, hash, byte_size, width, height, content_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (asset_id, scene_id, "tile", rec["storage_path"], rec["hash"],
                 rec["byte_size"], rec["width"], rec["height"], "image/png", now),
            )
            conn.execute(
                "INSERT INTO scene_tiles "
                "(scene_id, layer_id, tile_ref, asset_id, tx, ty, width, height, hash, byte_size, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (scene_id, layer_id, rec["tile_ref"], asset_id,
                 rec["tx"], rec["ty"], rec["width"], rec["height"],
                 rec["hash"], rec["byte_size"], now),
            )
        conn.commit()
        print(f"[seed] {len(tile_records)} tiles written to DB and disk.")

    conn.commit()
    conn.close()

    print("\n[seed] Done.")
    print(f"  email:     {STRESS_EMAIL}")
    print(f"  password:  {STRESS_PASSWORD}")
    print(f"  scene_id:  {scene_id}")
    print(f"  layer_id:  {layer_id}")
    print(f"  map size:  {SCENE_WIDTH}x{SCENE_HEIGHT} @ {TILE_SIZE}px tiles = {tx_count}x{ty_count} = {expected} tiles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="storage/gravewright.sqlite3")
    args = parser.parse_args()
    seed(args.db)
