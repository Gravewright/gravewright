"""Mexer numa aba não pode jogar a pessoa de volta para a primeira.

``bindHtmlSheet`` religa a ficha inteira sempre que o dado muda de forma que o
host precise reprocessar — e ``wireTabs`` terminava ativando ``tabs[0]`` sem olhar
o que já estava ativo. O efeito: qualquer alteração feita na aba 2 devolvia a
pessoa para a aba 1, no meio da ação. Parecia que a ficha inteira tinha
recarregado, e foi diagnosticado como "submit" por três rodadas.

Numa recarga completa (``renderHtmlSheet``) o DOM é trocado e nenhuma aba fica
ativa — por isso a aba é lembrada antes e restaurada depois.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "static/js/sdk/gravewright-sdk.js"
RENDERER = ROOT / "static/js/sheets/actors/actor-sheet-renderer.js"


def test_rebinding_keeps_the_tab_the_user_is_on():
    source = SDK.read_text(encoding="utf-8")
    tabs = source.split("function wireTabs", 1)[1].split("\n    }", 1)[0]

    assert "activate(tabs[0].dataset.tab);" not in tabs, "ativar a primeira sempre é o bug"
    assert 'tabs.find((tab) => tab.classList.contains("is-active"))' in tabs
    assert "activate((current || tabs[0]).dataset.tab)" in tabs, (
        "sem aba ativa no DOM (primeira montagem) a primeira continua sendo o padrão"
    )


def test_a_full_reload_restores_the_tab_too():
    """Subir uma imagem na aba de token recarrega a ficha — e era a própria ação
    que expulsava a pessoa da aba onde estava."""
    source = RENDERER.read_text(encoding="utf-8")
    render = source.split("async function renderHtmlSheet", 1)[1].split("\n  }", 1)[0]

    assert '[data-tab].is-active' in render, "a aba precisa ser lembrada antes"
    assert render.index("abaAtiva") < render.index("root.innerHTML = html"), (
        "lembrar depois de trocar o DOM não lembra nada"
    )
    assert '?.click()' in render, "reusar o ativador do host evita duas verdades sobre o estado"
