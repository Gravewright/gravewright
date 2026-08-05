from __future__ import annotations

from dataclasses import dataclass

from app.business.permissions.permission_service import PermissionService
from app.domain.scenes import RenderPriority
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.engine.scenes.scene_visibility_service import SceneVisibilityService
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.viewport_priority import classify_chunk_priority


@dataclass(frozen=True)
class ViewportChunkPayload:
    scene_id: str
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    byte_size: int
    encoding: str
    data: bytes


@dataclass(frozen=True)
class ViewportChunkCandidate:
    scene_id: str
    scene_epoch: int
    viewport_id: str
    viewport_generation: int
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    byte_size: int
    encoding: str
    priority: RenderPriority
    priority_distance: int
    priority_ring: str


@dataclass(frozen=True)
class ViewportChunkCandidateResult:
    success: bool
    scene_id: str | None = None
    scene_epoch: int | None = None
    viewport_id: str | None = None
    viewport_generation: int | None = None
    chunks: tuple[ViewportChunkCandidate, ...] = ()
    missing_count: int = 0
    stale_count: int = 0
    error_key: str | None = None


@dataclass(frozen=True)
class ViewportSubscriptionResult:
    success: bool
    scene_id: str | None = None
    scene_epoch: int | None = None
    viewport_id: str | None = None
    viewport_generation: int | None = None
    chunks: tuple[ViewportChunkPayload, ...] = ()
    missing_count: int = 0
    stale_count: int = 0
    error_key: str | None = None


