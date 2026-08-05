from __future__ import annotations

import json
from dataclasses import dataclass

from app.business.permissions.permission_service import PermissionService
from app.domain.fog import FogCircleGeom
from app.domain.fog import FogInitialState
from app.domain.fog import FogOp
from app.domain.fog import FogPolygonGeom
from app.domain.fog import FogSquareGeom
from app.domain.permissions.permissions import TablePermission
from app.persistence.repositories.scene_repository import SceneRepository


                                                                               
                                                                           
MAX_FOG_TOTAL_OPS = 20_000


@dataclass(frozen=True)
class FogServiceResult:
    success: bool
    scene_id: str | None = None
    campaign_id: str | None = None
    enabled: bool = False
    version: int = 0
    baseline: str = FogInitialState.HIDE_ALL.value
    ops: list[dict] | None = None
    new_ops: list[dict] | None = None
    error_key: str | None = None


def _op_to_dict(op: FogOp) -> dict:
    geom = op.geom
    if isinstance(geom, FogCircleGeom):
        geom_dict = {
            "center_x_cells": geom.center_x_cells,
            "center_y_cells": geom.center_y_cells,
            "radius_cells": geom.radius_cells,
        }
    elif isinstance(geom, FogSquareGeom):
        geom_dict = {
            "center_x_cells": geom.center_x_cells,
            "center_y_cells": geom.center_y_cells,
            "size_cells": geom.size_cells,
        }
    elif isinstance(geom, FogPolygonGeom):
        geom_dict = {
            "points_cells": [[x, y] for x, y in geom.points_cells],
        }
    else:
        raise TypeError("unknown geom type")
    return {"mode": op.mode.value, "shape": op.shape.value, "geom": geom_dict}


def _load_ops(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return data


class FogService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        permissions: PermissionService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.permissions = permissions or PermissionService()

    def get_state(self, scene_id: str) -> FogServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return FogServiceResult(success=False, error_key="game.scenes.errors.not_found")

        return FogServiceResult(
            success=True,
            scene_id=scene["id"],
            campaign_id=scene["campaign_id"],
            enabled=bool(scene["fog_enabled"]),
            baseline=scene["fog_baseline"] or FogInitialState.HIDE_ALL.value,
            ops=_load_ops(scene["fog_ops_json"]),
            version=int(scene["fog_version"]),
        )

    def enable(
        self,
        *,
        scene_id: str,
        user_id: str,
        initial: FogInitialState,
    ) -> FogServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return FogServiceResult(success=False, error_key="game.scenes.errors.not_found")
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.FOG_PAINT,
        ):
            return FogServiceResult(success=False, error_key="permissions.errors.denied")

        version = int(scene["fog_version"]) + 1
        self.scenes.write_fog(
            scene_id=scene_id,
            enabled=True,
            baseline=initial.value,
            ops_json="[]",
            version=version,
        )
        return FogServiceResult(
            success=True,
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            enabled=True,
            baseline=initial.value,
            ops=[],
            version=version,
        )

    def disable(self, *, scene_id: str, user_id: str) -> FogServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return FogServiceResult(success=False, error_key="game.scenes.errors.not_found")
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.FOG_PAINT,
        ):
            return FogServiceResult(success=False, error_key="permissions.errors.denied")

        version = int(scene["fog_version"]) + 1
        self.scenes.write_fog(
            scene_id=scene_id,
            enabled=False,
            baseline=scene["fog_baseline"] or FogInitialState.HIDE_ALL.value,
            ops_json="[]",
            version=version,
        )
        return FogServiceResult(
            success=True,
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            enabled=False,
            baseline=scene["fog_baseline"] or FogInitialState.HIDE_ALL.value,
            ops=[],
            version=version,
        )

    def reset(
        self,
        *,
        scene_id: str,
        user_id: str,
        to: FogInitialState,
    ) -> FogServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return FogServiceResult(success=False, error_key="game.scenes.errors.not_found")
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.FOG_PAINT,
        ):
            return FogServiceResult(success=False, error_key="permissions.errors.denied")
        if not bool(scene["fog_enabled"]):
            return FogServiceResult(success=False, error_key="game.fog.errors.disabled")

        version = int(scene["fog_version"]) + 1
        self.scenes.write_fog(
            scene_id=scene_id,
            enabled=True,
            baseline=to.value,
            ops_json="[]",
            version=version,
        )
        return FogServiceResult(
            success=True,
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            enabled=True,
            baseline=to.value,
            ops=[],
            version=version,
        )

    def paint(
        self,
        *,
        scene_id: str,
        user_id: str,
        ops: list[FogOp],
        expected_version: int | None = None,
    ) -> FogServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return FogServiceResult(success=False, error_key="game.scenes.errors.not_found")
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.FOG_PAINT,
        ):
            return FogServiceResult(success=False, error_key="permissions.errors.denied")
        if not bool(scene["fog_enabled"]):
            return FogServiceResult(success=False, error_key="game.fog.errors.disabled")

        current_version = int(scene["fog_version"])
        if expected_version is not None and expected_version != current_version:
            return FogServiceResult(success=False, error_key="game.fog.errors.version_conflict")

        existing = _load_ops(scene["fog_ops_json"])
        new_dicts = [_op_to_dict(op) for op in ops]

                                                                               
                                                                              
                                                                         
        if len(existing) + len(new_dicts) > MAX_FOG_TOTAL_OPS:
            return FogServiceResult(success=False, error_key="game.fog.errors.too_many_ops")

        all_ops = existing + new_dicts
        baseline = scene["fog_baseline"] or FogInitialState.HIDE_ALL.value
        version = current_version + 1

        if expected_version is None:
                                                                                  
                              
            self.scenes.write_fog(
                scene_id=scene_id,
                enabled=True,
                baseline=baseline,
                ops_json=json.dumps(all_ops),
                version=version,
            )
        else:
                                                                              
                                                                                  
            committed = self.scenes.write_fog_ops_cas(
                scene_id=scene_id,
                baseline=baseline,
                ops_json=json.dumps(all_ops),
                expected_version=expected_version,
                new_version=version,
            )
            if not committed:
                return FogServiceResult(
                    success=False, error_key="game.fog.errors.version_conflict"
                )

        return FogServiceResult(
            success=True,
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            enabled=True,
            baseline=baseline,
            ops=all_ops,
            new_ops=new_dicts,
            version=version,
        )
