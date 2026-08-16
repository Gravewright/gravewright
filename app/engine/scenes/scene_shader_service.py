from __future__ import annotations
import re
from dataclasses import dataclass, field
from math import isfinite
from typing import Any
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_shader_repository import SceneShaderRepository
from app.engine.scenes.shader_preset_registry import get_preset, implementation_reference, public_registry, validate_parameters

BLEND_MODES = frozenset({"normal", "add", "multiply", "screen"})
from app.persistence.repositories.scene_repository import SceneRepository





















MAX_SOURCE = 32000
MAX_NAME = 60

MAX_RADIUS_CELLS = 120.0
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")



MAX_BULK = 500

@dataclass(frozen=True)
class ShaderResult:
    success: bool
    payload: dict = field(default_factory=dict)
    error_key: str | None = None

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def _strip_comments(source: str) -> str:
    """Comentario nao e codigo: `// while` nao pode reprovar um shader honesto."""
    without_block = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    return re.sub(r"//[^\n]*", " ", without_block)

def review(source: str) -> str | None:
    """Devolve a chave do problema, ou None se o texto pode ser gravado.

    So resta o que e sobre o CAMPO: vazio nao e shader, e texto sem teto encheria
    banco e rede. Se o GLSL compila, se e bonito ou se e lento, quem responde e a
    GPU de quem esta olhando, e a resposta dela volta como frase no editor.
    """
    if not source.strip(): return "lighting.errors.shader_empty"
    if len(source) > MAX_SOURCE: return "lighting.errors.shader_long"
    return None

