"""A visão dinâmica tem duas qualidades, e quem escolhe é quem olha.

O que estes testes protegem não é a aparência — é a fronteira entre as duas: o
modo pode mudar como a cena é pintada e nunca o que a pessoa enxerga. Se o modo
leve revelasse um palmo a mais, ele deixaria de ser uma opção de desempenho e
viraria uma opção de trapaça, escolhida pelo motivo errado.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = (ROOT / "static/js/lighting/dynamic-lighting.js").read_text(encoding="utf-8")
MODE_JS = (ROOT / "static/js/lighting/vision-mode.js").read_text(encoding="utf-8")
PIXI = (ROOT / "static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
RENDERER = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")


def _statement(source: str, start: str) -> str:
    """O trecho de código que começa em ``start`` e vai até o fim da declaração."""
    body = source.split(start, 1)[1]
    return start + body.split(";", 1)[0]


def test_the_geometry_is_computed_without_asking_the_mode():
    """Recorte nas paredes, alcance e porta aberta saem idênticos nos dois modos.

    É a garantia central: a escolha de qualidade só pode alcançar a pintura. Um
    modo que enxergasse mais deixaria de ser opção de desempenho.
    """
    vision = _statement(SCRIPT, "const visionPolygons = visionLimited")
    assert "classic" not in vision, "o recorte da visão não pode depender do modo"

    blockers = _statement(SCRIPT, "const blockers = this.blockers(walls)")
    assert "classic" not in blockers, "porta e parede bloqueiam igual nos dois modos"

    # As mesmas listas alimentam o desenho nos dois modos.
    lit = _statement(PIXI, "const litAreas = [")
    assert "classic" not in lit


def test_both_modes_reveal_exactly_the_same_area():
    """A regra que o modo cinematográfico já quebrou uma vez.

    Neste modelo, alfa da escuridão *é* visibilidade: apagar o polígono com uma
    queda radial deixava o anel externo do alcance meio escuro, e quem escolhia
    "bonito" enxergava menos que quem escolhia "leve". Opção de aparência não
    pode custar informação de jogo.

    Por isso a textura de escuridão é composta igual nos dois modos, e o véu que
    diferencia o cinematográfico vive na camada, somando por cima.
    """
    # A definição, não a chamada: a chamada vem antes no arquivo, dentro do render.
    definition = "_composeDarkness(board, rt, cssW, cssH, lighting, litAreas, lights, screen, flatten, cam) {"
    compose = PIXI.split(definition, 1)[1].split("\n        _", 1)[0]
    assert "veil()" not in compose, "véu na textura voltaria a esculpir a máscara"
    # Nem o parâmetro existe: a composição não tem como olhar o modo, e é essa
    # ausência que garante a área revelada idêntica.
    assert "classic" not in compose, "a composição da escuridão não olha o modo"

    # O véu soma escuridão (blend normal). Com `erase` ele voltaria a esculpir a
    # máscara, que é exatamente o que tirava visão de quem estava no cinematográfico.
    veil = PIXI.split("sprite.texture = veil();", 1)[1].split("});", 1)[0]
    assert 'sprite.blendMode = "normal";' in veil

    # E ele tem teto: no limite do raio para em VEIL_MAX da escuridão da cena,
    # nunca em 100%. O que está lá continua legível.
    veil_max = float(PIXI.split("VEIL_MAX = ", 1)[1].split(";", 1)[0])
    assert 0 < veil_max < 1, "véu opaco esconderia terreno que o clássico mostra"
    breath = float(PIXI.split("VEIL_BREATH_DEPTH = ", 1)[1].split(";", 1)[0])
    assert veil_max * (1 + breath) < 1, "nem no pico da respiração o véu pode fechar"

    # Nenhum filtro na composição da escuridão. Um borrão ali empurra a borda de
    # parede para fora e revela terreno que a geometria negou — foi assim que
    # vazou da primeira vez. Shader no halo é outra história: ele mora na camada,
    # é mascarado pelo polígono e não toca nesta textura.
    assert "Filter" not in compose, "filtro na escuridão volta a vazar pela parede"
    assert "board.lightingScene.filters = null;" in PIXI
    assert "board.lightingScene.filters = penumbra" not in PIXI


def test_the_cinematic_numbers_sit_inside_the_photography_recipe():
    """Névoa e tremulação chamam atenção para si quando passam do ponto, e o mapa
    é o que a mesa precisa ler. A receita põe fog em 5–25% e flicker em 5–10%; o
    que existia aqui antes era véu a 50% e chama oscilando 30%.

    As demais linhas da receita — luz ambiente, key, fill, accent — são autoria do
    mestre (escurididão da cena e intensidade por foco), não constante de código.
    """
    veil_max = float(PIXI.split("VEIL_MAX = ", 1)[1].split(";", 1)[0])
    assert 0.05 <= veil_max <= 0.25, "fog fora da faixa da receita"

    for name in ("FLICKER_PULSE", "FLICKER_TORCH"):
        amplitude = float(SCRIPT.split(f"{name} = ", 1)[1].split(";", 1)[0])
        assert 0.05 <= amplitude <= 0.1, f"{name} fora da faixa da receita"

    # Saturação moderada: cor cheia num halo grande vira gelatina colorida sobre o
    # mapa. Mas só no halo — no marcador do editor a cor é informação.
    keep = float(PIXI.split("HALO_SATURATION = ", 1)[1].split(";", 1)[0])
    assert 0.5 <= keep < 1, "moderada não é nem cor cheia nem cinza"
    # `light.tint` e a cor DAQUELE instante (so a arcana anda entre duas); a cor
    # escolhida pelo mestre segue sendo o ponto de partida dela.
    assert "desaturate(hexToInt(light.tint || light.color), HALO_SATURATION)" in PIXI
    marker = PIXI.split("lighting.lights.forEach((light) => {", 1)[1]
    assert "fill({ color: hexToInt(light.color)" in marker, "marcador mantém a cor cheia"


def test_the_veil_drifts_without_recomposing_the_darkness():
    """O véu anima; a textura de escuridão não. Dentro dela, mexer no véu
    recomporia tudo a cada quadro — que é justamente o que aquele cache evita."""
    assert "_acquireVeil(board, veilSlot)" in PIXI
    assert "lightingVeilPool" in RENDERER, "pool próprio, senão sobrescreve o halo"

    # O pool precisa nascer na própria camada. Os arquivos do tabuleiro são
    # servidos com versão fixa no template, então uma camada nova encontra um
    # renderer velho em cache — e a iluminação inteira cai no primeiro quadro.
    assert "if (!board.lightingVeilPool) board.lightingVeilPool = [];" in PIXI
    assert "board.lightingGlowPool || []" in PIXI

    # Girar um anel liso não mexe um pixel: a deriva precisa de lóbulos angulares.
    assert "VEIL_LOBES" in PIXI
    assert "Math.sin(angle * VEIL_LOBES)" in PIXI
    assert "sprite.rotation = (seconds * VEIL_SPIN + phase)" in PIXI

    # Fase por token: dois véus lado a lado em sincronia leem como engrenagem.
    assert "const phase = index * 1.7;" in PIXI

    # E o laço de animação precisa saber que há o que animar sem tocha nenhuma.
    assert "this.visionSources().some((source) => source.radius > 0)" in SCRIPT


def test_the_veil_stops_at_the_wall_like_the_vision_does():
    """Um véu que vazasse para o outro lado pintaria sombra em terreno que nem
    faz parte desta vista."""
    veil = PIXI.split("this._acquireVeil(board, veilSlot);", 1)[1]
    assert "mask.poly(flatten(polygon))" in veil.split("sprite.texture", 1)[0]


def test_the_veil_only_shades_the_end_of_the_range():
    """Enxerga-se igual a um metro e a dez; só no fim do alcance a coisa se perde.
    Então o véu é transparente no miolo e só sobe no último trecho."""
    start_at = float(PIXI.split("VEIL_START = ", 1)[1].split(";", 1)[0])
    assert 0 < start_at < 1, "o miolo do alcance fica limpo"
    assert "distance >= 1 || distance <= VEIL_START" in PIXI

    # Smoothstep: uma rampa linear termina num anel visível, porque o olho pega a
    # quebra de inclinação na chegada ao topo.
    assert "const eased = t * t * (3 - 2 * t);" in PIXI

    # E o alcance de cada visão precisa chegar ao desenho, senão não há o que
    # dimensionar e o véu some sem ninguém perceber.
    assert "visionRims" in SCRIPT and "lighting.visionRims || []" in PIXI


def test_a_token_without_range_gets_no_veil():
    """Sem alcance o polígono só termina em parede, e parede não ganha véu:
    seria sombra pintada em cima do próprio muro, e um limite de vista que a
    ficha do token não pediu."""
    assert "if (!rim || !(rim.radius > 0)) return;" in PIXI


def test_classic_drops_the_costly_passes():
    """O modo leve precisa cortar custo de verdade, não só mudar de nome."""
    # Sem chama, o laço de animação nem começa — é a maior economia do modo.
    assert "if (window.GravewrightVisionMode?.isClassic?.()) return false;" in SCRIPT
    assert 'animation: classic ? "none" : (light.animation || "none")' in SCRIPT

    # Sem halo colorido: é o passe mais caro por foco, dois sprites mascarados.
    assert "if (!classic) lighting.lights.forEach" in PIXI

    # E sem o véu animado, que é o que faz a cena ter quadro a entregar a 25fps
    # mesmo sem tocha nenhuma acesa.
    assert "if (!classic && lighting.darkness > 0) {" in PIXI


def test_switching_modes_repaints_without_moving_anything():
    """A escuridão é uma textura em cache por assinatura. Se o modo não entrar na
    chave, quem trocasse a opção continuaria vendo a composição anterior até
    mover a câmera — e leria isso como opção que não funciona."""
    key = PIXI.split("const key = [", 1)[1].split('].join(":")', 1)[0]
    assert "lighting.mode" in key
    assert "invalidateAll" in MODE_JS and "invalidateAll:" in SCRIPT


def test_the_choice_belongs_to_the_person_and_survives_the_session():
    assert 'DEFAULT_MODE = "cinematic"' in MODE_JS, "o padrão é o que já existia"
    assert '"/game/preferences/vision"' in MODE_JS
    assert 'data-vision-mode="{{ vision_mode }}"' in TEMPLATE
    for mode in ("classic", "cinematic"):
        assert f'data-vision-mode-choice="{mode}"' in TEMPLATE

    # A seção só aparece onde a iluminação existe: sem a flag, os scripts que
    # atendem esses botões nem são carregados, e a opção ficaria inerte na tela.
    before_buttons = TEMPLATE.split('data-vision-mode-choice="classic"', 1)[0]
    opened_section = before_buttons.rsplit("<section", 1)[0]
    assert opened_section.rstrip().endswith("{% if dynamic_lighting_enabled %}")

    assert "/static/js/lighting/vision-mode.js" in TEMPLATE
