"""O que um cartão de rolagem consegue dizer sozinho.

Um sistema descreve o cartão em `mappings/chat-cards.gw.json` e não roda código
nenhum. Estes fixam o que a apresentação oferece para ele: graus de sucesso a
partir de um alvo declarado, os dados legíveis, e o detalhamento que continua
disponível mesmo quando o sistema mapeia o próprio cartão.
"""

from __future__ import annotations

import pytest

from app.engine.rolls.roll_presentation_service import (
    RollPresentationService,
    _all_ones,
    _dice_summary,
    _outcome,
    _results_summary,
    _rich_text_plain,
)


def _context(total, groups=None, modifier=0) -> dict:
    return {
        "roll": {"total": total, "groups": groups or [], "modifier": modifier},
        "input": {},
    }


def test_rich_item_description_becomes_readable_chat_text():
    document = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Primeiro efeito."}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Segundo efeito."}]},
        ],
    }
    assert _rich_text_plain(document) == "Primeiro efeito.\nSegundo efeito."


# --- graus de sucesso -------------------------------------------------------


@pytest.mark.parametrize(
    ("total", "steps", "tone"),
    [
        (3, "", "failure"),
        (4, "", "success"),
        (7, "", "success"),
        (8, 1, "success"),
        (12, 2, "success"),
        (16, 3, "success"),
    ],
)
def test_a_target_and_a_step_produce_degrees_of_success(total, steps, tone):
    outcome = _outcome({"target": 4, "step": 4}, _context(total))
    assert outcome["steps"] == steps
    assert outcome["tone"] == tone
    assert outcome["margin"] == total - 4


def test_zero_steps_is_empty_so_the_line_disappears():
    """Uma linha com valor vazio não é desenhada. É o que evita o cartão
    anunciar 'Aumentos: 0' em toda rolagem que só passou raspando."""
    assert _outcome({"target": 4, "step": 4}, _context(5))["steps"] == ""


def test_a_card_without_a_step_still_says_pass_or_fail():
    assert _outcome({"target": 4}, _context(9))["tone"] == "success"
    assert _outcome({"target": 4}, _context(2))["tone"] == "failure"


def test_the_target_can_come_from_the_roll_dialog():
    context = _context(9)
    context["input"] = {"tn": 8}
    assert _outcome({"target": "@input.tn", "step": 4}, context)["margin"] == 1


def test_a_card_that_declares_no_outcome_gets_none():
    assert _outcome(None, _context(9)) is None
    assert _outcome({"step": 4}, _context(9)) is None, "sem alvo não há o que medir"


# --- os dados ---------------------------------------------------------------


def test_the_dice_read_as_one_line():
    groups = [
        {"notation": "1d8!>=8", "results": [8, 3]},
        {"notation": "1d6!>=6", "results": [2]},
    ]
    assert _dice_summary(groups) == "1d8!>=8 [8, 3] · 1d6!>=6 [2]"


def test_results_carry_no_notation():
    """O que se lê na face de um cartão é o número que saiu. A notação que o
    produziu é fórmula, e fórmula fica no detalhamento."""
    groups = [
        {"notation": "1d8!>=8", "results": [8, 3]},
        {"notation": "1d6!>=6", "results": [2]},
    ]
    summary = _results_summary(groups)
    assert summary == "8, 3 · 2"
    assert "d8" not in summary and "!" not in summary and ">=" not in summary


@pytest.mark.parametrize(
    ("groups", "expected"),
    [
        ([{"notation": "d8", "results": [1]}, {"notation": "d6", "results": [1]}], True),
        ([{"notation": "d8", "results": [1]}, {"notation": "d6", "results": [4]}], False),
        ([{"notation": "d8", "results": [1, 3]}], False),
        ([], False),
    ],
)
def test_all_ones_is_reported_without_being_named(groups, expected):
    """O motor relata o fato; quem chama isso de falha crítica é o sistema."""
    assert _all_ones(groups) is expected


# --- o cartão inteiro -------------------------------------------------------