class SceneShaderService:
    def __init__(self) -> None:
        self.shaders = SceneShaderRepository(); self.scenes = SceneRepository(); self.campaigns = CampaignRepository()

    def _scene_for(self, campaign_id: str, scene_id: str, user_id: str, *, gm_only: bool) -> tuple[dict | None, str | None]:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None or (gm_only and role != "gm"): return None, "lighting.errors.denied"
        scene = self.scenes.get_by_id(scene_id)
        if not scene or scene["campaign_id"] != campaign_id: return None, "lighting.errors.not_found"
        return scene, None

    def state(self, *, campaign_id: str, scene_id: str, user_id: str) -> ShaderResult:
        _, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=False)
        if error: return ShaderResult(False, error_key=error)
        return ShaderResult(True, {"campaign_id": campaign_id, "scene_id": scene_id, "shaders": self.shaders.list_for_scene(scene_id)})

    def presets(self) -> ShaderResult:
        return ShaderResult(True, {"presets": public_registry(), "schema_version": 1})

    def preset(self, preset_id: str) -> ShaderResult:
        value = get_preset(preset_id)
        return ShaderResult(True, {"preset": value}) if value else ShaderResult(False, error_key="sdk.shaders.preset_not_found")

    def semantic_state(self, *, campaign_id: str, scene_id: str, user_id: str) -> ShaderResult:
        result = self.state(campaign_id=campaign_id, scene_id=scene_id, user_id=user_id)
        if not result.success:
            return result
        return ShaderResult(True, {"instances": [self._semantic(row) for row in result.payload["shaders"] if row.get("preset_id")]})

    def apply_preset(self, *, campaign_id: str, scene_id: str, user_id: str, preset_id: str, schema_version: int, parameters: Any) -> ShaderResult:
        preset = get_preset(preset_id)
        if preset is None:
            return ShaderResult(False, error_key="sdk.shaders.preset_not_found")
        if schema_version != preset["schemaVersion"]:
            return ShaderResult(False, error_key="sdk.shaders.schema_version_invalid")
        normalized, error = validate_parameters(parameters, partial=False)
        if normalized is None:
            return ShaderResult(False, error_key=error)
        scene, denied = self._scene_for(campaign_id, scene_id, user_id, gm_only=True)
        if denied:
            return ShaderResult(False, error_key=denied)
        values = self._storage_values(normalized)
        cleaned, problem = self._clean(values, scene)
        if cleaned is None:
            return ShaderResult(False, error_key=problem)
        row = self.shaders.create(
            campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id,
            preset_id=preset_id, preset_schema_version=schema_version,
            source=implementation_reference(preset_id), name=preset["labelKey"], version=1,
            **cleaned,
        )
        return ShaderResult(True, {"instance": self._semantic(row)})

    def update_preset(self, *, campaign_id: str, shader_id: str, user_id: str, parameters: Any, expected_version: int | None) -> ShaderResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return ShaderResult(False, error_key="lighting.errors.denied")
        current = self.shaders.get(shader_id)
        if not current or current.get("campaign_id") != campaign_id or not current.get("preset_id"):
            return ShaderResult(False, error_key="sdk.shaders.instance_not_found")
        normalized, error = validate_parameters(parameters, partial=True)
        if normalized is None or not normalized:
            return ShaderResult(False, error_key=error or "sdk.shaders.parameters_invalid")
        cleaned, problem = self._clean(self._storage_values(normalized), self.scenes.get_by_id(current["scene_id"]))
        if cleaned is None:
            return ShaderResult(False, error_key=problem)
        updated = self.shaders.update(shader_id, expected_version=expected_version, **cleaned)
        if updated is None:
            return ShaderResult(False, error_key="sdk.shaders.stale_version" if self.shaders.get(shader_id) else "sdk.shaders.instance_not_found")
        return ShaderResult(True, {"instance": self._semantic(updated)})

    def remove_preset(self, *, campaign_id: str, shader_id: str, user_id: str) -> ShaderResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return ShaderResult(False, error_key="lighting.errors.denied")
        current = self.shaders.get(shader_id)
        if not current or current.get("campaign_id") != campaign_id or not current.get("preset_id"):
            return ShaderResult(False, error_key="sdk.shaders.instance_not_found")
        self.shaders.delete(shader_id)
        return ShaderResult(True, {"instance_id": shader_id, "scene_id": current["scene_id"]})

    @staticmethod
    def _storage_values(parameters: dict[str, Any]) -> dict[str, Any]:
        return {("blend_mode" if key == "blendMode" else key): value for key, value in parameters.items()}

    @staticmethod
    def _semantic(row: dict) -> dict:
        return {
            "id": row["id"], "sceneId": row["scene_id"], "presetId": row["preset_id"],
            "schemaVersion": int(row.get("preset_schema_version") or 1),
            "version": int(row.get("version") or 1),
            "parameters": {
                "x": row["x"], "y": row["y"], "radius": row["radius"], "rotation": row["rotation"],
                "opacity": row["opacity"], "intensity": row["intensity"], "scale": row["scale"],
                "speed": row["speed"], "color": row["color"], "blendMode": row["blend_mode"],
                "enabled": bool(row["enabled"]),
            },
        }

    def _clean(self, values: dict, scene: dict | None = None) -> tuple[dict | None, str | None]:
        cleaned: dict = {}


        for key in ("x", "y"):
            if key not in values: continue
            try: number = float(values[key])
            except (TypeError, ValueError): return None, "lighting.errors.invalid"
            if not isfinite(number): return None, "lighting.errors.invalid"
            if scene and abs(number) > max(float(scene["width"]), float(scene["height"])) * 2:
                return None, "lighting.errors.invalid"
            cleaned[key] = number
        if "radius" in values:
            try: number = float(values["radius"])
            except (TypeError, ValueError): return None, "lighting.errors.invalid"
            if not isfinite(number): return None, "lighting.errors.invalid"


            cleaned["radius"] = _clamp(number, 0.0, MAX_RADIUS_CELLS)
        if "rotation" in values:
            try: number = float(values["rotation"])
            except (TypeError, ValueError): return None, "lighting.errors.invalid"
            if not isfinite(number): return None, "lighting.errors.invalid"


            cleaned["rotation"] = number % 360.0
        if "source" in values:
            source = str(values["source"] or "")
            problem = review(source)
            if problem: return None, problem
            cleaned["source"] = source
        if "blend_mode" in values:
            blend_mode = str(values["blend_mode"] or "").strip().lower()
            if blend_mode not in BLEND_MODES: return None, "lighting.errors.invalid"
            cleaned["blend_mode"] = blend_mode
        if "name" in values:
            cleaned["name"] = str(values["name"] or "").strip()[:MAX_NAME]
        for key, low, high in (("intensity", 0.0, 1.0), ("opacity", 0.0, 1.0), ("scale", 0.1, 20.0), ("speed", 0.0, 8.0)):
            if key not in values: continue
            try: number = float(values[key])
            except (TypeError, ValueError): return None, "lighting.errors.invalid"
            if not isfinite(number): return None, "lighting.errors.invalid"
            cleaned[key] = _clamp(number, low, high)
        if "color" in values:
            color = str(values["color"] or "")
            if not HEX_COLOR.match(color): return None, "lighting.errors.invalid"
            cleaned["color"] = color.lower()
        if "enabled" in values:
            cleaned["enabled"] = 1 if values["enabled"] else 0
        return cleaned, None

    def create(self, *, campaign_id: str, scene_id: str, user_id: str, **values) -> ShaderResult:
        scene, error = self._scene_for(campaign_id, scene_id, user_id, gm_only=True)
        if error: return ShaderResult(False, error_key=error)


        centre = {"x": float(scene["width"]) / 2, "y": float(scene["height"]) / 2}
        cleaned, problem = self._clean({"source": DEFAULT_SOURCE, **centre, **values}, scene)
        if cleaned is None: return ShaderResult(False, error_key=problem)
        shader = self.shaders.create(campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id, **cleaned)
        return ShaderResult(True, {"shader": shader})

    def update(self, *, campaign_id: str, shader_id: str, user_id: str, **values) -> ShaderResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return ShaderResult(False, error_key="lighting.errors.denied")
        shader = self.shaders.get(shader_id)
        if not shader or shader["campaign_id"] != campaign_id: return ShaderResult(False, error_key="lighting.errors.not_found")
        cleaned, problem = self._clean(values, self.scenes.get_by_id(shader["scene_id"]))
        if cleaned is None: return ShaderResult(False, error_key=problem)
        if not cleaned: return ShaderResult(True, {"shader": shader})
        return ShaderResult(True, {"shader": self.shaders.update(shader_id, **cleaned)})

    def delete(self, *, campaign_id: str, shader_id: str, user_id: str) -> ShaderResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm": return ShaderResult(False, error_key="lighting.errors.denied")
        shader = self.shaders.get(shader_id)
        if not shader or shader["campaign_id"] != campaign_id: return ShaderResult(False, error_key="lighting.errors.not_found")
        self.shaders.delete(shader_id)
        return ShaderResult(True, {"shader_id": shader_id, "scene_id": shader["scene_id"]})

    def delete_many(self, *, campaign_id: str, shader_ids: list[str], user_id: str) -> ShaderResult:
        """Apaga o que for desta campanha e ignora o resto, em silencio.

        Uma selecao pode conter coisa que outra pessoa ja apagou, ou id de outra
        mesa se alguem forjar o corpo. Recusar o lote inteiro por causa de um item
        transformaria uma corrida comum em erro na cara do mestre; obedecer a
        qualquer id seria a porta aberta. Apagar so o que e daqui resolve os dois.
        """
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return ShaderResult(False, error_key="lighting.errors.denied")
        wanted = [str(value) for value in (shader_ids or []) if value][:MAX_BULK]
        rows = [row for row in (self.shaders.get(value) for value in wanted)
                if row and row["campaign_id"] == campaign_id]
        if not rows: return ShaderResult(True, {"shader_ids": [], "scene_id": None})
        self.shaders.delete_many([row["id"] for row in rows])
        return ShaderResult(True, {"shader_ids": [row["id"] for row in rows], "scene_id": rows[0]["scene_id"]})



