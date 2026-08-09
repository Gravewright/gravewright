from __future__ import annotations
import re
from dataclasses import dataclass, field
from math import isfinite
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_particle_repository import SceneParticleRepository
from app.persistence.repositories.scene_repository import SceneRepository



KINDS = ("smoke", "ember", "dust", "arcane", "rain", "snow", "firefly",
         "leaves", "bubbles", "ash", "blood", "runes")

MAX_SCALE_CELLS = 60.0
MIN_SCALE_CELLS = 0.5
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")



MAX_BULK = 500

@dataclass(frozen=True)
class ParticleResult:
    success: bool
    payload: dict = field(default_factory=dict)
    error_key: str | None = None

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

class SceneParticleService:
    def __init__(self) -> None:
        self.emitters = SceneParticleRepository(); self.scenes = SceneRepository(); self.campaigns = CampaignRepository()

    def _scene_for(self, campaign_id: str, scene_id: str, user_id: str, *, gm_only: bool) -> tuple[dict | None, str | None]:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None or (gm_only and role != "gm"): return None, "lighting.errors.denied"
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return None, "lighting.errors.not_found"
        return scene, None

    def state(self, *, campaign_id: str, scene_id: str, user_id: str) -> ParticleResult:
        scene, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=False)
        if error: return ParticleResult(False, error_key=error)
        return ParticleResult(True, {"campaign_id": campaign_id, "scene_id": scene_id, "emitters": self.emitters.list_for_scene(scene_id)})

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
        if "scale" in values:
            try: number = float(values["scale"])
            except (TypeError, ValueError): return None
            if not isfinite(number): return None
            cleaned["scale"] = _clamp(number, MIN_SCALE_CELLS, MAX_SCALE_CELLS)


        if "density" in values:
            try: cleaned["density"] = _clamp(float(values["density"]), 0.0, 1.0)
            except (TypeError, ValueError): return None
        if "color" in values:
            color = str(values["color"] or "")
            if not HEX_COLOR.match(color): return None
            cleaned["color"] = color.lower()
        if "kind" in values:
            kind = str(values["kind"] or "")
            if kind not in KINDS: return None
            cleaned["kind"] = kind
        if "enabled" in values:
            cleaned["enabled"] = 1 if values["enabled"] else 0
        return cleaned

    def create(self, *, campaign_id: str, scene_id: str, user_id: str, **values) -> ParticleResult:
        scene, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=True)
        if error: return ParticleResult(False, error_key=error)
        cleaned = self._clean({"x": 0.0, "y": 0.0, **values}, scene)
        if cleaned is None or "x" not in cleaned or "y" not in cleaned: return ParticleResult(False, error_key="lighting.errors.invalid")
        emitter = self.emitters.create(campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id, **cleaned)
        return ParticleResult(True, {"emitter": emitter})

    def update(self, *, campaign_id: str, emitter_id: str, user_id: str, **values) -> ParticleResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return ParticleResult(False, error_key="lighting.errors.denied")
        emitter = self.emitters.get(emitter_id)
        if not emitter or emitter["campaign_id"] != campaign_id: return ParticleResult(False, error_key="lighting.errors.not_found")
        scene = self.scenes.get_by_id(emitter["scene_id"])
        if not scene: return ParticleResult(False, error_key="lighting.errors.not_found")
        cleaned = self._clean(values, scene)
        if cleaned is None: return ParticleResult(False, error_key="lighting.errors.invalid")
        if not cleaned: return ParticleResult(True, {"emitter": emitter})
        return ParticleResult(True, {"emitter": self.emitters.update(emitter_id, **cleaned)})

    def delete(self, *, campaign_id: str, emitter_id: str, user_id: str) -> ParticleResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return ParticleResult(False, error_key="lighting.errors.denied")
        emitter = self.emitters.get(emitter_id)
        if not emitter or emitter["campaign_id"] != campaign_id: return ParticleResult(False, error_key="lighting.errors.not_found")
        self.emitters.delete(emitter_id)
        return ParticleResult(True, {"emitter_id": emitter_id, "scene_id": emitter["scene_id"]})

    def delete_many(self, *, campaign_id: str, emitter_ids: list[str], user_id: str) -> ParticleResult:
        """Apaga o que for desta campanha e ignora o resto, em silencio.

        Uma selecao pode conter coisa que outra pessoa ja apagou, ou id de outra
        mesa se alguem forjar o corpo. Recusar o lote inteiro por causa de um item
        transformaria uma corrida comum em erro na cara do mestre; obedecer a
        qualquer id seria a porta aberta. Apagar so o que e daqui resolve os dois.
        """
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return ParticleResult(False, error_key="lighting.errors.denied")
        wanted = [str(value) for value in (emitter_ids or []) if value][:MAX_BULK]
        rows = [row for row in (self.emitters.get(value) for value in wanted)
                if row and row["campaign_id"] == campaign_id]
        if not rows: return ParticleResult(True, {"emitter_ids": [], "scene_id": None})
        self.emitters.delete_many([row["id"] for row in rows])
        return ParticleResult(True, {"emitter_ids": [row["id"] for row in rows], "scene_id": rows[0]["scene_id"]})
