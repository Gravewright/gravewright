from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path


SCENE_ID = "779acc729cc24273a3877adfd77e1f3b"
CAMPAIGN_ID = "9456741070444fbf9b943a69b603b3f2"
GM_ID = "93a0fe9502ca49098e24ae02787c6215"


def seed(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    db = sqlite3.connect(target)
    now = int(time.time())
    for table in ("tokens", "scene_walls", "scene_lights", "scene_particles"):
        db.execute(f"DELETE FROM {table} WHERE scene_id = ?", (SCENE_ID,))
    db.execute(
        "UPDATE scenes SET grid_size=70, start_world_x=2500, start_world_y=2500, start_zoom=.28, "
        "fog_enabled=1, fog_baseline='hide_all', fog_ops_json=?, "
        "fog_version=fog_version+1, darkness=.62 WHERE id=?",
        (json.dumps([{"mode": "reveal", "shape": "circle", "x": 2500, "y": 2500, "size": 850}]), SCENE_ID),
    )
    for i in range(150):
        overrides = {"bars": {"hp": {"value": 37 + i % 63, "max": 100}}} if i < 30 else {}
        name = f"Campaign token {i + 1}" if i % 4 == 0 else None
        db.execute(
            "INSERT INTO tokens (id,scene_id,grid_x,grid_y,width_cells,height_cells,rotation,name,visible,hidden,locked,disposition,actor_link_mode,overrides_json,controlled_by_user_ids_json,controlled_by_role,version,created_at,updated_at,vision_enabled,vision_range) VALUES (?,?,?,?,?,?,?,?,1,0,0,?,'unlinked',?,'[]','gm',1,?,?,1,12)",
            (f"bench-token-{i}", SCENE_ID, 4 + i % 42, 4 + (i // 42) * 4, 1, 1, 0, name, "hostile" if i % 3 == 0 else "neutral", json.dumps(overrides), now, now),
        )
    for i in range(750):
        row, col = divmod(i, 30)
        x, y = 120 + col * 155, 120 + row * 185
        door = i < 75
        db.execute(
            "INSERT INTO scene_walls (id,campaign_id,scene_id,kind,door_state,x1,y1,x2,y2,created_by_user_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"bench-wall-{i}", CAMPAIGN_ID, SCENE_ID, "door" if door else "wall", "closed", x, y, x + (70 if i % 2 else 0), y + (0 if i % 2 else 70), GM_ID, now, now),
        )
    animations = ("none", "torch", "pulse")
    for i in range(40):
        db.execute(
            "INSERT INTO scene_lights (id,campaign_id,scene_id,x,y,bright_radius,dim_radius,color,intensity,animation,enabled,created_by_user_id,created_at,updated_at,angle,rotation) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"bench-light-{i}", CAMPAIGN_ID, SCENE_ID, 250 + (i % 8) * 590, 250 + (i // 8) * 900, 2.5, 6.0, "#ffd29a", .82, animations[i % len(animations)], 1, GM_ID, now, now, 360 if i % 5 else 90, (i * 31) % 360),
        )
    for i in range(8):
        db.execute(
            "INSERT INTO scene_particles (id,campaign_id,scene_id,x,y,kind,scale,density,color,enabled,created_by_user_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"bench-particle-{i}", CAMPAIGN_ID, SCENE_ID, 500 + i * 520, 700 + (i % 3) * 1100, ("smoke", "ember", "dust")[i % 3], 2.5, .25, "#9aa3ad", 1, GM_ID, now, now),
        )
    db.commit()
    counts = {table: db.execute(f"SELECT count(*) FROM {table} WHERE scene_id=?", (SCENE_ID,)).fetchone()[0] for table in ("tokens", "scene_walls", "scene_lights", "scene_particles")}
    db.close()
    print(json.dumps({"database": str(target), "scene_id": SCENE_ID, "counts": counts}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="storage/gravewright.sqlite3")
    parser.add_argument("--target", default=".tmp/real-campaign/gravewright.sqlite3")
    args = parser.parse_args()
    seed(Path(args.source), Path(args.target))