DEFAULT_SOURCE = """// Névoa. Este é um fragment shader: ele roda uma vez por pixel do quadro do
// efeito e escreve a cor final em finalColor.
//
// O quadro tem o tamanho do ALCANCE, e a máscara circular recorta a borda, o que
// você pintar fora dele não tem onde existir. Pinte à vontade.
//
// O alfa é o que deixa o mapa aparecer por baixo. Escreva sempre com a cor já
// multiplicada pelo alfa: vec4(cor * a, a).
float ruido(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float suave(vec2 p) {
    vec2 base = floor(p);
    vec2 f = smoothstep(0.0, 1.0, fract(p));
    return mix(
        mix(ruido(base), ruido(base + vec2(1.0, 0.0)), f.x),
        mix(ruido(base + vec2(0.0, 1.0)), ruido(base + vec2(1.0, 1.0)), f.x),
        f.y);
}

void main() {
    // gwPattern dá o ponto de mundo do pixel: girado pela régua de rotação e já
    // na escala certa. Desenhar em cima dele é o que mantém a névoa colada no mapa
    // quando alguém mexe no zoom, e o que faz um alcance pequeno mostrar o mesmo
    // tanto de desenho que um grande, em vez de um pedaço chapado.
    vec2 p = gwPattern(vTextureCoord);
    float t = uTime * 0.05 * uSpeed;

    float n = suave(p + vec2(t, t * 0.4)) * 0.65
            + suave(p * 2.3 - vec2(0.0, t * 0.7)) * 0.35;

    float a = smoothstep(0.35, 0.9, n) * uIntensity;
    vec3 cor = uColor * (0.75 + 0.25 * n);

    // A luz da cena entra aqui: perto de uma tocha a névoa esquenta e clareia, no
    // canto sem foco ela quase some. É isto que separa um efeito desenhado por
    // cima de um efeito que está na cena.
    vec4 luz = gwLight(vTextureCoord);
    float brilho = dot(luz.rgb, vec3(0.2126, 0.7152, 0.0722));
    cor = mix(cor * 0.45, cor + luz.rgb * 0.6, clamp(brilho * 1.6, 0.0, 1.0));
    a *= 0.55 + 0.45 * clamp(brilho * 2.0, 0.0, 1.0);

    finalColor = vec4(cor * a, a);
}
"""
