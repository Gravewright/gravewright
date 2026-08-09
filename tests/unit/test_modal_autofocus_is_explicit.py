"""Campo inicial de modal recebe foco por código, não pelo atributo `autofocus`.

Os modais de criação vivem no DOM desde o carregamento da página, apenas ocultos.
O navegador guarda o candidato a autofocus e só o processa quando o elemento passa
a ser renderizado — ou seja, ao abrir o modal. Como se chega lá por clique, o foco
já está no botão, e o navegador recusa:

    Autofocus processing was blocked because a document already has a
    focused element.

O resultado era o pior dos dois mundos: aviso no console e campo sem foco, com o GM
tendo de clicar para digitar. `autofocus` simplesmente não é a ferramenta certa
para um elemento que já está no documento antes de aparecer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
DOCKING = ROOT / "static/js/ui/modals/modal-docking.js"


def _templates() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def test_no_template_uses_the_autofocus_attribute():
    offenders: list[str] = []
    for path in _templates():
        source = path.read_text(encoding="utf-8")
        # ``data-modal-autofocus`` contém a palavra; casa só o atributo isolado
        if re.search(r"(?<!-)\bautofocus\b(?!-)", source.replace("data-modal-autofocus", "")):
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "use data-modal-autofocus: o atributo nativo é bloqueado ao abrir modal por clique "
        f"({offenders})"
    )


def test_the_marker_is_actually_used_somewhere():
    """Se ninguém marca campo nenhum, o teste acima passa sem guardar nada."""
    marked = [
        path
        for path in _templates()
        if "data-modal-autofocus" in path.read_text(encoding="utf-8")
    ]
    assert marked, "nenhum modal marca o campo inicial"


def test_opening_a_floating_modal_focuses_the_marked_field():
    source = DOCKING.read_text(encoding="utf-8")

    show = source.split("function showFloatingModal", 1)[1].split("function ", 1)[0]
    assert "focusInitialField(modal)" in show, "abrir o modal precisa dar o foco"

    focus = source.split("function focusInitialField", 1)[1].split("\n        }", 1)[0]
    assert '"[data-modal-autofocus]"' in focus
    # Um elemento que ainda não foi renderizado não aceita foco: precisa esperar o
    # frame em que o modal deixa de estar oculto.
    assert "requestAnimationFrame" in focus
    assert "preventScroll: true" in focus, "focar não pode fazer a página pular"
    # O modal pode ser fechado no mesmo instante em que o frame chega.
    assert "if (modal.hidden" in focus


@pytest.mark.parametrize(
    "modal_id",
    ["actor-create-", "item-create-", "actor-folder-create-", "journal-folder-create-"],
)
def test_creation_modals_still_mark_their_first_field(modal_id: str):
    """Estes são os que se abre para digitar um nome imediatamente."""
    source = (TEMPLATES / "pages/game/index.html").read_text(encoding="utf-8")
    block = source.split(f'data-modal-id="{modal_id}', 1)
    assert len(block) == 2, f"modal {modal_id} não encontrado"
    # até o próximo modal, ou o fim do arquivo
    body = re.split(r'data-modal-id="', block[1], maxsplit=1)[0]
    assert "data-modal-autofocus" in body, f"{modal_id} abre sem foco no campo de nome"
