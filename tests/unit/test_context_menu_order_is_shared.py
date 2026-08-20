"""As quatro abas de diretório abrem o mesmo menu, na mesma ordem.

Atores, Itens, Diários e Cenas são quatro painéis com a mesma forma, e o menu
de botão direito é a principal via de ação em todos. Quando a ordem diverge, a
memória muscular vira armadilha: o slot que abre uma ficha numa aba passa a
apagar ou a jogar uma cena na mesa na outra.

Cada aba mora num arquivo próprio, então nada além deste teste impede a ordem
de derivar de novo na próxima mexida.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MENUS = {
    "ator": ("static/js/ui/context-menu/actor-context-menu.js", "openActorMenu", "openActorFolderMenu"),
    "item": ("static/js/ui/context-menu/item-context-menu.js", "openItemMenu", "openItemFolderMenu"),
    "diário": ("static/js/ui/context-menu/journal-context-menu.js", "openJournalMenu", "openJournalFolderMenu"),
    "cena": ("static/js/scenes/scene-context-menu.js", "CARD", "openFolderMenu"),
}

# Slot de cada item. O que não está aqui é submenu de confirmação, que não conta
# como item de topo.
SLOTS = {
    # entrada: olhar -> agir no domínio -> ajustar -> apagar
    "ctxTokenOpenSheet": "abrir", "ctxItemOpen": "abrir",
    "ctxJournalOpen": "abrir", "sceneMenuNavigate": "abrir",
    "ctxSheetAddToScene": "domínio", "sceneMenuActivate": "domínio",
    "ctxActorPermissions": "ajustar", "ctxJournalOwner": "ajustar",
    "sceneMenuConfigure": "ajustar",
    "ctxActorDelete": "apagar", "ctxItemDelete": "apagar",
    "ctxJournalDelete": "apagar", "sceneMenuRemove": "apagar",
    # pasta: criar dentro -> agir no domínio -> mexer na pasta -> apagar
    "ctxActorCreate": "criar", "ctxItemCreate": "criar",
    "ctxJournalCreate": "criar", "sceneMenuNewInFolder": "criar",
    "ctxActorFolderAddToScene": "domínio",
    "ctxFolderEdit": "editar",
    "ctxActorFolderAddSubfolder": "subpasta",
    "ctxActorFolderDelete": "apagar", "ctxJournalFolderDelete": "apagar",
    "sceneMenuFolderDelete": "apagar",
}

ENTRY_ORDER = ["abrir", "domínio", "ajustar", "apagar"]
FOLDER_ORDER = ["criar", "domínio", "editar", "subpasta", "apagar"]


def _body(source: str, function_name: str) -> str:
    if function_name == "CARD":
        start = source.index("const items = [];")
        return source[start : source.index("menu.show(", start)]
    start = source.index(f"function {function_name}(")
    return source[start : source.index("\n    }\n", start)]


def _slots(body: str) -> list[str]:
    found = []
    pattern = r'(?:text|label):\s*(?:body\.dataset\.(\w+)|label\("(\w+)"|"([^"]+)")'
    for match in re.finditer(pattern, body):
        key = match.group(1) or match.group(2) or match.group(3)
        slot = SLOTS.get(key)
        # Um item repetido é o submenu de confirmação do anterior, não um slot novo.
        if slot and (not found or found[-1] != slot):
            found.append(slot)
    return found


def _expected(observed: list[str], canonical: list[str]) -> list[str]:
    """A ordem canônica reduzida aos slots que esta aba realmente tem.

    Nem toda aba preenche todos: só ator adiciona à cena, e grupo de cena não
    aninha, então cena não tem subpasta.
    """
    return [slot for slot in canonical if slot in observed]


def test_every_directory_tab_opens_the_same_entry_menu_order():
    for tab, (path, entry_fn, _) in MENUS.items():
        source = (ROOT / path).read_text(encoding="utf-8")
        observed = _slots(_body(source, entry_fn))
        assert observed, f"{tab}: nenhum item reconhecido — o menu mudou de forma?"
        assert observed == _expected(observed, ENTRY_ORDER), (
            f"o menu de entrada de {tab} saiu da ordem compartilhada: {observed}"
        )
        assert observed[-1] == "apagar", f"{tab}: apagar tem de ser o último"


def test_every_directory_tab_opens_the_same_folder_menu_order():
    for tab, (path, _, folder_fn) in MENUS.items():
        source = (ROOT / path).read_text(encoding="utf-8")
        observed = _slots(_body(source, folder_fn))
        assert observed, f"{tab}: nenhum item reconhecido — o menu mudou de forma?"
        assert observed == _expected(observed, FOLDER_ORDER), (
            f"o menu de pasta de {tab} saiu da ordem compartilhada: {observed}"
        )
        assert observed[0] == "criar", (
            f"{tab}: criar dentro da pasta é a razão de abrir esse menu; vem primeiro"
        )
        assert observed[-1] == "apagar", f"{tab}: apagar tem de ser o último"


def test_creating_inside_a_folder_targets_that_folder():
    """O item "criar" tem de levar a pasta junto, senão cria na raiz e o menu
    mente sobre o que faz."""
    esperado = {
        "static/js/ui/context-menu/actor-context-menu.js": "openActorCreateModal?.({ campaignId, folderId })",
        "static/js/ui/context-menu/item-context-menu.js": "openItemCreateModal?.({ campaignId, folderId })",
        "static/js/ui/context-menu/journal-context-menu.js": "detail: { campaignId, folderId }",
        "static/js/scenes/scene-context-menu.js": "openCreateModal(roomId, folderId)",
    }
    for path, trecho in esperado.items():
        assert trecho in (ROOT / path).read_text(encoding="utf-8"), path
