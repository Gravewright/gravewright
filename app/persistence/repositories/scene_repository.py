from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.engine import Connection

from app.domain.scenes import SceneStatus
from app.domain.scenes import SceneVisibility
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scenes as scenes_table


class SceneRepository:
    """Scene persistence implemented with SQLAlchemy Core."""

    def create(
        self,
        *,
        campaign_id: str,
        name: str,
        width: int,
        height: int,
        tile_size: int,
        chunk_size: int,
        group_id: str | None = None,
        status: SceneStatus = SceneStatus.DRAFT,
        visibility: SceneVisibility = SceneVisibility.PLAYERS,
        active: bool = False,
        grid_visible: bool = True,
        grid_color: str = "#6fddb4",
        grid_opacity: float = 0.4,
        start_world_x: float | None = None,
        start_world_y: float | None = None,
        start_zoom: float = 1.0,
        tile_table_version: int = 1,
        scene_epoch: int = 1,
    ) -> dict:
        now = int(time.time())
        scene_id = uuid.uuid4().hex
        start_world_x = float(width) / 2.0 if start_world_x is None else float(start_world_x)
        start_world_y = float(height) / 2.0 if start_world_y is None else float(start_world_y)

        with engine_begin() as conn:
            conn.execute(
                insert(scenes_table).values(
                    id=scene_id,
                    campaign_id=campaign_id,
                    group_id=group_id,
                    name=name,
                    status=status.value,
                    visibility=visibility.value,
                    active=1 if active else 0,
                    width=width,
                    height=height,
                    tile_size=tile_size,
                    chunk_size=chunk_size,
                    grid_visible=1 if grid_visible else 0,
                    grid_color=grid_color,
                    grid_opacity=grid_opacity,
                    start_world_x=start_world_x,
                    start_world_y=start_world_y,
                    start_zoom=start_zoom,
                    tile_table_version=tile_table_version,
                    scene_epoch=scene_epoch,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_by_id(conn, scene_id)

        if row is None:
            raise RuntimeError("Created scene could not be read back.")
        return row

    def get_by_id(self, scene_id: str) -> dict | None:
        with engine_connect() as conn:
            return self._get_by_id(conn, scene_id)

    def list_by_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scenes_table)
                    .where(scenes_table.c.campaign_id == campaign_id)
                    .order_by(scenes_table.c.created_at.asc())
                )
            )

    def get_active_scene(self, campaign_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(scenes_table)
                    .where(scenes_table.c.campaign_id == campaign_id)
                    .where(scenes_table.c.active == 1)
                    .limit(1)
                )
            )

    def delete(self, scene_id: str) -> None:
        """Remove a scene and its dependent rows via ON DELETE CASCADE."""
        with engine_begin() as conn:
            conn.execute(delete(scenes_table).where(scenes_table.c.id == scene_id))

    def set_active_scene(
        self,
        *,
        campaign_id: str,
        scene_id: str,
    ) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            target = one_or_none(
                conn.execute(
                    select(scenes_table)
                    .where(scenes_table.c.id == scene_id)
                    .where(scenes_table.c.campaign_id == campaign_id)
                    .limit(1)
                )
            )
            if target is None:
                return None

            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.campaign_id == campaign_id)
                .where(scenes_table.c.active == 1)
                .values(active=0, status=SceneStatus.DRAFT.value, updated_at=now)
            )
            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(
                    active=1,
                    status=SceneStatus.ACTIVE.value,
                    scene_epoch=scenes_table.c.scene_epoch + 1,
                    updated_at=now,
                )
            )
            return self._get_by_id(conn, scene_id)

    def update_metadata(
        self,
        *,
        scene_id: str,
        name: str,
        group_id: str | None,
        visibility: SceneVisibility,
        grid_visible: bool,
        grid_color: str,
        grid_opacity: float,
        tile_size: int,
        image_scale: float,
        tile_table_version: int,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            existing = one_or_none(
                conn.execute(
                    select(
                        scenes_table.c.visibility,
                        scenes_table.c.grid_visible,
                        scenes_table.c.grid_color,
                        scenes_table.c.grid_opacity,
                        scenes_table.c.tile_size,
                        scenes_table.c.image_scale,
                        scenes_table.c.tile_table_version,
                    )
                    .where(scenes_table.c.id == scene_id)
                    .limit(1)
                )
            )

            bump_epoch = False
            if existing is not None:
                bump_epoch = (
                    existing["visibility"] != visibility.value
                    or bool(existing["grid_visible"]) != grid_visible
                    or existing["grid_color"] != grid_color
                    or float(existing["grid_opacity"]) != float(grid_opacity)
                    or existing["tile_size"] != tile_size
                    or float(existing["image_scale"]) != float(image_scale)
                    or existing["tile_table_version"] != tile_table_version
                )

            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(
                    name=name,
                    group_id=group_id,
                    visibility=visibility.value,
                    grid_visible=1 if grid_visible else 0,
                    grid_color=grid_color,
                    grid_opacity=grid_opacity,
                    tile_size=tile_size,
                    image_scale=image_scale,
                    tile_table_version=tile_table_version,
                    scene_epoch=scenes_table.c.scene_epoch + (1 if bump_epoch else 0),
                    updated_at=now,
                )
            )

    def increment_scene_epoch(self, scene_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(scene_epoch=scenes_table.c.scene_epoch + 1, updated_at=now)
            )

    def update_start_point(
        self,
        *,
        scene_id: str,
        start_world_x: float,
        start_world_y: float,
        start_zoom: float,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(
                    start_world_x=start_world_x,
                    start_world_y=start_world_y,
                    start_zoom=start_zoom,
                    updated_at=now,
                )
            )

    def archive(self, scene_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(active=0, status=SceneStatus.ARCHIVED.value, updated_at=now)
            )

    def write_fog(
        self,
        *,
        scene_id: str,
        enabled: bool,
        baseline: str,
        ops_json: str,
        version: int,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .values(
                    fog_enabled=1 if enabled else 0,
                    fog_baseline=baseline,
                    fog_ops_json=ops_json,
                    fog_version=version,
                    updated_at=now,
                )
            )

    def write_fog_ops_cas(
        self,
        *,
        scene_id: str,
        baseline: str,
        ops_json: str,
        expected_version: int,
        new_version: int,
    ) -> bool:
        """Atomically append fog ops only if the version still matches."""
        now = int(time.time())
        with engine_begin() as conn:
            result = conn.execute(
                update(scenes_table)
                .where(scenes_table.c.id == scene_id)
                .where(scenes_table.c.fog_enabled == 1)
                .where(scenes_table.c.fog_version == expected_version)
                .values(
                    fog_ops_json=ops_json,
                    fog_version=new_version,
                    updated_at=now,
                )
            )
            return result.rowcount == 1

    def list_board_area_markers(self, scene_id: str) -> list[dict[str, Any]]:
        scene = self.get_by_id(scene_id)
        if scene is None:
            return []
        return _load_board_area_markers(scene["board_area_markers_json"])

    def get_board_version(self, scene_id: str) -> int | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(scenes_table.c.board_version)
                    .where(scenes_table.c.id == scene_id)
                    .limit(1)
                )
            )
        return None if row is None else int(row["board_version"] or 0)

    def upsert_board_area_marker(
        self,
        *,
        scene_id: str,
        marker: dict[str, Any],
        expected_board_version: int | None = None,
    ) -> list[dict[str, Any]] | None:
        now = int(time.time())
        with engine_begin() as conn:
            board_state = self._read_board_area_markers_state(conn, scene_id)
            if board_state is None:
                return None
            raw, current_version = board_state

            markers = _load_board_area_markers(raw)
            next_marker = _normalize_board_area_marker(marker)
            if next_marker["scene_id"] != scene_id:
                raise ValueError("marker.scene_id must match scene_id")
            idx = next((i for i, existing in enumerate(markers) if existing["id"] == next_marker["id"]), -1)
            if idx >= 0:
                markers[idx] = next_marker
            else:
                markers.append(next_marker)

            result = self._write_board_area_markers(
                conn,
                scene_id=scene_id,
                markers=markers,
                now=now,
                expected_board_version=expected_board_version,
            )
            return markers if result.rowcount == 1 else None

    def delete_board_area_marker(
        self,
        *,
        scene_id: str,
        marker_id: str,
        expected_board_version: int | None = None,
    ) -> list[dict[str, Any]] | None:
        now = int(time.time())
        with engine_begin() as conn:
            board_state = self._read_board_area_markers_state(conn, scene_id)
            if board_state is None:
                return None
            raw, current_version = board_state

            markers = [
                marker
                for marker in _load_board_area_markers(raw)
                if marker["id"] != marker_id
            ]
            result = self._write_board_area_markers(
                conn,
                scene_id=scene_id,
                markers=markers,
                now=now,
                expected_board_version=expected_board_version,
            )
            return markers if result.rowcount == 1 else None

    def clear_board_area_markers(
        self,
        scene_id: str,
        *,
        keep_gm_layer: bool = False,
        expected_board_version: int | None = None,
    ) -> bool:
        now = int(time.time())
        with engine_begin() as conn:
            board_state = self._read_board_area_markers_state(conn, scene_id)
            if board_state is None:
                return False
            raw, current_version = board_state

                                                                                         
            kept = (
                [
                    marker
                    for marker in _load_board_area_markers(raw)
                    if marker.get("layer") == "gm"
                ]
                if keep_gm_layer
                else []
            )
            result = self._write_board_area_markers(
                conn,
                scene_id=scene_id,
                markers=kept,
                now=now,
                expected_board_version=expected_board_version,
            )
            return result.rowcount > 0

    def clear_board_drawings(
        self,
        scene_id: str,
        *,
        owner_id: str | None = None,
        expected_board_version: int | None = None,
    ) -> list[dict[str, Any]] | None:
        now = int(time.time())

        def _keep(marker: dict[str, Any]) -> bool:
            if marker.get("kind") not in ("freehand", "text"):
                return True
                                                                                       
            return owner_id is not None and marker.get("owner_id") != owner_id

        with engine_begin() as conn:
            board_state = self._read_board_area_markers_state(conn, scene_id)
            if board_state is None:
                return None
            raw, current_version = board_state

            markers = [marker for marker in _load_board_area_markers(raw) if _keep(marker)]
            result = self._write_board_area_markers(
                conn,
                scene_id=scene_id,
                markers=markers,
                now=now,
                expected_board_version=expected_board_version,
            )
            return markers if result.rowcount == 1 else None

    @staticmethod
    def _get_by_id(conn: Connection, scene_id: str) -> dict | None:
        return one_or_none(
            conn.execute(select(scenes_table).where(scenes_table.c.id == scene_id).limit(1))
        )

    @staticmethod
    def _read_board_area_markers_state(conn: Connection, scene_id: str) -> tuple[str, int] | None:
        row = one_or_none(
            conn.execute(
                select(
                    scenes_table.c.board_area_markers_json,
                    scenes_table.c.board_version,
                )
                .where(scenes_table.c.id == scene_id)
                .limit(1)
            )
        )
        if row is None:
            return None
        return row["board_area_markers_json"], int(row["board_version"] or 0)

    @staticmethod
    def _write_board_area_markers(
        conn: Connection,
        *,
        scene_id: str,
        markers: list[dict[str, Any]],
        now: int,
        expected_board_version: int | None = None,
    ):
        stmt = update(scenes_table).where(scenes_table.c.id == scene_id)
        if expected_board_version is not None:
            stmt = stmt.where(scenes_table.c.board_version == expected_board_version)
        return conn.execute(
            stmt.values(
                board_area_markers_json=json.dumps(markers, separators=(",", ":")),
                board_version=scenes_table.c.board_version + 1,
                updated_at=now,
            )
        )

