"""Stable public snapshot DTOs for the SDK 1 semantic runtime."""

from __future__ import annotations

from typing import Any


def _pick(row: dict, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: row.get(name) for name in names if name in row}


def actor_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "campaign_id", "system_id", "type", "name", "folder_id", "portrait_asset_id", "token_asset_id", "version", "created_at", "updated_at"))


def item_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "campaign_id", "system_id", "type", "name", "folder_id", "portrait_asset_id", "version", "created_at", "updated_at"))


def scene_snapshot(row: dict) -> dict[str, Any]:
    raster = int(row.get("tile_size") or 0)
    grid = int(row.get("grid_size") or raster)
    chunk_span = int(row.get("chunk_size") or 0)
    result = _pick(row, ("id", "campaign_id", "name", "width", "height", "version", "scene_epoch", "tile_table_version", "grid_visible", "grid_color", "grid_opacity", "darkness", "start_world_x", "start_world_y", "start_zoom"))
    result.update({"grid_size": grid, "raster_tile_size": raster, "chunk_span": chunk_span})
    return result


def wall_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "kind", "door_state", "x1", "y1", "x2", "y2", "updated_at"))


def light_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "x", "y", "bright_radius", "dim_radius", "color", "intensity", "animation", "angle", "rotation", "enabled", "updated_at"))


def particle_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "x", "y", "kind", "scale", "density", "color", "enabled", "updated_at"))


def shader_metadata_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "name", "x", "y", "radius", "rotation", "blend_mode", "opacity", "intensity", "scale", "speed", "color", "enabled", "updated_at"))


def chat_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "campaign_id", "author_user_id", "author_name", "author_role", "kind", "content", "expression", "groups", "modifier", "total", "visibility", "metadata", "created_at"))
