import re
from pathlib import Path

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user

ROOT=Path(__file__).resolve().parents[2]

def _game_page(user_id):
    from main import app
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        return client.get("/game")

def test_game_page_renders_the_lighting_ui_for_the_gm(db):
    """As asserções estáticas leem arquivos soltos e não veem escopo de template:
    um `room` fora do laço passa por elas e derruba a página inteira."""
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); seed_scene(campaign)
    response=_game_page(gm)
    assert response.status_code == 200, response.text
    body=response.text

    assert f'data-modal-id="light-editor-{campaign}"' in body
    assert f'data-modal-id="token-vision-{campaign}"' in body
    assert 'data-tool="light"' in body
    assert 'data-tool-sub-panel="light"' in body
    for sub in ("torch", "pulse", "none"):
        assert f'data-subtool="{sub}"' in body, sub

def test_scene_edit_modal_renders_the_darkness_control(db):
    from main import app
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response=client.get(f'/game/scenes/{scene["id"]}/edit-modal', params={"campaign_id": campaign})
    assert response.status_code == 200, response.text
    body=response.text
    assert 'name="darkness"' in body
    # o bloco proprio e o que impede a escuridao de esticar o modal
    assert 'class="scene-boxed-field scene-grid-row--boxed"' in body
    assert "scene-field-hint" in body

