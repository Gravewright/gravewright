from __future__ import annotations
from dataclasses import dataclass, field
from math import hypot, isfinite
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_wall_repository import SceneWallRepository

NODE_TOLERANCE = 1.0



MIN_SEGMENT = 8.0

DOOR_STATES = ("closed", "open", "locked")
BEHAVIORS = {"block", "pass"}
SOUND_BEHAVIORS = {"block", "attenuate", "pass"}
PRESENTATIONS = {"normal", "window", "bars", "invisible", "secret"}



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
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        rows = [self._project(row, role=role) for row in self.walls.list_for_scene(scene_id)]
        return WallResult(True, {"campaign_id": campaign_id, "scene_id": scene_id, "walls": [row for row in rows if row is not None]})
    def _linked_endpoint(self, scene_id: str, x: float, y: float) -> tuple[float, float]:
        """Canonicalize a near endpoint so a visual junction is also a geometric junction."""
        best = None; best_distance = NODE_TOLERANCE
        for wall in self.walls.list_for_scene(scene_id):
            for px, py in ((wall["x1"], wall["y1"]), (wall["x2"], wall["y2"])):
                distance = hypot(px-x, py-y)
                if distance <= best_distance:
                    best = (float(px), float(py)); best_distance = distance
        return best or (x, y)
    def create(self, *, campaign_id: str, scene_id: str, user_id: str, kind: str, x1: float, y1: float, x2: float, y2: float, behavior: dict | None = None, presentation: str = "normal", vertical: dict | None = None) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return WallResult(False, error_key="lighting.errors.not_found")
        points = (x1,y1,x2,y2)
        channels = self._channels(behavior)
        bounds = self._vertical(vertical)
        if kind not in {"wall","door"} or channels is None or bounds is None or presentation not in PRESENTATIONS or not all(isfinite(v) for v in points): return WallResult(False, error_key="lighting.errors.invalid")
        limit = max(float(scene["width"]), float(scene["height"])) * 2
        if any(abs(v) > limit for v in points): return WallResult(False, error_key="lighting.errors.invalid")
        x1,y1=self._linked_endpoint(scene_id,x1,y1);x2,y2=self._linked_endpoint(scene_id,x2,y2)
        if hypot(x2-x1,y2-y1) < 2:return WallResult(False,error_key="lighting.errors.invalid")
        wall = self.walls.create(campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id, kind=kind, x1=x1,y1=y1,x2=x2,y2=y2, presentation=presentation, **channels, **bounds)
        return WallResult(True, {"wall": wall})
    def update(self, *, campaign_id: str, wall_id: str, user_id: str, **values) -> WallResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        wall = self.walls.get(wall_id)
        if not wall or wall["campaign_id"] != campaign_id:
            return WallResult(False, error_key="lighting.errors.not_found")
        allowed = {key: values[key] for key in ("x1", "y1", "x2", "y2") if key in values}
        behavior = values.get("behavior")
        if behavior is not None:
            channels = self._channels(behavior)
            if channels is None: return WallResult(False, error_key="lighting.errors.invalid")
            allowed.update(channels)
        if "presentation" in values:
            if values["presentation"] not in PRESENTATIONS: return WallResult(False, error_key="lighting.errors.invalid")
            allowed["presentation"] = values["presentation"]
        if "discovered" in values:
            if not isinstance(values["discovered"], bool): return WallResult(False, error_key="lighting.errors.invalid")
            allowed["discovered"] = int(values["discovered"])
        if "vertical" in values:
            bounds = self._vertical(values["vertical"])
            if bounds is None: return WallResult(False, error_key="lighting.errors.invalid")
            allowed.update(bounds)
        try:
            allowed = {key: float(value) if key in {"x1", "y1", "x2", "y2"} else value for key, value in allowed.items()}
        except (TypeError, ValueError):
            return WallResult(False, error_key="lighting.errors.invalid")
        merged = {**wall, **allowed}
        scene = self.scenes.get_by_id(wall["scene_id"])
        limit = max(float(scene["width"]), float(scene["height"])) * 2 if scene else 0
        coordinates = [value for key, value in allowed.items() if key in {"x1", "y1", "x2", "y2"}]
        if (not allowed or not all(isfinite(value) and abs(value) <= limit for value in coordinates)
                or hypot(merged["x2"] - merged["x1"], merged["y2"] - merged["y1"]) < 2):
            return WallResult(False, error_key="lighting.errors.invalid")
        return WallResult(True, {"wall": self.walls.update(wall_id, **allowed)})

    @staticmethod
    def _channels(behavior: dict | None) -> dict | None:
        raw = behavior if isinstance(behavior, dict) else {}
        if any(key not in {"movement", "vision", "light", "sound"} for key in raw): return None
        values = {name: str(raw.get(name, "block")).lower() for name in ("movement", "vision", "light")}
        if any(value not in BEHAVIORS for value in values.values()): return None
        sound = str(raw.get("sound", "block")).lower()
        if sound not in SOUND_BEHAVIORS: return None
        return {**{f"{name}_behavior": value for name, value in values.items()}, "sound_behavior": sound}

    @staticmethod
    def _vertical(vertical: dict | None) -> dict | None:
        if vertical is None:
            return {"vertical_bottom": None, "vertical_top": None}
        if not isinstance(vertical, dict) or any(key not in {"bottom", "top"} for key in vertical): return None
        bottom, top = vertical.get("bottom"), vertical.get("top")
        if bottom is None and top is None: return {"vertical_bottom": None, "vertical_top": None}
        if bottom is None or top is None: return None
        try: bottom, top = float(bottom), float(top)
        except (TypeError, ValueError): return None
        if not isfinite(bottom) or not isfinite(top) or abs(bottom)>1_000_000 or abs(top)>1_000_000 or bottom>=top: return None
        return {"vertical_bottom": bottom, "vertical_top": top}

    @staticmethod
    def _project(wall: dict, *, role: str | None) -> dict | None:
        row = dict(wall)
        presentation = str(row.get("presentation") or "normal")
        discovered = bool(row.get("discovered"))
        if role != "gm" and presentation == "invisible": return None
        if role != "gm" and presentation == "secret" and not discovered:
            row["presentation"] = "normal"
            row["kind"] = "wall"
            row.pop("door_state", None)
            row.pop("discovered", None)
        return row
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

    def move_endpoint(self, *, campaign_id: str, scene_id: str, wall_id: str, endpoint: int,
                      user_id: str, to_x: float, to_y: float) -> WallResult:
        """Move one wall endpoint, intentionally detaching it from a welded node."""
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return WallResult(False, error_key="lighting.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        wall = self.walls.get(wall_id)
        if not scene or scene["campaign_id"] != campaign_id or not wall or wall["scene_id"] != scene_id:
            return WallResult(False, error_key="lighting.errors.not_found")
        if endpoint not in {1, 2} or not all(isfinite(value) for value in (to_x, to_y)):
            return WallResult(False, error_key="lighting.errors.invalid")
        limit = max(float(scene["width"]), float(scene["height"])) * 2
        if abs(to_x) > limit or abs(to_y) > limit:
            return WallResult(False, error_key="lighting.errors.invalid")
        other_x, other_y = (wall["x2"], wall["y2"]) if endpoint == 1 else (wall["x1"], wall["y1"])
        if hypot(to_x - other_x, to_y - other_y) < 2:
            return WallResult(False, error_key="lighting.errors.invalid")
        updated = self.walls.update(wall_id, **{f"x{endpoint}": to_x, f"y{endpoint}": to_y})
        return WallResult(True, {"scene_id": scene_id, "wall": updated,
                                "walls": self.walls.list_for_scene(scene_id)})

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
            movement_behavior=wall.get("movement_behavior", "block"),
            vision_behavior=wall.get("vision_behavior", "block"),
            light_behavior=wall.get("light_behavior", "block"),
            sound_behavior=wall.get("sound_behavior", "block"),
            presentation=wall.get("presentation", "normal"), discovered=wall.get("discovered", 0),
            vertical_bottom=wall.get("vertical_bottom"), vertical_top=wall.get("vertical_top"),
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
        if role != "gm" and wall.get("presentation") == "secret" and not wall.get("discovered"):
            return WallResult(False, error_key="lighting.errors.not_found")
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