class ViewportSubscriptionService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        chunk_service: SceneChunkService | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)
        self.chunk_service = chunk_service or SceneChunkService(
            scenes=self.scenes,
            layers=self.layers,
            permissions=self.permissions,
            visibility=self.visibility,
        )

    def resolve_viewport_chunks(
        self,
        *,
        user_id: str,
        scene_id: str,
        viewport_id: str,
        viewport_generation: int,
        cx0: int,
        cy0: int,
        cx1: int,
        cy1: int,
        layer_ids: tuple[str, ...] = (),
        known_chunks: dict[str, int] | None = None,
    ) -> ViewportSubscriptionResult:
        scene = self.scenes.get_by_id(scene_id)

        if scene is None:
            return ViewportSubscriptionResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if not viewport_id or viewport_generation < 0:
            return ViewportSubscriptionResult(
                success=False,
                error_key="invalid_payload",
            )

        requested_layers = self._resolve_layers(
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            user_id=user_id,
            layer_ids=layer_ids,
        )

        known = known_chunks or {}
        chunks: list[ViewportChunkPayload] = []
        missing_count = 0
        stale_count = 0

        for layer_id in requested_layers:
            metadata_result = self.chunk_service.list_chunk_metadata_for_viewport(
                scene_id=scene_id,
                layer_id=layer_id,
                cx0=cx0,
                cy0=cy0,
                cx1=cx1,
                cy1=cy1,
                user_id=user_id,
            )

            if not metadata_result.success:
                return ViewportSubscriptionResult(
                    success=False,
                    error_key=metadata_result.error_key,
                )

            for chunk in metadata_result.chunks or []:
                known_version = known.get(self.chunk_key(
                    layer_id=layer_id,
                    cx=chunk["cx"],
                    cy=chunk["cy"],
                ))

                if known_version == chunk["version"]:
                    continue

                if known_version is None:
                    missing_count += 1
                else:
                    stale_count += 1

                read_result = self.chunk_service.read_chunk(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    cx=chunk["cx"],
                    cy=chunk["cy"],
                    user_id=user_id,
                )

                if not read_result.success or read_result.data is None:
                    return ViewportSubscriptionResult(
                        success=False,
                        error_key=read_result.error_key or "game.scenes.errors.chunk_not_found",
                    )

                chunks.append(
                    ViewportChunkPayload(
                        scene_id=scene_id,
                        layer_id=layer_id,
                        cx=chunk["cx"],
                        cy=chunk["cy"],
                        version=chunk["version"],
                        hash=chunk["hash"],
                        byte_size=chunk["byte_size"],
                        encoding=chunk["encoding"],
                        data=read_result.data,
                    )
                )

        return ViewportSubscriptionResult(
            success=True,
            scene_id=scene_id,
            scene_epoch=scene["scene_epoch"],
            viewport_id=viewport_id,
            viewport_generation=viewport_generation,
            chunks=tuple(chunks),
            missing_count=missing_count,
            stale_count=stale_count,
        )

    def resolve_viewport_chunk_candidates(
        self,
        *,
        user_id: str,
        scene_id: str,
        viewport_id: str,
        viewport_generation: int,
        cx0: int,
        cy0: int,
        cx1: int,
        cy1: int,
        layer_ids: tuple[str, ...] = (),
        known_chunks: dict[str, int] | None = None,
        focus_cx: float | None = None,
        focus_cy: float | None = None,
        prefetch_radius: int = 1,
    ) -> ViewportChunkCandidateResult:
        """List the chunks a viewport needs without reading their bytes.

        Each candidate carries its viewport-relative render priority so the
        scheduler can order the work; the actual chunk data is only read for the
        jobs the scheduler drains within budget (see ``read_candidate``).
        """

        scene = self.scenes.get_by_id(scene_id)

        if scene is None:
            return ViewportChunkCandidateResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if not viewport_id or viewport_generation < 0:
            return ViewportChunkCandidateResult(
                success=False,
                error_key="invalid_payload",
            )

        requested_layers = self._resolve_layers(
            scene_id=scene_id,
            campaign_id=scene["campaign_id"],
            user_id=user_id,
            layer_ids=layer_ids,
        )

        known = known_chunks or {}
        candidates: list[ViewportChunkCandidate] = []
        missing_count = 0
        stale_count = 0

        for layer_id in requested_layers:
            metadata_result = self.chunk_service.list_chunk_metadata_for_viewport(
                scene_id=scene_id,
                layer_id=layer_id,
                cx0=cx0,
                cy0=cy0,
                cx1=cx1,
                cy1=cy1,
                user_id=user_id,
            )

            if not metadata_result.success:
                return ViewportChunkCandidateResult(
                    success=False,
                    error_key=metadata_result.error_key,
                )

            for chunk in metadata_result.chunks or []:
                known_version = known.get(
                    self.chunk_key(layer_id=layer_id, cx=chunk["cx"], cy=chunk["cy"])
                )

                if known_version == chunk["version"]:
                    continue

                if known_version is None:
                    missing_count += 1
                else:
                    stale_count += 1

                classification = classify_chunk_priority(
                    cx=chunk["cx"],
                    cy=chunk["cy"],
                    cx0=cx0,
                    cy0=cy0,
                    cx1=cx1,
                    cy1=cy1,
                    focus_cx=focus_cx,
                    focus_cy=focus_cy,
                    prefetch_radius=prefetch_radius,
                )

                candidates.append(
                    ViewportChunkCandidate(
                        scene_id=scene_id,
                        scene_epoch=scene["scene_epoch"],
                        viewport_id=viewport_id,
                        viewport_generation=viewport_generation,
                        layer_id=layer_id,
                        cx=chunk["cx"],
                        cy=chunk["cy"],
                        version=chunk["version"],
                        hash=chunk["hash"],
                        byte_size=chunk["byte_size"],
                        encoding=chunk["encoding"],
                        priority=classification.priority,
                        priority_distance=classification.distance,
                        priority_ring=classification.ring,
                    )
                )

        return ViewportChunkCandidateResult(
            success=True,
            scene_id=scene_id,
            scene_epoch=scene["scene_epoch"],
            viewport_id=viewport_id,
            viewport_generation=viewport_generation,
            chunks=tuple(
                sorted(
                    candidates,
                    key=lambda candidate: (
                        int(candidate.priority),
                        self._focus_distance_sq(candidate, focus_cx, focus_cy, cx0, cy0, cx1, cy1),
                        candidate.cy,
                        candidate.cx,
                        candidate.layer_id,
                    ),
                )
            ),
            missing_count=missing_count,
            stale_count=stale_count,
        )

    @staticmethod
    def _focus_distance_sq(
        candidate: ViewportChunkCandidate,
        focus_cx: float | None,
        focus_cy: float | None,
        cx0: int,
        cy0: int,
        cx1: int,
        cy1: int,
    ) -> float:
        center_x = focus_cx if focus_cx is not None else (cx0 + cx1) / 2
        center_y = focus_cy if focus_cy is not None else (cy0 + cy1) / 2
        return (candidate.cx - center_x) ** 2 + (candidate.cy - center_y) ** 2

    def read_candidate(
        self,
        *,
        user_id: str,
        candidate: ViewportChunkCandidate,
    ) -> ViewportChunkPayload | None:
        payloads = self.read_candidates(user_id=user_id, candidates=(candidate,))
        return payloads[0] if payloads else None

    def read_candidates(
        self,
        *,
        user_id: str,
        candidates: tuple[ViewportChunkCandidate, ...],
    ) -> tuple[ViewportChunkPayload, ...]:
        grouped: dict[tuple[str, str], list[ViewportChunkCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault((candidate.scene_id, candidate.layer_id), []).append(candidate)

        data_by_candidate_key: dict[tuple[str, str, int, int], bytes] = {}
        for (scene_id, layer_id), layer_candidates in grouped.items():
            coords = tuple((candidate.cx, candidate.cy) for candidate in layer_candidates)
            read_result = self.chunk_service.read_chunks(
                scene_id=scene_id,
                layer_id=layer_id,
                coords=coords,
                user_id=user_id,
            )
            if not read_result.success or read_result.data_by_coord is None:
                continue
            for (cx, cy), data in read_result.data_by_coord.items():
                data_by_candidate_key[(scene_id, layer_id, cx, cy)] = data

        payloads: list[ViewportChunkPayload] = []
        for candidate in candidates:
            data = data_by_candidate_key.get(
                (candidate.scene_id, candidate.layer_id, candidate.cx, candidate.cy)
            )
            if data is None:
                continue
            payloads.append(
                ViewportChunkPayload(
                    scene_id=candidate.scene_id,
                    layer_id=candidate.layer_id,
                    cx=candidate.cx,
                    cy=candidate.cy,
                    version=candidate.version,
                    hash=candidate.hash,
                    byte_size=candidate.byte_size,
                    encoding=candidate.encoding,
                    data=data,
                )
            )

        return tuple(payloads)

    def _resolve_layers(
        self,
        *,
        scene_id: str,
        campaign_id: str,
        user_id: str,
        layer_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        requested = set(layer_ids)
        resolved = []

        for layer in self.layers.list_by_scene(scene_id):
            if requested and layer["id"] not in requested:
                continue
            if layer["kind"] != SceneLayerKind.RASTER_TILE_REFS.value:
                continue
            if layer["encoding"] != SceneChunkEncoding.UINT32_TILE_REFS_V1.value:
                continue
            if not self.visibility.can_view_layer(
                user_id=user_id,
                campaign_id=campaign_id,
                layer=layer,
            ):
                continue
            resolved.append(layer["id"])

        return tuple(resolved)

    @staticmethod
    def chunk_key(*, layer_id: str, cx: int, cy: int) -> str:
        return f"{layer_id}:{cx}:{cy}"