def test_player_game_page_renders_without_the_gm_only_lighting_tools(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player")
    campaign=seed_campaign(gm); seed_member(campaign,player,"player")
    response=_game_page(player)
    assert response.status_code == 200, response.text
    body=response.text

    assert f'data-modal-id="light-editor-{campaign}"' not in body, "editor de foco e so do GM"
    assert 'data-tool="light"' not in body
    assert 'data-tool="wall"' not in body

def test_gravewright_map_exports_every_api_its_consumers_call():
    """O harness JS estuba window.GravewrightMap inteiro, entao so este teste pega
    uma API consumida que nunca foi exportada pelo map-controller."""
    controller=(ROOT/"static/js/map/map-controller.js").read_text(encoding="utf-8")
    block=controller.split("window.GravewrightMap = {",1)[1].split("\n    };",1)[0]
    exported={m.group(1) for m in re.finditer(r"^\s+([A-Za-z_]\w*)\s*[:,]",block,re.MULTILINE)}

    missing={}
    for path in sorted((ROOT/"static/js").rglob("*.js")):
        if path.name=="map-controller.js": continue
        used=set(re.findall(r"window\.GravewrightMap\??\.(\w+)",path.read_text(encoding="utf-8")))
        if used-exported: missing[path.relative_to(ROOT).as_posix()]=sorted(used-exported)

    assert not missing, f"APIs chamadas mas nao exportadas por window.GravewrightMap: {missing}"

def test_wall_layer_has_wall_and_door_tools():
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    registry=(ROOT/"static/js/tools/tools-registry.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    assert 'data-active-layer="walls"' in template and 'data-active-layer="effects"' in template
    assert 'data-tool="wall"' in template and 'data-tool="door"' in template
    assert 'wall: ["walls"]' in registry and 'door: ["walls"]' in registry

    # Esconder a camada de Paredes apaga linha e no, nunca a escuridao nem o veu:
    # o jogador nao pode ganhar visao porque o GM arrumou o desenho da parede.
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    assert "const lightingVisible = shown(EDIT_LAYERS.light)" in script
    assert "activeLayer === EDIT_LAYERS.wall && wallsVisible" in script

    # E o marcador de foco vive na camada de Iluminacao: enquanto dividia o `return`
    # antecipado com a parede, editar luz obrigava a ver o emaranhado de linhas.
    assert "if (lighting.editingLights) {" in pixi
    assert pixi.index("if (lighting.editingLights) {") < pixi.index("if (!lighting.editing) {")

def test_lighting_uses_server_walls_and_no_eval_geometry():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    pixi_layers=(ROOT/"static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    assert "/game/walls" in script and "scene.walls.updated" in script
    assert "visibilityPolygon" in script and "rayHit" in script
    assert 'wall.kind !== "door" || wall.door_state !== "open"' in script
    assert "PIXI.Graphics" in pixi_layers and "_renderLighting" in pixi
    assert "data-lighting-layer" not in template
    assert 'surface.addEventListener("pointerup"' in script
    assert 'kind === "wall" && chain ? end : null' in script
    assert "eval(" not in script and "new Function" not in script

def test_lighting_second_point_commits_on_pointerdown_not_on_click():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")

    assert 'surface.addEventListener("click"' not in script

    pointerdown=script.split('surface.addEventListener("pointerdown"',1)[1].split('surface.addEventListener("pointerup"',1)[0]
    assert "void this.create(point, tool, !event.altKey)" in pointerdown

    assert "const DRAG_THRESHOLD_PX = 6" in script
    assert "event.clientX - down.x, event.clientY - down.y) >= DRAG_THRESHOLD_PX" in script

    assert 'surface.addEventListener("pointercancel"' in script

def test_lighting_draws_at_free_angles_and_chains_walls_by_default():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")

    assert "function snapToGrid(point, scene)" in script
    assert "scene?.scaledTileSize || 0) / SNAP_DIVISIONS" in script
    assert "const SNAP_DIVISIONS = 2" in script

    # angulo livre: o ima de extremidade continua ligado, a grade so com Shift
    assert "function nearestEndpoint(point, walls, tolerance, exclude = null)" in script
    assert "nearestEndpoint(point, this.walls, ENDPOINT_SNAP_PX / zoom, exclude)" in script
    assert "return event.shiftKey ? snapToGrid(point, this.scene()) : point" in script
    assert "if (!point || event.shiftKey) return point" not in script

    assert script.count("this.create(point, tool, !event.altKey)")==1
    assert script.count("this.create(end, tool, !event.altKey)")==1
    assert "event.ctrlKey" not in script

    assert "this.preview = this.target(event)" in script
    assert "const hit = this.hit(raw)" in script

def test_walls_and_doors_are_colour_coded_by_kind_and_state():
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")
    service=(ROOT/"app/engine/scenes/scene_wall_service.py").read_text(encoding="utf-8")
    routes=(ROOT/"app/actions/game/manage_walls.py").read_text(encoding="utf-8")

    # parede e porta nunca compartilham cor, e cada estado da porta tem a sua
    wall_colour="0x6366f1"
    door_colours={"closed":"0xf59e0b","open":"0x22c55e","locked":"0xef4444"}
    assert f"const WALL_COLOR = {wall_colour}" in pixi
    for state,colour in door_colours.items():
        assert f"{state}: {colour}" in pixi
    assert wall_colour not in door_colours.values()
    assert len(set(door_colours.values()))==3

    assert 'DOOR_CYCLE = { closed: "open", open: "locked", locked: "closed" }' in script
    assert '"/game/walls/door-state"' in script

    assert "door_state IN ('closed','open','locked')" in tables
    assert 'DOOR_STATES = ("closed", "open", "locked")' in service
    assert '@post("/game/walls/door-state")' in routes
    assert "toggle-door" not in routes and "toggle-door" not in script

def test_locked_doors_still_block_vision():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    # o filtro de bloqueadores e por "nao esta aberta", entao trancada bloqueia junto
    assert 'wall.kind !== "door" || wall.door_state !== "open"' in script

def test_door_state_migration_widens_the_check_constraint():
    migration=(ROOT/"migrations/versions/0025_door_locked_state.py").read_text(encoding="utf-8")
    assert 'down_revision = "0024_scene_walls"' in migration
    assert "door_state IN ('closed','open','locked')" in migration
    assert "batch_alter_table" in migration, "SQLite exige rebuild para trocar CHECK"
    # o downgrade nao pode deixar linhas fora do dominio antigo
    downgrade=migration.split("def downgrade()",1)[1]
    assert "UPDATE scene_walls SET door_state = 'closed'" in downgrade

def test_select_tool_drags_welded_wall_nodes():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    routes=(ROOT/"app/actions/game/manage_walls.py").read_text(encoding="utf-8")
    service=(ROOT/"app/engine/scenes/scene_wall_service.py").read_text(encoding="utf-8")

    assert "function moveNode(walls, from, to)" in script
    assert '"/game/walls/move-node"' in script
    assert "this.nodeDrag.to = this.target(event, this.nodeDrag.from)" in script

    # dentro da selecao a ordem importa: foco, depois no, depois corpo da parede
    select=script.split('if (tool === "select") {',1)[1].split("const hit = this.hit(raw)",1)[0]
    assert select.index("this.lightAt(raw)") < select.index("this.nodeAt(raw)")
    assert "this.nodeDrag = { from: { ...node }" in select

    assert "nodesGrabbable" in script and "nodesGrabbable" in pixi

    assert '@post("/game/walls/move-node")' in routes
    assert "def move_node(" in service and "NODE_TOLERANCE" in service

def test_doors_are_operable_in_play_on_any_layer():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")

    # a operacao em jogo precisa rodar antes do portao de GM/camada do editor
    handler=script.split('surface.addEventListener("pointerdown"',1)[1]
    play_index=handler.index("this.handlePlayDoor(event)")
    gate_index=handler.index("Object.values(EDIT_LAYERS)")
    assert play_index < gate_index, "porta em jogo nao pode depender do portao do editor"

    play=script.split("handlePlayDoor(event)",1)[1].split("bind()",1)[0]
    assert "if (activeLayer === EDIT_LAYERS.door) return false" in play, "na camada de parede manda o editor"
    assert "lock: event.button === 2" in play
    # o botao direito de um jogador nao pode ser engolido: o menu de contexto e dele
    assert "if (event.button === 2 && !this.isGm) return false" in play

    operate=script.split("operateDoor(door,",1)[1].split("async placeLight",1)[0]
    assert "if (!this.isGm) return" in operate, "a tranca e privilegio do GM"
    # o direito nao abre nem fecha: so alterna a tranca, e trancar fecha junto
    assert 'door.door_state === "locked" ? "closed" : "locked"' in operate
    assert "cycleDoor" not in operate, "o ciclo de tres estados ficou so no editor"
    assert 'toast("Esta porta está trancada.")' in operate, "esquerdo ainda respeita a tranca"

    # a porta inteira opera: mirar so o marcador do meio e dificil com a camera afastada
    door_at=script.split("doorAt(point) {",1)[1].split("lightAt(point)",1)[0]
    assert "pointSegmentDistance(point, wall)" in door_at
    assert "Math.min(" in door_at, "marcador e corpo da porta, o que estiver mais perto"

    # O marcador e o alvo do clique; os dois devem usar a mesma lista filtrada para
    # uma porta fora da visao nao vazar pelo desenho nem pela interacao.
    assert "if (!lighting.editing) {" in pixi and "lighting.doors.forEach" in pixi
    doors=script.split("const doors = walls.filter",1)[1].split("\n",1)[0]
    assert "editing || doorVisionPolygons.some" in script
    assert "pointInPolygon(midpoint(wall), polygon)" in script
    door_at=script.split("doorAt(point) {",1)[1].split("lightAt(point)",1)[0]
    assert "this.visibleDoorIds.has(wall.id)" in door_at

def test_light_sources_are_placed_animated_and_cached():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    registry=(ROOT/"static/js/tools/tools-registry.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'light: ["lighting"]' in registry
    assert 'light:     { options: ["none", "torch", "pulse"], default: "torch" }' in registry
    assert 'data-tool="light"' in template

    assert '"/game/lights"' in script and '"/game/lights/update"' in script and '"/game/lights/delete"' in script
    assert "function animationFactor(light, now)" in script
    # Cada emissao e uma entrada da tabela, nao um `if` a mais: acrescentar tipo
    # de luz nao pode significar acrescentar ramo no caminho quente do desenho.
    for emission in ("torch", "pulse"):
        assert f"{emission}: {{" in script, emission

    # a animacao so pode mexer no brilho: o poligono e caro e fica em cache
    factor=script.split("function animationFactor",1)[1].split("class LightingController",1)[0]
    assert "radius" not in factor and "dim_radius" not in factor
    assert "cachedPolygon(key, origin, blockers, scene, radius)" in script
    assert "this.polygonCache.clear()" in script

    # o laco so acorda quando ha foco animado de fato visivel
    animated=script.split("animated() {",1)[1].split("async refresh",1)[0]
    assert "scene.darkness > 0" in animated and 'light.animation !== "none"' in animated

    assert "RADIAL_SAMPLES" in script, "raio finito precisa de amostras proprias para virar arco"
    # O marcador segue o CONJUNTO de escolhidos, nao um id: com selecao multipla,
    # comparar com um id so pintaria apenas o ultimo que foi clicado.
    assert "lighting.picked?.light?.has(light.id)" in pixi

def test_scene_darkness_flows_from_the_scene_editor_to_the_canvas():
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")
    modal=(ROOT/"templates/pages/game/scene_edit_modal.html").read_text(encoding="utf-8")
    action=(ROOT/"app/actions/game/manage_scenes.py").read_text(encoding="utf-8")
    repo=(ROOT/"app/persistence/repositories/scene_repository.py").read_text(encoding="utf-8")
    scene_js=(ROOT/"static/js/map/scene/map-scene.js").read_text(encoding="utf-8")
    streaming=(ROOT/"static/js/map/streaming/map-streaming.js").read_text(encoding="utf-8")
    forms=(ROOT/"static/js/ui/modals/modal-forms.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    service=(ROOT/"app/engine/scenes/scene_service.py").read_text(encoding="utf-8")

    assert 'Column("darkness"' in tables
    assert 'name="darkness"' in modal
    assert "darkness=_clamp_opacity(data.darkness, 0.0)" in action
    assert "darkness=darkness" in repo and "float(existing[\"darkness\"]) != float(darkness)" in repo, "mudar escuridao precisa bumpar a epoca"
    assert '"darkness": float(scene["darkness"])' in service
    # os tres caminhos que atualizam o canvas precisam carregar o campo
    assert "data-scene-darkness" in template
    assert "canvas.dataset.sceneDarkness" in streaming
    assert '"data-scene-darkness"' in forms
    assert "darkness: clampOpacity(canvas.dataset.sceneDarkness, 0)" in scene_js

def test_vision_is_per_viewer_and_gm_is_not_blinded():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")
    view=(ROOT/"app/engine/tokens/token_view_service.py").read_text(encoding="utf-8")

    assert 'Column("vision_enabled"' in tables and 'Column("vision_range"' in tables
    assert '"vision_enabled": bool(token.get("vision_enabled", 1))' in view
    assert '"vision_range": float(token.get("vision_range") or 0.0)' in view

    sources=script.split("visionSources({ all: everyone = false } = {}) {",1)[1].split("pixiState()",1)[0]
    assert "this.controlsToken(token)" in sources, "jogador enxerga pelos tokens que controla"
    assert "token.vision_enabled !== false" in sources
    assert "(token.vision_range || 0) * size" in sources

    assert "const visionLimited = !this.isGm || playerView" in script
    assert "visionLimited ? 1 : GM_DARKNESS_PREVIEW" in script
    assert "const visionPolygons = visionLimited" in script, "GM sem visao de jogador nao tem recorte"
    # mover token muda o ponto de vista, entao o cache precisa cair
    assert "controllers.forEach((controller) => controller.invalidateGeometry())" in script

    # o GM precisa de um jeito de ligar e desligar a visao de um token
    commands=(ROOT/"app/realtime/commands.py").read_text(encoding="utf-8")
    handler=(ROOT/"app/realtime/token_command_handler.py").read_text(encoding="utf-8")
    menu=(ROOT/"static/js/ui/context-menu/token-context-menu.js").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/light-editor.js").read_text(encoding="utf-8")
    assert 'TOKEN_SET_VISION = "token.set_vision"' in commands
    assert "ClientCommand.TOKEN_SET_VISION.value," in handler, "comando precisa estar na lista tratada"
    assert "async def _set_vision(" in handler
    # o menu so abre o editor; quem envia o comando e o painel, com alcance junto
    assert 'new CustomEvent("token:edit-vision"' in menu
    assert '"token.set_vision"' in editor and "vision_range: range ? Number(range.value) : 0" in editor

def test_radial_samples_share_the_atan2_range():
    """Amostras em [0,2PI) caem depois dos cantos ao ordenar e o contorno enrola
    duas vezes — o foco se desenha como varias luzes empilhadas."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    body=script.split("function visibilityPolygon",1)[1].split("function pointInPolygon",1)[0]
    assert "angles.push(-Math.PI + (i / RADIAL_SAMPLES) * Math.PI * 2)" in body
    assert "angles.push((i / RADIAL_SAMPLES) * Math.PI * 2)" not in body

def test_token_control_comes_from_actor_ownership():
    """controlled_by_user_ids_json nunca e escrito; ler so dele deixaria todo
    jogador sem token e, por consequencia, sem visao nenhuma."""
    repo=(ROOT/"app/persistence/repositories/token_repository.py").read_text(encoding="utf-8")
    view=(ROOT/"app/engine/tokens/token_view_service.py").read_text(encoding="utf-8")
    service=(ROOT/"app/engine/tokens/token_service.py").read_text(encoding="utf-8")

    assert '"controlled_by_user_ids_json": "[]"' in repo, "a coluna segue sem escritor"
    assert "owner_user_ids: list[str] | None = None" in view
    assert "owner_user_ids\n                if owner_user_ids is not None" in view
    assert "def _owner_ids_by_actor(self, campaign_id: str)" in service
    assert "list_owners_for_campaign_actors" in service
    # os tres caminhos que montam TokenView precisam levar a posse junto
    assert service.count("owners_by_actor") >= 3
    assert "owners_by_actor_id=self._owner_ids_by_actor(campaign_id)" in service

def test_streamer_composition_tracks_alpha3_vision_and_effect_layers():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'this.isStreamer = document.body?.dataset?.streamerMode === "true"' in script
    sources=script.split("visionSources({ all: everyone = false } = {}) {",1)[1].split("pixiState()",1)[0]
    assert "if (this.isStreamer)" in sources and "chosen = all" in sources
    assert "shaders: (effectsVisible && !classic" in script

    for layer in ("effects", "walls", "lighting"):
        assert f'data-active-layer="{layer}"' in template
        assert f'data-layer-visibility="{{{{ layer }}}}"' in template or f'data-layer-visibility="{layer}"' in template

def test_alpha3_visual_layers_toggle_independently_for_streamer():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    toolbar=(ROOT/"static/js/tools/tools-toolbar.js").read_text(encoding="utf-8")

    for state in ("lightingVisible", "effectsVisible", "wallsVisible"):
        assert f"const {state}" in script
    assert "const visible = lightingVisible || effectsVisible || wallsVisible" in script
    assert "const darkness = lightingVisible" in script
    assert "particleClouds: (effectsVisible" in script
    assert "shaders: (effectsVisible && !classic" in script
    assert "wallsVisible && wall.kind === \"door\"" in script
    for layer in ("effects", "walls", "lighting"):
        assert f"{layer}: true" in toolbar

def test_streamer_gets_the_gm_layer_hud_and_local_alpha3_editors():
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")

    assert "room.member_role in ('gm', 'assistant_gm') or room.is_streamer" in template
    assert "dynamic_lighting_enabled and (room.member_role == 'gm' or room.is_streamer)" in template
    assert "room.member_role == 'gm' or room.is_streamer" in template
    assert 'data-lighting-gm="{{ \'true\' if room.member_role == \'gm\' or room.is_streamer else \'false\' }}"' in template
    assert 'dataset?.streamerMode === "true"' in script
    assert "return localPost(url, body)" in script

def test_light_and_vision_editors_use_the_project_modal_pattern():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/light-editor.js").read_text(encoding="utf-8")
    light_modal=(ROOT/"templates/pages/game/modals/light_editor.html").read_text(encoding="utf-8")
    vision_modal=(ROOT/"templates/pages/game/modals/token_vision.html").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'surface.addEventListener("dblclick"' in script
    assert 'new CustomEvent("lighting:edit-light"' in script
    assert "patchLight: (canvas, lightId, patch)" in script
    assert "deleteLight: (canvas, lightId)" in script

    # os dois painels sao modais do projeto, nao divs flutuantes proprias
    for modal in (light_modal, vision_modal):
        assert 'class="game-modal-window dialog-modal' in modal
        assert "data-modal-window" in modal and "data-modal-id=" in modal
        assert "game-modal-titlebar" in modal and "data-modal-drag-handle" in modal
        assert "data-modal-close" in modal
        assert 'class="game-field"' in modal
    assert "document.createElement" not in editor, "o markup vem do template, nao do JS"
    assert "modals()?.open?.(`light-editor-" in editor
    assert "modals()?.open?.(`token-vision-" in editor

    for control in ("bright_radius", "dim_radius", "intensity", "animation", "color"):
        assert f'data-light-field="{control}"' in light_modal, control
    assert 'data-vision-field="vision_range"' in vision_modal
    assert 'data-vision-field="vision_enabled"' in vision_modal

    # arrastar um slider nao pode virar uma requisicao por pixel
    assert "COMMIT_DELAY_MS" in editor and "window.setTimeout(flush, COMMIT_DELAY_MS)" in editor
    # trocar de camada/ferramenta nao pode engolir uma edicao pendente
    assert 'document.addEventListener("tool:active-layer", flush)' in editor

    assert "light-editor.js" in template
    assert "modals/light_editor.html" in template and "modals/token_vision.html" in template
    # O editor existe para GM e para o sandbox local do streamer.
    assert "{% if room.member_role == 'gm' or room.is_streamer %}{% include \"pages/game/modals/light_editor.html\" %}" in template

def test_players_only_see_through_tokens_they_own():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    sources=script.split("visionSources({ all: everyone = false } = {}) {",1)[1].split("pixiState()",1)[0]
    player_branch=sources.split("} else {",1)[1]
    # selecionar o token alheio nao pode emprestar a visao dele
    assert "const owned = all.filter((token) => this.controlsToken(token))" in player_branch
    assert "owned.find((token) => token.token_id === selectedTokenId)" in player_branch
    assert "chosen = selected ? [selected] : owned" in player_branch

def test_darkness_is_composed_with_erase_like_the_fog_layer():
    """Graphics.cut() so abre um buraco por vez: visao + varios focos se atropelam.
    A nevoa deste projeto ja resolve isso com blendMode erase numa RenderTexture,
    que e o mesmo caminho que o Foundry usa para mascarar visibilidade."""
    layers=(ROOT/"static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    renderer=(ROOT/"static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")

    assert ".cut()" not in pixi, "cut() nao acumula buracos"
    assert "board.lightingSprite = new PIXI.Sprite" in layers
    assert "board.lightingScene = new PIXI.Container()" in layers
    for field in ("lightingRT: null,", "lightingGfxPool: []," , "lightingSprite: null,"):
        assert field in renderer, field

    compose=pixi.split("_composeDarkness(board, rt, cssW, cssH, lighting, litAreas, lights, screen, flatten, cam) {",1)[1]
    assert 'eraser.blendMode = "erase"' in compose
    assert "litAreas.forEach((flat) => eraser.poly(flat).fill(" in compose
    assert "board.app.renderer.render({ container: board.lightingScene, target: rt, clear: true })" in compose
    # sem reciclar o pool, os buracos do frame anterior ficam
    assert "board.lightingPoolIndex = 0" in compose and "gfx.clear()" in compose

    # o brilho segue fora da composicao da escuridao, agora como sprites mascarados
    assert "board.lightingGlowGfx = new PIXI.Container()" in layers
    assert "mask.poly(flat).fill" in pixi
    assert "this._resetGlowPool(board)" in pixi, "sem reciclar, o brilho anterior fica"

def test_scene_form_boxed_blocks_span_instead_of_stretching_the_modal():
    """A escuridao entrou na linha flex da grade e, espremida numa das duas colunas,
    empurrava o modal de cena para alem da largura maxima."""
    modal=(ROOT/"templates/pages/game/scene_edit_modal.html").read_text(encoding="utf-8")
    css=(ROOT/"static/css/game.css").read_text(encoding="utf-8")

    # a escuridao tem bloco proprio, fora da linha de 3 itens da grade
    grid_row=modal.split('class="scene-grid-row scene-grid-row--boxed"',1)[1].split("</div>",1)[0]
    assert 'name="darkness"' not in grid_row, "escuridao nao volta para a linha da grade"
    assert 'name="grid_opacity"' in grid_row
    assert 'class="scene-boxed-field scene-grid-row--boxed"' in modal
    darkness=modal.split('class="scene-boxed-field',1)[1]
    assert 'name="darkness"' in darkness and "scene-field-hint" in darkness

    # o span tem de estar na regra dos blocos emoldurados, nao em qualquer lugar
    assert "> .scene-boxed-field {" in css
    rule=css.split("> .scene-boxed-field {",1)[1].split("}",1)[0]
    assert "grid-column: 1 / -1" in rule, rule
    assert ".scene-edit-grid > .scene-grid-row--boxed," in css, "a linha da grade tambem precisa vazar"

    row=css.split(".scene-grid-row {",1)[1].split("}",1)[0]
    assert "flex-wrap: wrap" in row, row

def test_form_controls_are_not_forced_into_text_input_boxes():
    """.game-field input impoe caixa de 38px com borda; range, cor e checkbox
    ficam desproporcionais dentro dela."""
    css=(ROOT/"static/css/game.css").read_text(encoding="utf-8")
    for control in ("range", "color", "checkbox"):
        assert f'.game-field input[type="{control}"]' in css, control
    assert ".scene-field-hint {" in css, "o hint era usado sem existir no CSS"
    # o slider e sua leitura numerica sao um padrao unico, nao copia por painel
    assert ".slider-row {" in css and ".slider-row output {" in css
    for modal in ("modals/light_editor.html", "modals/token_vision.html"):
        assert 'class="slider-row"' in (ROOT/"templates/pages/game"/modal).read_text(encoding="utf-8"), modal

def test_light_tool_exposes_its_animations_in_the_dock():
    """SUB_TOOLS.light sem painel deixa o GM preso na animacao padrao."""
    registry=(ROOT/"static/js/tools/tools-registry.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'light:     { options: ["none", "torch", "pulse"]' in registry
    assert 'data-tool-sub-panel="light"' in template
    panel=template.split('data-tool-sub-panel="light"',1)[1].split("</div>",1)[0]
    for sub in ("torch", "pulse", "none"):
        assert f'data-subtool="{sub}"' in panel, sub

    # Partículas ganharam painel próprio, na camada de Efeitos: não iluminam,
    # então não têm o que fazer no dock da iluminação.
    assert 'particles: ["effects"]' in registry
    assert 'data-tool-sub-panel="particles"' in template
    clouds=template.split('data-tool-sub-panel="particles"',1)[1].split("</div>",1)[0]
    for sub in ("smoke", "ember", "dust", "arcane"):
        assert f'data-subtool="{sub}"' in clouds, sub

def test_vision_range_has_visible_feedback_while_being_set():
    """Quem ajusta o alcance e o GM, que nao tem a visao recortada; e com escuridao 0
    nao ha recorte para ninguem. Sem previa o controle parece morto."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/light-editor.js").read_text(encoding="utf-8")
    modal=(ROOT/"templates/pages/game/modals/token_vision.html").read_text(encoding="utf-8")

    assert 'document.addEventListener("token:vision-preview"' in script
    assert "visionPreviewTokenId" in script
    # a previa ignora o filtro de dono e o de visao ligada: e o que se esta ajustando
    assert "this.visionSources({ all: true })" in script
    assert "visionPreview," in script

    # desenhada fora do bloco de edicao, senao so o GM na camada de luz veria
    preview=pixi.split("const preview = lighting.visionPreview;",1)[1].split("if (!lighting.editing)",1)[0]
    assert "preview.radius * cam.zoom" in preview, "anel do alcance"
    assert "flatten(preview.polygon)" in preview

    assert 'new CustomEvent("token:vision-preview"' in editor
    assert "MutationObserver" in editor, "a previa precisa apagar por qualquer caminho de fechar"
    # e o painel avisa quando a cena nao tem escuridao nenhuma
    assert "data-token-vision-notice" in editor and "data-token-vision-notice" in modal
    assert "sceneDarkness" in editor

def test_door_markers_use_the_state_icons_with_a_vector_fallback():
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    layers=(ROOT/"static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")

    for state in ("closed", "open", "locked"):
        assert f'{state}: "/static/icons/{state}-door.png"' in pixi, state
        assert (ROOT/f"static/icons/{state}-door.png").exists(), state

    assert "PIXI.Assets.load(url)" in pixi
    # sprite precisa de container proprio e de pool reciclado por frame
    assert "board.lightingDoorLayer = new PIXI.Container()" in layers
    assert "_resetDoorPool(board)" in pixi and "_acquireDoorSprite(board, index)" in pixi
    # ate a textura chegar, a porta nao pode ficar sem indicacao nenhuma
    marker=pixi.split("_drawDoorMarker(board, gfx, index, mx, my, door, color) {",1)[1]
    assert "if (texture) {" in marker and "gfx.circle(mx, my, 9)" in marker

def test_gm_borrows_the_vision_of_the_token_they_select():
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    assert "const previewingToken = this.isGm && Boolean(selectedTokenId)" in script
    assert "sources.length === 1 && sources[0].id === selectedTokenId" in script
    assert "const visionLimited = !this.isGm || playerView || previewingToken" in script

def test_wall_and_light_fetches_do_not_take_each_other_down():
    """Com Promise.all e um catch mudo, uma falha em /game/lights zerava tambem as
    paredes — a cena ficava sem portas e sem nenhum aviso."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    load=script.split("const load = async (path) => {",1)[1].split("};",1)[0]
    assert "try {" in load and "catch (error)" in load, "cada recurso trata a propria falha"
    assert "console.warn" in load, "falha silenciosa deixa o problema invisivel"
    refresh=script.split("async refresh(sceneId",1)[1].split("hit(point)",1)[0]
    assert "catch {}" not in refresh, "o catch mudo em volta do Promise.all sumiu"

def test_walls_are_indexed_by_chunk_like_the_rest_of_the_scene():
    """O poligono de visibilidade e quadratico no numero de segmentos. Indexar as
    paredes na mesma malha de chunks da cena faz um foco pagar so pela vizinhanca."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")

    assert "const WALL_CHUNK_TILES" in script
    assert "wallIndexFor(blockers, scene)" in script
    assert "blockersNear(blockers, scene, origin, radius)" in script
    # o indice acompanha o mesmo carimbo que invalida os poligonos
    assert "this.wallIndex.stamp === this.geometryStamp" in script
    assert "this.wallIndex = null" in script

    # sem alcance nao ha corte possivel: o raio livre vai ate a borda da cena
    near=script.split("blockersNear(blockers, scene, origin, radius) {",1)[1].split("cachedPolygon(",1)[0]
    assert "if (!(radius > 0)) return blockers" in near, "corte so vale com alcance finito"
    # o corte e por caixa de chunks, entao e conservador por construcao
    assert "Math.floor((origin.x - radius) / size)" in near

    assert "this.blockersNear(blockers, scene, origin, radius)" in script

def test_unbounded_vision_probes_instead_of_scanning_the_whole_map():
    """Visao sem alcance ainda para nas paredes: um token em sala fechada nao ve
    fora dela. Sondar raios crescentes corta o mapa sem mudar o resultado."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    probe=script.split("unboundedPolygon(origin, blockers, scene, key = \"\") {",1)[1].split("cachedPolygon(",1)[0]

    # so pode parar quando nenhum raio chegou ao limite, ou quando esgotou a cena
    assert "const open = polygon.some((point) => point.distance >= capped - 1e-6)" in probe
    assert "if (!open || exhausted)" in probe, "parar antes disso ignora paredes distantes"
    assert "const exhausted = capped >= diagonal" in probe
    # a ultima tentativa usa o mapa inteiro: o resultado nunca fica menor que o correto
    assert "exhausted ? blockers : this.blockersNear" in probe
    # amostras radiais sao para arco de foco; aqui so inflariam o poligono
    assert "capped, false)" in probe

    # o palpite aprendido evita sondar em vao num mapa aberto, e encolhe sozinho
    assert "this.probeReach.get(key) || step" in probe
    assert "Math.max(step, reached * 1.5)" in probe
    assert "this.probeReach = new Map()" in script

def test_light_animation_is_sampled_above_the_frame_rate():
    """Um componente com poucas amostras por ciclo nao vira chama, vira
    estroboscopio. A versao anterior tinha um seno de 232 ms amostrado a 66 ms."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")

    interval=int(re.search(r"ANIMATION_INTERVAL_MS = (\d+)", script).group(1))
    periods=[int(p) for p in re.findall(r"period: (\d+)", script)]
    # Os periodos das emissoes deliberadas chegam como argumento de breath(); o da
    # varredura, como divisor do proprio ciclo.
    periods += [int(p) for p in re.findall(r"breath\(now, phase[^,]*, (\d+)\)", script)]
    # Todo divisor de tempo do arquivo entra, nao so os das curvas de brilho: a
    # tremida do centro e o balanco das particulas amostram no mesmo laco, e um
    # periodo curto ali sai estroboscopico do mesmo jeito. Foi assim que um
    # `now / 137` passou despercebido.
    periods += [int(p) for p in re.findall(r"now / (\d+)[ )]", script)]
    periods += [int(p) for p in re.findall(r"now / \((\d+) \+ index", script)]

    assert periods, "as curvas precisam declarar periodo explicito, nao divisor cru"
    for period in periods:
        assert period / interval >= 6, f"periodo {period}ms a cada {interval}ms alias"

    # A formula antiga usava divisores crus; garantir que nao voltem. Com busca de
    # substring, `now / 900` contém `now / 90` — o limite de digito e o que separa
    # um periodo legitimo do divisor proibido.
    for banned in (37, 90):
        assert not re.search(rf"now / {banned}(?![0-9])", script), banned

    # a chama precisa de mais de uma oitava, senao e um seno puro
    assert len(re.findall(r"period: \d+", script)) >= 3
    # e o pulso precisa suavizar os extremos para respirar
    assert "wave * wave * (3 - 2 * wave)" in script

def test_lights_fall_off_instead_of_ending_in_a_flat_disc():
    """bright_radius era gravado, editavel e nunca desenhado: a luz saia como um
    poligono chapado com borda cortada a tesoura."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")

    assert "bright," in script and "dim," in script, "os dois raios chegam ao renderer"
    assert "(light.bright_radius || 0) * size" in script

    assert "function falloff()" in pixi
    assert "createRadialGradient" in pixi
    assert "(1 - t) * (1 - t)" in pixi, "queda quadratica: linear le como disco chapado"
    # a textura e unica e tingida por foco, nao uma por luz
    assert "let falloffTexture = null" in pixi
    # cor por foco, textura compartilhada. A tinta passa por uma dessaturacao
    # moderada: cor cheia num halo grande vira gelatina colorida sobre o mapa.
    assert "desaturate(hexToInt(light.tint || light.color), HALO_SATURATION)" in pixi
    # o recorte das paredes continua mandando no alcance do brilho
    assert "sprite.mask = mask" in pixi

def test_one_dial_for_brightness_and_the_mode_decides_the_effect():
    """Duas reguas que multiplicam o mesmo alfa sao uma regua a mais, e um botao
    para "melhorar a tocha" e uma escolha que o modo de visao ja fez.

    `opacity` separava tinta de quanto o foco levantava a escuridao; quando o
    recorte do foco passou a ser duro nos dois modos — para que a visao bonita
    nunca custasse area revelada — ela virou copia de `intensity`. E o nucleo
    pulsante deixou de ser opcao por foco: ele existe no cinematografico e nao
    existe no classico, que nao tem efeito nenhum.
    """
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")
    routes=(ROOT/"app/actions/game/manage_lights.py").read_text(encoding="utf-8")
    modal=(ROOT/"templates/pages/game/modals/light_editor.html").read_text(encoding="utf-8")
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")

    lights_table=tables.split("scene_lights = Table",1)[1].split("scene_layers = Table",1)[0]
    for gone in ("opacity", "animated_core"):
        assert gone not in lights_table, gone
        assert gone not in routes, gone
        assert f'data-light-field="{gone}"' not in modal, gone
    assert "light.opacity" not in pixi and "light.opacity" not in script

    # Forma e giro acompanham a emissao escolhida, e so fora do classico.
    assert "wobble: classic ? 1 : shapeFactor(light, now)," in script
    assert "spin: classic ? 0 : spinAngle(light, now)," in script

def test_the_client_never_posts_an_emission_it_does_not_know():
    """A barra de ferramentas e a iluminacao sao servidas com versao fixa no
    template, entao uma pode estar um passo atras da outra. Um nome de emissao
    fora da lista volta do servidor como "lighting.errors.invalid", que nao diz a
    ninguem o que aconteceu — melhor cair na tocha e acender a luz."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'const animation = chosen === "none" || EMISSIONS[chosen] ? chosen : "torch";' in script

    # E as duas listas precisam sair da mesma versao: editar o registro sem trocar
    # a query deixa o navegador com o dock antigo e o resto novo.
    registry=re.search(r'tools-registry\.js\?v=([\w-]+)', template).group(1)
    toolbar=re.search(r'tools-toolbar\.js\?v=([\w-]+)', template).group(1)
    assert registry == toolbar, "dock e registro precisam chegar juntos"

def test_a_failed_request_is_not_disguised_as_a_validation_error():
    """`lighting.errors.invalid` era o retorno de QUALQUER resposta sem corpo
    conhecido — 500, sessao expirada, proxy no meio. Um banco atras da migracao
    ficava com o sintoma identico ao de um campo mal preenchido, e mandava
    procurar erro de validacao onde nao havia nenhum."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    assert 'data.error_key || `lighting.errors.http_${response.status}`' in script

def test_a_light_moves_by_shape_not_only_by_brightness():
    """Uma luz que so muda de brilho por igual em toda a area nao parece se mexer:
    parece um dimmer. Foi o que aconteceu quando o brilho passou a respeitar a
    faixa de 5-10% da receita de fotografia e o raio do miolo, amarrado a ele,
    parou junto.

    A receita limita brilho porque brilho e o que mexe em quanto se enxerga.
    Forma e deslocamento nao mexem — o recorte do foco e duro nos dois modos —,
    entao e neles que a vida da luz pode morar.
    """
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")

    # Contas separadas: o raio deixou de ser derivado do alfa.
    assert "function shapeFactor(light, now)" in script
    assert "function spinAngle(light, now)" in script
    assert "light.alpha / Math.max(0.001, light.intensity)" not in pixi
    # O tamanho de cada fonte chega pronto do estado, ja com a respiracao e a
    # defasagem daquele instante — o desenho nao recalcula forma a partir do brilho.
    assert "const radius = source.radius * (source.wobble ?? 1);" in pixi

    # E a forma tem folga bem maior que o brilho, senao nao se ve diferenca.
    flicker=max(float(script.split(f"{name} = ",1)[1].split(";",1)[0])
                for name in ("FLICKER_PULSE", "FLICKER_TORCH"))
    shape=float(script.split("SHAPE_LIVE = ",1)[1].split(";",1)[0])
    assert shape > flicker * 2, "forma presa na faixa do brilho volta a ler como dimmer"

    # Girar um circulo perfeito nao mexe um pixel: o padrao precisa ter lobulos.
    assert "flameFalloff(light.lobes, light.lobeDepth)" in pixi
    # Fontes vizinhas giram em sentidos opostos, senao os lobulos se alinham e o
    # conjunto vira uma engrenagem.
    assert "(light.spin || 0) * (layer % 2 ? -1.6 : 1)" in pixi

    # Soma em vez de sobrepor: duas tochas perto somam a luz delas, como luz de
    # verdade. Sobrepondo, a de cima apagava a de baixo.
    assert 'sprite.blendMode = "add";' in pixi

    # E o centro passeia sem levar a mascara junto — mover a mascara faria a luz
    # espiar por tras da parede a cada tremida.
    assert "const drift = light.offset || { x: 0, y: 0 };" in pixi
    assert "mask.poly(flat)" in pixi

    # O entalhe protege so o miolo — recortar ali abriria um buraco girando no
    # meio da luz — e nunca estica para fora, senao a mascara do poligono cortaria
    # metade do efeito. A prova numerica disso esta em tests/js/flame_profile_harness.js.
    assert "const guard = Math.min(1, distance / 0.25);" in pixi
    assert "window.GravewrightBoardInternals.flameProfile = flameProfile;" in pixi

    # E foco sem lobulo cai no halo liso — o classico zera a silhueta, entao ele
    # nunca chega a desenhar padrao nenhum.
    assert "if (!count || !bite) return falloff();" in pixi
    assert "{ lobes: 0, lobeDepth: 0 }" in script

def test_light_and_scene_dressing_stay_apart():
    """Vela, fogueira, arcana e fumaça moravam no foco de luz porque era o lugar
    que existia — e o editor de foco acabou cheio de controle que não acendia
    nada. Fonte de luz ficou com o que muda a iluminação: chama e respiração.

    A separação precisa de guarda porque é fácil de desfazer sem perceber: basta
    alguém acrescentar um preset bonito no lugar errado.
    """
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")

    emissions=script.split("const EMISSIONS = {",1)[1].split("const LIGHT_DEFAULTS = {",1)[0]
    assert "torch: {" in emissions and "pulse: {" in emissions
    for gone in ("candle", "fire", "arcane", "smoke"):
        assert f"{gone}: {{" not in emissions, gone
    # Luz não solta partícula: isso é do emissor, noutra tabela e noutra camada.
    assert "particles:" not in emissions

    # A tocha tem lóbulos e treme; o pulso é círculo limpo e movimento puramente
    # matemático. Duas luzes, duas assinaturas.
    torch=emissions.split("torch: {",1)[1].split("},",1)[0]
    pulse=emissions.split("pulse: {",1)[1].split("},",1)[0]
    assert int(re.search(r"lobes: (\d+)", torch).group(1)) > 0
    assert int(re.search(r"lobes: (\d+)", pulse).group(1)) == 0
    assert "jitter: 0," in pulse and "spin: 0," in pulse

    # E o banco cobra o mesmo conjunto.
    assert "animation IN ('none','torch','pulse')" in tables
    assert "kind IN ('smoke','ember','dust','arcane')" in tables


def test_scene_shaders_are_occluded_by_walls_without_touching_the_glsl():
    """A fumaça atravessava muro e aparecia em sala fechada.

    O arquivo ``luz`` propunha entregar a oclusão como sampler para o shader
    multiplicar o alfa — o que só funciona se quem escreveu lembrar de usar. Aqui
    ela é a FORMA da máscara do quadro, então vale para qualquer shader já
    escrito: a parede deixou de ser cortesia do autor e virou propriedade do
    container, igual ao alcance.
    """
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    effects=(ROOT/"static/js/board/pixi/pixi-shader-effects.js").read_text(encoding="utf-8")

    # O mesmo polígono que o foco de luz usa, traçado da origem do efeito: porta
    # aberta e vão de parede valem para o shader pelo mesmo caminho, sem regra
    # própria que possa sair de sincronia com a da luz.
    assert 'this.cachedPolygon(`shader-${shader.id}`' in script
    assert "occlusionStamp: this.geometryStamp" in script

    # Cena inteira não é ocluída, de propósito.
    assert "occlusion: radiusWorld > 0" in script

    # Uma máscara só. Empilhar duas não existe: no Pixi a segunda substitui a
    # primeira, e o alcance sumiria.
    assert "function paintMask(" in effects
    assert 'textureSpace: "global"' in effects, "em espaço local o degradê fugiria da origem"
    # Uma máscara por sprite, e nunca máscara de máscara.
    assert "sprite.mask = mask" in effects
    assert "mask.mask" not in effects
    # E conferir o recorte não desliga o recorte: o contorno é um objeto à parte,
    # porque não dá para conferir uma máscara sem ver o que ela recorta.
    assert "function paintOutline(" in effects and "entry.outline.visible" in effects


def test_the_light_buffer_is_the_resulting_lighting_not_the_sum_of_sources():
    """O que o shader recebe é a iluminação resultante, já ocluída.

    Ambiente (1 - escuridão) por baixo, focos somados por cima, cada um recortado
    pelo próprio polígono de visibilidade. Sem o ambiente, um mapa de dia sem foco
    nenhum entregava preto, e um efeito que responde à luz sumia justamente onde
    tudo está iluminado.
    """
    buffer=(ROOT/"static/js/board/pixi/pixi-light-buffer.js").read_text(encoding="utf-8")
    layer=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    effects=(ROOT/"static/js/board/pixi/pixi-shader-effects.js").read_text(encoding="utf-8")

    # A escuridão da CENA, não a prévia atenuada do mestre. Ler a do mestre dizia
    # que uma sala preta estava quase clara, e o buffer saía branco na tela inteira.
    assert "lighting.sceneDarkness" in buffer, "ambiente é o que a escuridão da cena deixa passar"
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    assert "const sceneDarkness = scene.darkness || 0" in script
    assert 'sprite.blendMode = "add"' in buffer, "dois focos somam, como somam na tela"
    assert "sprite.mask = mask" in buffer, "cada foco recortado pelo próprio polígono"

    # A mesma queda radial da tela. Se cada um tivesse a própria curva, a luz que o
    # shader recebe divergiria da luz que a pessoa está olhando.
    assert "GravewrightBoardInternals.falloff" in buffer
    assert "window.GravewrightBoardInternals.falloff = falloff" in layer

    # E ele é construído ANTES do efeito ser desenhado: o shader lê a iluminação
    # deste quadro, não a do anterior.
    ordem=layer.split("_applySceneShaders(board, lighting", 1)[1]
    assert ordem.index("GravewrightLightBuffer") < ordem.index("effects.render(")
    assert "uniform sampler2D uLightBuffer" in effects


def test_the_editor_hands_out_a_prompt_instead_of_a_uniform_list():
    """Quem não escreve GLSL também precisa de shader.

    A referência de uniforms servia para conferir um nome; ela não ajuda quem não
    sabe por onde começar. O prompt vai mais longe pelo mesmo espaço de tela: o
    mestre descreve o efeito, a IA escreve o código, e ele volta colado no campo.
    """
    import app.i18n.pt_br as pt
    import app.i18n.en as en
    from pathlib import Path as _Path

    panel=(ROOT/"templates/pages/game/modals/shader_editor.html").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/shader-editor.js").read_text(encoding="utf-8")

    assert "data-shader-prompt" in panel and "data-shader-prompt-copy" in panel
    # A lista de uniforms ao lado do prompt seriam duas versões da mesma verdade,
    # e uma delas ficaria velha.
    assert "uniforms_hint" not in panel
    # O modo continua dito: sem isto o mestre acha que o shader está quebrado
    # quando alguém na mesa escolheu a visão leve.
    assert "mode_hint" in panel

    prompt = pt.TRANSLATIONS_PT_BR["lighting.shaders.prompt"] if hasattr(pt, "TRANSLATIONS_PT_BR") else None
    if prompt is None:
        prompt = next(v for k, v in vars(pt).items() if isinstance(v, dict) and "lighting.shaders.prompt" in v)["lighting.shaders.prompt"]
    ingles = next(v for k, v in vars(en).items() if isinstance(v, dict) and "lighting.shaders.prompt" in v)["lighting.shaders.prompt"]

    # O prompt tem de carregar o contrato inteiro: sem ele a IA devolve GLSL que
    # não compila aqui, e o mestre culpa o editor.
    preamble = (ROOT/"static/js/board/pixi/pixi-shader-effects.js").read_text(encoding="utf-8")
    preamble = preamble.split("const PREAMBLE = `", 1)[1].split("`;", 1)[0]
    for name in ("uTime", "uIntensity", "uScale", "uSpeed", "uColor", "uResolution",
                 "uOrigin", "uRadius", "uRotation", "uCamera", "uAspect", "gwWorld", "gwRotated"):
        assert name in preamble, name
        assert name in prompt, f"pt: {name}"
        assert name in ingles, f"en: {name}"

    # E as regras que separam um shader que funciona de um que parece quebrado.
    assert "vec4(cor * a, a)" in prompt, "alfa pré-multiplicado"
    # gwPattern e não gwWorld: o desenho tem de acompanhar o alcance, senão um
    # círculo pequeno mostra um pedaço chapado de um padrão gigante.
    assert "gwPattern(vTextureCoord)" in prompt, "desenhar em mundo e na escala do alcance"
    assert "NÃO recorte" in prompt, "o alcance é do quadro, não do código"

    # Duas versões do mesmo contrato: a estruturada, para quem quer conferir campo
    # a campo, e a corrida, que algumas IAs seguem melhor.
    prosa = next(v for v in vars(pt).values()
                 if isinstance(v, dict) and "lighting.shaders.prompt_prose" in v)["lighting.shaders.prompt_prose"]
    assert panel.count("data-shader-prompt") >= 2 and panel.count("data-shader-prompt-copy") == 2
    assert "gwLight" in prompt and "gwLight" in prosa, "responder à luz é o ponto desta rodada"

    # As faixas da engine em AMBOS: sem elas a IA escolhe constantes fora do que as
    # réguas alcançam, e o efeito sai diferente do que a pessoa pediu.
    for texto, nome in ((prompt, "estruturado"), (prosa, "corrido")):
        for faixa in ("0.1 a 20.0", "0.0 a 8.0", "0 a 120 células", "70 unidades"):
            assert faixa in texto, f"{nome}: {faixa}"

    # O botão copia o campo do PRÓPRIO bloco; pegar o primeiro copiaria sempre o
    # estruturado, e o segundo prompt viraria decoração.
    assert "button.previousElementSibling" in editor
    assert "navigator.clipboard.writeText" in editor


def test_every_slider_gets_fine_adjustment_buttons():
    """Arrastar acha a região; não faz o ajuste fino.

    Numa régua de 0,1 a 20 dentro de um painel de 400px, um pixel de mouse vale
    mais do que o passo — "um pouquinho mais" não tem como ser pedido arrastando.
    """
    nudge=(ROOT/"static/js/ui/slider-nudge.js").read_text(encoding="utf-8")
    index=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    css=(ROOT/"static/css/game.css").read_text(encoding="utf-8")

    assert "slider-nudge.js" in index
    # Um lugar só: foco de luz, emissor, shader e visão do token são todos o mesmo
    # `.slider-row`, e decorar de fora herda os quatro de uma vez.
    assert '.slider-row' in nudge and "FINE_STEP = 0.1" in nudge

    # Régua desligada ("sem limite") desliga os botões junto: mexeriam num número
    # que não está valendo.
    assert "input.disabled" in nudge

    # `input[type=range]` encaixa o valor no passo declarado, então numa régua de
    # passo 1 — rotação, alcance — escrever 8,1 devolvia 8 e o clique não fazia
    # nada. O passo precisa ser afrouxado antes, com o original guardado para a
    # exibição decidir as casas.
    assert "function prepare(input)" in nudge and 'input.dataset.baseStep = input.step' in nudge
    editor=(ROOT/"static/js/lighting/light-editor.js").read_text(encoding="utf-8")
    assert "input.dataset?.baseStep" in editor
    assert ".slider-row:has(input[type=\"range\"]:disabled) .slider-nudge" in css

    # E o evento tem de existir de verdade. Escutar um nome inventado é código
    # morto que ninguém percebe — já aconteceu com `modal:closed` neste arquivo.
    assert "vtt:modal-opened" not in nudge
    assert "MutationObserver" in nudge


def test_unlimited_range_is_a_checkbox_not_a_hidden_zero():
    """Zero continua sendo o que vai ao banco; deixa de ser o que se pede na tela.

    Arrastar uma régua até o mínimo e receber o alcance MÁXIMO não é algo que se
    descubra — se descobre por acidente, com a cena inteira acesa.
    """
    light=(ROOT/"templates/pages/game/modals/light_editor.html").read_text(encoding="utf-8")
    vision=(ROOT/"templates/pages/game/modals/token_vision.html").read_text(encoding="utf-8")
    shader=(ROOT/"templates/pages/game/modals/shader_editor.html").read_text(encoding="utf-8")
    toggle=(ROOT/"static/js/lighting/limit-toggle.js").read_text(encoding="utf-8")
    index=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")

    # Os três alcances onde zero queria dizer "ilimitado".
    for panel, key in ((light, "dim_radius"), (vision, "vision_range"), (shader, "radius")):
        assert f'data-limit-target="{key}"' in panel, key
        assert f'data-limit-for="{key}"' in panel, key
        # Sem valor de volta, desmarcar devolve zero — e o checkbox não teria
        # como ser desmarcado.
        assert "data-limit-default=" in panel, key

    assert "limit-toggle.js" in index
    assert "range.disabled = unlimited" in toggle


def test_the_shader_tool_places_on_the_map_like_every_other_tool():
    """Escolhe na barra, pinga no mapa, o editor abre. Sem nome, sem lista."""
    registry=(ROOT/"static/js/tools/tools-registry.js").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/shader-editor.js").read_text(encoding="utf-8")
    panel=(ROOT/"templates/pages/game/modals/shader_editor.html").read_text(encoding="utf-8")

    # Ferramenta de verdade, na mesma camada da particula — nao um botao que abre
    # um editor onde se cria o objeto.
    assert 'shader: ["effects"]' in registry
    assert 'data-tool="shader"' in template
    assert "data-shader-editor-open" not in template

    # Nome existia so para achar o shader numa lista; sem a lista, os dois somem.
    for gone in ("data-shader-pick", "data-shader-new", 'data-shader-field="name"'):
        assert gone not in panel, gone
    assert "fillList" not in editor

    # As reguas que sobraram sao as que moldam o efeito.
    for control in ("intensity", "scale", "speed", "rotation", "radius", "color", "enabled"):
        assert f'data-shader-field="{control}"' in panel, control


def test_particle_emitters_are_scene_dressing_not_light():
    """Emissor não tem raio claro, intensidade nem ângulo: se tivesse, seria um
    foco de luz com outro nome."""
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    service=(ROOT/"app/engine/scenes/scene_particle_service.py").read_text(encoding="utf-8")
    registry=(ROOT/"static/js/tools/tools-registry.js").read_text(encoding="utf-8")

    kinds=script.split("const PARTICLE_KINDS = {",1)[1].split("\n    };",1)[0]
    for kind in ("smoke", "ember", "dust", "arcane"):
        assert f"{kind}: {{" in kinds, kind

    for absent in ("intensity", "bright_radius", "angle"):
        assert absent not in service.split("def _clean",1)[1].split("def create",1)[0], absent

    # Camada de Efeitos: partícula e shader moram juntos, longe do foco de luz.
    assert 'particles: ["effects"]' in registry


def test_the_animated_halo_does_not_recompose_the_darkness():
    """O halo mora na camada, por cima da textura de escuridao. Se forma e giro
    entrassem na chave dela, cada quadro da chama recomporia a textura inteira —
    que e exatamente o que aquele cache existe para evitar."""
    pixi=(ROOT/"static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    key=pixi.split("const key = [",1)[1].split('].join(":")',1)[0]
    assert "wobble" not in key and "spin" not in key
    assert "l.intensity.toFixed(2)" in key, "so a intensidade parada entra"

def test_a_light_can_emit_in_a_cone():
    """Todo foco emitia em circulo. Com abertura e direcao o mesmo foco vira
    lanterna, facho de porta entreaberta ou holofote."""
    tables=(ROOT/"app/persistence/tables.py").read_text(encoding="utf-8")
    routes=(ROOT/"app/actions/game/manage_lights.py").read_text(encoding="utf-8")
    modal=(ROOT/"templates/pages/game/modals/light_editor.html").read_text(encoding="utf-8")
    script=(ROOT/"static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
    editor=(ROOT/"static/js/lighting/light-editor.js").read_text(encoding="utf-8")

    assert 'Column("angle", Float, nullable=False, server_default=text("360.0"))' in tables
    assert '"angle"' in routes and '"rotation"' in routes
    for field in ("angle", "rotation"):
        assert f'data-light-field="{field}"' in modal, field

    # O corte tem de sobreviver a virada de Math.atan2: um facho apontando para a
    # esquerda cruzaria a descontinuidade e apareceria partido ao meio.
    assert "function withinCone(angle, centre, half)" in script
    assert "while (delta <= -Math.PI) delta += Math.PI * 2;" in script

    # E a cunha precisa do vertice da origem, senao o poligono liga as duas pontas
    # do arco e o facho vira uma fatia solta, acesa longe da propria lampada.
    assert "apex = { x: origin.x, y: origin.y" in script
    assert "return apex ? [apex, ...points] : points;" in script

    # Abertura e direcao entram na chave do cache do poligono: mudar o facho sem
    # mover o foco devolveria a forma antiga ate alguem arrastar a luz.
    assert "const cone = coneOf(origin);" in script
    assert "${shape}" in script

    # Direcao com 360 graus nao significa nada, entao a regua some.
    assert "function syncEmissionRows(panel)" in editor
    assert 'row.hidden = !Number.isFinite(angle) || angle >= 360;' in editor

def test_lighting_is_feature_flagged():
    config=(ROOT/"app/config.py").read_text(encoding="utf-8")
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    assert 'env_bool("DYNAMIC_LIGHTING_ENABLED", True)' in config
    assert "{% if dynamic_lighting_enabled %}" in template
