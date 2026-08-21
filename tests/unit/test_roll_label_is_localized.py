"""O rótulo da rolagem é uma CHAVE do ruleset, e precisa ser traduzido.

Em `actions.gw.json` a ação de força tem `"label": "dnd5e.ui.teste.de.forca"`.
O serviço só resolvia `@template` -- chave de locale passava crua, e a chave
aparecia no chat, na bandeja de dados e no tooltip, em vez de "Teste de Força".

O locale do pacote já existia e já era usado para montar os diálogos das ações:
faltava só chegar até aqui.
"""

from __future__ import annotations

from app.engine.sheets.sheet_action_service import SheetActionService


def test_a_ruleset_key_becomes_the_translated_label(monkeypatch):
    service = SheetActionService()
    monkeypatch.setattr(
        type(service.locales), "get_locale",
        lambda self, package_id, locale: (
            {"dnd5e.ui.teste.de.forca": "Teste de Força"} if locale == "pt-BR"
            else {"dnd5e.ui.teste.de.forca": "Strength Check"}
        ),
    )

    assert service._localized("dnd5e", "dnd5e.ui.teste.de.forca", "pt-BR") == "Teste de Força"
    assert service._localized("dnd5e", "dnd5e.ui.teste.de.forca", "en") == "Strength Check"


def test_free_text_and_empty_labels_pass_through(monkeypatch):
    """Nem todo rótulo é chave: um texto escrito à mão não pode virar vazio."""
    service = SheetActionService()
    monkeypatch.setattr(type(service.locales), "get_locale", lambda self, p, l: {"a": "b"})

    assert service._localized("dnd5e", "Ataque Modelo", "pt-BR") == "Ataque Modelo"
    assert service._localized("dnd5e", "", "pt-BR") == ""
    assert service._localized("dnd5e", None, "pt-BR") == ""


def test_the_endpoint_hands_the_locale_to_the_action():
    """Sem isto o serviço traduz para o idioma padrão do servidor, não para o
    do jogador que rolou."""
    from pathlib import Path

    fonte = Path(__file__).resolve().parents[2] / "app/actions/game/manage_actors.py"
    corpo = fonte.read_text(encoding="utf-8")
    chamada = corpo.split("sheet_action_service.execute(", 1)[1]
    execucao = chamada[: chamada.index(chr(10) + "    )")]
    assert 'locale=view_context(cookies)["locale"]' in execucao
