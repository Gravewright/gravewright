"""A bandeja de dados fala a notação do xdice, que é quem avalia.

Duas coisas tornam isso fácil de errar:

1. No xdice, ``Ln``/``Hn`` **descartam** os n menores/maiores — não "mantêm".
   Vantagem em d20 é ``2d20L1``. Quem vem do Foundry escreve ``kh1``, que aqui é
   sintaxe inválida e volta como "rolagem inválida" na cara de quem joga.
2. ``L`` precisa vir **antes** de ``H`` num mesmo termo (``6D6L1H2``).

A bandeja também não rola por conta própria: ela manda ``/roll`` e ``/gmroll``
pelo chat, que é onde a rolagem é avaliada, persistida e vira cartão. Uma segunda
via de rolagem significaria dois formatos de resultado e duas histórias.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.engine.dice.roll_service import RollService

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests/js/dice_tray_harness.js"
SCRIPT = ROOT / "static/js/dice/dice-tray.js"
SAVAGE_SCRIPT = ROOT / "data/packages/rulesets/savage-worlds/scripts/dice-tray.js"
TEMPLATE = ROOT / "templates/pages/game/index.html"


@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente: harness de dados pulado")
def test_the_tray_composes_valid_notation():
    """Roda o dice-tray.js real e confere a expressão que ele monta (ver harness)."""
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize(
    "expression",
    [
        "1d20", "2d20L1", "4d6L1", "6d6L1H2", "1d6!", "1d%", "1dF", "1d6+1d8-2", "2d20L1+5",
        # Dado extra: o conjunto + um d6, os dois explodem, vale o melhor.
        "max(1d8!,1d6!)", "max(1d4!,1d6!)+2", "max(1d12!,1d6!)-1",
    ],
)
def test_every_shape_the_tray_can_build_is_accepted_by_the_evaluator(expression: str):
    """A ponte inteira: se o avaliador recusar, a bandeja monta algo que só falha
    depois de a pessoa clicar em Rolar."""
    assert RollService().evaluate(expression) is not None, expression


def test_foundry_notation_is_not_what_this_project_speaks():
    """Guarda contra a tentação de escrever kh/kl: é a notação de outro sistema."""
    assert RollService().evaluate("2d20kh1") is None, "kh não é xdice"
    assert RollService().evaluate("4d6kl3") is None, "kl não é xdice"

    source = SCRIPT.read_text(encoding="utf-8")
    montagem = source.split("function termoParaTexto", 1)[1].split("\n  }", 1)[0]
    assert "kh" not in montagem and "kl" not in montagem
    assert '`L${' in montagem and '`H${' in montagem
    assert montagem.index("descartarMenores") < montagem.index("descartarMaiores"), (
        "L precisa ser escrito antes de H"
    )


def test_the_tray_rolls_through_the_chat_command():
    source = SCRIPT.read_text(encoding="utf-8")
    envio = source.split("async rolar(paraGm)", 1)[1].split("\n    }", 1)[0]

    assert '"/gmroll" : "/roll"' in envio, "os dois modos são comandos de chat"
    assert '"/game/chat"' in envio, "não pode existir uma segunda rota de rolagem"
    assert "csrf_token" in envio


def test_the_bonus_die_keeps_the_better_of_two_exploding_dice():
    """Rola o conjunto E um d6 extra, e fica com o melhor. Os dois explodem. Como
    o xdice aceita ``max``, isso vira ``max(1d8!,1d6!)`` — e o cartão mostra os
    dois dados."""
    from app.engine.dice.roll_service import RollService

    resultado = RollService().evaluate("max(1d8!,1d6!)")
    assert resultado is not None
    notacoes = [g["notation"] for g in resultado.groups]
    assert len(notacoes) == 2, f"os dois dados precisam aparecer: {notacoes}"

    source = SAVAGE_SCRIPT.read_text(encoding="utf-8")
    montagem = source.split("transform(expression, tray)", 1)[1].split(chr(10) + "    }", 1)[0]
    assert "max(" in montagem, "é max(), não uma comparação feita no cliente"
    assert "explode: true" in montagem, "ligar o dadoExtra faz o dado de atributo explodir"

    # O modificador soma FORA do max: dentro, ele inflaria só um dos lados.
    assert montagem.index("max(") < montagem.index("modificador > 0")


def test_the_tray_opens_from_the_chat_composer():
    """Pedido explícito: não é aba no dock, é um botão acima de enviar e apagar."""
    html = TEMPLATE.read_text(encoding="utf-8")

    assert 'data-modal-id="dice-tray-' in html, "a bandeja é uma modal"
    assert "panel-dice-" not in html, "não sobra painel de doca"
    assert 'data-panel-toggle="panel-dice-' not in html, "nem botão no dock"
    assert "dice-tray.js" in html, "o script precisa ser carregado"

    composer = html.split('class="chat-composer', 1)[1].split("</div>", 1)[0]
    assert 'data-modal-open="dice-tray-' in composer, "o botão vive no composer do chat"

    # A ordem no DOM é a ordem na tela: bandeja, depois enviar/apagar, e o campo
    # por último ocupando a largura inteira.
    assert composer.index("chat-dice") < composer.index("chat-send") < composer.index("chat-input"), (
        "bandeja acima dos botões, campo abaixo de tudo"
    )
    assert "{{ t(\"game.dice.title\") }}" in composer, "o botão é rotulado, não só um ícone"

    styles = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    grade = styles.split(".chat-composer {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: 1fr 1fr" in grade, "enviar e apagar dividem a linha"
    esperado = ".chat-composer > .chat-dice," + chr(10) + ".chat-composer > .chat-input { grid-column: 1 / -1; }"
    assert esperado in styles, (
        "bandeja e campo ocupam as duas colunas"
    )
    assert ".chat-composer--single > .chat-send { grid-column: 1 / -1; }" in styles, (
        "sem o apagar, o enviar assume a linha toda"
    )


def test_the_panel_is_reachable_and_labelled():
    html = TEMPLATE.read_text(encoding="utf-8")

    corpo = html.split("data-dice-tray", 1)[1].split("</article>", 1)[0]
    for marca in ("data-dice-pool", "data-dice-formula", "data-dice-history",
                  "data-dice-bonus",
                  'data-dice-roll="public"', 'data-dice-roll="gm"'):
        assert marca in corpo, f"falta {marca} no painel"

    # O campo de fórmula é a saída para o que os botões não montam — e mostra a
    # notação que o servidor entende, que é como se aprende.
    assert "game.dice.formula_placeholder" in corpo


def test_the_roll_payload_carries_what_the_card_needs_to_show():
    """Um card que só recebe os dados que contaram não consegue mostrar o que a
    rolagem descartou — e é justamente isso que se quer ver numa rolagem com
    descarte: qual dado perdeu. O tamanho do dado vem junto para marcar o valor
    máximo sem reinterpretar a notação do outro lado."""
    from app.engine.dice.roll_service import RollService

    resultado = RollService().evaluate("4d6L1")
    assert resultado is not None
    grupo = resultado.groups[0]

    assert len(grupo["results"]) == 3, "sobram três depois do descarte"
    assert len(grupo["dropped"]) == 1, "o descartado precisa viajar junto"
    assert grupo["sides"] == 6
    assert grupo["subtotal"] == sum(grupo["results"])

    # d% e dF: um tem máximo conhecido, o outro não tem "máximo" que signifique algo.
    assert RollService().evaluate("1d%").groups[0]["sides"] == 100
    assert RollService().evaluate("1dF").groups[0]["sides"] == 0, (
        "fudge vai de -1 a 1; marcar crítico ali seria enganoso"
    )


def test_the_card_marks_max_min_and_dropped_dice():
    script = (ROOT / "static/js/chat/chat-roll-cards.js").read_text(encoding="utf-8")
    dados = script.split("function diceHtml", 1)[1].split("\n    }", 1)[0]

    assert "is-dropped" in dados and "is-max" in dados and "is-min" in dados
    # Sem saber o tamanho do dado, marcar crítico seria chute.
    assert "sides && value === sides" in dados
    assert "descartado" in dados, "o descartado é desenhado, não omitido"

    styles = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    descartado = styles.split(".roll-die.is-dropped {", 1)[1].split("}", 1)[0]
    assert "line-through" in descartado and "opacity" in descartado


def test_history_and_live_messages_come_from_the_same_renderer():
    """Histórico e mensagem ao vivo têm de ser a mesma coisa desenhada.

    Manter as duas parecidas conferindo se o Jinja e o JS usam as mesmas classes
    é o que já falhou: o cartão do sistema entrou só no JS, e recarregar a página
    trocava Aumentos e Margem pela rolagem crua. Agora o template entrega o
    payload e quem desenha é o mesmo arquivo nos dois casos — então o que se
    fixa aqui é que ele *não* redesenhe a rolagem por conta própria.
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    script = (ROOT / "static/js/chat/chat-roll-cards.js").read_text(encoding="utf-8")

    bloco = html.split('class="chat-message chat-message--roll"', 1)[1].split("{% endif %}", 1)[0]
    assert "data-roll-payload" in bloco, "o histórico precisa entregar o payload"
    for marca in ("roll-parts", "roll-part__formula", "roll-dice", "roll-die"):
        assert marca not in bloco, f"o template voltou a desenhar a rolagem ({marca})"

    for marca in ("roll-box", "roll-summary", "roll-parts", "roll-dice", "roll-die"):
        assert marca in script, f"mensagem ao vivo sem {marca}"

    # E o histórico precisa mesmo ser hidratado, senão sobra só o marcador.
    assert "data-roll-payload" in script, "ninguém redesenha o histórico"
    assert 'document.addEventListener("DOMContentLoaded"' in script
