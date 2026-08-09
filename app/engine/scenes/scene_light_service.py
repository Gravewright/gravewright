from __future__ import annotations
import re
from dataclasses import dataclass, field
from math import isfinite
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_light_repository import SceneLightRepository
from app.persistence.repositories.scene_repository import SceneRepository




ANIMATIONS = ("none", "candle", "torch", "fire", "pulse", "arcane", "smoke")
MAX_RADIUS_CELLS = 200.0


MIN_ANGLE = 5.0
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")



MAX_BULK = 500

@dataclass(frozen=True)
class LightResult:
    success: bool
    payload: dict = field(default_factory=dict)
    error_key: str | None = None

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

class SceneLightService:
    def __init__(self) -> None:
        self.lights = SceneLightRepository(); self.scenes = SceneRepository(); self.campaigns = CampaignRepository()

    def _scene_for(self, campaign_id: str, scene_id: str, user_id: str, *, gm_only: bool) -> tuple[dict | None, str | None]:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None or (gm_only and role != "gm"): return None, "lighting.errors.denied"
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return None, "lighting.errors.not_found"
        return scene, None

    def state(self, *, campaign_id: str, scene_id: str, user_id: str) -> LightResult:
        scene, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=False)
        if error: return LightResult(False, error_key=error)
        return LightResult(True, {"campaign_id": campaign_id, "scene_id": scene_id, "lights": self.lights.list_for_scene(scene_id)})

    def _clean(self, values: dict, scene: dict) -> dict | None:
        """Normaliza os campos editaveis; devolve None se algo for insalvavel."""
        cleaned: dict = {}
        for key in ("x", "y"):
            if key not in values: continue
            try: number = float(values[key])
            except (TypeError, ValueError): return None
            if not isfinite(number): return None
            limit = max(float(scene["width"]), float(scene["height"])) * 2
            if abs(number) > limit: return None
            cleaned[key] = number
        for key in ("bright_radius", "dim_radius"):
            if key not in values: continue
            try: number = float(values[key])
            except (TypeError, ValueError): return None
            if not isfinite(number): return None
            cleaned[key] = _clamp(number, 0.0, MAX_RADIUS_CELLS)
        if "intensity" in values:
            try: cleaned["intensity"] = _clamp(float(values["intensity"]), 0.0, 1.0)
            except (TypeError, ValueError): return None


        if "angle" in values:
            try: number = float(values["angle"])
            except (TypeError, ValueError): return None
            if not isfinite(number): return None
            cleaned["angle"] = _clamp(number, MIN_ANGLE, 360.0)


        if "rotation" in values:
            try: number = float(values["rotation"])
            except (TypeError, ValueError): return None
            if not isfinite(number): return None
            cleaned["rotation"] = number % 360.0
        if "color" in values:
            color = str(values["color"] or "")
            if not HEX_COLOR.match(color): return None
            cleaned["color"] = color.lower()
        if "animation" in values:
            animation = str(values["animation"] or "")
            if animation not in ANIMATIONS: return None
            cleaned["animation"] = animation
        if "enabled" in values:
            cleaned["enabled"] = 1 if values["enabled"] else 0

        bright, dim = cleaned.get("bright_radius"), cleaned.get("dim_radius")
        if bright is not None and dim is not None and bright > dim:
            cleaned["dim_radius"] = bright
        return cleaned

    def create(self, *, campaign_id: str, scene_id: str, user_id: str, **values) -> LightResult:
        scene, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=True)
        if error: return LightResult(False, error_key=error)
        cleaned = self._clean({"x": 0.0, "y": 0.0, **values}, scene)
        if cleaned is None or "x" not in cleaned or "y" not in cleaned: return LightResult(False, error_key="lighting.errors.invalid")
        light = self.lights.create(campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id, **cleaned)
        return LightResult(True, {"light": light})

    def update(self, *, campaign_id: str, light_id: str, user_id: str, **values) -> LightResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return LightResult(False, error_key="lighting.errors.denied")
        light = self.lights.get(light_id)
        if not light or light["campaign_id"] != campaign_id: return LightResult(False, error_key="lighting.errors.not_found")
        scene = self.scenes.get_by_id(light["scene_id"])
        if not scene: return LightResult(False, error_key="lighting.errors.not_found")
        cleaned = self._clean(values, scene)
        if cleaned is None: return LightResult(False, error_key="lighting.errors.invalid")
        if not cleaned: return LightResult(True, {"light": light})

        merged = {**light, **cleaned}
        if float(merged["bright_radius"]) > float(merged["dim_radius"]):
            cleaned["dim_radius"] = float(merged["bright_radius"])
        return LightResult(True, {"light": self.lights.update(light_id, **cleaned)})

    def delete(self, *, campaign_id: str, light_id: str, user_id: str) -> LightResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return LightResult(False, error_key="lighting.errors.denied")
        light = self.lights.get(light_id)
        if not light or light["campaign_id"] != campaign_id: return LightResult(False, error_key="lighting.errors.not_found")
        self.lights.delete(light_id)
        return LightResult(True, {"light_id": light_id, "scene_id": light["scene_id"]})

    def delete_many(self, *, campaign_id: str, light_ids: list[str], user_id: str) -> LightResult:
        """Apaga o que for desta campanha e ignora o resto, em silencio.

        Uma selecao pode conter coisa que outra pessoa ja apagou, ou id de outra
        mesa se alguem forjar o corpo. Recusar o lote inteiro por causa de um item
        transformaria uma corrida comum em erro na cara do mestre; obedecer a
        qualquer id seria a porta aberta. Apagar so o que e daqui resolve os dois.
        """
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return LightResult(False, error_key="lighting.errors.denied")
        wanted = [str(value) for value in (light_ids or []) if value][:MAX_BULK]
        rows = [row for row in (self.lights.get(value) for value in wanted)
                if row and row["campaign_id"] == campaign_id]
        if not rows: return LightResult(True, {"light_ids": [], "scene_id": None})
        self.lights.delete_many([row["id"] for row in rows])
        return LightResult(True, {"light_ids": [row["id"] for row in rows], "scene_id": rows[0]["scene_id"]})
