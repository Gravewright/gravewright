"""Um botão de ficha que só mexe na tela não pode virar POST para o servidor.

O host trata `data-action` como ação server-side do ruleset (`/game/actor/action`).
Um controlador de pacote pode reivindicar a ação; se não reivindicar, o clique é
encaminhado. Virar página de PDF, dar zoom ou alternar página dupla não são regras
de sistema — encaminhá-las faz o servidor receber uma ação que o ruleset nunca
declarou e devolver 400 a cada clique.

Este teste cobre os dois lados do contrato:
  1. o SDK só encaminha o que o controlador não reivindicou;
  2. todo `data-action` do template do sistema PDF é reivindicado.

O que ele NÃO cobre: o despacho real dentro de bindHtmlSheet, que só roda com o
SDK inteiro montado num DOM. Aqui a garantia é sobre o código dos dois lados.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "static/js/sdk/gravewright-sdk.js"
PACKAGE = ROOT / "data/packages/rulesets/gravewright-pdf-system"


def test_the_host_only_forwards_actions_the_controller_declined():
    source = SDK.read_text(encoding="utf-8")

    block = source.split('root.querySelectorAll("[data-action]")', 1)[1].split("cleanups.push", 1)[0]

    assert "controller.onAction?.(" in block, "o controlador precisa ter a primeira chance"
    assert "ctx.onAction?.(" in block, "e o host continua sendo o caminho padrão"
    assert "if (handled === true) return;" in block, (
        "sem esta guarda o host encaminha toda ação, mesmo a que o controlador já tratou"
    )

    # A guarda tem de vir ANTES do encaminhamento, senão não guarda nada.
    assert block.index("if (handled === true) return;") < block.index("ctx.onAction?.("), block


def test_every_pdf_sheet_button_is_claimed_by_its_controller():
    template = (PACKAGE / "sheets/character.html").read_text(encoding="utf-8")
    controller = (PACKAGE / "scripts/pdf-sheet.js").read_text(encoding="utf-8")

    buttons = set(re.findall(r'data-action="([^"]+)"', template))
    assert buttons, "o teste precisa achar botões, senão não guarda nada"

    switch = controller.split("onAction(action, ctx)", 1)[1].split("unmount(ctx)", 1)[0]

    # Fatia o switch por caso, para conferir o retorno de cada um separadamente.
    parts = re.split(r'case "([^"]+)":', switch)
    handled = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        handled[name] = body

    missing = sorted(buttons - set(handled))
    assert not missing, f"botões sem tratamento no controlador (viram POST e dão 400): {missing}"

    not_claimed = sorted(
        name for name in buttons if "return true;" not in handled[name].split("case ")[0]
    )
    assert not not_claimed, (
        f"ações de cliente que o controlador não reivindica com 'return true': {not_claimed}"
    )

    # O default precisa deixar passar: uma ação desconhecida pode ser regra do
    # sistema, e engolir tudo mataria o caminho server-side.
    default_body = switch.split("default:", 1)[1]
    assert "return false;" in default_body, "ação desconhecida deve seguir para o host"