def _load_board_area_markers(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    markers = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            markers.append(_normalize_board_area_marker(item))
        except ValueError:
            continue
    return markers


def _normalize_board_area_marker(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("kind") == "freehand":
        return _normalize_board_freehand(raw)
    if raw.get("kind") == "text":
        return _normalize_board_text(raw)

    marker_id = raw.get("id")
    scene_id = raw.get("scene_id")
    shape = raw.get("shape")
    start = raw.get("start")
    end = raw.get("end")
    if not isinstance(marker_id, str) or not marker_id:
        raise ValueError("marker.id is required")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("marker.scene_id is required")
    if shape not in {"line", "circle", "square", "cone"}:
        raise ValueError("marker.shape is invalid")
    if not isinstance(start, dict) or not isinstance(end, dict):
        raise ValueError("marker points are required")
    return {
        "id": marker_id,
        "scene_id": scene_id,
        "shape": shape,
        "start": _normalize_board_area_marker_point(start),
        "end": _normalize_board_area_marker_point(end),
        **_normalize_board_area_marker_preset_id(raw.get("preset_id")),
        **_normalize_board_area_marker_style(raw.get("style")),
        **_normalize_board_layer(raw.get("layer")),
    }


def _normalize_board_layer(raw: Any) -> dict[str, str]:
                                                                                  
                                                
    return {"layer": "gm"} if raw == "gm" else {}


def _normalize_board_owner(raw: Any) -> dict[str, str]:
    if not isinstance(raw, str) or not raw:
        return {}
    return {"owner_id": raw[:128]}


def _normalize_board_area_marker_point(raw: dict[str, Any]) -> dict[str, float]:
    world_x = raw.get("worldX")
    world_y = raw.get("worldY")
    if not isinstance(world_x, int | float) or not isinstance(world_y, int | float):
        raise ValueError("marker point coordinates are required")
    return {"worldX": float(world_x), "worldY": float(world_y)}


def _normalize_board_area_marker_style(raw: Any) -> dict[str, dict[str, str | float]]:
    if not isinstance(raw, dict):
        return {}
    style: dict[str, str | float] = {}
    for key in ("stroke", "fill", "strokeDasharray"):
        value = raw.get(key)
        if isinstance(value, str) and 0 < len(value) <= 64:
            style[key] = value
    stroke_width = raw.get("strokeWidth")
    if isinstance(stroke_width, int | float):
        style["strokeWidth"] = max(1.0, min(12.0, float(stroke_width)))
    return {"style": style} if style else {}


def _normalize_board_area_marker_preset_id(raw: Any) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, str):
        raise ValueError("marker.preset_id must be a string")
    preset_id = raw.strip()
    if not preset_id:
        return {}
    if len(preset_id) > 80:
        raise ValueError("marker.preset_id is too long")
    return {"preset_id": preset_id}


def _normalize_board_freehand(raw: dict[str, Any]) -> dict[str, Any]:
    marker_id = raw.get("id")
    scene_id = raw.get("scene_id")
    points = raw.get("points")
    if not isinstance(marker_id, str) or not marker_id:
        raise ValueError("drawing.id is required")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("drawing.scene_id is required")
    if not isinstance(points, list) or len(points) < 2 or len(points) > 512:
        raise ValueError("drawing.points must contain 2 to 512 points")
    normalized_points = [
        _normalize_board_area_marker_point(point)
        for point in points
        if isinstance(point, dict)
    ]
    if len(normalized_points) < 2:
        raise ValueError("drawing.points must contain 2 valid points")
    return {
        "id": marker_id,
        "scene_id": scene_id,
        "kind": "freehand",
        "points": normalized_points,
        **_normalize_board_area_marker_style(raw.get("style")),
        **_normalize_board_layer(raw.get("layer")),
        **_normalize_board_owner(raw.get("owner_id")),
    }


def _normalize_board_text(raw: dict[str, Any]) -> dict[str, Any]:
    marker_id = raw.get("id")
    scene_id = raw.get("scene_id")
    text = raw.get("text")
    position = raw.get("position")
    if not isinstance(marker_id, str) or not marker_id:
        raise ValueError("drawing.id is required")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("drawing.scene_id is required")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("drawing.text is required")
    if not isinstance(position, dict):
        raise ValueError("drawing.position is required")
    font_size = raw.get("fontSize")
    if not isinstance(font_size, int | float):
        font_size = 28.0
    return {
        "id": marker_id,
        "scene_id": scene_id,
        "kind": "text",
        "position": _normalize_board_area_marker_point(position),
        "text": text.strip()[:200],
        "fontSize": max(8.0, min(200.0, float(font_size))),
        **_normalize_board_area_marker_style(raw.get("style")),
        **_normalize_board_layer(raw.get("layer")),
        **_normalize_board_owner(raw.get("owner_id")),
    }
