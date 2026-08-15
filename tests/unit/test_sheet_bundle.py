"""O pacote que a ficha recebe para se desenhar.

Nenhum teste montava um bundle, e a suíte inteira passou com um `NameError`
dentro de `build_bundle`: o erro só aparecia ao abrir a ficha de um token no
navegador. São dois construtores para a mesma dataclass, o do ator e o do
token desvinculado -, e é fácil um crescer um campo que o outro não preenche.
"""

from __future__ import annotations

import pytest

from app.engine.sheets.actor_sheet_service import (
    ActorSheetBundle,
    ActorSheetService,
    action_dialogs,
)
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService


ACTIONS = {
    "roll.trait.spirit": {
        "type": "roll",
        "formula": "acing(6)",
        "dialog": {
            "enabled": True,
            "titleKey": "sw.ui.spirit",
            "fields": [{"id": "purpose", "type": "segmented", "labelKey": "sw.ui.purpose"}],
        },
    },
    "roll.initiative": {"type": "roll", "formula": "draw(54)"},
    "item.describe": {"type": "chat", "label": "@item.name"},
    "roll.hidden": {"type": "roll", "formula": "acing(6)", "dialog": {"enabled": False}},
}

CATALOG = {"sw.ui.spirit": "Espírito", "sw.ui.purpose": "Para quê"}


# --- os diálogos que viajam -------------------------------------------------


def test_only_the_actions_that_ask_send_a_dialog():
    dialogs = action_dialogs(ACTIONS, CATALOG)
    assert set(dialogs) == {"roll.trait.spirit"}, "ação sem diálogo não ocupa espaço"


def test_the_dialog_arrives_translated():
    dialog = action_dialogs(ACTIONS, CATALOG)["roll.trait.spirit"]
    assert dialog["title"] == "Espírito"
    assert dialog["fields"][0]["label"] == "Para quê"


def test_the_formula_never_travels():
    """O resultado é resolvido no servidor. Mandar a fórmula convidaria um
    cliente a discutir o total."""
    for dialog in action_dialogs(ACTIONS, CATALOG).values():
        assert "formula" not in dialog


def test_a_system_with_no_actions_sends_nothing():
    assert action_dialogs({}, CATALOG) == {}
    assert action_dialogs(None, CATALOG) == {}


# --- os dois construtores ---------------------------------------------------

TOKEN = {
    "id": "tok_1",
    "scene_id": "scene_1",
    "actor_id": "act_1",
    "name": "Bandido",
    "token_asset_url": None,
    "actor_link_mode": "unlinked",
    "overrides": {},
}
ACTOR = {
    "id": "act_1",
    "name": "Bandido",
    "type": "extra",
    "campaign_id": "camp_1",
    "system_id": "sw",
    "status": "active",
}


def _token_service(monkeypatch) -> TokenInstanceSheetService:
    service = TokenInstanceSheetService.__new__(TokenInstanceSheetService)
    monkeypatch.setattr(service, "_load", lambda **_: (TOKEN, ACTOR, {"id": "camp_1"}), False)
    monkeypatch.setattr(
        service, "_ensure_instance", lambda **_: {"name": "Bandido", "version": 3, "data": {}}, False
    )
    monkeypatch.setattr(service, "_can_control_token", lambda **_: True, False)
    monkeypatch.setattr(service, "_project_instance", lambda **_: {"bars": {}}, False)

    class _Systems:
        get_active_manifest = staticmethod(lambda _: None)

    service.systems = _Systems()
    return service


def test_a_token_sheet_bundle_can_actually_be_built(monkeypatch):
    """O construtor do token é o que quebrou: ele monta a mesma dataclass do
    ator e passava um nome que não existia no escopo."""
    bundle = _token_service(monkeypatch).build_bundle(token_id="tok_1", user_id="u1")

    assert isinstance(bundle, ActorSheetBundle)
    assert bundle.token_id == "tok_1"
    assert bundle.dialogs == {}, "sem sistema ativo não há diálogo a enviar"


def test_both_builders_fill_every_field_of_the_bundle():
    """A dataclass não tem valor padrão para `dialogs` de propósito: um
    construtor que esqueça o campo falha na construção, não em produção."""
    import dataclasses

    required = {
        f.name
        for f in dataclasses.fields(ActorSheetBundle)
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
    }
    assert "dialogs" in required

    import inspect

    for builder in (ActorSheetService.build_bundle, TokenInstanceSheetService.build_bundle):
        source = inspect.getsource(builder)
        missing = [name for name in required if f"{name}=" not in source]
        assert not missing, f"{builder.__qualname__} não preenche: {sorted(missing)}"


@pytest.mark.parametrize(
    "service_cls", [ActorSheetService, TokenInstanceSheetService], ids=["actor", "token"]
)
@pytest.mark.parametrize("field_name", ["dialogs", "layout", "sheet", "data"])
def test_the_bundle_reaches_the_client(service_cls, field_name):
    """`to_dict` é o que vira JSON. Um campo que fica de fora existe no servidor
    e não chega em lugar nenhum.

    Os dois serviços têm de responder igual: enquanto cada um serializava a sua
    cópia, a do token perdeu `dialogs` (rolagem sem opções quando a ficha vinha
    de um token) e `token_link_mode` (edição de token vinculado escrita numa
    cópia local em vez do ator, e a ficha parava de ver o que era posto nele).
    """
    service = service_cls.__new__(service_cls)
    bundle = ActorSheetBundle(
        actor_id="a1",
        campaign_id="c1",
        system_id="sw",
        name="Aria",
        type="character",
        version=1,
        can_edit=True,
        layout=None,
        sheet=None,
        dialogs={"roll.trait.spirit": {"fields": []}},
        data={},
        portrait_url=None,
        token_url=None,
        summary={},
        token_id="tok_1",
        token_link_mode="linked",
    )
    payload = service.to_dict(bundle)
    assert field_name in payload
    assert payload["actor"]["token_link_mode"] == "linked"
