"""Stable public snapshot DTOs for the SDK 1 semantic runtime."""

from __future__ import annotations

from typing import Any


def _pick(row: dict, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: row.get(name) for name in names if name in row}


def actor_snapshot(row: dict) -> dict[str, Any]:
    value = _pick(row, ("id", "campaign_id", "system_id", "type", "name", "folder_id", "portrait_asset_id", "token_asset_id", "version", "created_at", "updated_at"))
    value["owner_user_ids"] = [str(owner) for owner in row.get("owner_user_ids", [])]
    return value


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
    value = _pick(row, ("id", "scene_id", "kind", "door_state", "x1", "y1", "x2", "y2", "presentation", "discovered", "updated_at"))
    value["behavior"] = {name: row.get(f"{name}_behavior", "block") for name in ("movement", "vision", "light")}
    value["vertical"] = {"bottom": row.get("vertical_bottom"), "top": row.get("vertical_top")}
    return value


def light_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "x", "y", "elevation", "bright_radius", "dim_radius", "color", "intensity", "animation", "angle", "rotation", "enabled", "updated_at"))


def particle_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "x", "y", "kind", "scale", "density", "color", "enabled", "updated_at"))


def shader_metadata_snapshot(row: dict) -> dict[str, Any]:
    return _pick(row, ("id", "scene_id", "name", "x", "y", "radius", "rotation", "blend_mode", "opacity", "intensity", "scale", "speed", "color", "enabled", "updated_at"))


def roll_group_snapshot(group: dict) -> dict[str, Any]:
    """Project an internal roll group onto the exact public RollGroupDTO."""
    return {
        "faces": int(group.get("sides") or 0),
        "results": [int(result) for result in group.get("results") or []],
        "subtotal": int(group.get("subtotal") or 0),
    }


def chat_snapshot(row: dict) -> dict[str, Any]:
    snapshot = _pick(row, ("id", "campaign_id", "author_user_id", "author_name", "author_role", "kind", "content", "expression", "modifier", "total", "visibility", "metadata", "created_at"))
    groups = row.get("groups")
    snapshot["groups"] = (
        [roll_group_snapshot(group) for group in groups if isinstance(group, dict)]
        if isinstance(groups, list)
        else None
    )
    return snapshot


def token_snapshot(row: dict, *, controllers: list[str]) -> dict[str, Any]:
    """Project a core token view onto the declared public TokenDTO.

    The core view carries board-rendering and ownership fields the native UI
    needs; a package receives only the contracted shape, with `controllers`
    already filtered by the caller's authority to inspect control.
    """
    value = {
        "id": str(row.get("id") or row.get("token_id") or ""),
        "scene_id": row.get("scene_id"),
        "actor_id": row.get("actor_id"),
        "grid_x": row.get("grid_x"),
        "grid_y": row.get("grid_y"),
        "elevation": row.get("elevation"),
        "width_cells": row.get("width_cells"),
        "height_cells": row.get("height_cells"),
        "rotation": row.get("rotation"),
        "name": row.get("name"),
        "token_asset_url": row.get("token_asset_url"),
        "visible": bool(row.get("visible", True)),
        "hidden": bool(row.get("hidden", False)),
        "locked": bool(row.get("locked", False)),
        "disposition": row.get("disposition"),
        "vision": row.get("vision") or {
            "enabled": bool(row.get("vision_enabled", True)),
            "range": row.get("vision_range"),
            "source": "token",
        },
        "controllers": list(controllers),
        "updated_at": row.get("updated_at"),
    }
    return value
