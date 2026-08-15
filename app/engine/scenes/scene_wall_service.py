from __future__ import annotations
from dataclasses import dataclass, field
from math import hypot, isfinite
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_wall_repository import SceneWallRepository

NODE_TOLERANCE = 1.0



MIN_SEGMENT = 8.0

DOOR_STATES = ("closed", "open", "locked")



MAX_BULK = 500

@dataclass(frozen=True)
class WallResult:
    success: bool
    payload: dict = field(default_factory=dict)
    error_key: str | None = None

class SceneWallService:
    def __init__(self) -> None:
        self.walls = SceneWallRepository(); self.scenes = SceneRepository(); self.campaigns = CampaignRepository()
    def state(self, *, campaign_id: str, scene_id: str, user_id: str) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) is None:
            return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return WallResult(False, error_key="lighting.errors.not_found")
        return WallResult(True, {"campaign_id": campaign_id, "scene_id": scene_id, "walls": self.walls.list_for_scene(scene_id)})
    def create(self, *, campaign_id: str, scene_id: str, user_id: str, kind: str, x1: float, y1: float, x2: float, y2: float) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return WallResult(False, error_key="lighting.errors.not_found")
        points = (x1,y1,x2,y2)
        if kind not in {"wall","door"} or not all(isfinite(v) for v in points) or hypot(x2-x1,y2-y1) < 2: return WallResult(False, error_key="lighting.errors.invalid")
        limit = max(float(scene["width"]), float(scene["height"])) * 2
        if any(abs(v) > limit for v in points): return WallResult(False, error_key="lighting.errors.invalid")
        wall = self.walls.create(campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id, kind=kind, x1=x1,y1=y1,x2=x2,y2=y2)
        return WallResult(True, {"wall": wall})
    def update(self, *, campaign_id: str, wall_id: str, user_id: str, **values) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        wall = self.walls.get(wall_id)
        if not wall or wall["campaign_id"] != campaign_id:
            return WallResult(False, error_key="lighting.errors.not_found")
        allowed = {key: values[key] for key in ("x1", "y1", "x2", "y2") if key in values}
        try:
            allowed = {key: float(value) for key, value in allowed.items()}
        except (TypeError, ValueError):
            return WallResult(False, error_key="lighting.errors.invalid")
        merged = {**wall, **allowed}
        scene = self.scenes.get_by_id(wall["scene_id"])
        limit = max(float(scene["width"]), float(scene["height"])) * 2 if scene else 0
        if (not allowed or not all(isfinite(value) and abs(value) <= limit for value in allowed.values())
                or hypot(merged["x2"] - merged["x1"], merged["y2"] - merged["y1"]) < 2):
            return WallResult(False, error_key="lighting.errors.invalid")
        return WallResult(True, {"wall": self.walls.update(wall_id, **allowed)})
    def move_node(self, *, campaign_id: str, scene_id: str, user_id: str, from_x: float, from_y: float, to_x: float, to_y: float) -> WallResult:
        """Move todas as pontas soldadas em (from_x,from_y) para (to_x,to_y) de uma vez,
        para que paredes encadeadas nao se separem ao arrastar o vertice compartilhado."""
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return WallResult(False, error_key="lighting.errors.not_found")
        points = (from_x, from_y, to_x, to_y)
        if not all(isfinite(v) for v in points): return WallResult(False, error_key="lighting.errors.invalid")
        limit = max(float(scene["width"]), float(scene["height"])) * 2
        if any(abs(v) > limit for v in points): return WallResult(False, error_key="lighting.errors.invalid")
        pending = []
        for wall in self.walls.list_for_scene(scene_id):
            changes = {}
            if hypot(wall["x1"] - from_x, wall["y1"] - from_y) <= NODE_TOLERANCE: changes.update(x1=to_x, y1=to_y)
            if hypot(wall["x2"] - from_x, wall["y2"] - from_y) <= NODE_TOLERANCE: changes.update(x2=to_x, y2=to_y)
            if not changes: continue
            merged = {**wall, **changes}
            if hypot(merged["x2"] - merged["x1"], merged["y2"] - merged["y1"]) < 2: return WallResult(False, error_key="lighting.errors.invalid")
            pending.append((wall["id"], changes))
        if not pending: return WallResult(False, error_key="lighting.errors.not_found")
        for wall_id, changes in pending: self.walls.update(wall_id, **changes)
        return WallResult(True, {"scene_id": scene_id, "walls": self.walls.list_for_scene(scene_id)})

    def move_many(self, *, campaign_id: str, scene_id: str, wall_ids: list[str], user_id: str, dx: float, dy: float) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id:
            return WallResult(False, error_key="lighting.errors.not_found")
        if not all(isfinite(value) for value in (dx, dy)):
            return WallResult(False, error_key="lighting.errors.invalid")
        wanted = {str(value) for value in (wall_ids or []) if value}
        rows = [row for row in self.walls.list_for_scene(scene_id) if row["id"] in wanted][:MAX_BULK]
        limit = max(float(scene["width"]), float(scene["height"])) * 2
        for wall in rows:
            coords = {key: wall[key] + (dx if key.startswith("x") else dy) for key in ("x1", "y1", "x2", "y2")}
            if any(abs(value) > limit for value in coords.values()):
                return WallResult(False, error_key="lighting.errors.invalid")
        for wall in rows:
            self.walls.update(wall["id"], x1=wall["x1"] + dx, y1=wall["y1"] + dy,
                              x2=wall["x2"] + dx, y2=wall["y2"] + dy)
        return WallResult(True, {"scene_id": scene_id, "walls": self.walls.list_for_scene(scene_id)})
    def split(self, *, campaign_id: str, wall_id: str, user_id: str, x: float, y: float) -> WallResult:
        """Parte uma parede em duas no ponto dado, criando um no ali.

        Sem isto, corrigir o meio de uma parede longa era apagar e redesenhar as
        duas metades, e junto ia a porta, o estado dela e a solda com as vizinhas.

        O ponto e projetado sobre o segmento antes de cortar: um duplo clique
        raramente cai exatamente em cima da linha, e cortar no ponto cru dobraria
        a parede em vez de dividi-la.
        """
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        wall = self.walls.get(wall_id)
        if not wall or wall["campaign_id"] != campaign_id:
            return WallResult(False, error_key="lighting.errors.not_found")
        if not all(isfinite(v) for v in (x, y)):
            return WallResult(False, error_key="lighting.errors.invalid")

        x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
        dx, dy = x2 - x1, y2 - y1
        length = hypot(dx, dy)
        if length < 4: return WallResult(False, error_key="lighting.errors.invalid")
        along = ((x - x1) * dx + (y - y1) * dy) / (length * length)
        px, py = x1 + dx * along, y1 + dy * along



        if min(hypot(px - x1, py - y1), hypot(px - x2, py - y2)) < MIN_SEGMENT:
            return WallResult(False, error_key="lighting.errors.invalid")



        self.walls.update(wall_id, x2=px, y2=py)
        self.walls.create(
            campaign_id=campaign_id, scene_id=wall["scene_id"], created_by_user_id=user_id,
            kind=wall["kind"], x1=px, y1=py, x2=x2, y2=y2,
            **({"door_state": wall["door_state"]} if wall["kind"] == "door" else {}),
        )
        return WallResult(True, {"scene_id": wall["scene_id"], "walls": self.walls.list_for_scene(wall["scene_id"])})

    def set_door_state(self, *, campaign_id: str, wall_id: str, user_id: str, door_state: str) -> WallResult:
        """Portas sao operaveis em jogo, entao a autorizacao e mais fina que o resto:
        qualquer membro abre e fecha, mas so o GM tranca e destranca."""
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None: return WallResult(False, error_key="lighting.errors.denied")
        if door_state not in DOOR_STATES: return WallResult(False, error_key="lighting.errors.invalid")
        wall = self.walls.get(wall_id)
        if not wall or wall["campaign_id"] != campaign_id or wall["kind"] != "door": return WallResult(False, error_key="lighting.errors.not_found")
        if role != "gm":

            if door_state == "locked" or wall["door_state"] == "locked":
                return WallResult(False, error_key="lighting.errors.locked")
        return WallResult(True, {"wall": self.walls.update(wall_id, door_state=door_state)})
    def delete(self, *, campaign_id: str, wall_id: str, user_id: str) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return WallResult(False, error_key="lighting.errors.denied")
        wall = self.walls.get(wall_id)
        if not wall or wall["campaign_id"] != campaign_id: return WallResult(False, error_key="lighting.errors.not_found")
        self.walls.delete(wall_id); return WallResult(True, {"wall_id": wall_id, "scene_id": wall["scene_id"]})

    def delete_many(self, *, campaign_id: str, wall_ids: list[str], user_id: str) -> WallResult:
        """Apaga o que for desta campanha e ignora o resto, em silencio.

        Uma selecao pode conter coisa que outra pessoa ja apagou, ou id de outra
        mesa se alguem forjar o corpo. Recusar o lote inteiro por causa de um item
        transformaria uma corrida comum em erro na cara do mestre; obedecer a
        qualquer id seria a porta aberta. Apagar so o que e daqui resolve os dois.
        """
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        wanted = [str(value) for value in (wall_ids or []) if value][:MAX_BULK]
        rows = [row for row in (self.walls.get(value) for value in wanted)
                if row and row["campaign_id"] == campaign_id]
        if not rows: return WallResult(True, {"wall_ids": [], "scene_id": None})
        self.walls.delete_many([row["id"] for row in rows])
        return WallResult(True, {"wall_ids": [row["id"] for row in rows], "scene_id": rows[0]["scene_id"]})