def _render(spec: dict, *, total: int, groups: list[dict], monkeypatch) -> dict:
    service = RollPresentationService()
    monkeypatch.setattr(service.rules, "get_chat_card_mappings", lambda _: {"cards": {"t": spec}})
    context = service._context(
        metadata={},
        actor_name="Aria",
        label="Teste",
        expression="acing(8)",
        groups=groups,
        modifier=2,
        total=total,
    )
    return service._render_chat_card(system_id="sw", card_id="t", context=context, catalog={})


def test_the_card_says_which_system_it_belongs_to(monkeypatch):
    """O core desenha a estrutura; a aparência é da folha de estilo do pacote,
    que é carregada na página inteira. Sem esta marca, o único escopo possível
    para um pacote seria pintar o cartão de todos os outros sistemas junto."""
    card = _render({"title": "Teste"}, total=9, groups=[], monkeypatch=monkeypatch)
    assert card["system"] == "sw"


def test_a_mapped_card_keeps_the_dice_behind_it(monkeypatch):
    """Declarar um cartão trocava o detalhamento por um título. Os dados são
    metade da leitura: qual explodiu, qual deu 1."""
    groups = [{"notation": "1d8!>=8", "results": [8, 3], "subtotal": 11}]
    card = _render({"title": "Teste"}, total=13, groups=groups, monkeypatch=monkeypatch)

    assert card["groups"] == groups
    assert card["modifier"] == 2


def test_a_card_can_turn_the_dice_off(monkeypatch):
    card = _render(
        {"title": "Teste", "dice": False},
        total=13,
        groups=[{"notation": "1d8", "results": [8], "subtotal": 8}],
        monkeypatch=monkeypatch,
    )
    assert "groups" not in card


def test_the_outcome_reaches_the_lines_and_the_tone(monkeypatch):
    spec = {
        "title": "Teste",
        "outcome": {"target": 4, "step": 4},
        "lines": [
            {"label": "Aumentos", "value": "@outcome.steps"},
            {"label": "Dados", "value": "@roll.dice"},
        ],
    }
    card = _render(
        spec, total=12, groups=[{"notation": "1d8!>=8", "results": [8, 4]}], monkeypatch=monkeypatch
    )

    assert card["tone"] == "success"
    assert {"label": "Aumentos", "value": "2"} in card["lines"]
    assert {"label": "Dados", "value": "1d8!>=8 [8, 4]"} in card["lines"]


def test_a_failed_roll_drops_the_raises_line(monkeypatch):
    spec = {
        "title": "Teste",
        "outcome": {"target": 4, "step": 4},
        "lines": [{"label": "Aumentos", "value": "@outcome.steps"}],
    }
    card = _render(spec, total=2, groups=[], monkeypatch=monkeypatch)

    assert card["tone"] == "failure"
    assert card["lines"] == []


def test_critical_failure_overrides_total_and_has_a_localizable_status(monkeypatch):
    spec = {
        "title": "Teste",
        "outcome": {"target": 4, "step": 4},
        "statusKeys": {
            "success": "roll.success",
            "failure": "roll.failure",
            "criticalFailure": "roll.critical",
        },
        "lines": [{"label": "Aumentos", "value": "@outcome.steps"}],
    }
    card = _render(
        spec,
        total=8,
        groups=[{"results": [1]}, {"results": [1]}],
        monkeypatch=monkeypatch,
    )

    assert card["tone"] == "critical-failure"
    assert card["statusKey"] == "roll.critical"
    assert card["lines"] == []


def test_action_locale_key_becomes_the_specific_card_title(monkeypatch):
    service = RollPresentationService()
    monkeypatch.setattr(
        service.rules,
        "get_chat_card_mappings",
        lambda _system: {"cards": {"trait": {"lines": []}}},
    )
    context = service._context(
        metadata={"actionId": "roll.trait.strength"},
        actor_name="Conan",
        label="example.ui.strength_check",
        expression="1d8",
        groups=[{"results": [6]}],
        modifier=0,
        total=6,
    )
    card = service._render_chat_card(
        system_id="sw",
        card_id="trait",
        context=context,
        catalog={"example.ui.strength_check": "Teste de Força"},
    )

    assert card["title"] == "Teste de Força"
    assert card["titleKey"] == "example.ui.strength_check"
