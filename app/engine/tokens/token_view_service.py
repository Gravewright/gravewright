from __future__ import annotations


class TokenViewService:
    def build_view(
        self,
        *,
        token: dict,
        projection: dict | None = None,
        actor: dict | None = None,
        conditions: list[dict] | None = None,
    ) -> dict:
        """Resolve a scene token + its Actor Core projection into a compact TokenView.

        ``projection`` is the manifest-mapped TokenView for the linked actor
        (``{name, bars: {hp: {value, max}}, ...}``) produced by
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
            "effects": overrides.get("effects") if isinstance(overrides.get("effects"), list) else projection.get("effects") or [],
            "status_summary": status_summary,
            "controlled_by_role": token["controlled_by_role"],
            "controlled_by_user_ids": token.get("controlled_by_user_ids") or [],
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
                )
            )
        return views

    def _resolve_bars(self, *, projection: dict, overrides: dict) -> dict:
        """Resolve mapped bars from the projection, letting token overrides win."""
        proj_bars = projection.get("bars")
        if not isinstance(proj_bars, dict):
            return {}

        bars: dict[str, dict] = {}
        for key, bar in proj_bars.items():
            override_bar = overrides.get(key)
            if isinstance(override_bar, dict) and "value" in override_bar:
                value = override_bar["value"]
                bars[key] = {
                    "value": value,
                    "max": override_bar.get("max", value),
                    "visibility": override_bar.get("visibility", "everyone"),
                }
                continue
            if not isinstance(bar, dict):
                continue
            value = bar.get("value")
            if value is None:
                continue
            bars[key] = {
                "value": value,
                "max": bar.get("max", value),
                "visibility": "everyone",
            }
        return bars
