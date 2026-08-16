from __future__ import annotations

from app.engine.rules.token_mapping_resolver import BAR_SLOTS, DEFAULT_BAR_COLORS
from app.engine.actors.actor_asset_urls import actor_image_file_exists


class TokenViewService:
    def build_view(
        self,
        *,
        token: dict,
        projection: dict | None = None,
        actor: dict | None = None,
        conditions: list[dict] | None = None,
        owner_user_ids: list[str] | None = None,
    ) -> dict:
        """Resolve a scene token + its Actor Core projection into a compact TokenView.

        ``projection`` is the manifest-mapped TokenView for the linked actor
        (``{name, bars: {bar_1: {value, max, color}, ...}, ...}``) produced by
        :class:`ActorTokenProjector`. Per-token overrides win over the projection.
        """
        overrides = token.get("overrides") or {}
        projection = projection or {}

        if token.get("actor_link_mode") == "unlinked":
            name = (
                overrides.get("name")
                or token.get("name")
                or projection.get("name")
                or (actor.get("name") if actor else None)
                or ""
            )
        else:
            name = (
                token.get("name")
                or overrides.get("name")
                or projection.get("name")
                or (actor.get("name") if actor else None)
                or ""
            )
        asset_url = (
            token.get("token_asset_url")
            or overrides.get("token_asset_url")
            or projection.get("token_asset_url")
        )
        if asset_url and actor and str(asset_url).startswith(f"/game/actor/{actor.get('id')}/image/"):
            kind = "token" if "/image/token" in str(asset_url) else "portrait"
            if not actor_image_file_exists(actor, kind):
                asset_url = None

        bars = self._resolve_bars(projection=projection, overrides=overrides)

        conds = conditions or []
        status_summary = {
            "count": len(conds),
            "has_negative": any(c.get("kind") == "negative" for c in conds),
            "has_positive": any(c.get("kind") == "positive" for c in conds),
        }

        return {
            "token_id": token["id"],
            "scene_id": token["scene_id"],
            "actor_id": token.get("actor_id"),
            "grid_x": token["grid_x"],
            "grid_y": token["grid_y"],
            "width_cells": token["width_cells"],
            "height_cells": token["height_cells"],
            "name": name,
            "asset_url": asset_url,
            "disposition": token["disposition"],
            "hidden": bool(token["hidden"]),
            "locked": bool(token["locked"]),
            "bars": bars,
            "conditions": conds,
            "effects": overrides.get("effects")
            if isinstance(overrides.get("effects"), list)
            else projection.get("effects") or [],
            "status_summary": status_summary,
            "controlled_by_role": token["controlled_by_role"],



            "controlled_by_user_ids": (
                owner_user_ids
                if owner_user_ids is not None
                else (token.get("controlled_by_user_ids") or [])
            ),

            "vision_enabled": bool(token.get("vision_enabled", 1)),
            "vision_range": float(token.get("vision_range") or 0.0),
            "elevation": float(token.get("elevation") or 0.0),
            "vision": {
                "enabled": bool(token.get("vision_enabled", 1)),
                "range": float(token.get("vision_range") or 0.0),
                "source": "token",
            },
            "version": token["version"],
        }

    def build_views_for_scene(
        self,
        *,
        tokens: list[dict],
        projections_by_actor_id: dict[str, dict],
        actors_by_id: dict[str, dict],
        conditions_by_token_id: dict[str, list[dict]],
        is_gm: bool,
        owners_by_actor_id: dict[str, list[str]] | None = None,
    ) -> list[dict]:
        """Build views for a scene, filtering hidden tokens from non-GM users."""
        views = []
        for token in tokens:
            if not is_gm and token.get("hidden"):
                continue
            actor_id = token.get("actor_id") or ""
            views.append(
                self.build_view(
                    token=token,
                    projection=projections_by_actor_id.get(actor_id),
                    actor=actors_by_id.get(actor_id),
                    conditions=conditions_by_token_id.get(token["id"], []),
                    owner_user_ids=None if owners_by_actor_id is None else owners_by_actor_id.get(actor_id, []),
                )
            )
        return views

    def _resolve_bars(self, *, projection: dict, overrides: dict) -> dict:
        """Resolve the token's two bars, letting token overrides win on the numbers.

        An unlinked token carries its own value/max in ``overrides``; the colour
        still comes from the system's mapping, because that describes what the
        bar *is*, not what this copy currently reads.
        """
        proj_bars = projection.get("bars")
        if not isinstance(proj_bars, dict):
            proj_bars = {}

        bars: dict[str, dict] = {}
        for slot in BAR_SLOTS:
            mapped = proj_bars.get(slot) if isinstance(proj_bars.get(slot), dict) else {}
            override = overrides.get(slot) if isinstance(overrides.get(slot), dict) else None
            if override is not None and "value" in override:
                value = override["value"]
                maximum = override.get("max", value)
                visibility = override.get("visibility", "everyone")
            else:
                value = mapped.get("value")
                if value is None:
                    continue
                maximum = mapped.get("max", value)
                visibility = mapped.get("visibility", "everyone")
            bars[slot] = {
                "value": value,
                "max": maximum,
                "color": mapped.get("color")
                or (override or {}).get("color")
                or DEFAULT_BAR_COLORS[slot],
                "visibility": visibility,
            }
        return bars
