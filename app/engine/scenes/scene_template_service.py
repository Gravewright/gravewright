from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot, isfinite
from typing import Any
from uuid import uuid4

from app.business.permissions.permission_service import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository


SHAPES = frozenset({"circle", "cone", "line", "rectangle"})


@dataclass(frozen=True)
class TemplateResult:
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class SceneTemplateService:
    """Persistent shared gameplay templates backed by semantic board markers."""

    def __init__(self) -> None:
        self.scenes = SceneRepository()
        self.campaigns = CampaignRepository()
        self.permissions = PermissionService()

    def list(self, *, campaign_id: str, scene_id: str, user_id: str) -> TemplateResult:
        scene, role = self._scene(campaign_id, scene_id, user_id)
        if scene is None:
            return TemplateResult(False, error_key="sdk.templates.not_found")
        templates = [
            self._present(marker, int(scene.get("board_version") or 0))
            for marker in self.scenes.list_board_area_markers(scene_id)
            if marker.get("kind") not in {"freehand", "text"}
            and (marker.get("layer") != "gm" or role == "gm")
        ]
        return TemplateResult(True, {"templates": templates, "version": int(scene.get("board_version") or 0)})

    def create(self, *, campaign_id: str, scene_id: str, user_id: str, values: dict) -> TemplateResult:
        scene, role = self._scene(campaign_id, scene_id, user_id)
        if scene is None:
            return TemplateResult(False, error_key="sdk.templates.not_found")
        if not self.permissions.can(user_id=user_id, campaign_id=campaign_id, permission=TablePermission.BOARD_MARKER_CREATE):
            return TemplateResult(False, error_key="sdk.templates.denied")
        marker = self._normalize(scene, values, template_id=uuid4().hex, user_id=user_id, role=role)
        if marker is None:
            return TemplateResult(False, error_key="sdk.templates.invalid")
        updated = self.scenes.upsert_board_area_marker(
            scene_id=scene_id, marker=marker, expected_board_version=int(scene.get("board_version") or 0)
        )
        if updated is None:
            return TemplateResult(False, error_key="sdk.templates.stale_version")
        refreshed = self.scenes.get_by_id(scene_id) or scene
        return TemplateResult(True, {"template": self._present(marker, int(refreshed.get("board_version") or 0))})

    def update(self, *, campaign_id: str, template_id: str, user_id: str, values: dict, expected_version: int | None) -> TemplateResult:
        found = self._find(campaign_id, template_id, user_id)
        if found is None:
            return TemplateResult(False, error_key="sdk.templates.not_found")
        scene, current, role = found
        if role != "gm" and current.get("owner_id") != user_id:
            return TemplateResult(False, error_key="sdk.templates.denied")
        version = int(scene.get("board_version") or 0)
        if expected_version is not None and expected_version != version:
            return TemplateResult(False, error_key="sdk.templates.stale_version")
        merged = {**self._present(current, version), **values}
        marker = self._normalize(scene, merged, template_id=template_id, user_id=str(current.get("owner_id") or user_id), role=role)
        if marker is None:
            return TemplateResult(False, error_key="sdk.templates.invalid")
        updated = self.scenes.upsert_board_area_marker(scene_id=scene["id"], marker=marker, expected_board_version=version)
        if updated is None:
            return TemplateResult(False, error_key="sdk.templates.stale_version")
        refreshed = self.scenes.get_by_id(scene["id"]) or scene
        return TemplateResult(True, {"template": self._present(marker, int(refreshed.get("board_version") or 0))})

    def delete(self, *, campaign_id: str, template_id: str, user_id: str, expected_version: int | None) -> TemplateResult:
        found = self._find(campaign_id, template_id, user_id)
        if found is None:
            return TemplateResult(False, error_key="sdk.templates.not_found")
        scene, current, role = found
        if role != "gm" and current.get("owner_id") != user_id:
            return TemplateResult(False, error_key="sdk.templates.denied")
        version = int(scene.get("board_version") or 0)
        if expected_version is not None and expected_version != version:
            return TemplateResult(False, error_key="sdk.templates.stale_version")
        updated = self.scenes.delete_board_area_marker(scene_id=scene["id"], marker_id=template_id, expected_board_version=version)
        if updated is None:
            return TemplateResult(False, error_key="sdk.templates.stale_version")
        refreshed = self.scenes.get_by_id(scene["id"]) or scene
        return TemplateResult(True, {"template_id": template_id, "scene_id": scene["id"], "version": int(refreshed.get("board_version") or 0), "audience": self._audience(current)})

    def _find(self, campaign_id: str, template_id: str, user_id: str):
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return None
        for scene in self.scenes.list_by_campaign(campaign_id):
            for marker in self.scenes.list_board_area_markers(scene["id"]):
                if marker.get("id") == template_id and marker.get("kind") not in {"freehand", "text"}:
                    if marker.get("layer") == "gm" and role != "gm":
                        return None
                    return scene, marker, role
        return None

    def _scene(self, campaign_id: str, scene_id: str, user_id: str):
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        scene = self.scenes.get_by_id(scene_id)
        return (scene, role) if role and scene and scene.get("campaign_id") == campaign_id else (None, None)

    def _normalize(self, scene: dict, values: dict, *, template_id: str, user_id: str, role: str | None) -> dict | None:
        shape = str(values.get("shape") or "")
        origin = values.get("origin") if isinstance(values.get("origin"), dict) else values.get("start")
        target = values.get("target") if isinstance(values.get("target"), dict) else values.get("end")
        if shape not in SHAPES or not isinstance(origin, dict) or not isinstance(target, dict):
            return None
        try:
            x1, y1 = float(origin.get("x", origin.get("worldX"))), float(origin.get("y", origin.get("worldY")))
            x2, y2 = float(target.get("x", target.get("worldX"))), float(target.get("y", target.get("worldY")))
        except (TypeError, ValueError):
            return None
        if not all(isfinite(value) for value in (x1, y1, x2, y2)):
            return None
        width, height = float(scene.get("width") or 0), float(scene.get("height") or 0)
        if not (0 <= x1 <= width and 0 <= x2 <= width and 0 <= y1 <= height and 0 <= y2 <= height):
            return None
        if hypot(x2 - x1, y2 - y1) <= 0 or hypot(x2 - x1, y2 - y1) > hypot(width, height):
            return None
        audience = str(values.get("audience") or "campaign")
        if audience not in {"campaign", "gm"} or (audience == "gm" and role != "gm"):
            return None
        return {
            "id": template_id, "scene_id": scene["id"],
            "shape": "square" if shape == "rectangle" else shape,
            "start": {"worldX": x1, "worldY": y1}, "end": {"worldX": x2, "worldY": y2},
            "owner_id": user_id, **({"layer": "gm"} if audience == "gm" else {}),
        }

    @staticmethod
    def _audience(marker: dict) -> str:
        return "gm" if marker.get("layer") == "gm" else "campaign"

    def _present(self, marker: dict, version: int) -> dict:
        start, end = marker.get("start") or {}, marker.get("end") or {}
        return {
            "id": marker["id"], "sceneId": marker["scene_id"],
            "shape": "rectangle" if marker.get("shape") == "square" else marker.get("shape"),
            "origin": {"x": float(start.get("worldX") or 0), "y": float(start.get("worldY") or 0)},
            "target": {"x": float(end.get("worldX") or 0), "y": float(end.get("worldY") or 0)},
            "creatorId": marker.get("owner_id"), "audience": self._audience(marker),
            "persistence": "persistent", "version": version,
        }
