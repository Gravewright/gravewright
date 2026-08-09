"""Editar uma ficha não pode destruir o campo que se está editando.

Toda escrita transmite ``sheet.data.updated`` para a sala, e o cliente recarrega a
ficha ao receber — inclusive o eco da própria escrita. Recarregar troca o
``innerHTML`` inteiro, então quem estava digitando perde foco e texto.

Somado a isso, o caminho de ficha HTML do SDK notificava a cada tecla (evento
``input``), enquanto a ficha nativa sempre gravou no ``change``. O resultado era
uma letra por POST, uma transmissão por letra, e a ficha se reconstruindo em cima
de quem digitava: campo de texto inutilizável e checkbox que parecia dar submit.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "static/js/sdk/gravewright-sdk.js"
EVENTS = ROOT / "static/js/sheets/actors/actor-sheet-events.js"
NATIVE = ROOT / "static/js/sheets/actors/actor-sheet-controller.js"


def test_the_sdk_sheet_writes_on_change_not_on_every_keystroke():
    source = SDK.read_text(encoding="utf-8")
    block = source.split('root.querySelectorAll("[data-bind]")', 1)[1].split("root.querySelectorAll", 1)[0]

    assert 'node.addEventListener("change", onCommit)' in block, "gravar é no fim da edição"

    # ``input`` pode continuar existindo — mas só para estado local, nunca para
    # notificar o host (que é quem faz o POST e dispara a transmissão).
    local = block.split("const onLocal = () =>", 1)[1].split("};", 1)[0]
    assert "ctx.onChange" not in local, "notificar a cada tecla é o bug"
    assert "setPath(ctx.data" in local, "o estado local precisa acompanhar a digitação"


def test_the_sdk_path_matches_the_native_sheet_convention():
    """A ficha nativa sempre gravou no ``change``; o caminho do SDK é que destoava."""
    native = NATIVE.read_text(encoding="utf-8")
    assert 'root.addEventListener("change"' in native
    assert 'root.addEventListener("input"' not in native


def test_a_sheet_being_edited_is_not_rebuilt_underneath_the_user():
    source = EVENTS.read_text(encoding="utf-8")

    assert "refreshQuandoOcioso" in source, "o refresh direto destrói edição em curso"
    helper = source.split("function refreshQuandoOcioso", 1)[1].split("\n  }", 1)[0]

    assert "root.contains(document.activeElement)" in helper, "só adia se houver foco dentro"
    assert 'root.addEventListener("focusout"' in helper, "e recarrega quando o foco sai"
    # focusout dispara antes de o foco assumir o destino; sem o tique, mover-se
    # entre dois campos da mesma ficha pareceria uma saída.
    assert "setTimeout(" in helper

    # A atualização de outro jogador não pode ser descartada, só adiada.
    assert helper.count("refresh(root)") == 2, "adiar é diferente de ignorar"


def test_your_own_echo_never_rebuilds_your_sheet():
    """Toda escrita transmite para a sala, e o autor recebe de volta. Ele já
    aplicou o valor localmente ao editar — recarregar por causa do próprio eco só
    desmonta a ficha embaixo de quem está usando. Numa ficha PDF isso reabre o
    documento inteiro, o que parece um submit a cada clique."""
    source = EVENTS.read_text(encoding="utf-8")

    assert "const souEu = (payload)" in source
    guard = source.split("const souEu = (payload)", 1)[1].split("};", 1)[0]
    assert "document.body?.dataset?.currentUserId" in guard, "é a convenção do projeto"
    assert 'payload?.updated_by === eu' in guard

    ouvinte = source.split('if (envelope.event !== "sheet.data.updated") return;', 1)[1]
    assert "souEu(envelope.payload)" in ouvinte.split("\n  });", 1)[0], (
        "o eco precisa ser descartado antes de procurar a ficha"
    )

    # Atualização de OUTRA pessoa continua chegando — só espera o foco sair.
    assert "refreshQuandoOcioso(root)" in ouvinte


def test_the_project_already_ignores_its_own_echo_elsewhere():
    """Não é convenção nova: o chat faz o mesmo, pelo mesmo dataset."""
    chat = (ROOT / "static/js/chat/chat-renderer.js").read_text(encoding="utf-8")
    assert "document.body.dataset.currentUserId" in chat
