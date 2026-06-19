from __future__ import annotations

from dataclasses import dataclass

from app.business.permissions.permission_service import PermissionService
from app.contracts.transport import RealtimeGatewayContract
from app.helpers.async_blocking import run_blocking
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.domain.roles import has_full_view
from app.domain.tokens import TokenActorLinkMode
from app.domain.tokens import TokenConditionKind
from app.domain.tokens import TokenDisposition
from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.engine.tokens.token_instance_sheet_service import INSTANCE_KEY
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService
from app.engine.tokens.token_placement_service import TokenPlacementService
from app.engine.tokens.token_view_service import TokenViewService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_condition_repository import TokenConditionRepository
from app.persistence.repositories.token_repository import TokenRepository
from app.realtime.events import TransportEvent


@dataclass(frozen=True)
class TokenResult:
    success: bool
    tokens: list[dict] | None = None
    token: dict | None = None
    error_key: str | None = None


class TokenService:
    _SIZE_CELLS = {
        "tiny": 1,
        "small": 1,
        "medium": 1,
        "large": 2,
        "huge": 3,
        "gargantuan": 4,
    }

    def __init__(
        self,
        *,
        tokens: TokenRepository | None = None,
        conditions: TokenConditionRepository | None = None,
        actors: ActorRepository | None = None,
        scenes: SceneRepository | None = None,
        campaigns: CampaignRepository | None = None,
        permissions: PermissionService | None = None,
        placement: TokenPlacementService | None = None,
        views: TokenViewService | None = None,
        projector: ActorTokenProjector | None = None,
        token_instances: TokenInstanceSheetService | None = None,
    ) -> None:
        self.tokens = tokens or TokenRepository()
        self.conditions = conditions or TokenConditionRepository()
        self.actors = actors or ActorRepository()
        self.scenes = scenes or SceneRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.permissions = permissions or PermissionService()
        self.placement = placement or TokenPlacementService()
        self.views = views or TokenViewService()
        self.projector = projector or ActorTokenProjector()
        self.token_instances = token_instances or TokenInstanceSheetService()

    async def create_many_from_actors(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        actor_ids: list[str],
        origin_x: int,
        origin_y: int,
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_CREATE,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene["campaign_id"] != campaign_id:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")

        if not actor_ids:
            return TokenResult(success=False, error_key="tokens.errors.no_actors")

        actors = []
        for aid in actor_ids:
            actor = self.actors.get(aid)
            if actor is None or actor["campaign_id"] != campaign_id or actor["status"] != "active":
                return TokenResult(success=False, error_key="tokens.errors.actor_not_found")
            actors.append(actor)

        positions = self.placement.calculate_positions(
            origin_x=origin_x,
            origin_y=origin_y,
            count=len(actors),
        )

        projections = {a["id"]: self.projector.project(a) for a in actors}
        actors_by_id = {a["id"]: a for a in actors}
        actor_id_counts = {aid: actor_ids.count(aid) for aid in set(actor_ids)}
        actor_existing_tokens = {
            aid: self.tokens.list_by_actor(aid)
            for aid in actor_id_counts
        }

                              
                                                                                           
                                                                                        
                                                                                     
                                                                                        
                                                     
        promoted_views: list[dict] = []
        for aid, existing_tokens in actor_existing_tokens.items():
            creates_more_than_one = actor_id_counts[aid] > 1
            already_has_token = bool(existing_tokens)
            if not already_has_token and not creates_more_than_one:
                continue
            actor = actors_by_id[aid]
            projection = projections.get(aid, {})
            for token in existing_tokens:
                if token.get("actor_link_mode") != TokenActorLinkMode.LINKED:
                    continue
                promoted = self.tokens.update_link_mode_and_overrides(
                    token_id=token["id"],
                    actor_link_mode=TokenActorLinkMode.UNLINKED,
                    name=projection.get("name") or actor["name"],
                    token_asset_url=projection.get("token_asset_url"),
                    overrides=self._snapshot_overrides(actor=actor, projection=projection),
                )
                if promoted is not None:
                    promoted_views.append(
                        self.views.build_view(
                            token=promoted,
                            projection=projection,
                            actor=actor,
                        )
                    )

        specs = []
        for actor, (gx, gy) in zip(actors, positions):
            config = self._load_token_config(actor)
            projection = projections.get(actor["id"], {})
            width_cells, height_cells = self._resolve_token_dimensions(
                config=config,
                projection=projection,
            )
            existing_count = len(actor_existing_tokens.get(actor["id"], []))
            batch_count = actor_id_counts.get(actor["id"], 0)
            create_linked = existing_count == 0 and batch_count == 1
            if create_linked:
                actor_link_mode = TokenActorLinkMode.LINKED
                name = None
                token_asset_url = None
                overrides = {}
            else:
                actor_link_mode = TokenActorLinkMode.UNLINKED
                name = projection.get("name") or actor["name"]
                token_asset_url = projection.get("token_asset_url")
                overrides = self._snapshot_overrides(actor=actor, projection=projection)
            specs.append({
                "scene_id": scene_id,
                "actor_id": actor["id"],
                "grid_x": gx,
                "grid_y": gy,
                "width_cells": width_cells,
                "height_cells": height_cells,
                "disposition": config.get("disposition", TokenDisposition.NEUTRAL),
                "actor_link_mode": actor_link_mode,
                "name": name,
                "token_asset_url": token_asset_url,
                "overrides": overrides,
            })

        created = self.tokens.create_many(specs)

        token_views = [
            self.views.build_view(
                token=t,
                projection=projections.get(t.get("actor_id") or ""),
                actor=actors_by_id.get(t.get("actor_id") or ""),
            )
            for t in created
        ]

        if transport is not None:
            if promoted_views:
                promoted_by_scene: dict[str, list[dict]] = {}
                for view in promoted_views:
                    promoted_by_scene.setdefault(view["scene_id"], []).append(view)
                for promoted_scene_id, views in promoted_by_scene.items():
                    await transport.to_room(
                        room_id=campaign_id,
                        event=TransportEvent.TOKENS_UPDATED,
                        payload={
                            "room_id": campaign_id,
                            "scene_id": promoted_scene_id,
                            "tokens": views,
                        },
                    )
            await self._emit_tokens_created(
                campaign_id=campaign_id,
                scene_id=scene_id,
                token_views=token_views,
                transport=transport,
            )

        return TokenResult(success=True, tokens=token_views)

    def _snapshot_overrides(self, *, actor: dict, projection: dict) -> dict:
        overrides = {
            INSTANCE_KEY: self.token_instances.make_instance_snapshot(actor=actor),
        }
        bars = projection.get("bars")
        if isinstance(bars, dict):
            for key, value in bars.items():
                if isinstance(key, str) and isinstance(value, dict):
                    overrides[key] = dict(value)
        effects = projection.get("effects")
        if isinstance(effects, list):
            overrides["effects"] = [dict(effect) for effect in effects if isinstance(effect, dict)]
        return overrides

    async def refresh_actor_tokens(
        self,
        *,
        campaign_id: str,
        actor_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> None:
        """Notify clients that an actor's linked tokens must be recomputed.

        Called after an actor's sheet data changes (patch/append/action/drop).
        Clients re-fetch the scene snapshot, which re-projects the bars/name from
        the updated Actor Core data — completing "HP on the sheet updates the token".
        """
        if transport is None:
            return
        tokens = await run_blocking(self.tokens.list_by_actor, actor_id)
        tokens = [token for token in tokens if token.get("actor_link_mode") == TokenActorLinkMode.LINKED]
        if not tokens:
            return
        tokens_by_scene: dict[str, list[dict]] = {}
        for token in tokens:
            tokens_by_scene.setdefault(token["scene_id"], []).append(token)
        for scene_id, scene_tokens in tokens_by_scene.items():
                                                                              
                                                                        
            await transport.to_room(
                room_id=campaign_id,
                event=TransportEvent.TOKENS_UPDATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "tokens": [
                        {"token_id": t["id"], "version": t["version"]} for t in scene_tokens
                    ],
                },
            )

    async def move(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
        grid_x: int,
        grid_y: int,
        user_id: str,
        expected_version: int | None = None,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        scene, token = await run_blocking(
            self._get_token_in_campaign,
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
        )
        if scene is None:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(self._can_control_token, token=token, user_id=user_id, campaign_id=campaign_id):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        if token.get("locked"):
            return TokenResult(success=False, error_key="tokens.errors.locked")

        updated = await run_blocking(
            self.tokens.move,
            token_id=token_id,
            grid_x=grid_x,
            grid_y=grid_y,
            expected_version=expected_version,
        )
        if updated is None:
            return TokenResult(success=False, token=token, error_key="tokens.errors.version_conflict")

        if transport is not None:
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_MOVED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "tokens": [
                        {
                            "token_id": token_id,
                            "grid_x": grid_x,
                            "grid_y": grid_y,
                            "version": updated["version"],
                        }
                    ],
                },
                token=updated,
                transport=transport,
            )

        return TokenResult(success=True, token=updated)

    async def update_override(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
        overrides: dict,
        user_id: str,
        expected_version: int | None = None,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        scene, token = await run_blocking(
            self._get_token_in_campaign,
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
        )
        if scene is None:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(
            self._authorize_token_management,
            token=token,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_OVERRIDE_MANAGE,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        updated = await run_blocking(
            self.tokens.update_overrides,
            token_id=token_id,
            overrides=overrides,
            expected_version=expected_version,
        )
        if updated is None:
            return TokenResult(success=False, token=token, error_key="tokens.errors.version_conflict")

        if transport is not None:
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_UPDATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "tokens": [
                        {
                            "token_id": token_id,
                            "version": updated["version"],
                            "changed": {"overrides": overrides},
                        }
                    ],
                },
                token=updated,
                transport=transport,
            )

        return TokenResult(success=True, token=updated)

    async def set_hidden(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
        hidden: bool,
        user_id: str,
        expected_version: int | None = None,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        scene, token = await run_blocking(
            self._get_token_in_campaign,
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
        )
        if scene is None:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(
            self._authorize_token_management,
            token=token,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_VISIBILITY,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        updated = await run_blocking(
            self.tokens.set_hidden,
            token_id=token_id,
            hidden=hidden,
            expected_version=expected_version,
        )
        if updated is None:
            return TokenResult(success=False, token=token, error_key="tokens.errors.version_conflict")

        if transport is not None:
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_VISIBILITY_CHANGED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "tokens": [
                        {
                            "token_id": token_id,
                            "hidden": hidden,
                            "version": updated["version"],
                        }
                    ],
                },
                token=updated,
                transport=transport,
                include_hidden_players=True,
            )

        return TokenResult(success=True, token=updated)

    async def remove_from_scene(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        scene, token = await run_blocking(
            self._get_token_in_campaign,
            campaign_id=campaign_id,
            scene_id=scene_id,
            token_id=token_id,
        )
        if scene is None:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(
            self.permissions.can,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_DELETE,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        await run_blocking(self.tokens.remove, token_id=token_id)

        if transport is not None:
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_DELETED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "token_ids": [token_id],
                },
                token=token,
                transport=transport,
            )

        return TokenResult(success=True)

    async def add_condition(
        self,
        *,
        campaign_id: str,
        token_id: str,
        condition_id: str,
        label: str,
        icon: str | None = None,
        duration: int | None = None,
        source: str | None = None,
        kind: str = TokenConditionKind.NEUTRAL,
        visible_to: str = "everyone",
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        token = await run_blocking(self.tokens.get_by_id, token_id)
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        scene = await run_blocking(self.scenes.get_by_id, token["scene_id"])
        if scene is None or scene["campaign_id"] != campaign_id:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(
            self._authorize_token_management,
            token=token,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_CONDITION_MANAGE,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        await run_blocking(
            self.conditions.add,
            token_id=token_id,
            condition_id=condition_id,
            label=label,
            icon=icon,
            duration=duration,
            source=source,
            kind=kind,
            visible_to=visible_to,
        )

        if transport is not None:
            all_conditions = await run_blocking(self.conditions.list_by_token, token_id)
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_CONDITIONS_UPDATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": token["scene_id"],
                    "token_id": token_id,
                    "conditions": all_conditions,
                },
                token=token,
                transport=transport,
            )

        return TokenResult(success=True)

    async def remove_condition(
        self,
        *,
        campaign_id: str,
        token_id: str,
        condition_id: str,
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> TokenResult:
        token = await run_blocking(self.tokens.get_by_id, token_id)
        if token is None:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        scene = await run_blocking(self.scenes.get_by_id, token["scene_id"])
        if scene is None or scene["campaign_id"] != campaign_id:
            return TokenResult(success=False, error_key="tokens.errors.not_found")

        if not await run_blocking(
            self._authorize_token_management,
            token=token,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.TOKEN_CONDITION_MANAGE,
        ):
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

        removed = await run_blocking(self.conditions.remove, token_id=token_id, condition_id=condition_id)
        if not removed:
            return TokenResult(success=False, error_key="tokens.errors.condition_not_found")

        if transport is not None:
            all_conditions = await run_blocking(self.conditions.list_by_token, token_id)
            await self._emit_token_event_to_viewers(
                campaign_id=campaign_id,
                event=TransportEvent.TOKENS_CONDITIONS_UPDATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": token["scene_id"],
                    "token_id": token_id,
                    "conditions": all_conditions,
                },
                token=token,
                transport=transport,
            )

        return TokenResult(success=True)

    def get_snapshot(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        user_id: str,
    ) -> TokenResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene["campaign_id"] != campaign_id:
            return TokenResult(success=False, error_key="tokens.errors.scene_not_found")

        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return TokenResult(success=False, error_key="tokens.errors.permission_denied")

                                                                                  
        is_gm = has_full_view(campaign["member_role"])

        all_tokens = self.tokens.list_by_scene(scene_id)

        actor_ids = list({t["actor_id"] for t in all_tokens if t.get("actor_id")})
        actors_by_id: dict[str, dict] = {}
        projections_by_actor_id: dict[str, dict] = {}
        for aid in actor_ids:
            actor = self.actors.get(aid)
            if actor and actor["status"] == "active":
                actors_by_id[aid] = actor
                projections_by_actor_id[aid] = self.projector.project(actor)

        visible_tokens = [
            token
            for token in all_tokens
            if self._can_view_token(token=token, user_id=user_id, is_gm=is_gm)
        ]

        token_ids = [t["id"] for t in visible_tokens]
        conditions_by_token = self.conditions.list_by_tokens(token_ids) if token_ids else {}

        token_views = self.views.build_views_for_scene(
            tokens=visible_tokens,
            projections_by_actor_id=projections_by_actor_id,
            actors_by_id=actors_by_id,
            conditions_by_token_id=conditions_by_token,
            is_gm=is_gm,
        )

        return TokenResult(success=True, tokens=token_views)

    async def _emit_tokens_created(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_views: list[dict],
        transport: RealtimeGatewayContract,
    ) -> None:
                                                     
        await transport.to_gm(
            room_id=campaign_id,
            event=TransportEvent.TOKENS_CREATED,
            payload={
                "room_id": campaign_id,
                "scene_id": scene_id,
                "tokens": token_views,
            },
        )

                                                                                        
        visible_tokens = [view for view in token_views if not view.get("hidden")]
        if visible_tokens:
            await transport.to_players_in_room(
                room_id=campaign_id,
                event=TransportEvent.TOKENS_CREATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "tokens": visible_tokens,
                },
            )

    async def _emit_token_event_to_viewers(
        self,
        *,
        campaign_id: str,
        event: TransportEvent,
        payload: dict,
        token: dict,
        transport: RealtimeGatewayContract,
        include_hidden_players: bool = False,
    ) -> None:
        # Coalesced: GMs/assistant-GMs and streamers always see the event;
        # plain players see it unless the token is hidden. A single delivery to
        # that audience replaces the previous three broadcasts (3 recipient
        # queries + 3 event-log writes -> 1 of each).
        include_players = include_hidden_players or not token.get("hidden")
        await transport.to_token_audience(
            room_id=campaign_id,
            event=event,
            payload=payload,
            include_players=include_players,
        )

    def _can_view_token(self, *, token: dict, user_id: str, is_gm: bool) -> bool:
                                                                
                                                                                                
        return is_gm or not token.get("hidden")

    def _authorize_token_management(
        self,
        *,
        token: dict,
        user_id: str,
        campaign_id: str,
        permission: TablePermission,
    ) -> bool:
        """A token-management action is allowed when the caller either controls
        the specific token (GM, or owner of its linked actor) or holds the
        explicit "manage any token" permission for this capability."""
        if self._can_control_token(token=token, user_id=user_id, campaign_id=campaign_id):
            return True
        return self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=permission,
        )

    def _can_control_token(self, *, token: dict, user_id: str, campaign_id: str) -> bool:
        member_role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if member_role is None:
            return False

                                                             
        if member_role == PlayerRole.GM.value:
            return True

                                                                     
        actor_id = token.get("actor_id")
        if not actor_id:
            return False
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return False
        return can_edit_actor(actor=actor, campaign={"member_role": member_role}, user_id=user_id)

    def _get_scene_in_campaign(self, *, campaign_id: str, scene_id: str) -> dict | None:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene["campaign_id"] != campaign_id:
            return None
        return scene

    def _get_token_in_campaign(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
    ) -> tuple[dict | None, dict | None]:
        scene = self._get_scene_in_campaign(campaign_id=campaign_id, scene_id=scene_id)
        if scene is None:
            return None, None

        token = self.tokens.get_by_scene_and_id(scene_id=scene_id, token_id=token_id)
        if token is None:
            return scene, None
        return scene, token

    def _load_token_config(self, actor: dict) -> dict:
        import json as _json
        config_json = actor.get("default_token_config_json")
        if config_json:
            try:
                return _json.loads(config_json)
            except (ValueError, TypeError):
                pass
        return {}

    def _resolve_token_dimensions(self, *, config: dict, projection: dict) -> tuple[int, int]:
        mapped_size = str(projection.get("size", "")).strip().lower()
        mapped_cells = self._SIZE_CELLS.get(mapped_size, 1)
        return (
            self._positive_cells(config.get("width_cells"), fallback=mapped_cells),
            self._positive_cells(config.get("height_cells"), fallback=mapped_cells),
        )

    @staticmethod
    def _positive_cells(value: object, *, fallback: int) -> int:
        try:
            cells = int(value) if value is not None else fallback
        except (TypeError, ValueError):
            cells = fallback
        return max(1, cells)
