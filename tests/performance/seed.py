"""
Bootstrap a test user + campaign + active scene (with tiles) for performance tests.

Run once before starting the app container:

    python tests/performance/seed.py [--db storage/gravewright.sqlite3]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import math
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

PERF_EMAIL = "perf@test.local"
PERF_PASSWORD = "Perf1234!"
PERF_NAME = "Perf User"

SCENE_WIDTH = 800
SCENE_HEIGHT = 600
TILE_SIZE = 50
CHUNK_SIZE = 16


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(key)}"


def _generate_tiles(scene_id: str, layer_id: str, storage_root: Path) -> list[dict[str, Any]]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[seed] Pillow not installed — skipping tile generation")
        return []

    tile_dir = storage_root / "scenes" / scene_id / "assets" / "tiles" / layer_id
    orig_dir = storage_root / "scenes" / scene_id / "assets" / "original"
    tile_dir.mkdir(parents=True, exist_ok=True)
    orig_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (SCENE_WIDTH, SCENE_HEIGHT), (30, 30, 40, 255))
    draw = ImageDraw.Draw(img)

    for x in range(0, SCENE_WIDTH, TILE_SIZE):
        draw.line([(x, 0), (x, SCENE_HEIGHT)], fill=(60, 60, 80, 180), width=1)

    for y in range(0, SCENE_HEIGHT, TILE_SIZE):
        draw.line([(0, y), (SCENE_WIDTH, y)], fill=(60, 60, 80, 180), width=1)

    for gx in range(0, SCENE_WIDTH, TILE_SIZE * 5):
        draw.line([(gx, 0), (gx, SCENE_HEIGHT)], fill=(100, 90, 60, 200), width=1)

    for gy in range(0, SCENE_HEIGHT, TILE_SIZE * 5):
        draw.line([(0, gy), (SCENE_WIDTH, gy)], fill=(100, 90, 60, 200), width=1)

    orig_path = orig_dir / "original.png"
    img.save(str(orig_path), "PNG")

    tx_count = math.ceil(SCENE_WIDTH / TILE_SIZE)
    ty_count = math.ceil(SCENE_HEIGHT / TILE_SIZE)

    tile_records: list[dict[str, Any]] = []
    tile_ref = 1

    for ty in range(ty_count):
        for tx in range(tx_count):
            x0 = tx * TILE_SIZE
            y0 = ty * TILE_SIZE
            x1 = min(x0 + TILE_SIZE, SCENE_WIDTH)
            y1 = min(y0 + TILE_SIZE, SCENE_HEIGHT)

            tile_img = img.crop((x0, y0, x1, y1))
            tile_path = tile_dir / f"{tx}_{ty}.png"
            tile_img.save(str(tile_path), "PNG")

            data = tile_path.read_bytes()
            tile_hash = hashlib.sha256(data).hexdigest()

            tile_records.append(
                {
                    "asset_id": uuid.uuid4().hex,
                    "tile_ref": tile_ref,
                    "tx": tx,
                    "ty": ty,
                    "width": x1 - x0,
                    "height": y1 - y0,
                    "hash": tile_hash,
                    "byte_size": len(data),
                    "storage_path": str(tile_path.relative_to(storage_root)),
                }
            )
            tile_ref += 1

    print(f"[seed] Generated {len(tile_records)} tiles ({tx_count}×{ty_count})")
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
        # Transaction is committed by SQLAlchemy's engine.begin() context on clean close.
        return None

    def close(self) -> None:
        self._ctx.__exit__(None, None, None)
        self._engine.dispose()


def _table_columns(conn: _Connection, table_name: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"]: dict(row) for row in rows}


def _insert_dynamic(
    conn: _Connection,
    table_name: str,
    values: dict[str, Any],
    *,
    conflict_clause: str = "",
) -> None:
    """
    Insert only columns that exist in the current SQLite schema.

    This keeps the performance seed resilient across small schema changes while still
    failing loudly if the DB has a required NOT NULL column that the seed does not know
    how to populate.
    """
    columns = _table_columns(conn, table_name)

    insert_values = {key: value for key, value in values.items() if key in columns}

    missing_required = []
    for name, meta in columns.items():
        if name in insert_values:
            continue

        # SQLite PRAGMA fields:
        # - notnull: 1 when NOT NULL
        # - dflt_value: default expression, or None
        # - pk: 1-based primary key position, or 0
        required = bool(meta.get("notnull")) and meta.get("dflt_value") is None and not meta.get("pk")
        if required:
            missing_required.append(name)

    if missing_required:
        missing = ", ".join(sorted(missing_required))
        raise RuntimeError(
            f"Cannot seed table {table_name!r}. Missing required columns without defaults: {missing}"
        )

    column_names = list(insert_values.keys())
    placeholders = ", ".join("?" for _ in column_names)
    quoted_columns = ", ".join(column_names)
    sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders}) {conflict_clause}".strip()
    params = tuple(insert_values[name] for name in column_names)
    conn.execute(sql, params)


def seed(db_path: str) -> None:
    path = Path(db_path)
    storage_root = path.parent
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = _Connection(str(path))
    conn.execute("PRAGMA foreign_keys = ON")

    existing = conn.execute("SELECT id FROM users WHERE email = ?", (PERF_EMAIL,)).fetchone()

    if existing:
        user_id = existing["id"]
        print(f"[seed] User already exists: {user_id}")
    else:
        user_id = uuid.uuid4().hex
        now = int(time.time())
        _insert_dynamic(
            conn,
            "users",
            {
                "id": user_id,
                "name": PERF_NAME,
                "email": PERF_EMAIL,
                "password_hash": hash_password(PERF_PASSWORD),
                "system_role": "user",
                "created_at": now,
                "updated_at": now,
            },
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

        _insert_dynamic(
            conn,
            "campaigns",
            {
                "id": campaign_id,
                "owner_user_id": user_id,
                "title": "Perf Campaign",
                "description": "",
                "active_system_id": None,
                "initial_state_json": "{}",
                "persistent_state_json": "{}",
                "state_version": 1,
                "created_at": now,
                "updated_at": now,
            },
            conflict_clause="ON CONFLICT DO NOTHING",
        )

        _insert_dynamic(
            conn,
            "campaign_members",
            {
                "id": uuid.uuid4().hex,
                "campaign_id": campaign_id,
                "user_id": user_id,
                "role": "gm",
                "created_at": now,
                "updated_at": now,
            },
        )

        print(f"[seed] Created campaign: {campaign_id}")

    existing_scene = conn.execute(
        "SELECT id FROM scenes WHERE campaign_id = ? AND active = 1",
        (campaign_id,),
    ).fetchone()

    layer_id: str | None

    if existing_scene:
        scene_id = existing_scene["id"]
        print(f"[seed] Active scene already exists: {scene_id}")

        layer = conn.execute(
            "SELECT id FROM scene_layers WHERE scene_id = ? AND kind = 'raster_tile_refs'",
            (scene_id,),
        ).fetchone()

        layer_id = layer["id"] if layer else None
        tile_dir = storage_root / "scenes" / scene_id / "assets" / "tiles" / (layer_id or "")

        need_tiles = bool(
            layer_id
            and (
                not conn.execute(
                    "SELECT 1 FROM scene_tiles WHERE layer_id = ? LIMIT 1",
                    (layer_id,),
                ).fetchone()
                or not any(tile_dir.glob("*.png"))
            )
        )
    else:
        scene_id = uuid.uuid4().hex
        layer_id = uuid.uuid4().hex
        now = int(time.time())

        _insert_dynamic(
            conn,
            "scenes",
            {
                "id": scene_id,
                "campaign_id": campaign_id,
                "name": "Perf Scene",
                "status": "active",
                "visibility": "players",
                "width": SCENE_WIDTH,
                "height": SCENE_HEIGHT,
                "tile_size": TILE_SIZE,
                "chunk_size": CHUNK_SIZE,
                "image_scale": 1.0,
                "grid_visible": 1,
                "grid_color": "#ededed",
                "active": 1,
                "group_id": None,
                "tile_table_version": 1,
                # Current schema requires these JSON columns as NOT NULL.
                # Empty lists = no fog operations or board area markers yet.
                "fog_ops_json": "[]",
                "board_area_markers_json": "[]",
                "created_at": now,
                "updated_at": now,
            },
        )

        _insert_dynamic(
            conn,
            "scene_layers",
            {
                "id": layer_id,
                "scene_id": scene_id,
                "kind": "raster_tile_refs",
                "name": "Ground",
                "visibility": "visible",
                "display_order": 0,
                "encoding": "uint32_tile_refs_v1",
                "tile_table_version": 1,
                "created_at": now,
                "updated_at": now,
            },
            conflict_clause="ON CONFLICT DO NOTHING",
        )

        print(f"[seed] Created scene: {scene_id}, layer: {layer_id}")
        need_tiles = True

    if need_tiles and layer_id:
        tile_records = _generate_tiles(scene_id, layer_id, storage_root)
        now = int(time.time())

        for rec in tile_records:
            asset_id = rec["asset_id"]

            _insert_dynamic(
                conn,
                "scene_assets",
                {
                    "id": asset_id,
                    "scene_id": scene_id,
                    "kind": "tile",
                    "storage_path": rec["storage_path"],
                    "hash": rec["hash"],
                    "byte_size": rec["byte_size"],
                    "width": rec["width"],
                    "height": rec["height"],
                    "content_type": "image/png",
                    "created_at": now,
                },
                conflict_clause="ON CONFLICT DO NOTHING",
            )

            _insert_dynamic(
                conn,
                "scene_tiles",
                {
                    "scene_id": scene_id,
                    "layer_id": layer_id,
                    "tile_ref": rec["tile_ref"],
                    "asset_id": asset_id,
                    "tx": rec["tx"],
                    "ty": rec["ty"],
                    "width": rec["width"],
                    "height": rec["height"],
                    "hash": rec["hash"],
                    "byte_size": rec["byte_size"],
                    "created_at": now,
                },
                conflict_clause="ON CONFLICT DO NOTHING",
            )

    conn.commit()
    conn.close()

    print("\n[seed] Done.")
    print(f"  email:    {PERF_EMAIL}")
    print(f"  password: {PERF_PASSWORD}")
    print(f"  scene_id: {scene_id}")
    print(f"  layer_id: {layer_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="storage/gravewright.sqlite3")
    args = parser.parse_args()
    seed(args.db)
